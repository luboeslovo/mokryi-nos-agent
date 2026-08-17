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
    "reports/staffSettlement/employee"
    "?showReport=1"
    "&filters%5BdateRange%5D=01.07.2026+-+31.07.2026"
)


def clean(text):
    return " ".join(
        (text or "").split()
    )


def main():

    print()
    print("=" * 100)
    print("ЗАРПЛАТА — СТРУКТУРА ТАБЛИЦЫ")
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
            print("ОШИБКА: CRM отправила на login")
            browser.close()
            return

        print()
        print("ЗАГОЛОВКИ")
        print("-" * 100)

        headers = page.locator(
            "table th"
        )

        for i in range(
            headers.count()
        ):

            print(
                f"{i:02d} | "
                f"{clean(headers.nth(i).text_content())}"
            )

        print()
        print("=" * 100)
        print("ЯЧЕЙКИ СТРОК")
        print("=" * 100)

        rows = page.locator(
            "table tr"
        )

        for i in range(
            rows.count()
        ):

            cells = rows.nth(i).locator(
                "td"
            )

            if cells.count() == 0:
                continue

            print()
            print(
                f"СТРОКА {i}"
            )
            print("-" * 100)

            for j in range(
                cells.count()
            ):

                cell = cells.nth(j)

                text = clean(
                    cell.text_content()
                )

                print(
                    f"[{j:02d}] {text}"
                )

                links = cell.locator(
                    "a"
                )

                for k in range(
                    links.count()
                ):

                    href = links.nth(k).get_attribute(
                        "href"
                    )

                    link_text = clean(
                        links.nth(k).text_content()
                    )

                    print(
                        f"     LINK: "
                        f"{link_text!r} -> {href}"
                    )

        print()
        print("=" * 100)

        browser.close()


if __name__ == "__main__":
    main()