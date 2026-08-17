import os
from collections import defaultdict
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
    "reports/paymentDocument/index"
)

DOCUMENT_TYPES = {
    "1": "ПКО",
    "2": "РКО",
    "3": "Входящие платежи",
    "4": "Исходящие платежи",
}


def clean(text):
    return " ".join(
        (text or "").split()
    )


def parse_amount(text):

    text = clean(text)

    text = (
        text
        .replace("\xa0", "")
        .replace(" ", "")
        .replace(",", ".")
    )

    if not text:
        return 0.0

    try:
        return float(text)
    except ValueError:
        return 0.0


def make_url(document_type):

    params = [
        (
            "showReport",
            "1",
        ),
        (
            "filters[dateRange]",
            "01.07.2026 - 31.07.2026",
        ),
        (
            "filters[documentType][]",
            document_type,
        ),
    ]

    return (
        BASE_URL
        + "?"
        + urlencode(params)
    )


def main():

    print()
    print("=" * 100)
    print("ПЛАТЕЖНЫЕ ДОКУМЕНТЫ — ИЮЛЬ 2026")
    print("АГРЕГАЦИЯ ПО СТАТЬЯМ PL")
    print("=" * 100)

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        context = browser.new_context(
            storage_state=AUTH_FILE
        )

        page = context.new_page()

        for document_type, document_name in DOCUMENT_TYPES.items():

            print()
            print("=" * 100)
            print(
                f"{document_type} — {document_name}"
            )
            print("=" * 100)

            url = make_url(
                document_type
            )

            response = page.goto(
                url,
                wait_until="networkidle",
                timeout=60000
            )

            print(
                "HTTP:",
                response.status if response else "?"
            )

            if "/login" in page.url:

                print(
                    "ОШИБКА: CRM отправила на login"
                )

                browser.close()
                return

            rows = page.locator(
                "table tr"
            )

            articles = defaultdict(
                lambda: {
                    "count": 0,
                    "amount": 0.0,
                }
            )

            real_rows = 0
            total_amount = 0.0

            for i in range(
                rows.count()
            ):

                cells = rows.nth(i).locator(
                    "td"
                )

                if cells.count() < 9:
                    continue

                values = [
                    clean(
                        cells.nth(j).text_content()
                    )
                    for j in range(
                        cells.count()
                    )
                ]

                if (
                    not values
                    or "Нет результатов" in " ".join(values)
                ):
                    continue

                pl_article = values[6]

                amount = parse_amount(
                    values[8]
                )

                real_rows += 1
                total_amount += amount

                if not pl_article:
                    pl_article = "(без статьи PL)"

                articles[
                    pl_article
                ]["count"] += 1

                articles[
                    pl_article
                ]["amount"] += amount

            print()
            print(
                "Документов:",
                real_rows
            )

            print(
                "Сумма:",
                f"{total_amount:,.2f} ₽"
            )

            print()
            print("СТАТЬИ PL:")
            print("-" * 100)

            if not articles:

                print(
                    "Нет данных."
                )

            else:

                sorted_articles = sorted(
                    articles.items(),
                    key=lambda item: (
                        -item[1]["amount"],
                        item[0],
                    )
                )

                for article, data in sorted_articles:

                    print(
                        f"{article:<65} | "
                        f"{data['count']:>3} док. | "
                        f"{data['amount']:>12,.2f} ₽"
                    )

        browser.close()

    print()
    print("=" * 100)


if __name__ == "__main__":
    main()