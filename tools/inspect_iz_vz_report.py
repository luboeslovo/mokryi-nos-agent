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
    "reports/individualAndExternalOrdersInSales/index"
)


def clean(text):
    return " ".join(
        (text or "").split()
    )


def main():

    print()
    print("=" * 100)
    print(
        "ИЗ И ВЗ В ПРОДАЖАХ — ИЮЛЬ 2026"
    )
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
            "1"
        ),
        (
            "filters[reportGroupBy]",
            "filials"
        ),
    ]

    url = (
        BASE_URL
        + "?"
        + urlencode(params)
    )

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        context = browser.new_context(
            storage_state=AUTH_FILE
        )

        page = context.new_page()

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
        print("=" * 100)
        print("URL")
        print("=" * 100)
        print(page.url)

        print()
        print("=" * 100)
        print("ЗАГОЛОВКИ")
        print("=" * 100)

        headers = page.locator(
            "table th"
        )

        print(
            "Заголовков:",
            headers.count()
        )

        for i in range(
            headers.count()
        ):

            value = clean(
                headers
                .nth(i)
                .text_content()
            )

            if value:
                print(
                    f"{i:02d} | {value}"
                )

        print()
        print("=" * 100)
        print("СТРОКИ ТАБЛИЦ")
        print("=" * 100)

        rows = page.locator(
            "table tr"
        )

        print(
            "Всего строк:",
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