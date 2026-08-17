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

URL = "https://it.mokryinos.ru/cashOut/index"


def clean(text):
    return " ".join(
        (text or "").split()
    )


def main():

    print()
    print("=" * 100)
    print("РКО — ИЮЛЬ 2026")
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

        date_input = page.locator(
            "#finance_document_date_filter"
        )

        if date_input.count():

            date_input.fill(
                "01.07.2026 - 31.07.2026"
            )

            date_input.press(
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
        print("ПОЛЯ ФИЛЬТРОВ")
        print("=" * 100)

        controls = page.locator(
            "input, select"
        )

        for i in range(
            controls.count()
        ):

            el = controls.nth(i)

            try:

                tag = el.evaluate(
                    "e => e.tagName"
                )

                name = el.get_attribute(
                    "name"
                )

                element_id = el.get_attribute(
                    "id"
                )

                value = el.input_value()

                if name or element_id:

                    print(
                        f"{tag:<7} | "
                        f"name={name!r} | "
                        f"id={element_id!r} | "
                        f"value={value!r}"
                    )

            except Exception:
                pass

        print()
        print("=" * 100)
        print("СТРОКИ")
        print("=" * 100)

        rows = page.locator(
            "table tr"
        )

        print(
            "Всего <tr>:",
            rows.count()
        )

        for i in range(
            rows.count()
        ):

            cells = rows.nth(i).locator(
                "td, th"
            )

            if cells.count() == 0:
                continue

            values = []

            for j in range(
                cells.count()
            ):

                text = clean(
                    cells.nth(j).text_content()
                )

                values.append(text)

            row_text = " | ".join(values)

            if row_text:
                print(
                    f"{i:03d} | {row_text}"
                )

        print()
        print("=" * 100)

        browser.close()


if __name__ == "__main__":
    main()