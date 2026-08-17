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

URL = (
    "https://it.mokryinos.ru/"
    "checkKkm/21740229"
)


def clean(text):
    return " ".join(
        (text or "").split()
    )


def main():

    print()
    print("=" * 100)
    print(
        "СТРУКТУРА ЯЧЕЕК ВОЗВРАТА 21740229"
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

        rows = page.locator(
            "table tr"
        )

        for i in range(
            rows.count()
        ):

            row = rows.nth(i)

            cells = row.locator(
                "th, td"
            )

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

            row_text = " | ".join(
                values
            )

            lower = row_text.lower()

            if not (
                "пластик" in lower
                or "налич" in lower
                or "оплат" in lower
                or "144" in lower
            ):
                continue

            print()
            print(
                f"СТРОКА {i}"
            )

            print("-" * 100)

            print(
                row_text
            )

            print()
            print(
                "ЯЧЕЙКИ:"
            )

            for j, value in enumerate(
                values
            ):

                print(
                    f"  [{j:02d}] {value!r}"
                )

        browser.close()

    print()
    print("=" * 100)


if __name__ == "__main__":
    main()