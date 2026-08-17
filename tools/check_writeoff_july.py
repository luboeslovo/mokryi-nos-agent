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
    "reports/retirementAndPosting/index"
)


def clean(text):
    return " ".join(
        (text or "").split()
    )


def main():

    print()
    print("=" * 100)
    print(
        "СПИСАНИЯ И ОПРИХОДОВАНИЯ — ИЮЛЬ 2026"
    )
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

        # Выставляем июль.
        page.locator(
            "#filters_dateRange"
        ).evaluate(
            """
            el => {
                el.value = '01.07.2026 - 31.07.2026';
                el.dispatchEvent(
                    new Event('input', {bubbles: true})
                );
                el.dispatchEvent(
                    new Event('change', {bubbles: true})
                );
            }
            """
        )

        # Стандартный отчёт.
        page.locator(
            "#filters_reportMode"
        ).select_option(
            "1"
        )

        # Периодичность: Нет.
        page.locator(
            "#filters_periodicity"
        ).select_option(
            "1"
        )

        # Группировка по причинам.
        page.locator(
            "#filters_reportGroupBy"
        ).select_option(
            "retirementAndPostingType"
        )

        # Все причины.
        page.locator(
            "#filters_retirementAndPostingType"
        ).select_option(
            "0"
        )

        # Данные: сумма.
        page.locator(
            "#filters_reportResultBy"
        ).select_option(
            "amount"
        )

        print()
        print(
            "Нажимаю «Показать»..."
        )

        button = page.get_by_role(
            "button",
            name="Показать"
        )

        button.click()

        page.wait_for_timeout(
            2000
        )

        try:
            page.wait_for_load_state(
                "networkidle",
                timeout=30000
            )
        except Exception:
            pass

        print()
        print(
            "URL после нажатия:"
        )
        print(
            page.url
        )

        print()
        print("-" * 100)
        print(
            "СТРОКИ ОТЧЁТА"
        )
        print("-" * 100)

        rows = page.locator(
            "table tr"
        )

        print(
            "Всего строк:",
            rows.count()
        )

        for i in range(
            rows.count()
        ):

            cells = rows.nth(i).locator(
                "th, td"
            )

            if cells.count() == 0:
                continue

            values = []

            for j in range(
                cells.count()
            ):

                values.append(
                    clean(
                        cells.nth(j)
                        .text_content()
                    )
                )

            text = " | ".join(
                values
            )

            if text:

                print(
                    f"{i:03d} | {text}"
                )

        if rows.count() == 0:

            print()
            print(
                "Таблицы нет."
            )

            body = clean(
                page.locator(
                    "body"
                ).text_content()
            )

            print()
            print(
                body[-1500:]
            )

        print()
        print("=" * 100)

        browser.close()


if __name__ == "__main__":
    main()