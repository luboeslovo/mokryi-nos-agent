import csv
import os
from datetime import datetime
from urllib.parse import urlencode

from playwright.sync_api import sync_playwright


PROJECT_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

AUTH_FILE = os.path.join(
    PROJECT_DIR,
    "auth.json",
)

OUTPUT_FILE = os.path.join(
    PROJECT_DIR,
    "delivery_sales_monthly.csv",
)

BASE_URL = (
    "https://it.mokryinos.ru/"
    "reports/sellSum/index"
)

CHANNELS = {
    "Купер": {
        "id": "3",
        "commission_rate": 0.19,
    },
    "Яндекс Еда": {
        "id": "4",
        "commission_rate": 0.1626,
    },
}


def parse_money(text):
    text = (
        (text or "")
        .replace("\xa0", "")
        .replace(" ", "")
        .replace(",", ".")
        .strip()
    )

    if not text:
        return 0.0

    return float(text)


def month_bounds(year, month):
    start = datetime(
        year,
        month,
        1,
    )

    if month == 12:
        next_month = datetime(
            year + 1,
            1,
            1,
        )
    else:
        next_month = datetime(
            year,
            month + 1,
            1,
        )

    end = next_month.replace(
        day=1,
    )

    from datetime import timedelta

    end = end - timedelta(
        days=1,
    )

    return start, end


def fetch_channel_sales(
    page,
    year,
    month,
    channel_id,
):

    start, end = month_bounds(
        year,
        month,
    )

    date_range = (
        start.strftime("%d.%m.%Y")
        + " - "
        + end.strftime("%d.%m.%Y")
    )

    params = [
        ("showReport", "1"),
        (
            "filters[dateRange]",
            date_range,
        ),
        (
            "filters[reportMode]",
            "1",
        ),
        (
            "filters[periodicity]",
            "1",
        ),
        (
            "filters[reportGroupBy]",
            "organizations",
        ),
        (
            "filters[salesSource][]",
            channel_id,
        ),
        (
            "filters[reportResultBy]",
            "amount",
        ),
    ]

    url = (
        BASE_URL
        + "?"
        + urlencode(params)
    )

    page.goto(
        url,
        wait_until="networkidle",
        timeout=60000,
    )

    if "/login" in page.url:
        raise RuntimeError(
            "CRM отправила на страницу login"
        )

    rows = page.locator(
        "table tr"
    )

    for i in range(
        rows.count()
    ):

        cells = rows.nth(i).locator(
            "td, th"
        )

        if cells.count() < 2:
            continue

        first = " ".join(
            (
                cells.nth(0)
                .text_content()
                or ""
            ).split()
        )

        second = " ".join(
            (
                cells.nth(1)
                .text_content()
                or ""
            ).split()
        )

        if first == "Итого":
            return parse_money(
                second
            )

    return 0.0


def load_existing():

    result = {}

    if not os.path.exists(
        OUTPUT_FILE
    ):
        return result

    with open(
        OUTPUT_FILE,
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        reader = csv.DictReader(
            file
        )

        for row in reader:

            result[row["month"]] = row

    return result


def save_rows(rows):

    fieldnames = [
        "month",
        "yandex_sales",
        "yandex_commission",
        "kuper_sales",
        "kuper_commission",
        "delivery_sales",
        "delivery_commission",
        "updated_at",
    ]

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for month in sorted(rows):

            writer.writerow(
                rows[month]
            )


def main():

    print()
    print("=" * 70)
    print(
        "СИНХРОНИЗАЦИЯ ПРОДАЖ "
        "ЯНДЕКС ЕДА И КУПЕР"
    )
    print("=" * 70)

    now = datetime.now()

    # Для первой проверки обязательно
    # пересчитываем июль и текущий месяц.
    months_to_refresh = {
        (2026, 7),
        (
            now.year,
            now.month,
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
            months_to_refresh
        ):

            month_key = (
                f"{year:04d}-{month:02d}"
            )

            print()
            print(
                f"Получаю {month_key}..."
            )

            yandex_sales = (
                fetch_channel_sales(
                    page,
                    year,
                    month,
                    CHANNELS[
                        "Яндекс Еда"
                    ]["id"],
                )
            )

            kuper_sales = (
                fetch_channel_sales(
                    page,
                    year,
                    month,
                    CHANNELS[
                        "Купер"
                    ]["id"],
                )
            )

            yandex_commission = round(
                yandex_sales
                * CHANNELS[
                    "Яндекс Еда"
                ]["commission_rate"],
                2,
            )

            kuper_commission = round(
                kuper_sales
                * CHANNELS[
                    "Купер"
                ]["commission_rate"],
                2,
            )

            delivery_sales = round(
                yandex_sales
                + kuper_sales,
                2,
            )

            delivery_commission = round(
                yandex_commission
                + kuper_commission,
                2,
            )

            existing[month_key] = {
                "month":
                    month_key,

                "yandex_sales":
                    f"{yandex_sales:.2f}",

                "yandex_commission":
                    f"{yandex_commission:.2f}",

                "kuper_sales":
                    f"{kuper_sales:.2f}",

                "kuper_commission":
                    f"{kuper_commission:.2f}",

                "delivery_sales":
                    f"{delivery_sales:.2f}",

                "delivery_commission":
                    f"{delivery_commission:.2f}",

                "updated_at":
                    datetime.now().isoformat(
                        timespec="seconds"
                    ),
            }

            print(
                "Яндекс Еда:",
                f"{yandex_sales:,.2f} ₽",
                "→ комиссия",
                f"{yandex_commission:,.2f} ₽",
            )

            print(
                "Купер:",
                f"{kuper_sales:,.2f} ₽",
                "→ комиссия",
                f"{kuper_commission:,.2f} ₽",
            )

            print(
                "Итого комиссия:",
                f"{delivery_commission:,.2f} ₽",
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
        OUTPUT_FILE,
    )


if __name__ == "__main__":
    main()