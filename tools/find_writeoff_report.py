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


def clean(text):
    return " ".join(
        (text or "").split()
    )


def main():

    print()
    print("=" * 100)
    print("ИЩУ ОТЧЁТ «СПИСАНИЕ И ОПРИХОДОВАНИЕ»")
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
            "https://it.mokryinos.ru/",
            wait_until="networkidle",
            timeout=60000
        )

        if "/login" in page.url:
            print("ОШИБКА: CRM отправила на login")
            browser.close()
            return

        links = page.locator("a")

        found = []

        for i in range(
            links.count()
        ):

            link = links.nth(i)

            try:

                text = clean(
                    link.text_content()
                )

                href = link.get_attribute(
                    "href"
                )

                if not text or not href:
                    continue

                low = text.lower()

                if (
                    "списание" in low
                    and "оприход" in low
                ):

                    item = (
                        text,
                        href
                    )

                    if item not in found:
                        found.append(
                            item
                        )

            except Exception:
                pass

        print()

        for text, href in found:
            print(
                f"{text} -> {href}"
            )

        print()
        print(
            "Найдено:",
            len(found)
        )

        print("=" * 100)

        browser.close()


if __name__ == "__main__":
    main()