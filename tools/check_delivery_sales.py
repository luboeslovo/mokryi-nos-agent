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

CHANNELS = {
    "Яндекс Еда": "4",
    "Купер": "3",
}


def clean(text):
    return " ".join(
        (text or "").split()
    )


def main():

    print()
    print("=" * 100)
    print("ПРОДАЖИ ЯНДЕКС ЕДА И КУПЕР — ИЮЛЬ 2026")
    print("=" * 100)

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        context = browser.new_context(
            storage_state=AUTH_FILE
        )

        page = context.new_page()

        for name, channel_id in CHANNELS.items():

            params = [
                ("showReport", "1"),
                (
                    "filters[dateRange]",
                    "01.07.2026 - 31.07.2026",
                ),
                (
                    "filters[reportMode]",
                    "1",
                ),
                (
                    "filters[periodicity]",
                    "1",
                ),
                (
                    "filters[reportGroupBy]",
                    "organizations",
                ),
                (
                    "filters[salesSource][]",
                    channel_id,
                ),
                (
                    "filters[reportResultBy]",
                    "amount",
                ),
            ]

            url = (
                BASE_URL
                + "?"
                + urlencode(params)
            )

            page.goto(
                url,
                wait_until="networkidle",
                timeout=60000,
            )

            if "/login" in page.url:

                print(
                    "ОШИБКА: CRM отправила на login"
                )

                browser.close()
                return

            print()
            print("=" * 100)
            print(name)
            print("=" * 100)

            print(
                "URL:",
                page.url
            )

            rows = page.locator(
                "table tr"
            )

            print()
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

                text = " | ".join(
                    values
                )

                if text:

                    print(
                        f"{i:03d} | {text}"
                    )

        print()
        print("=" * 100)

        browser.close()


if __name__ == "__main__":
    main()