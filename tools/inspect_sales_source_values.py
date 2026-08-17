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

URL = "https://it.mokryinos.ru/reports/sellSum/index"

TARGETS = [
    "Яндекс Еда",
    "Купер",
]


def clean(text):
    return " ".join(
        (text or "").split()
    )


def main():

    print()
    print("=" * 100)
    print("ИЩУ ID КАНАЛОВ ПРОДАЖ")
    print("=" * 100)

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

        select = page.locator(
            "#filters_salesSource"
        )

        print()
        print("SELECT:")
        print(
            select.evaluate(
                "el => el.outerHTML"
            )
        )

        for target in TARGETS:

            print()
            print("-" * 100)
            print("ИЩУ:", target)
            print("-" * 100)

            # Открываем Select2 через jQuery
            page.evaluate(
                """
                () => {
                    $('#filters_salesSource')
                        .select2('open');
                }
                """
            )

            page.wait_for_timeout(500)

            search = page.locator(
                ".select2-container--open "
                "input.select2-search__field"
            )

            if search.count():

                search.fill(target)

                page.wait_for_timeout(1500)

            options = page.locator(
                ".select2-container--open "
                ".select2-results__option"
            )

            print(
                "Вариантов найдено:",
                options.count()
            )

            chosen = False

            for i in range(
                options.count()
            ):

                option = options.nth(i)

                text = clean(
                    option.text_content()
                )

                print(
                    f"{i:02d} | {text}"
                )

                if (
                    target.lower()
                    in text.lower()
                ):

                    option.click()

                    page.wait_for_timeout(
                        500
                    )

                    chosen = True
                    break

            if not chosen:

                print(
                    "НЕ УДАЛОСЬ ВЫБРАТЬ"
                )

                page.keyboard.press(
                    "Escape"
                )

                continue

            values = select.evaluate(
                """
                el => Array.from(
                    el.selectedOptions
                ).map(
                    option => ({
                        value: option.value,
                        text: option.textContent.trim()
                    })
                )
                """
            )

            print()
            print(
                "ВЫБРАННОЕ:",
                values
            )

            # Очищаем перед следующим поиском
            page.evaluate(
                """
                () => {
                    $('#filters_salesSource')
                        .val(null)
                        .trigger('change');
                }
                """
            )

        print()
        print("=" * 100)

        browser.close()


if __name__ == "__main__":
    main()