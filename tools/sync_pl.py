import csv
import os
import re
from calendar import monthrange
from datetime import datetime

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
    "pl_monthly.csv"
)

START_YEAR = 2025
START_MONTH = 1


FIELDS = [
    "Выручка",
    "Себестоимость",
    "Валовая прибыль",
    "Коммерческие расходы",
    "Прибыль от продаж",
    "Управленческие расходы",
    "Операционная прибыль (EBITDA)",
    "Прибыль до налогообложения",
    "Налоги",
    "Чистая прибыль",
]


def month_key(year, month):

    return f"{year:04d}-{month:02d}"


def month_url(year, month):

    last_day = monthrange(
        year,
        month
    )[1]

    start = (
        f"01.{month:02d}.{year}"
    )

    end = (
        f"{last_day:02d}."
        f"{month:02d}."
        f"{year}"
    )

    return (
        "https://it.mokryinos.ru/"
        "reports/profitAndLost/index"
        "?showReport=1"
        f"&filters%5BdateRange%5D={start}+-+{end}"
        "&filters%5BreportMode%5D=1"
        "&filters%5Bperiodicity%5D=1"
    )


def parse_number(text):

    text = (
        text
        .replace("\xa0", "")
        .replace(" ", "")
        .replace(",", ".")
    )

    return round(
        float(text),
        2
    )


def extract_pl(text):

    result = {}

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    for line in lines:

        for field in FIELDS:

            if not line.startswith(field):
                continue

            tail = line[
                len(field):
            ].strip()

            match = re.search(
                r"-?\d[\d\s\xa0]*,\d{2}",
                tail
            )

            if match:

                result[field] = (
                    parse_number(
                        match.group(0)
                    )
                )

    return result


def load_existing():

    if not os.path.exists(
        OUTPUT_FILE
    ):
        return {}

    rows = {}

    with open(
        OUTPUT_FILE,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        for row in csv.DictReader(
            file
        ):

            rows[
                row["month"]
            ] = row

    return rows


def months_between(
    start_year,
    start_month,
    end_year,
    end_month
):

    year = start_year
    month = start_month

    result = []

    while (
        year < end_year
        or (
            year == end_year
            and month <= end_month
        )
    ):

        result.append(
            (
                year,
                month
            )
        )

        month += 1

        if month == 13:

            month = 1
            year += 1

    return result


def previous_month(
    year,
    month
):

    month -= 1

    if month == 0:

        month = 12
        year -= 1

    return (
        year,
        month
    )


def fetch_month(
    page,
    year,
    month
):

    key = month_key(
        year,
        month
    )

    url = month_url(
        year,
        month
    )

    response = page.goto(
        url,
        wait_until="networkidle",
        timeout=60000
    )

    if not response:

        raise RuntimeError(
            f"{key}: нет HTTP-ответа"
        )

    if "/login" in page.url:

        raise RuntimeError(
            f"{key}: CRM отправила на login"
        )

    if response.status != 200:

        raise RuntimeError(
            f"{key}: HTTP {response.status}"
        )

    text = page.locator(
        "body"
    ).inner_text()

    data = extract_pl(
        text
    )

    if "Выручка" not in data:

        raise RuntimeError(
            f"{key}: не найдена выручка"
        )

    row = {
        "month": key,
    }

    for field in FIELDS:

        row[field] = data.get(
            field,
            0.0
        )

    return row


def save_rows(rows):

    fieldnames = [
        "month",
        *FIELDS,
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

        for key in sorted(
            rows.keys()
        ):

            writer.writerow(
                rows[key]
            )


def main():

    now = datetime.now()

    existing = load_existing()

    all_months = months_between(
        START_YEAR,
        START_MONTH,
        now.year,
        now.month
    )

    prev_year, prev_month = (
        previous_month(
            now.year,
            now.month
        )
    )

    refresh_keys = {
        month_key(
            now.year,
            now.month
        ),
        month_key(
            prev_year,
            prev_month
        ),
    }

    months_to_fetch = []

    for year, month in all_months:

        key = month_key(
            year,
            month
        )

        if (
            key not in existing
            or key in refresh_keys
        ):

            months_to_fetch.append(
                (
                    year,
                    month
                )
            )

    print()
    print("=" * 70)
    print("СИНХРОНИЗАЦИЯ PL ИЗ CRM")
    print("=" * 70)

    print()
    print(
        "Месяцев уже сохранено:",
        len(existing)
    )

    print(
        "Нужно получить:",
        len(months_to_fetch)
    )

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        context = browser.new_context(
            storage_state=AUTH_FILE
        )

        page = context.new_page()

        for index, (
            year,
            month
        ) in enumerate(
            months_to_fetch,
            start=1
        ):

            row = fetch_month(
                page,
                year,
                month
            )

            existing[
                row["month"]
            ] = row

            print(
                f"{index}/{len(months_to_fetch)} | "
                f"{row['month']} | "
                f"Выручка: "
                f"{row['Выручка']:,.2f} | "
                f"EBITDA: "
                f"{row['Операционная прибыль (EBITDA)']:,.2f}"
            )

        browser.close()

    save_rows(
        existing
    )

    print()
    print("=" * 70)
    print("PL СИНХРОНИЗИРОВАН")
    print("=" * 70)

    print()
    print(
        "Месяцев в базе:",
        len(existing)
    )

    print(
        "Файл:",
        OUTPUT_FILE
    )

    print("=" * 70)


if __name__ == "__main__":
    main()