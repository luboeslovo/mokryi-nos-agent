import os
from collections import Counter, defaultdict
from urllib.parse import urlencode

from playwright.sync_api import sync_playwright


PROJECT_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

AUTH_FILE = os.path.join(
    PROJECT_DIR,
    "auth.json"
)

BASE_URL = (
    "https://it.mokryinos.ru/"
    "delivery/externalOrderFranchisee/index"
)

DATE_FILTER_NAME = (
    "app_modules_delivery_models_"
    "ExternalOrderForm[createdAt]"
)

PAGE_PARAM = (
    "app_modules_delivery_models_"
    "ExternalOrderForm_page"
)

DATE_RANGE = (
    "01.07.2026 - 31.07.2026"
)


def clean(text):

    return " ".join(
        (text or "").split()
    )


def parse_money(text):

    value = (
        clean(text)
        .replace("\xa0", "")
        .replace(" ", "")
        .replace(",", ".")
    )

    if not value:

        return 0.0

    try:

        return float(value)

    except ValueError:

        return 0.0


def get_data_rows(page):

    result = []

    rows = page.locator(
        "table tbody tr"
    )

    for i in range(
        rows.count()
    ):

        cells = (
            rows
            .nth(i)
            .locator("td")
        )

        values = [
            clean(
                cells
                .nth(j)
                .text_content()
            )
            for j in range(
                cells.count()
            )
        ]

        if (
            len(values) >= 8
            and not values[0]
        ):

            values = values[1:]

        if len(values) < 7:

            continue

        date_text = values[0]

        if (
            len(date_text) < 10
            or date_text[2] != "."
            or date_text[5] != "."
        ):

            continue

        result.append(
            {
                "date": values[0],
                "platform": values[1],
                "number": values[2],
                "status": values[3],
                "delivery_type": values[4],
                "branch": values[5],
                "amount": parse_money(
                    values[6]
                ),
            }
        )

    return result


def build_url(page_number):

    params = [
        (
            DATE_FILTER_NAME,
            DATE_RANGE,
        )
    ]

    if page_number > 1:

        params.append(
            (
                PAGE_PARAM,
                str(page_number),
            )
        )

    return (
        BASE_URL
        + "?"
        + urlencode(params)
    )


def main():

    print()
    print("=" * 100)
    print(
        "ВНЕШНИЕ ЗАКАЗЫ — "
        "ПОЛНЫЙ ИЮЛЬ 2026"
    )
    print("=" * 100)

    all_orders = []

    seen_numbers = set()

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        context = browser.new_context(
            storage_state=AUTH_FILE
        )

        page = context.new_page()

        for page_number in range(
            1,
            21,
        ):

            target_url = build_url(
                page_number
            )

            page.goto(
                target_url,
                wait_until="networkidle",
                timeout=60000
            )

            if "/login" in page.url:

                raise RuntimeError(
                    "CRM отправила на login"
                )

            rows = get_data_rows(
                page
            )

            print()
            print(
                f"Страница {page_number}: "
                f"{len(rows)} заказов"
            )

            if not rows:

                break

            new_rows = []

            for row in rows:

                number = row[
                    "number"
                ]

                if number in seen_numbers:

                    continue

                seen_numbers.add(
                    number
                )

                new_rows.append(
                    row
                )

            if not new_rows:

                print(
                    "Новых заказов нет — "
                    "заканчиваю."
                )

                break

            all_orders.extend(
                new_rows
            )

            print(
                "Первый:",
                new_rows[0],
            )

            print(
                "Последний:",
                new_rows[-1],
            )

            if len(rows) < 50:

                break

        browser.close()

    print()
    print("=" * 100)
    print("ИТОГ")
    print("=" * 100)

    print()
    print(
        "Всего уникальных заказов:",
        len(all_orders)
    )

    statuses = Counter(
        row["status"]
        for row in all_orders
    )

    print()
    print("Статусы:")

    for status, count in (
        statuses.most_common()
    ):

        print(
            f"- {status}: {count}"
        )

    all_sum = sum(
        row["amount"]
        for row in all_orders
    )

    delivered = [
        row
        for row in all_orders
        if row["status"] == "Доставлен"
    ]

    cancelled = [
        row
        for row in all_orders
        if row["status"] == "Отменен"
    ]

    delivered_sum = sum(
        row["amount"]
        for row in delivered
    )

    print()
    print(
        "Сумма всех записей:",
        f"{all_sum:,.2f} ₽"
    )

    print(
        "Доставленных заказов:",
        len(delivered)
    )

    print(
        "Сумма доставленных:",
        f"{delivered_sum:,.2f} ₽"
    )

    print()
    print(
        "Отменённых заказов:",
        len(cancelled)
    )

    for row in cancelled:

        print(
            "-",
            row,
        )

    platform_counts = Counter(
        row["platform"]
        for row in delivered
    )

    platform_sums = defaultdict(
        float
    )

    for row in delivered:

        platform_sums[
            row["platform"]
        ] += row["amount"]

    print()
    print("=" * 100)
    print(
        "ДОСТАВЛЕННЫЕ ПО ПЛАТФОРМАМ"
    )
    print("=" * 100)

    for platform, count in (
        platform_counts.most_common()
    ):

        print()
        print(
            platform
        )

        print(
            "Заказов:",
            count
        )

        print(
            "Сумма:",
            f"{platform_sums[platform]:,.2f} ₽"
        )

    daily_counts = Counter()

    daily_sums = defaultdict(
        float
    )

    for row in delivered:

        day = row[
            "date"
        ][:10]

        daily_counts[
            day
        ] += 1

        daily_sums[
            day
        ] += row[
            "amount"
        ]

    print()
    print("=" * 100)
    print(
        "ДОСТАВЛЕННЫЕ ПО ДНЯМ"
    )
    print("=" * 100)

    for day in sorted(
        daily_counts,
        key=lambda value: (
            value[6:10],
            value[3:5],
            value[0:2],
        ),
    ):

        print(
            f"{day} | "
            f"{daily_counts[day]} заказов | "
            f"{daily_sums[day]:,.2f} ₽"
        )

    print()
    print("=" * 100)
    print("ГОТОВО")
    print("=" * 100)


if __name__ == "__main__":

    main()