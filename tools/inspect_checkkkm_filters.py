import os
import re

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
    print("ЧЕКИ ККМ — ФИЛЬТРЫ И РЕАЛЬНЫЕ СТРОКИ")
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
        print("=" * 100)
        print("ПОЛЯ ФИЛЬТРОВ")
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

            value = ""

            try:
                value = field.input_value()
            except Exception:
                pass

            print(
                f"{tag:<7} | "
                f"name={name!r} | "
                f"id={field_id!r} | "
                f"value={value!r}"
            )

            if tag == "SELECT":

                options = field.locator(
                    "option"
                )

                for j in range(
                    options.count()
                ):

                    option = options.nth(j)

                    option_text = clean(
                        option.text_content()
                    )

                    option_value = (
                        option.get_attribute(
                            "value"
                        )
                    )

                    if (
                        "Чек ККМ" in option_text
                        or "Возврат" in option_text
                    ):

                        print(
                            f"    OPTION "
                            f"value={option_value!r} "
                            f"| {option_text}"
                        )

        print()
        print("=" * 100)
        print("РЕАЛЬНЫЕ СТРОКИ")
        print("=" * 100)

        rows = page.locator(
            "table tr"
        )

        shown = 0

        for i in range(
            rows.count()
        ):

            row = rows.nth(i)

            text = clean(
                row.text_content()
            )

            if not re.search(
                r"\b\d{2}\.\d{2}\.\d{4}\b",
                text
            ):
                continue

            print()
            print(
                f"СТРОКА {i}"
            )
            print("-" * 100)
            print(text)

            links = row.locator(
                "a"
            )

            for j in range(
                links.count()
            ):

                link = links.nth(j)

                print(
                    "LINK:",
                    repr(
                        clean(
                            link.text_content()
                        )
                    ),
                    "->",
                    link.get_attribute(
                        "href"
                    )
                )

            shown += 1

            if shown >= 10:
                break

        print()
        print("=" * 100)

        browser.close()


if __name__ == "__main__":
    main()