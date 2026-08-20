import calendar
import csv
import os
from datetime import datetime

from historical_daily_tools import get_historical_daily_sales


PROJECT_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

DAILY_SALES_PATH = os.path.join(
    PROJECT_DIR,
    "daily_sales.csv",
)

HISTORICAL_SALES_PATH = os.path.join(
    PROJECT_DIR,
    "historical_sales_monthly.csv",
)


SUM_METRICS = [
    "total_revenue",
    "check_revenue_net",
    "checks",
    "items",
    "cash",
    "card",
    "returns",
    "self_pickup",
    "yandex_food",
    "kuper",
    "external_total",
    "yandex_orders",
    "kuper_orders",
    "external_orders",
    "no_receipt",
]


MODERN_DAY_AVAILABLE_METRICS = [
    "total_revenue",
    "sales_revenue",
    "returns",
    "check_revenue_net",
    "checks",
    "return_checks",
    "items",
    "returned_items",
    "ktch",
    "average_check",
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
]


DAY_COMPARISON_METRICS = [
    "total_revenue",
    "sales_revenue",
    "returns",
    "check_revenue_net",
    "checks",
    "return_checks",
    "items",
    "returned_items",
    "ktch",
    "average_check",
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
]


def to_float(value):
    if value is None:
        return 0.0

    text = str(
        value
    ).strip()

    if not text:
        return 0.0

    text = (
        text
        .replace(
            "\xa0",
            "",
        )
        .replace(
            " ",
            "",
        )
        .replace(
            ",",
            ".",
        )
    )

    try:
        return float(
            text
        )

    except Exception:
        return 0.0


def to_int(value):
    try:
        return int(
            round(
                to_float(
                    value
                )
            )
        )

    except Exception:
        return 0


def to_bool(value):
    text = str(
        value or ""
    ).strip().lower()

    return text in {
        "1",
        "true",
        "yes",
        "да",
    }


def round_money(value):
    return round(
        float(
            value or 0
        ),
        2,
    )


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
        "%Y-%m-%d %H:%M:%S",
        "%d.%m.%Y %H:%M:%S",
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
        f"Не удалось распознать дату: {value}"
    )


def format_date(value):
    return parse_date(
        value
    ).strftime(
        "%d.%m.%Y"
    )


def load_daily_sales():
    if not os.path.exists(
        DAILY_SALES_PATH
    ):
        raise FileNotFoundError(
            f"Не найден файл: {DAILY_SALES_PATH}"
        )

    rows = []

    with open(
        DAILY_SALES_PATH,
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
                    ""
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

            row = dict(
                raw
            )

            row["_date"] = date_dt

            rows.append(
                row
            )

    rows.sort(
        key=lambda item:
            item["_date"]
    )

    return rows


def load_historical_sales():
    if not os.path.exists(
        HISTORICAL_SALES_PATH
    ):
        return []

    rows = []

    with open(
        HISTORICAL_SALES_PATH,
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        reader = csv.DictReader(
            file
        )

        for raw in reader:
            try:
                year = int(
                    raw.get(
                        "year",
                        0,
                    )
                )

                month = int(
                    raw.get(
                        "month",
                        0,
                    )
                )

            except Exception:
                continue

            if (
                year <= 0
                or month < 1
                or month > 12
            ):
                continue

            row = dict(
                raw
            )

            row["_year"] = year
            row["_month"] = month

            rows.append(
                row
            )

    rows.sort(
        key=lambda item: (
            item["_year"],
            item["_month"],
        )
    )

    return rows


def normalize_day(row):
    checks = to_int(
        row.get(
            "checks"
        )
    )

    return_checks = to_int(
        row.get(
            "return_checks"
        )
    )

    items = to_float(
        row.get(
            "items"
        )
    )

    returned_items = to_float(
        row.get(
            "returned_items"
        )
    )

    check_revenue_net = to_float(
        row.get(
            "check_revenue_net"
        )
    )

    returns = to_float(
        row.get(
            "returns",
            row.get(
                "total_return"
            ),
        )
    )

    sales_revenue = to_float(
        row.get(
            "sales_revenue",
            row.get(
                "check_revenue"
            ),
        )
    )

    if (
        sales_revenue == 0
        and check_revenue_net != 0
    ):
        sales_revenue = (
            check_revenue_net
            - returns
        )

    average_check = to_float(
        row.get(
            "average_check"
        )
    )

    if (
        average_check == 0
        and checks > 0
    ):
        average_check = (
            check_revenue_net
            / checks
        )

    ktch = to_float(
        row.get(
            "ktch"
        )
    )

    if (
        ktch == 0
        and checks > 0
    ):
        ktch = (
            items
            / checks
        )

    return {
        "date":
            row["_date"].strftime(
                "%d.%m.%Y"
            ),

        "source":
            "daily_sales",

        "source_name":
            "daily_sales.csv",

        "data_granularity":
            "daily",

        "data_scope":
            "full_sales",

        "full_revenue_available":
            True,

        "available_metrics":
            list(
                MODERN_DAY_AVAILABLE_METRICS
            ),

        "unavailable_metrics":
            [],

        "total_revenue":
            round_money(
                to_float(
                    row.get(
                        "total_revenue"
                    )
                )
            ),

        "sales_revenue":
            round_money(
                sales_revenue
            ),

        "returns":
            round_money(
                returns
            ),

        "check_revenue_net":
            round_money(
                check_revenue_net
            ),

        "checks":
            checks,

        "return_checks":
            return_checks,

        "items":
            round(
                items,
                2,
            ),

        "returned_items":
            round(
                returned_items,
                2,
            ),

        "ktch":
            round(
                ktch,
                2,
            ),

        "average_check":
            round_money(
                average_check
            ),

        "cash":
            round_money(
                to_float(
                    row.get(
                        "cash"
                    )
                )
            ),

        "card":
            round_money(
                to_float(
                    row.get(
                        "card"
                    )
                )
            ),

        "self_pickup":
            round_money(
                to_float(
                    row.get(
                        "self_pickup"
                    )
                )
            ),

        "yandex_food":
            round_money(
                to_float(
                    row.get(
                        "yandex_food"
                    )
                )
            ),

        "kuper":
            round_money(
                to_float(
                    row.get(
                        "kuper"
                    )
                )
            ),

        "external_total":
            round_money(
                to_float(
                    row.get(
                        "external_total"
                    )
                )
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
            round_money(
                to_float(
                    row.get(
                        "no_receipt"
                    )
                )
            ),

        "data_note":
            (
                "Для этой даты доступна полная "
                "дневная управленческая выручка "
                "из daily_sales.csv вместе с "
                "подключёнными каналами продаж."
            ),
    }


def normalize_historical_month(
    row,
):
    year = int(
        row["_year"]
    )

    month = int(
        row["_month"]
    )

    is_complete = to_bool(
        row.get(
            "is_complete"
        )
    )

    if not is_complete:
        return None

    days_in_month = (
        calendar.monthrange(
            year,
            month,
        )[1]
    )

    total_revenue = round_money(
        to_float(
            row.get(
                "total_revenue"
            )
        )
    )

    check_revenue_net = round_money(
        to_float(
            row.get(
                "check_revenue_net"
            )
        )
    )

    checks = to_int(
        row.get(
            "checks"
        )
    )

    average_check = round_money(
        to_float(
            row.get(
                "average_check"
            )
        )
    )

    ktch = round(
        to_float(
            row.get(
                "ktch"
            )
        ),
        2,
    )

    external_total = round_money(
        to_float(
            row.get(
                "external_total"
            )
        )
    )

    external_orders = to_int(
        row.get(
            "external_orders"
        )
    )

    summary = {
        "status":
            "ok",

        "source":
            "historical_monthly",

        "source_name":
            row.get(
                "source",
                "ПО ЧИСЛАМ",
            ),

        "data_granularity":
            "monthly",

        "year":
            year,

        "month":
            month,

        "start_date":
            f"01.{month:02d}.{year:04d}",

        "end_date":
            (
                f"{days_in_month:02d}."
                f"{month:02d}."
                f"{year:04d}"
            ),

        "days_in_month":
            days_in_month,

        "max_loaded_day":
            days_in_month,

        "is_complete":
            True,

        "total_revenue":
            total_revenue,

        "check_revenue_net":
            check_revenue_net,

        "checks":
            checks,

        "average_check":
            average_check,

        "ktch":
            ktch,

        "cash":
            round_money(
                to_float(
                    row.get(
                        "cash"
                    )
                )
            ),

        "card":
            round_money(
                to_float(
                    row.get(
                        "card"
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

        "self_pickup":
            round_money(
                to_float(
                    row.get(
                        "self_pickup"
                    )
                )
            ),

        "yandex_food":
            round_money(
                to_float(
                    row.get(
                        "yandex_food"
                    )
                )
            ),

        "kuper":
            round_money(
                to_float(
                    row.get(
                        "kuper"
                    )
                )
            ),

        "external_total":
            external_total,

        "external_orders":
            external_orders,

        "no_receipt":
            round_money(
                to_float(
                    row.get(
                        "no_receipt"
                    )
                )
            ),

        "revenue_per_data_day":
            round_money(
                total_revenue
                / days_in_month
            ),

        "checks_per_data_day":
            round(
                checks
                / days_in_month,
                2,
            ),

        "external_revenue_per_data_day":
            round_money(
                external_total
                / days_in_month
            ),

        "historical_note":
            (
                "Месячный итог взят из "
                "исторического листа «ПО ЧИСЛАМ». "
                "Для этого периода нет детальной "
                "дневной аналитики в daily_sales.csv."
            ),
    }

    return summary


def get_historical_month_summary(
    year,
    month,
):
    year = int(
        year
    )

    month = int(
        month
    )

    rows = load_historical_sales()

    for row in rows:
        if (
            row["_year"] == year
            and row["_month"] == month
        ):
            summary = (
                normalize_historical_month(
                    row
                )
            )

            if summary is None:
                return {
                    "status":
                        "not_found",

                    "year":
                        year,

                    "month":
                        month,

                    "reason":
                        "historical_month_not_complete",
                }

            return summary

    return {
        "status":
            "not_found",

        "year":
            year,

        "month":
            month,
    }


def get_latest_sales_day():
    rows = load_daily_sales()

    if not rows:
        return {
            "status":
                "no_data",
        }

    return {
        "status":
            "ok",

        "day":
            normalize_day(
                rows[-1]
            ),
    }


def get_daily_sales(date=None):
    rows = load_daily_sales()

    if (
        date is None
        or str(
            date
        ).strip().lower()
        in {
            "",
            "latest",
            "последний",
        }
    ):
        if not rows:
            return {
                "status":
                    "no_data",
            }

        return {
            "status":
                "ok",

            "day":
                normalize_day(
                    rows[-1]
                ),
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
                    normalize_day(
                        row
                    ),
            }

    historical = (
        get_historical_daily_sales(
            target.strftime(
                "%d.%m.%Y"
            )
        )
    )

    if (
        historical.get(
            "status"
        )
        == "ok"
    ):
        return historical

    return {
        "status":
            "not_found",

        "date":
            target.strftime(
                "%d.%m.%Y"
            ),

        "historical_result":
            historical,
    }


def percent_change(
    later,
    earlier,
):
    later = to_float(
        later
    )

    earlier = to_float(
        earlier
    )

    if earlier == 0:
        return None

    return round(
        (
            later
            - earlier
        )
        / abs(
            earlier
        )
        * 100,
        2,
    )


def metric_comparison(
    earlier,
    later,
):
    earlier = to_float(
        earlier
    )

    later = to_float(
        later
    )

    difference = round(
        later - earlier,
        2,
    )

    if difference > 0:
        direction = "increase"

    elif difference < 0:
        direction = "decrease"

    else:
        direction = "same"

    return {
        "earlier":
            round(
                earlier,
                2,
            ),

        "later":
            round(
                later,
                2,
            ),

        "difference_later_minus_earlier":
            difference,

        "change_percent_vs_earlier":
            percent_change(
                later,
                earlier,
            ),

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
        result_a.get(
            "status"
        )
        != "ok"
        or result_b.get(
            "status"
        )
        != "ok"
    ):
        return {
            "status":
                "missing_data",

            "date_a":
                date_a,

            "date_b":
                date_b,

            "result_a":
                result_a,

            "result_b":
                result_b,
        }

    day_a = result_a[
        "day"
    ]

    day_b = result_b[
        "day"
    ]

    dt_a = parse_date(
        day_a["date"]
    )

    dt_b = parse_date(
        day_b["date"]
    )

    if dt_a <= dt_b:
        earlier = day_a
        later = day_b

    else:
        earlier = day_b
        later = day_a

    earlier_available = set(
        earlier.get(
            "available_metrics",
            [],
        )
    )

    later_available = set(
        later.get(
            "available_metrics",
            [],
        )
    )

    common_metrics = [
        metric
        for metric in DAY_COMPARISON_METRICS
        if (
            metric in earlier_available
            and metric in later_available
        )
    ]

    metrics = {}

    for metric in common_metrics:
        metrics[
            metric
        ] = metric_comparison(
            earlier.get(
                metric
            ),
            later.get(
                metric
            ),
        )

    excluded_metrics = [
        metric
        for metric in DAY_COMPARISON_METRICS
        if metric not in common_metrics
    ]

    full_revenue_comparable = (
        "total_revenue"
        in common_metrics
    )

    if not common_metrics:
        return {
            "status":
                "no_common_metrics",

            "earlier_day":
                earlier,

            "later_day":
                later,
        }

    return {
        "status":
            "ok",

        "comparison_direction":
            "later_vs_earlier",

        "comparison_scope":
            (
                "full_sales"
                if full_revenue_comparable
                else "common_available_metrics"
            ),

        "full_revenue_comparable":
            full_revenue_comparable,

        "earlier_date":
            earlier["date"],

        "later_date":
            later["date"],

        "earlier_source":
            earlier.get(
                "source"
            ),

        "later_source":
            later.get(
                "source"
            ),

        "earlier_data_scope":
            earlier.get(
                "data_scope"
            ),

        "later_data_scope":
            later.get(
                "data_scope"
            ),

        "common_metrics":
            common_metrics,

        "excluded_metrics":
            excluded_metrics,

        "metrics":
            metrics,

        "earlier_day":
            earlier,

        "later_day":
            later,

        "comparison_note":
            (
                "Полная дневная выручка доступна "
                "для обеих дат, поэтому сравнение "
                "может включать total_revenue и "
                "каналы продаж."
                if full_revenue_comparable
                else (
                    "Для одной или обеих дат нет "
                    "подтверждённой полной дневной "
                    "выручки. Сравниваются только "
                    "показатели, которые точно "
                    "доступны для обеих дат. "
                    "Чековую выручку нельзя "
                    "называть полной выручкой "
                    "магазина."
                )
            ),
    }


def get_recent_sales(days=7):
    days = max(
        1,
        min(
            int(
                days
            ),
            31,
        ),
    )

    rows = load_daily_sales()

    selected = rows[
        -days:
    ]

    return {
        "status":
            "ok",

        "requested_days":
            days,

        "returned_days":
            len(
                selected
            ),

        "days": [
            normalize_day(
                row
            )
            for row in selected
        ],
    }


def get_month_rows(
    year,
    month,
    end_day=None,
):
    year = int(
        year
    )

    month = int(
        month
    )

    rows = load_daily_sales()

    result = []

    for row in rows:
        date_dt = row[
            "_date"
        ]

        if (
            date_dt.year
            != year
            or date_dt.month
            != month
        ):
            continue

        if (
            end_day is not None
            and date_dt.day
            > int(
                end_day
            )
        ):
            continue

        result.append(
            row
        )

    return result


def summarize_rows(
    rows,
    year=None,
    month=None,
):
    if not rows:
        return {
            "status":
                "no_data",
        }

    totals = {
        metric:
            0.0
        for metric in SUM_METRICS
    }

    for row in rows:
        day = normalize_day(
            row
        )

        for metric in SUM_METRICS:
            totals[
                metric
            ] += to_float(
                day.get(
                    metric,
                    0,
                )
            )

    checks = int(
        round(
            totals[
                "checks"
            ]
        )
    )

    items = totals[
        "items"
    ]

    check_revenue_net = totals[
        "check_revenue_net"
    ]

    average_check = 0.0

    if checks > 0:
        average_check = (
            check_revenue_net
            / checks
        )

    ktch = 0.0

    if checks > 0:
        ktch = (
            items
            / checks
        )

    start_date = rows[
        0
    ][
        "_date"
    ]

    end_date = rows[
        -1
    ][
        "_date"
    ]

    calendar_days_covered = (
        end_date.date()
        - start_date.date()
    ).days + 1

    summary = {
        "status":
            "ok",

        "source":
            "daily_sales",

        "data_granularity":
            "daily",

        "start_date":
            start_date.strftime(
                "%d.%m.%Y"
            ),

        "end_date":
            end_date.strftime(
                "%d.%m.%Y"
            ),

        "days_with_data":
            len(
                rows
            ),

        "calendar_days_covered":
            calendar_days_covered,

        "total_revenue":
            round_money(
                totals[
                    "total_revenue"
                ]
            ),

        "check_revenue_net":
            round_money(
                check_revenue_net
            ),

        "checks":
            checks,

        "items":
            round(
                items,
                2,
            ),

        "average_check":
            round_money(
                average_check
            ),

        "ktch":
            round(
                ktch,
                2,
            ),

        "cash":
            round_money(
                totals[
                    "cash"
                ]
            ),

        "card":
            round_money(
                totals[
                    "card"
                ]
            ),

        "returns":
            round_money(
                totals[
                    "returns"
                ]
            ),

        "self_pickup":
            round_money(
                totals[
                    "self_pickup"
                ]
            ),

        "yandex_food":
            round_money(
                totals[
                    "yandex_food"
                ]
            ),

        "kuper":
            round_money(
                totals[
                    "kuper"
                ]
            ),

        "external_total":
            round_money(
                totals[
                    "external_total"
                ]
            ),

        "yandex_orders":
            int(
                round(
                    totals[
                        "yandex_orders"
                    ]
                )
            ),

        "kuper_orders":
            int(
                round(
                    totals[
                        "kuper_orders"
                    ]
                )
            ),

        "external_orders":
            int(
                round(
                    totals[
                        "external_orders"
                    ]
                )
            ),

        "no_receipt":
            round_money(
                totals[
                    "no_receipt"
                ]
            ),
    }

    if (
        year is not None
        and month is not None
    ):
        year = int(
            year
        )

        month = int(
            month
        )

        days_in_month = (
            calendar.monthrange(
                year,
                month,
            )[1]
        )

        max_loaded_day = max(
            row[
                "_date"
            ].day
            for row in rows
        )

        summary[
            "year"
        ] = year

        summary[
            "month"
        ] = month

        summary[
            "days_in_month"
        ] = days_in_month

        summary[
            "max_loaded_day"
        ] = max_loaded_day

        summary[
            "is_complete"
        ] = (
            max_loaded_day
            >= days_in_month
        )

    days_for_pace = len(
        rows
    )

    if days_for_pace > 0:
        summary[
            "revenue_per_data_day"
        ] = round_money(
            totals[
                "total_revenue"
            ]
            / days_for_pace
        )

        summary[
            "checks_per_data_day"
        ] = round(
            checks
            / days_for_pace,
            2,
        )

        summary[
            "items_per_data_day"
        ] = round(
            items
            / days_for_pace,
            2,
        )

        summary[
            "external_revenue_per_data_day"
        ] = round_money(
            totals[
                "external_total"
            ]
            / days_for_pace
        )

    return summary


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

    rows = get_month_rows(
        year,
        month,
    )

    if rows:
        return summarize_rows(
            rows,
            year=year,
            month=month,
        )

    historical = (
        get_historical_month_summary(
            year,
            month,
        )
    )

    if (
        historical.get(
            "status"
        )
        == "ok"
    ):
        return historical

    return {
        "status":
            "not_found",

        "year":
            year,

        "month":
            month,
    }


def get_month_period_summary(
    year,
    month,
    end_day,
):
    year = int(
        year
    )

    month = int(
        month
    )

    end_day = int(
        end_day
    )

    max_day = calendar.monthrange(
        year,
        month,
    )[1]

    end_day = min(
        end_day,
        max_day,
    )

    rows = get_month_rows(
        year,
        month,
        end_day=end_day,
    )

    if not rows:
        historical = (
            get_historical_month_summary(
                year,
                month,
            )
        )

        return {
            "status":
                "not_found",

            "year":
                year,

            "month":
                month,

            "end_day":
                end_day,

            "reason":
                (
                    "partial_period_requires_daily_data"
                    if historical.get(
                        "status"
                    )
                    == "ok"
                    else "no_data"
                ),

            "full_month_available":
                historical.get(
                    "status"
                )
                == "ok",
        }

    summary = summarize_rows(
        rows,
        year=year,
        month=month,
    )

    summary[
        "comparison_end_day"
    ] = end_day

    return summary


def build_comparison_metrics(
    earlier,
    later,
):
    metrics = {}

    metric_names = [
        "total_revenue",
        "check_revenue_net",
        "checks",
        "items",
        "average_check",
        "ktch",
        "external_total",
        "external_orders",
        "yandex_food",
        "yandex_orders",
        "kuper",
        "kuper_orders",
        "returns",
        "no_receipt",
        "revenue_per_data_day",
        "checks_per_data_day",
        "items_per_data_day",
        "external_revenue_per_data_day",
    ]

    for metric in metric_names:
        if (
            metric not in earlier
            or metric not in later
        ):
            continue

        metrics[
            metric
        ] = metric_comparison(
            earlier[
                metric
            ],
            later[
                metric
            ],
        )

    return metrics


def compare_sales_months(
    year_a,
    month_a,
    year_b,
    month_b,
):
    year_a = int(
        year_a
    )

    month_a = int(
        month_a
    )

    year_b = int(
        year_b
    )

    month_b = int(
        month_b
    )

    summary_a = get_month_summary(
        year_a,
        month_a,
    )

    summary_b = get_month_summary(
        year_b,
        month_b,
    )

    if (
        summary_a.get(
            "status"
        )
        != "ok"
        or summary_b.get(
            "status"
        )
        != "ok"
    ):
        return {
            "status":
                "missing_data",

            "period_a":
                summary_a,

            "period_b":
                summary_b,

            "message":
                (
                    "Для сравнения нужны данные "
                    "по обоим месяцам."
                ),
        }

    index_a = (
        year_a * 12
        + month_a
    )

    index_b = (
        year_b * 12
        + month_b
    )

    if index_a <= index_b:
        earlier_year = year_a
        earlier_month = month_a
        earlier_full = summary_a

        later_year = year_b
        later_month = month_b
        later_full = summary_b

    else:
        earlier_year = year_b
        earlier_month = month_b
        earlier_full = summary_b

        later_year = year_a
        later_month = month_a
        later_full = summary_a

    later_is_complete = bool(
        later_full.get(
            "is_complete"
        )
    )

    if later_is_complete:
        comparison_type = (
            "full_month_vs_full_month"
        )

        earlier_compare = (
            earlier_full
        )

        later_compare = (
            later_full
        )

        comparison_end_day = None

    else:
        comparison_type = (
            "like_for_like_partial_month"
        )

        comparison_end_day = int(
            later_full.get(
                "max_loaded_day",
                0,
            )
        )

        earlier_compare = (
            get_month_period_summary(
                earlier_year,
                earlier_month,
                comparison_end_day,
            )
        )

        later_compare = (
            get_month_period_summary(
                later_year,
                later_month,
                comparison_end_day,
            )
        )

        if (
            earlier_compare.get(
                "status"
            )
            != "ok"
            or later_compare.get(
                "status"
            )
            != "ok"
        ):
            return {
                "status":
                    "missing_like_for_like_data",

                "comparison_type":
                    comparison_type,

                "comparison_end_day":
                    comparison_end_day,

                "earlier_full_summary":
                    earlier_full,

                "later_full_summary":
                    later_full,

                "earlier_comparison_summary":
                    earlier_compare,

                "later_comparison_summary":
                    later_compare,

                "message":
                    (
                        "Более поздний месяц ещё "
                        "не завершён, а для старого "
                        "месяца есть только полный "
                        "месячный итог без дневной "
                        "разбивки. Корректное "
                        "like-for-like сравнение "
                        "сделать нельзя."
                    ),
            }

    metrics = build_comparison_metrics(
        earlier_compare,
        later_compare,
    )

    sources = {
        "earlier":
            earlier_compare.get(
                "source"
            ),

        "later":
            later_compare.get(
                "source"
            ),
    }

    return {
        "status":
            "ok",

        "comparison_type":
            comparison_type,

        "comparison_direction":
            "later_month_vs_earlier_month",

        "earlier_period": {
            "year":
                earlier_year,

            "month":
                earlier_month,
        },

        "later_period": {
            "year":
                later_year,

            "month":
                later_month,
        },

        "comparison_end_day":
            comparison_end_day,

        "earlier_full_summary":
            earlier_full,

        "later_full_summary":
            later_full,

        "earlier_comparison_summary":
            earlier_compare,

        "later_comparison_summary":
            later_compare,

        "metrics":
            metrics,

        "sources":
            sources,

        "analysis_note":
            (
                (
                    "Более поздний месяц ещё не завершён. "
                    f"Основное сравнение сделано "
                    f"за одинаковый период: "
                    f"1–{comparison_end_day} число "
                    f"обоих месяцев. "
                    "Полные текущие месячные суммы "
                    "переданы отдельно только справочно."
                )
                if comparison_type
                == "like_for_like_partial_month"
                else (
                    "Оба месяца завершены. "
                    "Сравниваются полные месячные итоги."
                )
            ),
    }


def print_month_test(
    year,
    month,
):
    result = get_month_summary(
        year,
        month,
    )

    print()
    print(
        f"{month:02d}.{year}"
    )

    print(
        "status:",
        result.get(
            "status"
        )
    )

    if (
        result.get(
            "status"
        )
        == "ok"
    ):
        print(
            "source:",
            result.get(
                "source"
            )
        )

        print(
            "total_revenue:",
            result.get(
                "total_revenue"
            )
        )

        print(
            "check_revenue_net:",
            result.get(
                "check_revenue_net"
            )
        )

        print(
            "checks:",
            result.get(
                "checks"
            )
        )

        print(
            "average_check:",
            result.get(
                "average_check"
            )
        )

        print(
            "ktch:",
            result.get(
                "ktch"
            )
        )

        print(
            "external_total:",
            result.get(
                "external_total"
            )
        )


def print_comparison_test(
    title,
    year_a,
    month_a,
    year_b,
    month_b,
):
    print()
    print("-" * 70)

    print(
        title
    )

    result = compare_sales_months(
        year_a,
        month_a,
        year_b,
        month_b,
    )

    print(
        "status:",
        result.get(
            "status"
        )
    )

    print(
        "comparison_type:",
        result.get(
            "comparison_type"
        )
    )

    if (
        result.get(
            "status"
        )
        == "ok"
    ):
        total = (
            result.get(
                "metrics",
                {},
            ).get(
                "total_revenue"
            )
        )

        checks = (
            result.get(
                "metrics",
                {},
            ).get(
                "checks"
            )
        )

        average_check = (
            result.get(
                "metrics",
                {},
            ).get(
                "average_check"
            )
        )

        ktch = (
            result.get(
                "metrics",
                {},
            ).get(
                "ktch"
            )
        )

        print(
            "sources:",
            result.get(
                "sources"
            )
        )

        print(
            "total_revenue:",
            total
        )

        print(
            "checks:",
            checks
        )

        print(
            "average_check:",
            average_check
        )

        print(
            "ktch:",
            ktch
        )

    else:
        print(
            result.get(
                "message"
            )
        )


def demo():
    print()
    print("=" * 70)
    print(
        "SALES TOOLS — TEST"
    )
    print("=" * 70)

    print()
    print(
        "ИСТОРИЧЕСКИЕ МЕСЯЦЫ:"
    )

    print_month_test(
        2025,
        4,
    )

    print_month_test(
        2025,
        5,
    )

    print_month_test(
        2026,
        4,
    )

    print_month_test(
        2026,
        5,
    )

    print_month_test(
        2026,
        6,
    )

    print_month_test(
        2026,
        7,
    )

    print_month_test(
        2026,
        8,
    )

    print()
    print("=" * 70)
    print(
        "СРАВНЕНИЯ"
    )
    print("=" * 70)

    print_comparison_test(
        (
            "Апрель 2025 "
            "против мая 2025"
        ),
        2025,
        4,
        2025,
        5,
    )

    print_comparison_test(
        (
            "Апрель 2026 "
            "против мая 2026"
        ),
        2026,
        4,
        2026,
        5,
    )

    print_comparison_test(
        (
            "Июнь 2026 "
            "против июля 2026"
        ),
        2026,
        6,
        2026,
        7,
    )

    print_comparison_test(
        (
            "Июль 2026 "
            "против августа 2026"
        ),
        2026,
        7,
        2026,
        8,
    )


if __name__ == "__main__":
    demo()