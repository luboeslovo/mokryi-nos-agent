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
    "reports/sellSum/index"
)


def clean(text):
    return " ".join(
        (text or "").split()
    )


def main():

    print()
    print("=" * 90)
    print("ВАРИАНТЫ ПОКАЗАТЕЛЕЙ ОТЧЁТА «ПРОДАЖИ»")
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

        selectors = [
            "filters_reportResultBy",
            "filters_reportMode",
            "filters_periodicity",
        ]

        for selector_id in selectors:

            print()
            print("-" * 90)
            print(selector_id)
            print("-" * 90)

            select = page.locator(
                f"#{selector_id}"
            )

            if select.count() == 0:

                print("SELECT не найден")
                continue

            options = select.locator(
                "option"
            )

            print(
                "Вариантов:",
                options.count()
            )

            for i in range(
                options.count()
            ):

                option = options.nth(i)

                value = option.get_attribute(
                    "value"
                )

                text = clean(
                    option.text_content()
                )

                print(
                    f"value={value!r:<15} | {text}"
                )

        browser.close()

    print()
    print("=" * 90)


if __name__ == "__main__":
    main()