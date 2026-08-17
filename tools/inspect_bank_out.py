import os

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

URL = "https://it.mokryinos.ru/bankOut/index"


def clean(text):
    return " ".join(
        (text or "").split()
    )


def main():

    print()
    print("=" * 100)
    print("ИСХОДЯЩИЕ ПЛАТЕЖИ — ИЮЛЬ 2026")
    print("=" * 100)

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        context = browser.new_context(
            storage_state=AUTH_FILE
        )

        page = context.new_page()

        page.goto(
            URL,
            wait_until="networkidle",
            timeout=60000
        )

        if "/login" in page.url:

            print(
                "ОШИБКА: CRM отправила на login"
            )

            browser.close()
            return

        date_filter = page.locator(
            "#finance_document_date_filter"
        )

        date_filter.fill(
            "01.07.2026 - 31.07.2026"
        )

        date_filter.press(
            "Enter"
        )

        page.wait_for_load_state(
            "networkidle"
        )

        print()
        print(
            "URL:",
            page.url
        )

        print()
        print("=" * 100)
        print("РЕАЛЬНЫЕ СТРОКИ")
        print("=" * 100)

        rows = page.locator(
            "tbody tr"
        )

        print(
            "Строк:",
            rows.count()
        )

        printed = 0

        for i in range(
            rows.count()
        ):

            cells = rows.nth(i).locator(
                "td"
            )

            if cells.count() == 0:
                continue

            values = []

            for j in range(
                cells.count()
            ):

                values.append(
                    clean(
                        cells.nth(j).text_content()
                    )
                )

            text = " | ".join(
                values
            )

            if not text:
                continue

            if "Нет результатов" in text:
                print(text)
                continue

            if "Выбрать" in text:
                continue

            print(
                f"{printed + 1:03d} | {text}"
            )

            printed += 1

            if printed >= 50:
                break

        print()
        print("=" * 100)
        print(
            "Показано реальных строк:",
            printed
        )
        print("=" * 100)

        browser.close()


if __name__ == "__main__":
    main()