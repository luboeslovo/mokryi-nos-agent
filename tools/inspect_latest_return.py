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
    "checkKkm/index"
)


def clean(text):
    return " ".join(
        (text or "").split()
    )


def main():

    print()
    print("=" * 100)
    print("ИЩУ ПОСЛЕДНИЙ ВОЗВРАТ ЧЕКА")
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

        found = False

        for i in range(
            rows.count()
        ):

            row = rows.nth(i)

            text = clean(
                row.text_content()
            )

            if (
                "Возврат Чека ККМ"
                not in text
            ):
                continue

            found = True

            print()
            print("СТРОКА:")
            print("-" * 100)
            print(text)

            print()
            print("ЯЧЕЙКИ:")
            print("-" * 100)

            cells = row.locator(
                "th, td"
            )

            for j in range(
                cells.count()
            ):

                value = clean(
                    cells.nth(j)
                    .text_content()
                )

                print(
                    f"[{j:02d}] {value}"
                )

            print()
            print("ССЫЛКИ:")
            print("-" * 100)

            links = row.locator(
                "a"
            )

            for j in range(
                links.count()
            ):

                link = links.nth(j)

                link_text = clean(
                    link.text_content()
                )

                href = link.get_attribute(
                    "href"
                )

                print(
                    f"[{j:02d}] "
                    f"{link_text!r} -> {href}"
                )

            break

        if not found:

            print()
            print(
                "На текущей странице "
                "возвратов не найдено."
            )

        browser.close()

    print()
    print("=" * 100)


if __name__ == "__main__":
    main()