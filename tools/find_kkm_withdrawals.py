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

BASE_URL = "https://it.mokryinos.ru/"


def main():

    print()
    print("=" * 80)
    print("ИЩУ ССЫЛКУ «ВЫЕМКИ ИЗ ККМ»")
    print("=" * 80)

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        context = browser.new_context(
            storage_state=AUTH_FILE
        )

        page = context.new_page()

        page.goto(
            BASE_URL,
            wait_until="networkidle",
            timeout=60000
        )

        if "/login" in page.url:

            print(
                "ОШИБКА: CRM отправила на login"
            )

            browser.close()
            return

        links = page.locator("a")

        found = 0

        for i in range(
            links.count()
        ):

            link = links.nth(i)

            text = " ".join(
                (
                    link.text_content()
                    or ""
                ).split()
            )

            if (
                "Выемки из ККМ"
                in text
            ):

                href = link.get_attribute(
                    "href"
                )

                print(
                    f"{text} -> {href}"
                )

                found += 1

        print()
        print(
            "Найдено:",
            found
        )

        browser.close()


if __name__ == "__main__":
    main()