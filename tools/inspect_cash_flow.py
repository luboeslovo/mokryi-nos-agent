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
    "reports/cashFlowArticleMovement/index"
    "?showReport=1"
    "&filters%5BdateRange%5D=01.07.2026+-+31.07.2026"
    "&filters%5Bperiodicity%5D=1"
    "&filters%5BreportGroupBy%5D=article_hierarchy"
    "&filters%5BvgoFilter%5D=1"
)


def clean(text):
    return " ".join(
        (text or "").split()
    )


def main():

    print()
    print("=" * 90)
    print("CASH FLOW — ИЮЛЬ 2026")
    print("=" * 90)

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

        if "/login" in page.url:
            print("ОШИБКА: CRM отправила на login")
            browser.close()
            return

        print()
        print("=" * 90)
        print("СТРОКИ CASH FLOW")
        print("=" * 90)

        rows = page.locator("tr")

        print(
            "Всего <tr>:",
            rows.count()
        )

        seen = set()

        for i in range(
            rows.count()
        ):

            text = clean(
                rows.nth(i).text_content()
            )

            if not text:
                continue

            if text in seen:
                continue

            seen.add(text)

            print(
                f"{i:03d} | {text}"
            )

        print()
        print("=" * 90)

        browser.close()


if __name__ == "__main__":
    main()