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
    "salary/4686476"
)


def clean(text):
    return " ".join(
        (text or "").split()
    )


def main():

    print()
    print("=" * 100)
    print("ДЕТАЛИ ЗАРПЛАТЫ #4686476")
    print("=" * 100)

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        context = browser.new_context(
            storage_state=AUTH_FILE
        )

        page = context.new_page()

        response = page.goto(
            URL,
            wait_until="networkidle",
            timeout=60000
        )

        print()
        print(
            "HTTP:",
            response.status if response else "?"
        )

        print(
            "URL:",
            page.url
        )

        print(
            "TITLE:",
            page.title()
        )

        if "/login" in page.url:

            print(
                "ОШИБКА: CRM отправила на login"
            )

            browser.close()
            return

        print()
        print("=" * 100)
        print("ПОЛЯ")
        print("=" * 100)

        controls = page.locator(
            "input, select, textarea"
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

                value = ""

                if tag in (
                    "INPUT",
                    "SELECT",
                    "TEXTAREA",
                ):
                    value = el.input_value()

                if name or element_id:

                    print(
                        f"{tag:<8} | "
                        f"name={name!r} | "
                        f"id={element_id!r} | "
                        f"value={value!r}"
                    )

            except Exception:
                pass

        print()
        print("=" * 100)
        print("ЗАГОЛОВКИ ТАБЛИЦ")
        print("=" * 100)

        headers = page.locator(
            "table th"
        )

        print(
            "Всего th:",
            headers.count()
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
        print("СТРОКИ ТАБЛИЦ")
        print("=" * 100)

        rows = page.locator(
            "table tr"
        )

        print(
            "Всего tr:",
            rows.count()
        )

        for i in range(
            rows.count()
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
                        cells.nth(j).text_content()
                    )
                )

            text = " | ".join(values)

            if text:
                print(
                    f"{i:03d} | {text}"
                )

        print()
        print("=" * 100)
        print("ССЫЛКИ НА СТРАНИЦЕ")
        print("=" * 100)

        links = page.locator("a")

        shown = set()

        for i in range(
            links.count()
        ):

            link = links.nth(i)

            text = clean(
                link.text_content()
            )

            href = link.get_attribute(
                "href"
            )

            if not text or not href:
                continue

            item = (
                text,
                href,
            )

            if item in shown:
                continue

            shown.add(item)

            if (
                "сотруд" in text.lower()
                or "зарп" in text.lower()
                or "/salary/" in href
                or "settlement" in href.lower()
            ):

                print(
                    f"{text} -> {href}"
                )

        print()
        print("=" * 100)

        browser.close()


if __name__ == "__main__":
    main()