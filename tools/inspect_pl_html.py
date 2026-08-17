import os
import re
from html import unescape

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
    "интернет",
    "рко",
    "эквайр",
    "заработ",
    "инвентар",
    "списан",
    "банк",
]


def clean_html_fragment(text):

    text = unescape(text)

    text = re.sub(
        r"<[^>]+>",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def main():

    print()
    print("=" * 90)
    print("ИЩУ СКРЫТУЮ ДЕТАЛИЗАЦИЮ PL")
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

        if "/login" in page.url:
            print("ОШИБКА: CRM отправила на login")
            browser.close()
            return

        html = page.content()

        html_lower = html.lower()

        for keyword in KEYWORDS:

            print()
            print("=" * 90)
            print(
                "КЛЮЧЕВОЕ СЛОВО:",
                keyword
            )
            print("=" * 90)

            positions = []

            start = 0

            while True:

                pos = html_lower.find(
                    keyword.lower(),
                    start
                )

                if pos == -1:
                    break

                positions.append(pos)

                start = pos + len(keyword)

            print(
                "Совпадений:",
                len(positions)
            )

            for number, pos in enumerate(
                positions[:5],
                start=1
            ):

                left = max(
                    0,
                    pos - 600
                )

                right = min(
                    len(html),
                    pos + 900
                )

                fragment = html[
                    left:right
                ]

                cleaned = clean_html_fragment(
                    fragment
                )

                print()
                print(
                    f"[{number}]"
                )

                print(
                    cleaned
                )

        browser.close()

    print()
    print("=" * 90)


if __name__ == "__main__":
    main()