import csv
import os
import re
from datetime import datetime
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

OUTPUT_FILE = os.path.join(
    PROJECT_DIR,
    "kkm_daily.csv"
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


def collect_rows(
    page,
    seen_documents
):

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

        if cells.count() < 2:
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

        date = date_match.group(1)

        amount = parse_money(
            values[-1]
        )

        if "(Наличка)" in row_text:
            payment_type = "cash"
        else:
            payment_type = "card"

        result.append(
            {
                "date":
                    date,

                "document_number":
                    document_number,

                "payment_type":
                    payment_type,

                "amount":
                    amount,
            }
        )

    return result


def fetch_month(
    page,
    year,
    month
):

    if month == 12:

        next_month = datetime(
            year + 1,
            1,
            1
        )

    else:

        next_month = datetime(
            year,
            month + 1,
            1
        )

    last_day = (
        next_month
        - __import__(
            "datetime"
        ).timedelta(days=1)
    )

    date_range = (
        f"01.{month:02d}.{year:04d}"
        + " - "
        + last_day.strftime(
            "%d.%m.%Y"
        )
    )

    params = [
        (
            "ExtractingMoneyFromCashKkmDocument[date]",
            date_range,
        ),
    ]

    first_url = (
        BASE_URL
        + "?"
        + urlencode(params)
    )

    page.goto(
        first_url,
        wait_until="networkidle",
        timeout=60000
    )

    if "/login" in page.url:

        raise RuntimeError(
            "CRM отправила на login"
        )

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

    seen_documents = set()

    documents = []

    for url in page_urls:

        page.goto(
            url,
            wait_until="networkidle",
            timeout=60000
        )

        documents.extend(
            collect_rows(
                page,
                seen_documents
            )
        )

    by_day = {}

    for document in documents:

        date = document["date"]

        if date not in by_day:

            by_day[date] = {
                "cash": 0.0,
                "card": 0.0,
            }

        by_day[date][
            document["payment_type"]
        ] += document["amount"]

    result = []

    for date in sorted(
        by_day,
        key=lambda value: datetime.strptime(
            value,
            "%d.%m.%Y"
        )
    ):

        cash = round(
            by_day[date]["cash"],
            2
        )

        card = round(
            by_day[date]["card"],
            2
        )

        result.append(
            {
                "date":
                    date,

                "cash":
                    cash,

                "card":
                    card,

                "total":
                    round(
                        cash + card,
                        2
                    ),
            }
        )

    return (
        result,
        len(documents),
        len(page_urls),
    )


def load_existing():

    rows = {}

    if not os.path.exists(
        OUTPUT_FILE
    ):

        return rows

    with open(
        OUTPUT_FILE,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.DictReader(
            file
        )

        for row in reader:

            rows[
                row["date"]
            ] = row

    return rows


def save_rows(rows):

    fieldnames = [
        "date",
        "cash",
        "card",
        "total",
        "updated_at",
    ]

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()

        sorted_rows = sorted(
            rows.values(),
            key=lambda row: datetime.strptime(
                row["date"],
                "%d.%m.%Y"
            )
        )

        writer.writerows(
            sorted_rows
        )


def main():

    print()
    print("=" * 70)
    print(
        "СИНХРОНИЗАЦИЯ НАЛ / БЕЗНАЛ ИЗ ККМ"
    )
    print("=" * 70)

    now = datetime.now()

    months = {
        (2026, 7),
        (
            now.year,
            now.month
        ),
    }

    existing = load_existing()

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        context = browser.new_context(
            storage_state=AUTH_FILE
        )

        page = context.new_page()

        for year, month in sorted(
            months
        ):

            month_key = (
                f"{year:04d}-{month:02d}"
            )

            print()
            print(
                f"Получаю {month_key}..."
            )

            (
                daily_rows,
                document_count,
                page_count,
            ) = fetch_month(
                page,
                year,
                month
            )

            # Удаляем старые значения
            # этого месяца перед обновлением.
            keys_to_delete = []

            for date in existing:

                parsed = datetime.strptime(
                    date,
                    "%d.%m.%Y"
                )

                if (
                    parsed.year == year
                    and parsed.month == month
                ):

                    keys_to_delete.append(
                        date
                    )

            for key in keys_to_delete:

                del existing[key]

            for row in daily_rows:

                existing[
                    row["date"]
                ] = {
                    "date":
                        row["date"],

                    "cash":
                        f"{row['cash']:.2f}",

                    "card":
                        f"{row['card']:.2f}",

                    "total":
                        f"{row['total']:.2f}",

                    "updated_at":
                        datetime.now().isoformat(
                            timespec="seconds"
                        ),
                }

            cash_total = round(
                sum(
                    row["cash"]
                    for row in daily_rows
                ),
                2
            )

            card_total = round(
                sum(
                    row["card"]
                    for row in daily_rows
                ),
                2
            )

            print(
                "Страниц:",
                page_count
            )

            print(
                "Документов:",
                document_count
            )

            print(
                "Дней:",
                len(daily_rows)
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
                f"{cash_total + card_total:,.2f} ₽"
            )

        browser.close()

    save_rows(
        existing
    )

    print()
    print("=" * 70)
    print("ГОТОВО")
    print("=" * 70)

    print(
        "Файл:",
        OUTPUT_FILE
    )


if __name__ == "__main__":

    main()