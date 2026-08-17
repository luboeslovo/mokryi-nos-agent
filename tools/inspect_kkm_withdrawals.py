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
    "extractingMoneyFromCashKkm/index"
)


def clean(text):
    return " ".join(
        (text or "").split()
    )


def main():

    print()
    print("=" * 100)
    print("ВЫЕМКИ ИЗ ККМ — СТРУКТУРА")
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

        print()
        print("URL:")
        print(page.url)

        print()
        print("=" * 100)
        print("ПОЛЯ")
        print("=" * 100)

        fields = page.locator(
            "input, select"
        )

        for i in range(
            fields.count()
        ):

            field = fields.nth(i)

            tag = field.evaluate(
                "el => el.tagName"
            )

            name = field.get_attribute(
                "name"
            )

            field_id = field.get_attribute(
                "id"
            )

            value = field.input_value()

            print(
                f"{tag:<7} | "
                f"name={name!r} | "
                f"id={field_id!r} | "
                f"value={value!r}"
            )

        print()
        print("=" * 100)
        print("СТРОКИ ТАБЛИЦЫ")
        print("=" * 100)

        rows = page.locator(
            "table tr"
        )

        print(
            "Всего строк:",
            rows.count()
        )

        for i in range(
            min(
                rows.count(),
                30
            )
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

        print()
        print("=" * 100)

        browser.close()


if __name__ == "__main__":
    main()