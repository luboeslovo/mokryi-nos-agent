import asyncio
import csv
import json
import os
import re
import sqlite3
import time
from datetime import datetime

from playwright.async_api import async_playwright


# ============================================================
# ПУТИ
# ============================================================

PROJECT_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

AUTH_FILE = os.path.join(
    PROJECT_DIR,
    "auth.json"
)

CHECKS_FILE = os.path.join(
    PROJECT_DIR,
    "checks_raw.csv"
)

DB_FILE = os.path.join(
    PROJECT_DIR,
    "check_items.sqlite"
)


# ============================================================
# CRM
# ============================================================

BASE_URL = "https://it.mokryinos.ru"

CONCURRENCY = 10
RETRIES = 3


class AuthExpired(Exception):
    pass


# ============================================================
# БАЗА
# ============================================================

def open_database():

    connection = sqlite3.connect(
        DB_FILE
    )

    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS processed_checks (
            check_id TEXT PRIMARY KEY,
            check_number TEXT,
            item_count INTEGER,
            processed_at TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS items (
            crm_item_id TEXT,
            check_id TEXT,
            check_number TEXT,
            date TEXT,
            customer TEXT,
            check_type TEXT,
            product_id TEXT,
            product_name TEXT,
            unit TEXT,
            quantity REAL,
            amount_before_discount REAL,
            discount REAL,
            amount REAL,
            signed_amount REAL
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS errors (
            check_id TEXT PRIMARY KEY,
            check_number TEXT,
            error TEXT,
            updated_at TEXT
        )
        """
    )

    connection.commit()

    return connection


# ============================================================
# ЧЕКИ
# ============================================================

def load_checks():

    with open(
        CHECKS_FILE,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        return list(
            csv.DictReader(file)
        )


def get_processed_ids(connection):

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT check_id
        FROM processed_checks
        """
    )

    return {
        str(row[0])
        for row in cursor.fetchall()
    }


# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

def to_float(value):

    if value is None:
        return 0.0

    if isinstance(
        value,
        (int, float)
    ):
        return float(value)

    text = str(value).strip()

    if not text:
        return 0.0

    text = (
        text
        .replace(" ", "")
        .replace(",", ".")
    )

    try:
        return float(text)

    except ValueError:
        return 0.0


def first_value(
    data,
    *keys
):

    for key in keys:

        if key in data:

            value = data[key]

            if value is not None:
                return value

    return ""


# ============================================================
# РАСПАКОВЫВАЕМ AJAX-ОТВЕТ CRM
# ============================================================

def unwrap_crm_response(text):

    try:

        payload = json.loads(
            text
        )

    except json.JSONDecodeError:

        # Если CRM вдруг вернула обычный HTML,
        # просто работаем с ним напрямую.
        return text

    if isinstance(
        payload,
        dict
    ):

        content = payload.get(
            "content"
        )

        if isinstance(
            content,
            str
        ):
            return content

    if isinstance(
        payload,
        str
    ):
        return payload

    return text


# ============================================================
# PARSE localdata
# ============================================================

def parse_items(
    response_text,
    check
):

    text = unwrap_crm_response(
        response_text
    )

    match = re.search(
        r"localdata\s*:\s*(\[.*?\])\s*\};",
        text,
        re.DOTALL
    )

    if not match:

        raise RuntimeError(
            "Не найден localdata"
        )

    raw = match.group(1)

    try:

        raw_items = json.loads(
            raw
        )

    except Exception as error:

        preview = (
            raw[:300]
            .replace(
                "\n",
                " "
            )
        )

        raise RuntimeError(
            "Не удалось разобрать localdata. "
            f"Начало: {preview} | "
            f"Ошибка: {error}"
        )

    if not isinstance(
        raw_items,
        list
    ):

        raise RuntimeError(
            "localdata имеет неправильный формат"
        )

    result = []

    is_return = (
        "возврат"
        in check.get(
            "type",
            ""
        ).lower()
    )

    for item in raw_items:

        crm_item_id = str(
            first_value(
                item,
                "id",
                "check_kkm_item_id",
                "checkKkmItem_id"
            )
        )

        product_id = str(
            first_value(
                item,
                "nomenclature_measure_item_id",
                "nomenclature_id",
                "product_id"
            )
        )

        product_name = str(
            first_value(
                item,
                "nomenclature_name",
                "product_name",
                "name"
            )
        )

        unit = str(
            first_value(
                item,
                "measure_name",
                "unit",
                "measure"
            )
        )

        quantity = to_float(
            first_value(
                item,
                "quantity",
                "count"
            )
        )

        amount_before_discount = to_float(
            first_value(
                item,
                "amount_before_discount",
                "amountBeforeDiscount"
            )
        )

        discount = to_float(
            first_value(
                item,
                "discount",
                "discount_amount"
            )
        )

        amount = to_float(
            first_value(
                item,
                "amount",
                "final_amount",
                "sum"
            )
        )

        signed_amount = (
            -amount
            if is_return
            else amount
        )

        result.append(
            {
                "crm_item_id":
                    crm_item_id,

                "check_id":
                    check["check_id"],

                "check_number":
                    check["number"],

                "date":
                    check["date"],

                "customer":
                    check["customer"],

                "check_type":
                    check["type"],

                "product_id":
                    product_id,

                "product_name":
                    product_name,

                "unit":
                    unit,

                "quantity":
                    quantity,

                "amount_before_discount":
                    amount_before_discount,

                "discount":
                    discount,

                "amount":
                    amount,

                "signed_amount":
                    signed_amount,
            }
        )

    return result


# ============================================================
# СКАЧИВАЕМ ОДИН ЧЕК
# ============================================================

async def download_check(
    context,
    semaphore,
    check
):

    check_id = check[
        "check_id"
    ]

    url = (
        f"{BASE_URL}/checkKkm/"
        f"{check_id}"
        f"?_={int(time.time() * 1000)}"
    )

    async with semaphore:

        last_error = None

        for attempt in range(
            1,
            RETRIES + 1
        ):

            try:

                response = await (
                    context.request.get(
                        url,
                        headers={
                            "X-Requested-With":
                                "XMLHttpRequest"
                        },
                        timeout=30000
                    )
                )

                if (
                    "/login"
                    in response.url.lower()
                ):

                    raise AuthExpired()

                if response.status != 200:

                    raise RuntimeError(
                        f"HTTP "
                        f"{response.status}"
                    )

                text = await response.text()

                items = parse_items(
                    text,
                    check
                )

                return (
                    check,
                    items,
                    None
                )

            except AuthExpired:
                raise

            except Exception as error:

                last_error = str(
                    error
                )

                if attempt < RETRIES:

                    await asyncio.sleep(
                        attempt
                    )

        return (
            check,
            None,
            last_error
        )


# ============================================================
# СОХРАНЕНИЕ УСПЕХА
# ============================================================

def save_success(
    connection,
    check,
    items
):

    cursor = connection.cursor()

    check_id = check[
        "check_id"
    ]

    cursor.execute(
        """
        DELETE FROM items
        WHERE check_id = ?
        """,
        (check_id,)
    )

    for item in items:

        cursor.execute(
            """
            INSERT INTO items (
                crm_item_id,
                check_id,
                check_number,
                date,
                customer,
                check_type,
                product_id,
                product_name,
                unit,
                quantity,
                amount_before_discount,
                discount,
                amount,
                signed_amount
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item["crm_item_id"],
                item["check_id"],
                item["check_number"],
                item["date"],
                item["customer"],
                item["check_type"],
                item["product_id"],
                item["product_name"],
                item["unit"],
                item["quantity"],
                item["amount_before_discount"],
                item["discount"],
                item["amount"],
                item["signed_amount"],
            )
        )

    cursor.execute(
        """
        INSERT OR REPLACE INTO processed_checks (
            check_id,
            check_number,
            item_count,
            processed_at
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            check_id,
            check["number"],
            len(items),
            datetime.now().isoformat(
                timespec="seconds"
            ),
        )
    )

    # Если раньше этот чек лежал в errors,
    # после успешной загрузки ошибка удаляется.

    cursor.execute(
        """
        DELETE FROM errors
        WHERE check_id = ?
        """,
        (check_id,)
    )

    connection.commit()


# ============================================================
# СОХРАНЕНИЕ ОШИБКИ
# ============================================================

def save_error(
    connection,
    check,
    error
):

    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT OR REPLACE INTO errors (
            check_id,
            check_number,
            error,
            updated_at
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            check["check_id"],
            check["number"],
            error,
            datetime.now().isoformat(
                timespec="seconds"
            ),
        )
    )

    connection.commit()


# ============================================================
# MAIN
# ============================================================

async def main():

    connection = open_database()

    checks = load_checks()

    processed_ids = get_processed_ids(
        connection
    )

    pending = [
        check
        for check in checks
        if str(
            check["check_id"]
        )
        not in processed_ids
    ]

    print()
    print("=" * 70)

    print(
        f"Всего чеков: "
        f"{len(checks)}"
    )

    print(
        f"Уже обработано: "
        f"{len(processed_ids)}"
    )

    print(
        f"Нужно обработать: "
        f"{len(pending)}"
    )

    print("=" * 70)

    if not pending:

        print(
            "Новых чеков для товаров нет."
        )

        connection.close()
        return

    semaphore = asyncio.Semaphore(
        CONCURRENCY
    )

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True
        )

        context = await browser.new_context(
            storage_state=AUTH_FILE
        )

        response = await context.request.get(
            f"{BASE_URL}/checkKkm/index",
            timeout=30000
        )

        if "/login" in response.url.lower():

            print()
            print(
                "Авторизация CRM истекла."
            )

            await context.close()
            await browser.close()

            connection.close()
            return

        print()
        print(
            "Авторизация в порядке."
        )

        print(
            "Скачиваю товары..."
        )
        print()

        tasks = [
            asyncio.create_task(
                download_check(
                    context,
                    semaphore,
                    check
                )
            )
            for check in pending
        ]

        completed = 0
        successful = 0
        failed = 0
        total_items = 0

        try:

            for task in asyncio.as_completed(
                tasks
            ):

                try:

                    (
                        check,
                        items,
                        error
                    ) = await task

                except AuthExpired:

                    print()
                    print(
                        "Авторизация CRM "
                        "истекла."
                    )

                    for pending_task in tasks:

                        if not pending_task.done():
                            pending_task.cancel()

                    break

                completed += 1

                if error is None:

                    save_success(
                        connection,
                        check,
                        items
                    )

                    successful += 1

                    total_items += len(
                        items
                    )

                    print(
                        f"{completed}/"
                        f"{len(pending)}"
                        f" | "
                        f"{check['number']}"
                        f" | "
                        f"{len(items)} товаров"
                    )

                else:

                    save_error(
                        connection,
                        check,
                        error
                    )

                    failed += 1

                    print(
                        f"{completed}/"
                        f"{len(pending)}"
                        f" | "
                        f"{check['number']}"
                        f" | ОШИБКА: "
                        f"{error}"
                    )

        finally:

            await context.close()
            await browser.close()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM processed_checks
        """
    )

    processed_total = (
        cursor.fetchone()[0]
    )

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM items
        """
    )

    items_total = (
        cursor.fetchone()[0]
    )

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM errors
        """
    )

    errors_total = (
        cursor.fetchone()[0]
    )

    print()
    print("=" * 70)

    print(
        f"Успешно сейчас: "
        f"{successful}"
    )

    print(
        f"Ошибок сейчас: "
        f"{failed}"
    )

    print(
        f"Новых строк товаров: "
        f"{total_items}"
    )

    print()

    print(
        f"Всего обработано чеков: "
        f"{processed_total}"
    )

    print(
        f"Всего строк товаров: "
        f"{items_total}"
    )

    print(
        f"Ошибок в базе: "
        f"{errors_total}"
    )

    print("=" * 70)

    connection.close()


if __name__ == "__main__":

    asyncio.run(
        main()
    )