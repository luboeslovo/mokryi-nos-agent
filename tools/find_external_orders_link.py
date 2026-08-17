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

URL = "https://it.mokryinos.ru/"


def clean(text):
    return " ".join(
        (text or "").split()
    )


def main():

    print()
    print("=" * 100)
    print("ИЩУ ССЫЛКИ НА ВНЕШНИЕ / ИНТЕРНЕТ-ЗАКАЗЫ")
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

        links = page.locator("a")

        found = []

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

            lower = text.lower()

            if (
                "внешн" not in lower
                and "интернет" not in lower
                and "заказ" not in lower
            ):
                continue

            if not href:
                continue

            item = (
                text,
                href,
            )

            if item in found:
                continue

            found.append(
                item
            )

        for text, href in found:

            print()
            print(
                f"{text:<45} -> {href}"
            )

        print()
        print("=" * 100)
        print(
            "Найдено:",
            len(found)
        )
        print("=" * 100)

        browser.close()


if __name__ == "__main__":
    main()