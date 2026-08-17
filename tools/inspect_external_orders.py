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
    "delivery/externalOrderFranchisee/index"
)


def clean(text):
    return " ".join(
        (text or "").split()
    )


def main():

    print()
    print("=" * 100)
    print("ВНЕШНИЕ ЗАКАЗЫ — ИССЛЕДУЮ СТРАНИЦУ")
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
        print("=" * 100)
        print("URL")
        print("=" * 100)
        print(page.url)

        print()
        print("=" * 100)
        print("ПОЛЯ ФИЛЬТРОВ")
        print("=" * 100)

        elements = page.locator(
            "input, select"
        )

        for i in range(
            elements.count()
        ):

            element = elements.nth(i)

            tag = element.evaluate(
                "el => el.tagName"
            )

            name = element.get_attribute(
                "name"
            )

            element_id = element.get_attribute(
                "id"
            )

            try:
                value = element.input_value()
            except Exception:
                value = ""

            print(
                f"{tag:<7} | "
                f"name={name!r} | "
                f"id={element_id!r} | "
                f"value={value!r}"
            )

        print()
        print("=" * 100)
        print("ЗАГОЛОВКИ ТАБЛИЦ")
        print("=" * 100)

        headers = page.locator(
            "table th"
        )

        for i in range(
            headers.count()
        ):

            value = clean(
                headers.nth(i).text_content()
            )

            if value:
                print(
                    f"{i:02d} | {value}"
                )

        print()
        print("=" * 100)
        print("ПЕРВЫЕ СТРОКИ")
        print("=" * 100)

        rows = page.locator(
            "table tr"
        )

        print(
            "Всего строк:",
            rows.count()
        )

        shown = 0

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

            shown += 1

            if shown >= 15:
                break

        print()
        print("=" * 100)

        browser.close()


if __name__ == "__main__":
    main()