import os
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
    "reports/sellSum/index"
)


SOURCES = [
    ("Яндекс Еда", "4"),
    ("Купер", "3"),
]


def clean(text):
    return " ".join(
        (text or "").split()
    )


def build_url(source_id):

    params = [
        ("showReport", "1"),
        (
            "filters[dateRange]",
            "01.07.2026 - 31.07.2026"
        ),
        (
            "filters[reportMode]",
            "1"
        ),
        (
            "filters[periodicity]",
            "1"
        ),
        (
            "filters[reportGroupBy]",
            "organizations"
        ),
        (
            "filters[salesSource][]",
            source_id
        ),
        (
            "filters[reportResultBy]",
            "count"
        ),
    ]

    return (
        BASE_URL
        + "?"
        + urlencode(params)
    )


def main():

    print()
    print("=" * 100)
    print(
        "ПРОВЕРЯЮ РЕЖИМ «ШТУКИ» "
        "ДЛЯ ВНЕШНИХ ЗАКАЗОВ — ИЮЛЬ 2026"
    )
    print("=" * 100)

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        context = browser.new_context(
            storage_state=AUTH_FILE
        )

        page = context.new_page()

        for source_name, source_id in SOURCES:

            print()
            print("=" * 100)
            print(source_name)
            print("=" * 100)

            url = build_url(
                source_id
            )

            page.goto(
                url,
                wait_until="networkidle",
                timeout=60000
            )

            if "/login" in page.url:

                print(
                    "ОШИБКА: CRM отправила на login"
                )

                browser.close()
                return

            print()
            print("URL:")
            print(page.url)

            print()
            print("-" * 100)

            rows = page.locator(
                "table tr"
            )

            print(
                "Строк таблицы:",
                rows.count()
            )

            for i in range(
                rows.count()
            ):

                cells = (
                    rows
                    .nth(i)
                    .locator(
                        "th, td"
                    )
                )

                values = []

                for j in range(
                    cells.count()
                ):

                    value = clean(
                        cells
                        .nth(j)
                        .text_content()
                    )

                    if value:
                        values.append(
                            value
                        )

                if not values:
                    continue

                print(
                    f"{i:03d} | "
                    + " | ".join(values)
                )

        browser.close()

    print()
    print("=" * 100)


if __name__ == "__main__":
    main()