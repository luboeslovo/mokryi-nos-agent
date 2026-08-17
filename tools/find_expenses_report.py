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
    "reports/profitAndLost/index"
)


def clean(text):
    return " ".join(
        (text or "").split()
    )


def main():

    print()
    print("=" * 90)
    print("ИЩУ ССЫЛКУ НА ОТЧЁТ «РАСХОДЫ»")
    print("=" * 90)

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

            if not text or not href:
                continue

            if (
                text.lower() == "расходы"
                or "расход" in text.lower()
            ):

                item = (
                    text,
                    href,
                )

                if item not in found:
                    found.append(
                        item
                    )

        for text, href in found:

            print(
                f"{text:<45} -> {href}"
            )

        print()
        print(
            "Найдено:",
            len(found)
        )

        print("=" * 90)

        browser.close()


if __name__ == "__main__":
    main()