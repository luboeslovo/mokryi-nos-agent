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

URL = (
    "https://it.mokryinos.ru/"
    "reports/sellSum/index"
)


SOURCES = {
    "Самовывоз с ИМ": "2",
    "Купер": "3",
    "Яндекс Еда": "4",
}


def clean(text):
    return " ".join(
        (text or "").split()
    )


def main():

    print()
    print("=" * 100)
    print(
        "ПРОДАЖИ ПО ДНЯМ — ИЮЛЬ 2026"
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

        for source_name, source_id in SOURCES.items():

            print()
            print("=" * 100)
            print(source_name)
            print("=" * 100)

            params = [
                (
                    "showReport",
                    "1"
                ),
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
                    "2"
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
                    "amount"
                ),
            ]

            target_url = (
                URL
                + "?"
                + urlencode(params)
            )

            page.goto(
                target_url,
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

                cells = rows.nth(i).locator(
                    "th, td"
                )

                if cells.count() == 0:
                    continue

                values = []

                for j in range(
                    cells.count()
                ):

                    values.append(
                        clean(
                            cells.nth(j)
                            .text_content()
                        )
                    )

                print(
                    f"{i:03d} | "
                    + " | ".join(values)
                )

        browser.close()

    print()
    print("=" * 100)
    print("ГОТОВО")
    print("=" * 100)


if __name__ == "__main__":
    main()