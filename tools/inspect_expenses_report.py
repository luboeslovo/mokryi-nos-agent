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
    "reports/incomeOutcome/index"
    "?showReport=1"
    "&filters%5BdateRange%5D=01.07.2026+-+31.07.2026"
    "&filters%5Bperiodicity%5D=1"
    "&filters%5BreportGroupBy%5D=article_hierarchy"
)


def clean(text):
    return " ".join(
        (text or "").split()
    )


def main():

    print()
    print("=" * 100)
    print("РАСХОДЫ CRM — ИЮЛЬ 2026")
    print("ГРУППИРОВКА ПО СТАТЬЯМ PL")
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

        if "/login" in page.url:

            print(
                "ОШИБКА: CRM отправила на login"
            )

            browser.close()
            return

        print()
        print("=" * 100)
        print("СТРОКИ ОТЧЁТА")
        print("=" * 100)

        rows = page.locator(
            "table tr"
        )

        print(
            "Всего <tr>:",
            rows.count()
        )

        seen = set()
        printed = 0

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
                f"{printed:03d} | {text}"
            )

            printed += 1

        print()
        print("=" * 100)
        print(
            "Выведено строк:",
            printed
        )
        print("=" * 100)

        browser.close()


if __name__ == "__main__":
    main()