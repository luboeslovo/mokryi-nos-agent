import csv
import os
from datetime import datetime


PROJECT_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

HISTORICAL_DAILY_PATH = os.path.join(
    PROJECT_DIR,
    "historical_daily_checks.csv",
)


def to_float(value):

    if value is None:
        return 0.0

    text = (
        str(value)
        .replace("\xa0", "")
        .replace(" ", "")
        .replace(",", ".")
        .strip()
    )

    if not text:
        return 0.0

    try:
        return float(text)

    except Exception:
        return 0.0


def to_int(value):

    try:
        return int(
            round(
                to_float(value)
            )
        )

    except Exception:
        return 0


def parse_date(value):

    if isinstance(
        value,
        datetime,
    ):
        return value

    text = str(
        value or ""
    ).strip()

    formats = [
        "%d.%m.%Y",
        "%Y-%m-%d",
        "%d.%m.%Y %H:%M",
        "%d.%m.%Y %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
    ]

    for fmt in formats:

        try:
            return datetime.strptime(
                text,
                fmt,
            )

        except ValueError:
            continue

    raise ValueError(
        f"Не удалось распознать дату: {value!r}"
    )


def round_money(value):

    return round(
        float(value or 0),
        2,
    )


def load_historical_daily_checks():

    if not os.path.exists(
        HISTORICAL_DAILY_PATH
    ):

        return []

    rows = []

    with open(
        HISTORICAL_DAILY_PATH,
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        reader = csv.DictReader(
            file
        )

        for raw in reader:

            date_text = str(
                raw.get(
                    "date",
                    "",
                )
            ).strip()

            if not date_text:
                continue

            try:
                date_dt = parse_date(
                    date_text
                )

            except ValueError:
                continue

            row = dict(raw)

            row["_date"] = date_dt

            rows.append(
                row
            )

    rows.sort(
        key=lambda row:
            row["_date"]
    )

    return rows


def normalize_historical_day(row):

    return {
        "date":
            row["_date"].strftime(
                "%d.%m.%Y"
            ),

        "source":
            "historical_daily_checks",

        "source_name":
            (
                "checks_raw.csv"
                " + check_items.csv"
            ),

        "data_granularity":
            "daily",

        "data_scope":
            "checks_and_items",

        "full_revenue_available":
            False,

        "sales_revenue":
            round_money(
                to_float(
                    row.get(
                        "sales_revenue"
                    )
                )
            ),

        "returns":
            round_money(
                to_float(
                    row.get(
                        "returns"
                    )
                )
            ),

        "check_revenue_net":
            round_money(
                to_float(
                    row.get(
                        "check_revenue_net"
                    )
                )
            ),

        "checks":
            to_int(
                row.get(
                    "checks"
                )
            ),

        "return_checks":
            to_int(
                row.get(
                    "return_checks"
                )
            ),

        "items":
            round(
                to_float(
                    row.get(
                        "items"
                    )
                ),
                2,
            ),

        "returned_items":
            round(
                to_float(
                    row.get(
                        "returned_items"
                    )
                ),
                2,
            ),

        "average_check":
            round_money(
                to_float(
                    row.get(
                        "average_check"
                    )
                )
            ),

        "ktch":
            round(
                to_float(
                    row.get(
                        "ktch"
                    )
                ),
                2,
            ),

        "available_metrics": [
            "sales_revenue",
            "returns",
            "check_revenue_net",
            "checks",
            "return_checks",
            "items",
            "returned_items",
            "average_check",
            "ktch",
        ],

        "unavailable_metrics": [
            "total_revenue",
            "cash",
            "card",
            "self_pickup",
            "yandex_food",
            "kuper",
            "external_total",
            "yandex_orders",
            "kuper_orders",
            "external_orders",
            "no_receipt",
        ],

        "data_note":
            (
                "Для этой даты доступны точные "
                "чековые показатели и товары. "
                "Полная дневная выручка магазина "
                "не подтверждена, потому что "
                "исторические дневные данные по "
                "внешним каналам и продажам без "
                "чека не подключены."
            ),
    }


def get_historical_daily_sales(
    date,
):

    rows = (
        load_historical_daily_checks()
    )

    if not rows:

        return {
            "status":
                "no_data",
        }

    target = parse_date(
        date
    ).date()

    for row in rows:

        if (
            row["_date"].date()
            == target
        ):

            return {
                "status":
                    "ok",

                "day":
                    normalize_historical_day(
                        row
                    ),
            }

    return {
        "status":
            "not_found",

        "date":
            target.strftime(
                "%d.%m.%Y"
            ),

        "available_start_date":
            rows[0][
                "_date"
            ].strftime(
                "%d.%m.%Y"
            ),

        "available_end_date":
            rows[-1][
                "_date"
            ].strftime(
                "%d.%m.%Y"
            ),
    }


def get_historical_daily_coverage():

    rows = (
        load_historical_daily_checks()
    )

    if not rows:

        return {
            "status":
                "no_data",
        }

    return {
        "status":
            "ok",

        "start_date":
            rows[0][
                "_date"
            ].strftime(
                "%d.%m.%Y"
            ),

        "end_date":
            rows[-1][
                "_date"
            ].strftime(
                "%d.%m.%Y"
            ),

        "calendar_days":
            (
                rows[-1][
                    "_date"
                ].date()
                - rows[0][
                    "_date"
                ].date()
            ).days + 1,

        "rows":
            len(rows),

        "data_scope":
            "checks_and_items",

        "full_revenue_available":
            False,

        "note":
            (
                "Точная дневная история чеков, "
                "возвратов, товаров, среднего "
                "чека и КТЧ. Полная дневная "
                "выручка с внешними каналами "
                "для старой истории не заявляется."
            ),
    }


def demo():

    print()
    print("=" * 70)
    print(
        "HISTORICAL DAILY TOOLS — TEST"
    )
    print("=" * 70)

    coverage = (
        get_historical_daily_coverage()
    )

    print()
    print(
        "ПОКРЫТИЕ:"
    )

    print(
        coverage
    )

    print()
    print(
        "19.08.2025:"
    )

    print(
        get_historical_daily_sales(
            "19.08.2025"
        )
    )

    print()
    print(
        "29.01.2025:"
    )

    print(
        get_historical_daily_sales(
            "29.01.2025"
        )
    )


if __name__ == "__main__":

    demo()