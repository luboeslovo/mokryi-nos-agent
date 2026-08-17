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
    "checkKkm/20312252"
)


def clean(text):
    return " ".join(
        (text or "").split()
    )


def main():

    print()
    print("=" * 100)
    print(
        "ИССЛЕДУЮ UNKNOWN-ВОЗВРАТ "
        "14.02.2026 НА 1 059 ₽"
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

        print()
        print("URL:")
        print(page.url)

        print()
        print("=" * 100)
        print("НЕПУСТЫЕ ПОЛЯ")
        print("=" * 100)

        fields = page.locator(
            "input, select, textarea"
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

            value = clean(
                value
            )

            if not value:
                continue

            print(
                f"{tag:<8} | "
                f"name={name!r} | "
                f"id={field_id!r} | "
                f"value={value!r}"
            )

        print()
        print("=" * 100)
        print("СТРОКИ С СУММОЙ 1 059")
        print("=" * 100)

        rows = page.locator(
            "table tr"
        )

        for i in range(
            rows.count()
        ):

            text = clean(
                rows.nth(i)
                .text_content()
            )

            normalized = (
                text
                .replace(" ", "")
                .replace(",", ".")
            )

            if (
                "1059" not in normalized
                and "возврат" not in text.lower()
                and "оплат" not in text.lower()
                and "касс" not in text.lower()
                and "налич" not in text.lower()
                and "пластик" not in text.lower()
            ):
                continue

            print(
                f"{i:03d} | {text}"
            )

            links = rows.nth(i).locator(
                "a"
            )

            for j in range(
                links.count()
            ):

                link = links.nth(j)

                print(
                    "      LINK:",
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

        print()
        print("=" * 100)
        print("ВСЕ СТРОКИ В КОНЦЕ КАРТОЧКИ")
        print("=" * 100)

        count = rows.count()

        start = max(
            0,
            count - 40
        )

        for i in range(
            start,
            count
        ):

            text = clean(
                rows.nth(i)
                .text_content()
            )

            if text:

                print(
                    f"{i:03d} | {text}"
                )

        print()
        print("=" * 100)

        browser.close()


if __name__ == "__main__":
    main()