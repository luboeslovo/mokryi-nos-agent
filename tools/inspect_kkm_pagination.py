import os
from urllib.parse import urlencode

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

BASE_URL = (
    "https://it.mokryinos.ru/"
    "extractingMoneyFromCashKkm/index"
)


def clean(text):
    return " ".join(
        (text or "").split()
    )


def main():

    print()
    print("=" * 100)
    print("ПАГИНАЦИЯ «ВЫЕМКИ ИЗ ККМ» — ИЮЛЬ 2026")
    print("=" * 100)

    params = [
        (
            "ExtractingMoneyFromCashKkmDocument[date]",
            "01.07.2026 - 31.07.2026",
        ),
    ]

    url = (
        BASE_URL
        + "?"
        + urlencode(params)
    )

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        context = browser.new_context(
            storage_state=AUTH_FILE
        )

        page = context.new_page()

        page.goto(
            url,
            wait_until="networkidle",
            timeout=60000
        )

        if "/login" in page.url:

            print(
                "ОШИБКА: CRM отправила на login"
            )

            browser.close()
            return

        print()
        print("URL:")
        print(page.url)

        print()
        print("-" * 100)
        print("ССЫЛКИ ПАГИНАЦИИ")
        print("-" * 100)

        links = page.locator(
            "ul.pagination a, .pagination a"
        )

        print(
            "Найдено ссылок:",
            links.count()
        )

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

            print(
                f"{i:02d} | "
                f"{text!r} -> {href}"
            )

        print()
        print("-" * 100)
        print("ИНФОРМАЦИЯ О КОЛИЧЕСТВЕ")
        print("-" * 100)

        body = clean(
            page.locator(
                "body"
            ).text_content()
        )

        for phrase in [
            "Элементы",
            "из",
        ]:

            if phrase in body:
                print(
                    body[
                        max(
                            0,
                            body.find(
                                phrase
                            ) - 100
                        ):
                        body.find(
                            phrase
                        ) + 200
                    ]
                )
                break

        print()
        print("=" * 100)

        browser.close()


if __name__ == "__main__":
    main()