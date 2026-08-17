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

PL_URL = (
    "https://it.mokryinos.ru/"
    "reports/profitAndLost/index"
    "?showReport=1"
    "&filters%5BdateRange%5D=01.07.2026+-+31.07.2026"
    "&filters%5BreportMode%5D=1"
    "&filters%5Bperiodicity%5D=1"
)


KEYWORDS = [
    "Выручка",
    "Себестоимость",
    "Валовая прибыль",
    "Коммерческие расходы",
    "Прибыль от продаж",
    "Управленческие расходы",
    "Операционная прибыль",
    "EBITDA",
    "Прибыль до налогообложения",
    "Налоги",
    "Чистая прибыль",
]


def main():

    print()
    print("=" * 70)
    print("ПРОВЕРКА ОТЧЁТА PL")
    print("=" * 70)

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        context = browser.new_context(
            storage_state=AUTH_FILE
        )

        page = context.new_page()

        response = page.goto(
            PL_URL,
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

            print()
            print(
                "ОШИБКА: CRM отправила на страницу входа."
            )

            browser.close()
            return

        text = page.locator(
            "body"
        ).inner_text()

        lines = [
            line.strip()
            for line in text.splitlines()
            if line.strip()
        ]

        print()
        print("НАЙДЕННЫЕ СТРОКИ:")
        print("-" * 70)

        found = 0

        for line in lines:

            if any(
                keyword.lower() in line.lower()
                for keyword in KEYWORDS
            ):

                print(line)
                found += 1

        print("-" * 70)

        print(
            "Строк найдено:",
            found
        )

        browser.close()

    print("=" * 70)


if __name__ == "__main__":
    main()