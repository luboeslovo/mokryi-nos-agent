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
    "cashOut/index"
)

TARGET_CODES = [
    "13100",  # аренда
    "13400",  # интернет
    "13600",  # банковское обслуживание
    "12400",  # эквайринг — контроль
]


def clean(text):
    return " ".join(
        (text or "").split()
    )


def main():

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        context = browser.new_context(
            storage_state=AUTH_FILE
        )

        page = context.new_page()

        page.goto(
            BASE_URL,
            wait_until="networkidle",
            timeout=60000
        )

        if "/login" in page.url:

            print(
                "ОШИБКА: CRM отправила на login"
            )

            browser.close()
            return

        select = page.locator(
            "#CashOutDocument_article_filter"
        )

        options = select.locator(
            "option"
        )

        article_values = {}

        for i in range(
            options.count()
        ):

            option = options.nth(i)

            text = clean(
                option.text_content()
            )

            value = option.get_attribute(
                "value"
            )

            for code in TARGET_CODES:

                if text.startswith(
                    code + " "
                ):

                    article_values[code] = (
                        value,
                        text,
                    )

        print()
        print("=" * 100)
        print("НАЙДЕННЫЕ СТАТЬИ")
        print("=" * 100)

        for code in TARGET_CODES:

            print(
                code,
                "->",
                article_values.get(code)
            )

        for code in TARGET_CODES:

            if code not in article_values:
                continue

            value, title = article_values[
                code
            ]

            print()
            print("=" * 100)
            print(title)
            print("=" * 100)

            params = {
                "CashOutDocument[date]":
                    "01.07.2026 - 31.07.2026",
                "CashOutDocument[article]":
                    value,
                "CashOutDocument_page":
                    "1",
            }

            url = (
                BASE_URL
                + "?"
                + urlencode(params)
            )

            page.goto(
                url,
                wait_until="networkidle",
                timeout=60000
            )

            print(
                "URL:",
                page.url
            )

            rows = page.locator(
                "table tr"
            )

            found = []

            for i in range(
                rows.count()
            ):

                cells = rows.nth(i).locator(
                    "td"
                )

                if cells.count() < 5:
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

                if (
                    "2026" in text
                    and "Проведен" in text
                ):

                    found.append(
                        text
                    )

            if not found:

                print(
                    "Реальных документов не найдено."
                )

            else:

                for row in found:

                    print(row)

                print()
                print(
                    "Документов:",
                    len(found)
                )

        print()
        print("=" * 100)

        browser.close()


if __name__ == "__main__":
    main()