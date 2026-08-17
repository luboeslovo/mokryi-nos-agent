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


def print_select_options(
    page,
    selector,
    title
):

    print()
    print("=" * 90)
    print(title)
    print("=" * 90)

    select = page.locator(
        selector
    )

    if select.count() == 0:

        print(
            "Поле не найдено:",
            selector
        )

        return

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
            f"value={value!r:<12} | {text}"
        )


def main():

    print()
    print("=" * 90)
    print(
        "ПРОДАЖИ CRM — ИСТОЧНИКИ И ПЕРИОДИЧНОСТЬ"
    )
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

        print()
        print(
            "URL:",
            page.url
        )

        print_select_options(
            page,
            "#filters_salesSource",
            "ИСТОЧНИКИ ПРОДАЖ"
        )

        print_select_options(
            page,
            "#filters_periodicity",
            "ПЕРИОДИЧНОСТЬ"
        )

        print_select_options(
            page,
            "#filters_reportGroupBy",
            "ГРУППИРОВКА"
        )

        print()
        print("=" * 90)

        browser.close()


if __name__ == "__main__":
    main()