import os
import re
from urllib.parse import urlencode, urljoin

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


def parse_money(text):

    text = (
        clean(text)
        .replace("\xa0", "")
        .replace(" ", "")
        .replace(",", ".")
    )

    if not text:
        return 0.0

    return float(text)


def collect_rows(page, seen_documents):

    result = []

    rows = page.locator(
        "table tr"
    )

    for i in range(
        rows.count()
    ):

        cells = rows.nth(i).locator(
            "td"
        )

        if cells.count() < 7:
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

        row_text = " | ".join(
            values
        )

        if "Проведен" not in row_text:
            continue

        if (
            "(Наличка)" not in row_text
            and "(Безнал)" not in row_text
        ):
            continue

        date_match = re.search(
            r"\b(\d{2}\.\d{2}\.\d{4})\b",
            row_text
        )

        if not date_match:
            continue

        date = date_match.group(1)

        # В таблице номер документа —
        # обычно третья содержательная колонка.
        document_number = None

        for value in values:

            if re.fullmatch(
                r"\d{5,}",
                value
            ):
                document_number = value
                break

        if not document_number:
            continue

        if document_number in seen_documents:
            continue

        seen_documents.add(
            document_number
        )

        amount = parse_money(
            values[-1]
        )

        if "(Наличка)" in row_text:
            payment_type = "cash"
        else:
            payment_type = "card"

        result.append(
            {
                "document_number":
                    document_number,

                "date":
                    date,

                "payment_type":
                    payment_type,

                "amount":
                    amount,
            }
        )

    return result


def main():

    print()
    print("=" * 90)
    print("ВЫЕМКИ ИЗ ККМ — ИЮЛЬ 2026")
    print("=" * 90)

    params = [
        (
            "ExtractingMoneyFromCashKkmDocument[date]",
            "01.07.2026 - 31.07.2026",
        ),
    ]

    first_url = (
        BASE_URL
        + "?"
        + urlencode(params)
    )

    all_rows = []
    seen_documents = set()

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        context = browser.new_context(
            storage_state=AUTH_FILE
        )

        page = context.new_page()

        page.goto(
            first_url,
            wait_until="networkidle",
            timeout=60000
        )

        if "/login" in page.url:

            print(
                "ОШИБКА: CRM отправила на login"
            )

            browser.close()
            return

        # Берём только реально существующие
        # страницы из пагинации CRM.
        page_urls = [
            first_url
        ]

        pagination_links = page.locator(
            ".pagination a"
        )

        for i in range(
            pagination_links.count()
        ):

            href = (
                pagination_links
                .nth(i)
                .get_attribute("href")
            )

            if not href:
                continue

            full_url = urljoin(
                BASE_URL,
                href
            )

            if full_url not in page_urls:
                page_urls.append(
                    full_url
                )

        # Сортируем:
        # первая страница,
        # потом page=2, page=3 и т.д.
        def page_number(url):

            match = re.search(
                r"ExtractingMoneyFromCashKkmDocument_page=(\d+)",
                url
            )

            if match:
                return int(
                    match.group(1)
                )

            return 1

        page_urls.sort(
            key=page_number
        )

        print()
        print(
            "Реальных страниц:",
            len(page_urls)
        )

        for index, url in enumerate(
            page_urls,
            start=1
        ):

            page.goto(
                url,
                wait_until="networkidle",
                timeout=60000
            )

            rows = collect_rows(
                page,
                seen_documents
            )

            all_rows.extend(
                rows
            )

            print(
                f"Страница {index}: "
                f"{len(rows)} уникальных документов"
            )

        browser.close()

    cash_by_day = {}
    card_by_day = {}

    for row in all_rows:

        date = row["date"]
        amount = row["amount"]

        if row["payment_type"] == "cash":

            cash_by_day[date] = (
                cash_by_day.get(
                    date,
                    0.0
                )
                + amount
            )

        else:

            card_by_day[date] = (
                card_by_day.get(
                    date,
                    0.0
                )
                + amount
            )

    dates = sorted(
        set(cash_by_day)
        | set(card_by_day),
        key=lambda x: (
            int(x[6:10]),
            int(x[3:5]),
            int(x[0:2]),
        )
    )

    print()
    print("-" * 90)
    print("ПО ДНЯМ")
    print("-" * 90)

    for date in dates:

        cash = cash_by_day.get(
            date,
            0.0
        )

        card = card_by_day.get(
            date,
            0.0
        )

        print(
            f"{date} | "
            f"НАЛ {cash:>10,.2f} | "
            f"БЕЗНАЛ {card:>10,.2f} | "
            f"ИТОГО {cash + card:>10,.2f}"
        )

    cash_total = round(
        sum(
            cash_by_day.values()
        ),
        2
    )

    card_total = round(
        sum(
            card_by_day.values()
        ),
        2
    )

    total = round(
        cash_total
        + card_total,
        2
    )

    print()
    print("=" * 90)
    print("ИТОГО ЗА ИЮЛЬ")
    print("=" * 90)

    print(
        "Уникальных документов:",
        len(all_rows)
    )

    print(
        "Дней:",
        len(dates)
    )

    print(
        "НАЛ:",
        f"{cash_total:,.2f} ₽"
    )

    print(
        "БЕЗНАЛ:",
        f"{card_total:,.2f} ₽"
    )

    print(
        "ВСЕГО:",
        f"{total:,.2f} ₽"
    )

    print("=" * 90)


if __name__ == "__main__":
    main()