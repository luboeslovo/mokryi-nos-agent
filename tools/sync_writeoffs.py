import csv
import os
from datetime import datetime, timedelta

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
    "writeoffs_monthly.csv"
)

URL = (
    "https://it.mokryinos.ru/"
    "reports/retirementAndPosting/index"
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


def month_bounds(year, month):

    start = datetime(
        year,
        month,
        1
    )

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

    end = (
        next_month
        - timedelta(days=1)
    )

    return start, end


def fetch_month(
    page,
    year,
    month
):

    start, end = month_bounds(
        year,
        month
    )

    date_range = (
        start.strftime("%d.%m.%Y")
        + " - "
        + end.strftime("%d.%m.%Y")
    )

    page.goto(
        URL,
        wait_until="networkidle",
        timeout=60000
    )

    if "/login" in page.url:
        raise RuntimeError(
            "CRM отправила на login"
        )

    page.locator(
        "#filters_dateRange"
    ).evaluate(
        """
        (el, value) => {
            el.value = value;
            el.dispatchEvent(
                new Event(
                    'input',
                    {bubbles: true}
                )
            );
            el.dispatchEvent(
                new Event(
                    'change',
                    {bubbles: true}
                )
            );
        }
        """,
        date_range
    )

    page.locator(
        "#filters_reportMode"
    ).select_option("1")

    page.locator(
        "#filters_periodicity"
    ).select_option("1")

    page.locator(
        "#filters_reportGroupBy"
    ).select_option(
        "retirementAndPostingType"
    )

    page.locator(
        "#filters_retirementAndPostingType"
    ).select_option("0")

    page.locator(
        "#filters_reportResultBy"
    ).select_option("amount")

    page.get_by_role(
        "button",
        name="Показать"
    ).click()

    try:
        page.wait_for_load_state(
            "networkidle",
            timeout=30000
        )
    except Exception:
        pass

    page.wait_for_timeout(1000)

    result = {
        "inventory": 0.0,
        "consumables": 0.0,
        "expired": 0.0,
        "samples": 0.0,
        "defect": 0.0,
    }

    mapping = {
        "инвентаризация":
            "inventory",

        "расходные материалы":
            "consumables",

        "просрочка":
            "expired",

        "образцы дистрибуции":
            "samples",

        "брак":
            "defect",
    }

    rows = page.locator(
        "table tr"
    )

    for i in range(
        rows.count()
    ):

        cells = rows.nth(i).locator(
            "th, td"
        )

        if cells.count() < 2:
            continue

        name = clean(
            cells.nth(0).text_content()
        ).lower()

        value = parse_money(
            cells.nth(1).text_content()
        )

        if name in mapping:

            # В CRM списания отрицательные,
            # в ОПиУ расходы записываем
            # положительными числами.
            result[
                mapping[name]
            ] = abs(value)

    return result


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
        newline=""
    ) as file:

        reader = csv.DictReader(
            file
        )

        for row in reader:
            result[
                row["month"]
            ] = row

    return result


def save_rows(rows):

    fields = [
        "month",
        "inventory",
        "consumables",
        "expired",
        "samples",
        "defect",
        "opiu_inventory_total",
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
            fieldnames=fields
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
        "СИНХРОНИЗАЦИЯ СПИСАНИЙ CRM"
    )
    print("=" * 70)

    now = datetime.now()

    # Пока для проверки обновляем
    # июль и текущий месяц.
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

            data = fetch_month(
                page,
                year,
                month
            )

            opiu_total = round(
                data["inventory"]
                + data["expired"]
                + data["samples"]
                + data["defect"],
                2
            )

            existing[
                month_key
            ] = {
                "month":
                    month_key,

                "inventory":
                    f"{data['inventory']:.2f}",

                "consumables":
                    f"{data['consumables']:.2f}",

                "expired":
                    f"{data['expired']:.2f}",

                "samples":
                    f"{data['samples']:.2f}",

                "defect":
                    f"{data['defect']:.2f}",

                "opiu_inventory_total":
                    f"{opiu_total:.2f}",

                "updated_at":
                    datetime.now().isoformat(
                        timespec="seconds"
                    ),
            }

            print(
                "Инвентаризация:",
                f"{data['inventory']:,.2f} ₽"
            )

            print(
                "Расходные материалы:",
                f"{data['consumables']:,.2f} ₽"
            )

            print(
                "Просрочка:",
                f"{data['expired']:,.2f} ₽"
            )

            print(
                "Образцы:",
                f"{data['samples']:,.2f} ₽"
            )

            print(
                "Брак:",
                f"{data['defect']:,.2f} ₽"
            )

            print(
                "Итого в расход ОПиУ:",
                f"{opiu_total:,.2f} ₽"
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