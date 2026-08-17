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

URL = "https://it.mokryinos.ru/reports/sellSum/index"


def clean(text):
    return " ".join(
        (text or "").split()
    )


def main():

    print()
    print("=" * 100)
    print("СТРУКТУРА ОТЧЁТА «ПРОДАЖИ»")
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
        print("ПОЛЯ")
        print("-" * 100)

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
        print("ОПЦИИ ВЫПАДАЮЩИХ СПИСКОВ")
        print("=" * 100)

        selects = page.locator(
            "select"
        )

        for i in range(
            selects.count()
        ):

            select = selects.nth(i)

            name = select.get_attribute(
                "name"
            )

            element_id = select.get_attribute(
                "id"
            )

            options = select.locator(
                "option"
            )

            interesting = []

            for j in range(
                options.count()
            ):

                option = options.nth(j)

                text = clean(
                    option.text_content()
                )

                value = option.get_attribute(
                    "value"
                )

                low = text.lower()

                if (
                    "яндекс" in low
                    or "купер" in low
                    or "канал" in low
                ):

                    interesting.append(
                        (
                            value,
                            text,
                        )
                    )

            if interesting:

                print()
                print(
                    f"SELECT name={name!r} id={element_id!r}"
                )

                for value, text in interesting:

                    print(
                        f"value={value!r:<15} | {text}"
                    )

        print()
        print("=" * 100)

        browser.close()


if __name__ == "__main__":
    main()