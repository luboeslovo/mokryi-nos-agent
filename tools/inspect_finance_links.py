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

KEYWORDS = [
    "Cash Flow",
    "ПКО",
    "РКО",
    "Вх. ПП",
    "Исх. ПП",
    "Импорт банка",
    "Заработная плата",
    "Движение ДС",
    "Платежные документы",
    "Платежного календаря",
]


def main():

    print()
    print("=" * 90)
    print("ФИНАНСОВЫЕ ССЫЛКИ CRM")
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
            print("ОШИБКА: CRM отправила на login")
            browser.close()
            return

        links = page.locator("a")

        found = []

        for i in range(
            links.count()
        ):

            link = links.nth(i)

            text = (
                link.inner_text()
                or ""
            ).strip()

            href = link.get_attribute(
                "href"
            )

            if not text or not href:
                continue

            if any(
                keyword.lower()
                in text.lower()
                for keyword in KEYWORDS
            ):

                item = (
                    text,
                    href
                )

                if item not in found:
                    found.append(
                        item
                    )

        for text, href in found:

            print()
            print(
                f"{text:<35} -> {href}"
            )

        print()
        print("=" * 90)
        print(
            "Найдено:",
            len(found)
        )
        print("=" * 90)

        browser.close()


if __name__ == "__main__":
    main()