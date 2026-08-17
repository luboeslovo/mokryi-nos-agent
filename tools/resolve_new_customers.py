import asyncio
import csv
import html
import json
import os
import re
from urllib.parse import urlencode

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

RAW_CHECKS_FILE = os.path.join(
    PROJECT_DIR,
    "checks_raw.csv"
)

RESOLVED_CHECKS_FILE = os.path.join(
    PROJECT_DIR,
    "checks_with_customer_id.csv"
)


# ============================================================
# CRM
# ============================================================

BASE_URL = "https://it.mokryinos.ru"

AUTOCOMPLETE_URL = (
    BASE_URL
    + "/individual/individual/autocomplete"
)

CHECKS_URL = (
    BASE_URL
    + "/checkKkm/index"
)

CONCURRENCY = 8
RETRIES = 3


# Общая карта для покупателей,
# которые не хотят оформлять свою карту.
#
# Ее продажи сохраняем,
# но клиентом ее не считаем.

SHARED_CUSTOMER_IDS = {
    "806542"
}


class AuthExpired(Exception):
    pass


# ============================================================
# ЧТЕНИЕ CSV
# ============================================================

def read_csv(path):

    if not os.path.exists(path):
        return [], []

    with open(
        path,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.DictReader(file)

        return (
            reader.fieldnames or [],
            list(reader)
        )


# ============================================================
# НОРМАЛИЗАЦИЯ ИМЕНИ
# ============================================================

def normalize_name(value):

    if value is None:
        return ""

    return " ".join(
        str(value).strip().split()
    )


# ============================================================
# AUTOCOMPLETE
# ============================================================

def extract_candidate_ids(payload):

    if isinstance(payload, dict):

        # Иногда данные могут лежать внутри
        # одного из этих полей.

        for key in (
            "items",
            "results",
            "data",
        ):

            if key in payload:

                return extract_candidate_ids(
                    payload[key]
                )

        payload = [payload]

    if not isinstance(payload, list):
        return []

    result = []

    for item in payload:

        if not isinstance(item, dict):
            continue

        candidate_id = None

        for key in (
            "id",
            "individual_id",
            "customer_id",
        ):

            value = item.get(key)

            if value is not None:

                text = str(value).strip()

                if text:

                    candidate_id = text
                    break

        if candidate_id:
            result.append(candidate_id)

    # Убираем повторы, сохраняя порядок.

    return list(
        dict.fromkeys(result)
    )


async def get_candidates(
    context,
    name
):

    params = urlencode(
        {
            "term": name
        }
    )

    url = (
        f"{AUTOCOMPLETE_URL}"
        f"?{params}"
    )

    last_error = None

    for attempt in range(
        1,
        RETRIES + 1
    ):

        try:

            response = await (
                context.request.get(
                    url,
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

            text = await response.text()

            payload = json.loads(text)

            return extract_candidate_ids(
                payload
            )

        except AuthExpired:
            raise

        except Exception as error:

            last_error = error

            if attempt < RETRIES:
                await asyncio.sleep(attempt)

    raise RuntimeError(
        f"autocomplete: {last_error}"
    )


# ============================================================
# ТОЧНАЯ ПРОВЕРКА
# ============================================================

async def candidate_has_check(
    context,
    customer_id,
    check_number
):

    params = urlencode(
        {
            "pageSize": 500,
            "CheckKkm[individual_id]":
                customer_id,
            "CheckKkm[client_id]":
                check_number,
        }
    )

    url = (
        f"{CHECKS_URL}"
        f"?{params}"
    )

    response = await (
        context.request.get(
            url,
            timeout=30000
        )
    )

    if "/login" in response.url.lower():

        raise AuthExpired()

    if response.status != 200:

        raise RuntimeError(
            f"HTTP {response.status}"
        )

    text = await response.text()

    text = html.unescape(text)

    pattern = (
        r"<td[^>]*>\s*"
        + re.escape(check_number)
        + r"\s*</td>"
    )

    return bool(
        re.search(
            pattern,
            text,
            flags=re.IGNORECASE
        )
    )


# ============================================================
# ОПРЕДЕЛЕНИЕ ОДНОГО ЧЕКА
# ============================================================

async def resolve_check(
    context,
    semaphore,
    check,
    candidate_cache
):

    async with semaphore:

        check_id = str(
            check.get(
                "check_id",
                ""
            )
        ).strip()

        check_number = str(
            check.get(
                "number",
                ""
            )
        ).strip()

        customer_name = normalize_name(
            check.get(
                "customer",
                ""
            )
        )

        # ----------------------------------------
        # Нет покупателя вообще
        # ----------------------------------------

        if not customer_name:

            return {
                "check_id":
                    check_id,

                "customer_id":
                    "",

                "resolution_status":
                    "anonymous",

                "resolution_method":
                    "no_customer",
            }

        # ----------------------------------------
        # AUTOCOMPLETE
        # ----------------------------------------

        cache_key = (
            customer_name.casefold()
        )

        if cache_key in candidate_cache:

            candidates = candidate_cache[
                cache_key
            ]

        else:

            candidates = await get_candidates(
                context,
                customer_name
            )

            candidate_cache[
                cache_key
            ] = candidates

        # ----------------------------------------
        # 0 кандидатов
        # ----------------------------------------

        if len(candidates) == 0:

            return {
                "check_id":
                    check_id,

                "customer_id":
                    "",

                "resolution_status":
                    "unresolved",

                "resolution_method":
                    "no_candidates",
            }

        # ----------------------------------------
        # 1 кандидат
        # ----------------------------------------

        if len(candidates) == 1:

            customer_id = str(
                candidates[0]
            )

            # Общая карта.

            if (
                customer_id
                in SHARED_CUSTOMER_IDS
            ):

                return {
                    "check_id":
                        check_id,

                    "customer_id":
                        "",

                    "resolution_status":
                        "anonymous",

                    "resolution_method":
                        "shared_card",
                }

            return {
                "check_id":
                    check_id,

                "customer_id":
                    customer_id,

                "resolution_status":
                    "resolved",

                "resolution_method":
                    "unique_name",
            }

        # ----------------------------------------
        # Несколько кандидатов
        # ----------------------------------------

        exact_matches = []

        for customer_id in candidates:

            found = await candidate_has_check(
                context,
                customer_id,
                check_number
            )

            if found:

                exact_matches.append(
                    str(customer_id)
                )

        if len(exact_matches) == 1:

            customer_id = exact_matches[0]

            if (
                customer_id
                in SHARED_CUSTOMER_IDS
            ):

                return {
                    "check_id":
                        check_id,

                    "customer_id":
                        "",

                    "resolution_status":
                        "anonymous",

                    "resolution_method":
                        "shared_card",
                }

            return {
                "check_id":
                    check_id,

                "customer_id":
                    customer_id,

                "resolution_status":
                    "resolved",

                "resolution_method":
                    "candidate_exact",
            }

        if len(exact_matches) == 0:

            return {
                "check_id":
                    check_id,

                "customer_id":
                    "",

                "resolution_status":
                    "unresolved",

                "resolution_method":
                    "no_exact_match",
            }

        return {
            "check_id":
                check_id,

            "customer_id":
                "",

            "resolution_status":
                "unresolved",

            "resolution_method":
                "multiple_exact_matches",
        }


# ============================================================
# ЗАПИСЬ НОВОГО CSV
# ============================================================

def save_output(
    raw_checks,
    existing_resolution,
    new_resolution
):

    resolution_map = {}

    # Старые результаты.

    for row in existing_resolution:

        check_id = str(
            row.get(
                "check_id",
                ""
            )
        ).strip()

        if check_id:

            resolution_map[
                check_id
            ] = {
                "customer_id":
                    row.get(
                        "customer_id",
                        ""
                    ),

                "resolution_status":
                    row.get(
                        "resolution_status",
                        ""
                    ),

                "resolution_method":
                    row.get(
                        "resolution_method",
                        ""
                    ),
            }

    # Новые результаты.

    for row in new_resolution:

        resolution_map[
            row["check_id"]
        ] = row

    # ----------------------------------------
    # ИСПРАВЛЯЕМ ОБЩУЮ КАРТУ
    # ВО ВСЕЙ ИСТОРИИ
    # ----------------------------------------

    shared_fixed = 0

    for check_id, resolution in (
        resolution_map.items()
    ):

        customer_id = str(
            resolution.get(
                "customer_id",
                ""
            )
        ).strip()

        if (
            customer_id
            in SHARED_CUSTOMER_IDS
        ):

            resolution[
                "customer_id"
            ] = ""

            resolution[
                "resolution_status"
            ] = "anonymous"

            resolution[
                "resolution_method"
            ] = "shared_card"

            shared_fixed += 1

    fieldnames = [
        "check_id",
        "date",
        "number",
        "customer",
        "type",
        "organization",
        "branch",
        "user",
        "amount",
        "customer_id",
        "resolution_status",
        "resolution_method",
    ]

    with open(
        RESOLVED_CHECKS_FILE,
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()

        for check in raw_checks:

            check_id = str(
                check.get(
                    "check_id",
                    ""
                )
            ).strip()

            resolution = (
                resolution_map.get(
                    check_id,
                    {
                        "customer_id":
                            "",

                        "resolution_status":
                            "unresolved",

                        "resolution_method":
                            "not_processed",
                    }
                )
            )

            output = {
                "check_id":
                    check.get(
                        "check_id",
                        ""
                    ),

                "date":
                    check.get(
                        "date",
                        ""
                    ),

                "number":
                    check.get(
                        "number",
                        ""
                    ),

                "customer":
                    check.get(
                        "customer",
                        ""
                    ),

                "type":
                    check.get(
                        "type",
                        ""
                    ),

                "organization":
                    check.get(
                        "organization",
                        ""
                    ),

                "branch":
                    check.get(
                        "branch",
                        ""
                    ),

                "user":
                    check.get(
                        "user",
                        ""
                    ),

                "amount":
                    check.get(
                        "amount",
                        ""
                    ),

                "customer_id":
                    resolution.get(
                        "customer_id",
                        ""
                    ),

                "resolution_status":
                    resolution.get(
                        "resolution_status",
                        ""
                    ),

                "resolution_method":
                    resolution.get(
                        "resolution_method",
                        ""
                    ),
            }

            writer.writerow(output)

    return shared_fixed


# ============================================================
# MAIN
# ============================================================

async def main():

    (
        raw_fields,
        raw_checks
    ) = read_csv(
        RAW_CHECKS_FILE
    )

    (
        resolved_fields,
        existing_resolution
    ) = read_csv(
        RESOLVED_CHECKS_FILE
    )

    if not raw_checks:

        print(
            "checks_raw.csv пуст."
        )

        return

    existing_ids = {
        str(
            row.get(
                "check_id",
                ""
            )
        ).strip()
        for row in existing_resolution
    }

    pending = [
        check
        for check in raw_checks
        if str(
            check.get(
                "check_id",
                ""
            )
        ).strip()
        not in existing_ids
    ]

    print()
    print("=" * 70)

    print(
        f"Всего чеков: "
        f"{len(raw_checks)}"
    )

    print(
        f"Уже есть customer resolution: "
        f"{len(existing_resolution)}"
    )

    print(
        f"Новых чеков для определения: "
        f"{len(pending)}"
    )

    print("=" * 70)

    semaphore = asyncio.Semaphore(
        CONCURRENCY
    )

    candidate_cache = {}

    new_results = []

    if pending:

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
                    CHECKS_URL,
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

                return

            print()
            print(
                "Авторизация в порядке."
            )

            print(
                "Определяю покупателей..."
            )
            print()

            tasks = [
                asyncio.create_task(
                    resolve_check(
                        context,
                        semaphore,
                        check,
                        candidate_cache
                    )
                )
                for check in pending
            ]

            try:

                for index, task in enumerate(
                    asyncio.as_completed(
                        tasks
                    ),
                    start=1
                ):

                    result = await task

                    new_results.append(
                        result
                    )

                    print(
                        f"{index}/"
                        f"{len(pending)}"
                        f" | "
                        f"{result['check_id']}"
                        f" | "
                        f"{result['resolution_status']}"
                        f" | "
                        f"{result['resolution_method']}"
                    )

            except AuthExpired:

                print()
                print(
                    "Авторизация CRM истекла."
                )

                for task in tasks:

                    if not task.done():
                        task.cancel()

                await context.close()
                await browser.close()

                return

            await context.close()
            await browser.close()

    shared_fixed = save_output(
        raw_checks,
        existing_resolution,
        new_results
    )

    # ========================================================
    # ИТОГИ
    # ========================================================

    (
        _,
        final_rows
    ) = read_csv(
        RESOLVED_CHECKS_FILE
    )

    counts = {}

    methods = {}

    for row in final_rows:

        status = row.get(
            "resolution_status",
            ""
        )

        method = row.get(
            "resolution_method",
            ""
        )

        counts[status] = (
            counts.get(status, 0)
            + 1
        )

        methods[method] = (
            methods.get(method, 0)
            + 1
        )

    print()
    print("=" * 70)
    print("ГОТОВО")

    print()
    print(
        f"Всего строк: "
        f"{len(final_rows)}"
    )

    print()
    print("СТАТУСЫ:")

    for key, value in sorted(
        counts.items()
    ):

        print(
            f"{key}: {value}"
        )

    print()
    print(
        "Чеков общей карты "
        "исключено из клиентской аналитики:"
    )

    print(
        shared_fixed
    )

    print()
    print(
        f"Файл: "
        f"{os.path.basename(RESOLVED_CHECKS_FILE)}"
    )

    print("=" * 70)


if __name__ == "__main__":

    asyncio.run(
        main()
    )