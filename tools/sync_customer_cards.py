import asyncio
import csv
import json
import os
import sqlite3
import time
from collections import Counter
from datetime import datetime
from html.parser import HTMLParser

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
    "checks_with_customer_id.csv"
)

DB_FILE = os.path.join(
    PROJECT_DIR,
    "customer_cards.sqlite"
)

CSV_FILE = os.path.join(
    PROJECT_DIR,
    "customers.csv"
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
# HTML-ПАРСЕР КАРТОЧКИ
# ============================================================

class CustomerParser(HTMLParser):

    def __init__(self):
        super().__init__()

        self.inputs = {}
        self.selects = {}
        self.textareas = {}

        self.current_select = None
        self.current_option_value = None
        self.current_option_selected = False
        self.current_option_text = ""

        self.current_textarea = None
        self.current_textarea_text = ""

    def handle_starttag(
        self,
        tag,
        attrs
    ):

        attrs_list = attrs
        attrs = dict(attrs)

        if tag == "input":

            name = attrs.get(
                "name"
            )

            if name:

                self.inputs[name] = attrs.get(
                    "value",
                    ""
                )

        elif tag == "select":

            self.current_select = attrs.get(
                "name"
            )

        elif (
            tag == "option"
            and self.current_select
        ):

            self.current_option_value = attrs.get(
                "value",
                ""
            )

            self.current_option_selected = any(
                key == "selected"
                for key, value
                in attrs_list
            )

            self.current_option_text = ""

        elif tag == "textarea":

            self.current_textarea = attrs.get(
                "name"
            )

            self.current_textarea_text = ""

    def handle_data(
        self,
        data
    ):

        if self.current_option_value is not None:

            self.current_option_text += data

        if self.current_textarea is not None:

            self.current_textarea_text += data

    def handle_endtag(
        self,
        tag
    ):

        if (
            tag == "option"
            and self.current_option_value
            is not None
        ):

            if self.current_option_selected:

                self.selects[
                    self.current_select
                ] = {
                    "value":
                        self.current_option_value,

                    "text":
                        " ".join(
                            self.current_option_text.split()
                        ),
                }

            self.current_option_value = None
            self.current_option_selected = False
            self.current_option_text = ""

        elif tag == "select":

            self.current_select = None

        elif (
            tag == "textarea"
            and self.current_textarea
        ):

            self.textareas[
                self.current_textarea
            ] = (
                self.current_textarea_text.strip()
            )

            self.current_textarea = None
            self.current_textarea_text = ""


# ============================================================
# ПОИСК ПОЛЯ ПО СУФФИКСУ
# ============================================================

def input_value(
    parser,
    field
):

    suffix = (
        f"[{field}]"
    )

    for key, value in (
        parser.inputs.items()
    ):

        if key.endswith(suffix):

            return value or ""

    return ""


def select_value(
    parser,
    field
):

    suffix = (
        f"[{field}]"
    )

    for key, value in (
        parser.selects.items()
    ):

        if key.endswith(suffix):

            return (
                value.get(
                    "value",
                    ""
                ),
                value.get(
                    "text",
                    ""
                ),
            )

    return "", ""


def textarea_value(
    parser,
    field
):

    suffix = (
        f"[{field}]"
    )

    for key, value in (
        parser.textareas.items()
    ):

        if key.endswith(suffix):

            return value or ""

    return ""


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
        CREATE TABLE IF NOT EXISTS customers (
            customer_id TEXT PRIMARY KEY,
            check_name TEXT,
            name TEXT,
            lastname TEXT,
            birthdate TEXT,
            sex_id TEXT,
            sex_name TEXT,
            phone TEXT,
            email TEXT,
            loyalty_id TEXT,
            loyalty_name TEXT,
            note TEXT,
            delivery_address TEXT,
            resolved_check_count INTEGER,
            source_title TEXT,
            updated_at TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS errors (
            customer_id TEXT PRIMARY KEY,
            error TEXT,
            attempts INTEGER,
            updated_at TEXT
        )
        """
    )

    connection.commit()

    return connection


# ============================================================
# ТЕКУЩИЕ КЛИЕНТЫ ИЗ ЧЕКОВ
# ============================================================

def load_resolved_customers():

    with open(
        CHECKS_FILE,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        rows = list(
            csv.DictReader(file)
        )

    counts = Counter()

    latest_name = {}

    for row in rows:

        if (
            row.get(
                "resolution_status"
            )
            != "resolved"
        ):
            continue

        customer_id = str(
            row.get(
                "customer_id",
                ""
            )
        ).strip()

        if not customer_id:
            continue

        counts[
            customer_id
        ] += 1

        # checks_with_customer_id.csv идёт
        # от новых чеков к старым.
        # Поэтому первое имя — самое свежее.

        if customer_id not in latest_name:

            latest_name[
                customer_id
            ] = row.get(
                "customer",
                ""
            )

    return (
        counts,
        latest_name
    )


# ============================================================
# ПАРСИНГ ОТВЕТА CRM
# ============================================================

def parse_customer_payload(
    response_text,
    customer_id,
    check_name,
    resolved_check_count
):

    payload = json.loads(
        response_text
    )

    if not isinstance(
        payload,
        dict
    ):

        raise RuntimeError(
            "Ответ карточки не является объектом"
        )

    if payload.get(
        "status"
    ) != "render":

        raise RuntimeError(
            f"Неожиданный status: "
            f"{payload.get('status')}"
        )

    content = payload.get(
        "content"
    )

    if not isinstance(
        content,
        str
    ):

        raise RuntimeError(
            "В ответе нет content"
        )

    parser = CustomerParser()

    parser.feed(
        content
    )

    sex_id, sex_name = (
        select_value(
            parser,
            "sex"
        )
    )

    loyalty_id, loyalty_name = (
        select_value(
            parser,
            "loyaltyId"
        )
    )

    delivery_address = input_value(
        parser,
        "fullAddress"
    )

    return {
        "customer_id":
            customer_id,

        "check_name":
            check_name,

        "name":
            input_value(
                parser,
                "name"
            ),

        "lastname":
            input_value(
                parser,
                "lastname"
            ),

        "birthdate":
            input_value(
                parser,
                "birthdate"
            ),

        "sex_id":
            sex_id,

        "sex_name":
            sex_name,

        "phone":
            input_value(
                parser,
                "phone"
            ),

        "email":
            input_value(
                parser,
                "email"
            ),

        "loyalty_id":
            loyalty_id,

        "loyalty_name":
            loyalty_name,

        "note":
            textarea_value(
                parser,
                "note"
            ),

        "delivery_address":
            delivery_address,

        "resolved_check_count":
            resolved_check_count,

        "source_title":
            payload.get(
                "title",
                ""
            ),

        "updated_at":
            datetime.now().isoformat(
                timespec="seconds"
            ),
    }


# ============================================================
# СКАЧИВАНИЕ ОДНОЙ КАРТОЧКИ
# ============================================================

async def download_customer(
    context,
    semaphore,
    customer_id,
    check_name,
    resolved_check_count
):

    async with semaphore:

        last_error = ""

        for attempt in range(
            1,
            RETRIES + 1
        ):

            try:

                url = (
                    f"{BASE_URL}"
                    f"/individual/individual/view/"
                    f"{customer_id}"
                    f"?_={int(time.time() * 1000)}"
                )

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
                        f"HTTP {response.status}"
                    )

                text = await (
                    response.text()
                )

                customer = (
                    parse_customer_payload(
                        text,
                        customer_id,
                        check_name,
                        resolved_check_count
                    )
                )

                return (
                    customer_id,
                    customer,
                    None,
                    attempt
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
            customer_id,
            None,
            last_error,
            RETRIES
        )


# ============================================================
# СОХРАНЕНИЕ
# ============================================================

def save_customer(
    connection,
    customer
):

    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT OR REPLACE INTO customers (
            customer_id,
            check_name,
            name,
            lastname,
            birthdate,
            sex_id,
            sex_name,
            phone,
            email,
            loyalty_id,
            loyalty_name,
            note,
            delivery_address,
            resolved_check_count,
            source_title,
            updated_at
        )
        VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?
        )
        """,
        (
            customer[
                "customer_id"
            ],
            customer[
                "check_name"
            ],
            customer[
                "name"
            ],
            customer[
                "lastname"
            ],
            customer[
                "birthdate"
            ],
            customer[
                "sex_id"
            ],
            customer[
                "sex_name"
            ],
            customer[
                "phone"
            ],
            customer[
                "email"
            ],
            customer[
                "loyalty_id"
            ],
            customer[
                "loyalty_name"
            ],
            customer[
                "note"
            ],
            customer[
                "delivery_address"
            ],
            customer[
                "resolved_check_count"
            ],
            customer[
                "source_title"
            ],
            customer[
                "updated_at"
            ],
        )
    )

    cursor.execute(
        """
        DELETE FROM errors
        WHERE customer_id = ?
        """,
        (
            customer[
                "customer_id"
            ],
        )
    )

    connection.commit()


def save_error(
    connection,
    customer_id,
    error,
    attempts
):

    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT OR REPLACE INTO errors (
            customer_id,
            error,
            attempts,
            updated_at
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            customer_id,
            error,
            attempts,
            datetime.now().isoformat(
                timespec="seconds"
            ),
        )
    )

    connection.commit()


# ============================================================
# ОБНОВЛЯЕМ ЛОКАЛЬНЫЕ СЧЁТЧИКИ
# ============================================================

def refresh_existing_counts(
    connection,
    counts,
    latest_name
):

    cursor = connection.cursor()

    for customer_id, count in (
        counts.items()
    ):

        cursor.execute(
            """
            UPDATE customers
            SET
                resolved_check_count = ?,
                check_name = ?
            WHERE customer_id = ?
            """,
            (
                count,
                latest_name.get(
                    customer_id,
                    ""
                ),
                customer_id,
            )
        )

    connection.commit()


# ============================================================
# EXPORT CSV
# ============================================================

def export_csv(
    connection
):

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            customer_id,
            check_name,
            name,
            lastname,
            birthdate,
            sex_id,
            sex_name,
            phone,
            email,
            loyalty_id,
            loyalty_name,
            note,
            delivery_address,
            resolved_check_count,
            source_title,
            updated_at
        FROM customers
        ORDER BY customer_id
        """
    )

    rows = cursor.fetchall()

    fieldnames = [
        "customer_id",
        "check_name",
        "name",
        "lastname",
        "birthdate",
        "sex_id",
        "sex_name",
        "phone",
        "email",
        "loyalty_id",
        "loyalty_name",
        "note",
        "delivery_address",
        "resolved_check_count",
        "source_title",
        "updated_at",
    ]

    with open(
        CSV_FILE,
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        writer = csv.writer(
            file
        )

        writer.writerow(
            fieldnames
        )

        writer.writerows(
            rows
        )


# ============================================================
# MAIN
# ============================================================

async def main():

    connection = open_database()

    (
        counts,
        latest_name
    ) = load_resolved_customers()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT customer_id
        FROM customers
        """
    )

    existing_ids = {
        str(row[0])
        for row in cursor.fetchall()
    }

    current_ids = set(
        counts.keys()
    )

    missing_ids = sorted(
        current_ids
        - existing_ids
    )

    print()
    print("=" * 70)

    print(
        f"Клиентов в текущих чеках: "
        f"{len(current_ids)}"
    )

    print(
        f"Карточек уже сохранено: "
        f"{len(existing_ids)}"
    )

    print(
        f"Новых карточек нужно скачать: "
        f"{len(missing_ids)}"
    )

    print("=" * 70)

    # Обновляем количество чеков
    # у уже известных клиентов.

    refresh_existing_counts(
        connection,
        counts,
        latest_name
    )

    if missing_ids:

        semaphore = asyncio.Semaphore(
            CONCURRENCY
        )

        async with async_playwright() as p:

            browser = await (
                p.chromium.launch(
                    headless=True
                )
            )

            context = await (
                browser.new_context(
                    storage_state=AUTH_FILE
                )
            )

            # Проверяем авторизацию.

            response = await (
                context.request.get(
                    f"{BASE_URL}/checkKkm/index",
                    timeout=30000
                )
            )

            if (
                "/login"
                in response.url.lower()
            ):

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
                "Скачиваю новые карточки..."
            )
            print()

            tasks = [
                asyncio.create_task(
                    download_customer(
                        context,
                        semaphore,
                        customer_id,
                        latest_name.get(
                            customer_id,
                            ""
                        ),
                        counts[
                            customer_id
                        ]
                    )
                )
                for customer_id
                in missing_ids
            ]

            completed = 0
            successful = 0
            failed = 0

            try:

                for task in (
                    asyncio.as_completed(
                        tasks
                    )
                ):

                    try:

                        (
                            customer_id,
                            customer,
                            error,
                            attempts
                        ) = await task

                    except AuthExpired:

                        print()
                        print(
                            "Авторизация CRM истекла."
                        )

                        for pending_task in tasks:

                            if not pending_task.done():
                                pending_task.cancel()

                        break

                    completed += 1

                    if error is None:

                        save_customer(
                            connection,
                            customer
                        )

                        successful += 1

                        print(
                            f"{completed}/"
                            f"{len(missing_ids)}"
                            f" | "
                            f"{customer_id}"
                            f" | сохранено"
                        )

                    else:

                        save_error(
                            connection,
                            customer_id,
                            error,
                            attempts
                        )

                        failed += 1

                        print(
                            f"{completed}/"
                            f"{len(missing_ids)}"
                            f" | "
                            f"{customer_id}"
                            f" | ОШИБКА: "
                            f"{error}"
                        )

            finally:

                await context.close()
                await browser.close()

    # ========================================================
    # EXPORT
    # ========================================================

    export_csv(
        connection
    )

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM customers
        """
    )

    total_customers = (
        cursor.fetchone()[0]
    )

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM errors
        """
    )

    total_errors = (
        cursor.fetchone()[0]
    )

    print()
    print("=" * 70)

    print(
        f"Всего карточек в базе: "
        f"{total_customers}"
    )

    print(
        f"Ошибок карточек: "
        f"{total_errors}"
    )

    print(
        f"CSV обновлён: "
        f"{os.path.basename(CSV_FILE)}"
    )

    print("=" * 70)

    connection.close()


if __name__ == "__main__":

    asyncio.run(
        main()
    )