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
    "reports/profitAndLost/index"
    "?showReport=1"
    "&filters%5BdateRange%5D=01.07.2026+-+31.07.2026"
    "&filters%5BreportMode%5D=1"
    "&filters%5Bperiodicity%5D=1"
)


KEYWORDS = [
    "аренд",
    "интернет",
    "рко",
    "эквайр",
    "яндекс",
    "купер",
    "роялти",
    "заработ",
    "зарплат",
    "реклам",
    "инвентар",
    "списан",
    "брак",
    "налог",
    "банк",
    "комисси",
]


def clean(text):
    return re.sub(
        r"\s+",
        " ",
        text
    ).strip()


def main():

    print()
    print("=" * 80)
    print("ИЩУ ДЕТАЛИЗАЦИЮ РАСХОДОВ В CRM PL")
    print("=" * 80)

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
        print("=" * 80)
        print("СТРОКИ ТАБЛИЦ")
        print("=" * 80)

        rows = page.locator("tr")

        count = rows.count()

        print(
            "Найдено <tr>:",
            count
        )

        seen = set()

        for i in range(count):

            text = clean(
                rows.nth(i).text_content() or ""
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
        print("=" * 80)
        print("ПОИСК НУЖНЫХ СТАТЕЙ В HTML")
        print("=" * 80)

        html = page.content()

        html_lower = html.lower()

        for keyword in KEYWORDS:

            found = (
                keyword.lower()
                in html_lower
            )

            print(
                f"{keyword:<12} : "
                f"{'НАЙДЕНО' if found else 'нет'}"
            )

        print()
        print("=" * 80)

        browser.close()


if __name__ == "__main__":
    main()