import csv
import os
from datetime import datetime


PROJECT_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

DAILY_SALES_FILE = os.path.join(
    PROJECT_DIR,
    "daily_sales.csv",
)


def parse_date(value):
    value = str(
        value or ""
    ).strip()

    for fmt in (
        "%d.%m.%Y",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(
                value,
                fmt,
            ).date()

        except ValueError:
            pass

    raise ValueError(
        f"Не удалось распознать дату: {value}"
    )


def to_float(value):
    try:
        return float(
            value or 0
        )

    except Exception:
        return 0.0


def to_int(value):
    try:
        return int(
            float(
                value or 0
            )
        )

    except Exception:
        return 0


def load_daily_sales():
    if not os.path.exists(
        DAILY_SALES_FILE
    ):
        raise FileNotFoundError(
            f"Не найден файл: {DAILY_SALES_FILE}"
        )

    rows = []

    with open(
        DAILY_SALES_FILE,
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        reader = csv.DictReader(
            file
        )

        for row in reader:
            try:
                date = parse_date(
                    row.get("date")
                )

            except Exception:
                continue

            row["_date"] = date

            rows.append(
                row
            )

    rows.sort(
        key=lambda row:
            row["_date"]
    )

    return rows


def compact_day(row):
    if not row:
        return None

    return {
        "date":
            row["_date"].strftime(
                "%d.%m.%Y"
            ),

        "total_revenue":
            round(
                to_float(
                    row.get(
                        "total_revenue"
                    )
                ),
                2,
            ),

        "check_revenue_net":
            round(
                to_float(
                    row.get(
                        "check_revenue_net"
                    )
                ),
                2,
            ),

        "checks":
            to_int(
                row.get(
                    "checks"
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

        "ktch":
            round(
                to_float(
                    row.get(
                        "ktch"
                    )
                ),
                2,
            ),

        "average_check":
            round(
                to_float(
                    row.get(
                        "average_check"
                    )
                ),
                2,
            ),

        "cash":
            round(
                to_float(
                    row.get(
                        "cash"
                    )
                ),
                2,
            ),

        "card":
            round(
                to_float(
                    row.get(
                        "card"
                    )
                ),
                2,
            ),

        "returns":
            round(
                to_float(
                    row.get(
                        "total_return"
                    )
                ),
                2,
            ),

        "self_pickup":
            round(
                to_float(
                    row.get(
                        "self_pickup"
                    )
                ),
                2,
            ),

        "yandex_food":
            round(
                to_float(
                    row.get(
                        "yandex_food"
                    )
                ),
                2,
            ),

        "kuper":
            round(
                to_float(
                    row.get(
                        "kuper"
                    )
                ),
                2,
            ),

        "external_total":
            round(
                to_float(
                    row.get(
                        "external_total"
                    )
                ),
                2,
            ),

        "yandex_orders":
            to_int(
                row.get(
                    "yandex_orders"
                )
            ),

        "kuper_orders":
            to_int(
                row.get(
                    "kuper_orders"
                )
            ),

        "external_orders":
            to_int(
                row.get(
                    "external_orders"
                )
            ),

        "no_receipt":
            round(
                to_float(
                    row.get(
                        "no_receipt"
                    )
                ),
                2,
            ),
    }


def get_latest_sales_day():
    rows = load_daily_sales()

    if not rows:
        return {
            "status": "no_data"
        }

    return {
        "status": "ok",
        "day": compact_day(
            rows[-1]
        ),
    }


def get_daily_sales(
    date=None,
):
    rows = load_daily_sales()

    if not rows:
        return {
            "status": "no_data"
        }

    if (
        date is None
        or str(date).strip().lower()
        in {
            "",
            "latest",
            "last",
            "последний",
            "последний день",
        }
    ):
        return {
            "status": "ok",
            "day": compact_day(
                rows[-1]
            ),
        }

    wanted_date = parse_date(
        date
    )

    for row in rows:
        if row["_date"] == wanted_date:
            return {
                "status": "ok",
                "day": compact_day(
                    row
                ),
            }

    return {
        "status": "not_found",

        "date":
            wanted_date.strftime(
                "%d.%m.%Y"
            ),

        "latest_available":
            rows[-1][
                "_date"
            ].strftime(
                "%d.%m.%Y"
            ),
    }


def percent_change(
    later,
    earlier,
):
    if earlier == 0:
        return None

    return round(
        (
            later
            - earlier
        )
        / abs(earlier)
        * 100,
        2,
    )


def build_metric_comparison(
    earlier_value,
    later_value,
):
    difference = (
        later_value
        - earlier_value
    )

    change_percent = (
        percent_change(
            later_value,
            earlier_value,
        )
    )

    if difference > 0:
        direction = "increase"

    elif difference < 0:
        direction = "decrease"

    else:
        direction = "no_change"

    return {
        "earlier":
            earlier_value,

        "later":
            later_value,

        "difference_later_minus_earlier":
            round(
                difference,
                2,
            ),

        "change_percent_vs_earlier":
            change_percent,

        "direction":
            direction,
    }


def compare_sales_days(
    date_a,
    date_b,
):
    result_a = get_daily_sales(
        date_a
    )

    result_b = get_daily_sales(
        date_b
    )

    if (
        result_a.get("status") != "ok"
        or result_b.get("status") != "ok"
    ):
        return {
            "status": "not_found",
            "date_a": result_a,
            "date_b": result_b,
        }

    day_a = result_a["day"]
    day_b = result_b["day"]

    parsed_a = parse_date(
        day_a["date"]
    )

    parsed_b = parse_date(
        day_b["date"]
    )

    if parsed_a <= parsed_b:
        earlier = day_a
        later = day_b

    else:
        earlier = day_b
        later = day_a

    metrics = {}

    for key in (
        "total_revenue",
        "check_revenue_net",
        "checks",
        "items",
        "ktch",
        "average_check",
        "external_total",
        "external_orders",
        "yandex_food",
        "yandex_orders",
    ):
        metrics[key] = (
            build_metric_comparison(
                earlier.get(
                    key,
                    0,
                ),
                later.get(
                    key,
                    0,
                ),
            )
        )

    return {
        "status": "ok",

        "comparison_direction":
            "later_vs_earlier",

        "earlier_date":
            earlier["date"],

        "later_date":
            later["date"],

        "metrics":
            metrics,
    }


def get_recent_sales(
    days=7,
):
    days = max(
        1,
        min(
            int(days),
            31,
        ),
    )

    rows = load_daily_sales()

    selected = rows[
        -days:
    ]

    return {
        "status": "ok",

        "days_requested":
            days,

        "days_returned":
            len(selected),

        "days": [
            compact_day(
                row
            )
            for row
            in selected
        ],
    }


def get_month_summary(
    year,
    month,
):
    year = int(
        year
    )

    month = int(
        month
    )

    rows = [
        row
        for row
        in load_daily_sales()
        if (
            row["_date"].year
            == year
            and row["_date"].month
            == month
        )
    ]

    if not rows:
        return {
            "status": "not_found",
            "year": year,
            "month": month,
        }

    total_revenue = sum(
        to_float(
            row.get(
                "total_revenue"
            )
        )
        for row in rows
    )

    check_revenue_net = sum(
        to_float(
            row.get(
                "check_revenue_net"
            )
        )
        for row in rows
    )

    checks = sum(
        to_int(
            row.get(
                "checks"
            )
        )
        for row in rows
    )

    items = sum(
        to_float(
            row.get(
                "items"
            )
        )
        for row in rows
    )

    external_total = sum(
        to_float(
            row.get(
                "external_total"
            )
        )
        for row in rows
    )

    external_orders = sum(
        to_int(
            row.get(
                "external_orders"
            )
        )
        for row in rows
    )

    yandex_food = sum(
        to_float(
            row.get(
                "yandex_food"
            )
        )
        for row in rows
    )

    yandex_orders = sum(
        to_int(
            row.get(
                "yandex_orders"
            )
        )
        for row in rows
    )

    returns = sum(
        to_float(
            row.get(
                "total_return"
            )
        )
        for row in rows
    )

    average_check = (
        check_revenue_net
        / checks
        if checks
        else 0
    )

    ktch = (
        items
        / checks
        if checks
        else 0
    )

    return {
        "status": "ok",

        "period": {
            "year": year,
            "month": month,

            "first_date":
                rows[0][
                    "_date"
                ].strftime(
                    "%d.%m.%Y"
                ),

            "last_date":
                rows[-1][
                    "_date"
                ].strftime(
                    "%d.%m.%Y"
                ),

            "days":
                len(rows),
        },

        "total_revenue":
            round(
                total_revenue,
                2,
            ),

        "check_revenue_net":
            round(
                check_revenue_net,
                2,
            ),

        "checks":
            checks,

        "items":
            round(
                items,
                2,
            ),

        "average_check":
            round(
                average_check,
                2,
            ),

        "ktch":
            round(
                ktch,
                2,
            ),

        "external_total":
            round(
                external_total,
                2,
            ),

        "external_orders":
            external_orders,

        "yandex_food":
            round(
                yandex_food,
                2,
            ),

        "yandex_orders":
            yandex_orders,

        "returns":
            round(
                returns,
                2,
            ),
    }


def demo():
    print()
    print("=" * 70)
    print(
        "SALES TOOLS — TEST"
    )
    print("=" * 70)

    latest = get_latest_sales_day()

    print()
    print(
        "Последний закрытый день:"
    )
    print(
        latest
    )

    rows = load_daily_sales()

    if len(rows) >= 2:
        latest_date = (
            rows[-1][
                "_date"
            ].strftime(
                "%d.%m.%Y"
            )
        )

        previous_date = (
            rows[-2][
                "_date"
            ].strftime(
                "%d.%m.%Y"
            )
        )

        print()
        print(
            "Сравнение последних двух дней:"
        )

        print(
            compare_sales_days(
                previous_date,
                latest_date,
            )
        )


if __name__ == "__main__":
    demo()