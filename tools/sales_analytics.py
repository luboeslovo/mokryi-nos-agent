import calendar
import csv
import os
from datetime import date, datetime, timedelta

from sales_tools import (
    get_month_summary,
    load_daily_sales,
    metric_comparison,
    normalize_day,
    parse_date,
    summarize_rows,
)


PROJECT_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

HISTORICAL_SALES_PATH = os.path.join(
    PROJECT_DIR,
    "historical_sales_monthly.csv",
)


ADDITIVE_METRICS = [
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


SUPPORTED_RANK_METRICS = {
    "total_revenue",
    "check_revenue_net",
    "checks",
    "items",
    "average_check",
    "ktch",
    "cash",
    "card",
    "returns",
    "self_pickup",
    "yandex_food",
    "kuper",
    "external_total",
    "external_orders",
    "no_receipt",
    "revenue_per_data_day",
    "checks_per_data_day",
    "items_per_data_day",
    "external_revenue_per_data_day",
}


MONTH_NAMES = {
    1: "январь",
    2: "февраль",
    3: "март",
    4: "апрель",
    5: "май",
    6: "июнь",
    7: "июль",
    8: "август",
    9: "сентябрь",
    10: "октябрь",
    11: "ноябрь",
    12: "декабрь",
}


def to_float_optional(value):
    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    text = (
        text
        .replace("\xa0", "")
        .replace(" ", "")
        .replace(",", ".")
    )

    try:
        return float(text)

    except Exception:
        return None


def to_int_optional(value):
    number = to_float_optional(value)

    if number is None:
        return None

    return int(
        round(number)
    )


def to_bool(value):
    return (
        str(value or "")
        .strip()
        .lower()
        in {
            "1",
            "true",
            "yes",
            "да",
        }
    )


def parse_day(value):
    if (
        isinstance(value, date)
        and not isinstance(value, datetime)
    ):
        return value

    return parse_date(
        value
    ).date()


def format_day(value):
    if isinstance(value, datetime):
        value = value.date()

    return value.strftime(
        "%d.%m.%Y"
    )


def month_start(year, month):
    return date(
        int(year),
        int(month),
        1,
    )


def month_end(year, month):
    last_day = calendar.monthrange(
        int(year),
        int(month),
    )[1]

    return date(
        int(year),
        int(month),
        last_day,
    )


def next_month(year, month):
    year = int(year)
    month = int(month)

    if month == 12:
        return (
            year + 1,
            1,
        )

    return (
        year,
        month + 1,
    )


def iterate_months(
    start_date,
    end_date,
):
    year = start_date.year
    month = start_date.month

    while (
        year,
        month,
    ) <= (
        end_date.year,
        end_date.month,
    ):
        yield (
            year,
            month,
        )

        year, month = next_month(
            year,
            month,
        )


def month_label(year, month):
    return (
        f"{MONTH_NAMES.get(int(month), str(month))} "
        f"{int(year)}"
    )


def get_latest_daily_date():
    rows = load_daily_sales()

    if not rows:
        return None

    return rows[-1][
        "_date"
    ].date()


def get_earliest_daily_date():
    rows = load_daily_sales()

    if not rows:
        return None

    return rows[0][
        "_date"
    ].date()


def load_historical_periods():
    if not os.path.exists(
        HISTORICAL_SALES_PATH
    ):
        return []

    result = []

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
                start_date = parse_day(
                    raw.get(
                        "start_date"
                    )
                )

                end_date = parse_day(
                    raw.get(
                        "end_date"
                    )
                )

            except Exception:
                continue

            row = dict(raw)

            row["_start_date"] = (
                start_date
            )

            row["_end_date"] = (
                end_date
            )

            row["_period_type"] = (
                str(
                    raw.get(
                        "period_type",
                        "month",
                    )
                    or "month"
                )
                .strip()
                .lower()
            )

            result.append(
                row
            )

    result.sort(
        key=lambda item:
            item["_start_date"]
    )

    return result


def get_historical_combined_periods():
    return [
        row
        for row in load_historical_periods()
        if (
            row.get(
                "_period_type"
            )
            == "combined"
        )
    ]


def normalize_historical_period(row):
    start_date = row[
        "_start_date"
    ]

    end_date = row[
        "_end_date"
    ]

    days = (
        end_date
        - start_date
    ).days + 1

    period_type = row.get(
        "_period_type",
        "month",
    )

    source = (
        "historical_combined"
        if period_type == "combined"
        else "historical_monthly"
    )

    granularity = (
        "combined"
        if period_type == "combined"
        else "monthly"
    )

    result = {
        "status":
            "ok",

        "source":
            source,

        "source_name":
            row.get(
                "source",
                "ПО ЧИСЛАМ",
            ),

        "data_granularity":
            granularity,

        "period_type":
            period_type,

        "start_date":
            format_day(
                start_date
            ),

        "end_date":
            format_day(
                end_date
            ),

        "days_with_data":
            days,

        "calendar_days_covered":
            days,

        "is_complete":
            to_bool(
                row.get(
                    "is_complete"
                )
            ),

        "source_label":
            row.get(
                "source_label"
            ),
    }

    year = to_int_optional(
        row.get(
            "year"
        )
    )

    month = to_int_optional(
        row.get(
            "month"
        )
    )

    if year is not None:
        result[
            "year"
        ] = year

    if month is not None:
        result[
            "month"
        ] = month

    numeric_fields = [
        "total_revenue",
        "check_revenue_net",
        "average_check",
        "ktch",
        "cash",
        "card",
        "returns",
        "self_pickup",
        "yandex_food",
        "kuper",
        "external_total",
        "no_receipt",
    ]

    integer_fields = [
        "checks",
        "external_orders",
    ]

    for field in numeric_fields:
        value = to_float_optional(
            row.get(
                field
            )
        )

        if value is not None:
            result[
                field
            ] = round(
                value,
                2,
            )

    for field in integer_fields:
        value = to_int_optional(
            row.get(
                field
            )
        )

        if value is not None:
            result[
                field
            ] = value

    total_revenue = result.get(
        "total_revenue"
    )

    checks = result.get(
        "checks"
    )

    external_total = result.get(
        "external_total"
    )

    if (
        total_revenue is not None
        and days > 0
    ):
        result[
            "revenue_per_data_day"
        ] = round(
            total_revenue
            / days,
            2,
        )

    if (
        checks is not None
        and days > 0
    ):
        result[
            "checks_per_data_day"
        ] = round(
            checks
            / days,
            2,
        )

    if (
        external_total is not None
        and days > 0
    ):
        result[
            "external_revenue_per_data_day"
        ] = round(
            external_total
            / days,
            2,
        )

    return result


def get_exact_combined_period(
    start_date,
    end_date,
):
    for row in (
        get_historical_combined_periods()
    ):
        if (
            row["_start_date"]
            == start_date
            and row["_end_date"]
            == end_date
            and to_bool(
                row.get(
                    "is_complete"
                )
            )
        ):
            return normalize_historical_period(
                row
            )

    return None


def find_combined_period_starting(
    start_date,
    max_end_date,
):
    matches = []

    for row in (
        get_historical_combined_periods()
    ):
        if (
            row["_start_date"]
            != start_date
        ):
            continue

        if (
            row["_end_date"]
            > max_end_date
        ):
            continue

        if not to_bool(
            row.get(
                "is_complete"
            )
        ):
            continue

        matches.append(
            row
        )

    if not matches:
        return None

    matches.sort(
        key=lambda item:
            item["_end_date"],
        reverse=True,
    )

    return normalize_historical_period(
        matches[0]
    )


def get_earliest_history_date():
    periods = load_historical_periods()

    candidates = []

    if periods:
        candidates.append(
            periods[0][
                "_start_date"
            ]
        )

    daily = get_earliest_daily_date()

    if daily is not None:
        candidates.append(
            daily
        )

    if not candidates:
        return None

    return min(
        candidates
    )


def get_available_sales_coverage():
    earliest_day = (
        get_earliest_daily_date()
    )

    latest_day = (
        get_latest_daily_date()
    )

    earliest_history = (
        get_earliest_history_date()
    )

    combined_periods = []

    for row in (
        get_historical_combined_periods()
    ):
        combined_periods.append(
            {
                "start_date":
                    format_day(
                        row[
                            "_start_date"
                        ]
                    ),

                "end_date":
                    format_day(
                        row[
                            "_end_date"
                        ]
                    ),

                "source_label":
                    row.get(
                        "source_label"
                    ),
            }
        )

    return {
        "status":
            "ok",

        "daily": {
            "available":
                bool(
                    earliest_day
                    and latest_day
                ),

            "start_date":
                (
                    format_day(
                        earliest_day
                    )
                    if earliest_day
                    else None
                ),

            "end_date":
                (
                    format_day(
                        latest_day
                    )
                    if latest_day
                    else None
                ),

            "note":
                (
                    "Точные дневные сравнения "
                    "и рейтинги возможны только "
                    "внутри этого диапазона."
                ),
        },

        "historical": {
            "available":
                bool(
                    earliest_history
                ),

            "start_date":
                (
                    format_day(
                        earliest_history
                    )
                    if earliest_history
                    else None
                ),

            "combined_periods":
                combined_periods,

            "note":
                (
                    "Старые данные могут быть "
                    "месячными или объединёнными. "
                    "Объединённый период нельзя "
                    "искусственно делить на месяцы."
                ),
        },

        "profit_available":
            False,

        "profit_note":
            (
                "Сейчас подключена выручка, "
                "но не полноценная себестоимость "
                "и расходы. Поэтому максимум "
                "выручки нельзя называть "
                "максимумом прибыли."
            ),
    }


def summarize_daily_range(
    start_date,
    end_date,
):
    rows = load_daily_sales()

    selected = []

    for row in rows:
        row_date = (
            row["_date"]
            .date()
        )

        if (
            start_date
            <= row_date
            <= end_date
        ):
            selected.append(
                row
            )

    expected_days = (
        end_date
        - start_date
    ).days + 1

    if (
        not selected
        or len(selected)
        != expected_days
    ):
        return {
            "status":
                "not_found",

            "source":
                "daily_sales",

            "start_date":
                format_day(
                    start_date
                ),

            "end_date":
                format_day(
                    end_date
                ),

            "expected_days":
                expected_days,

            "days_with_data":
                len(
                    selected
                ),
        }

    summary = summarize_rows(
        selected
    )

    summary[
        "source"
    ] = "daily_sales"

    summary[
        "data_granularity"
    ] = "daily"

    summary[
        "requested_start_date"
    ] = format_day(
        start_date
    )

    summary[
        "requested_end_date"
    ] = format_day(
        end_date
    )

    return summary


def metric_is_available(
    summary,
    metric,
):
    if metric not in summary:
        return False

    return (
        to_float_optional(
            summary.get(
                metric
            )
        )
        is not None
    )


def aggregate_summaries(
    summaries,
    start_date,
    end_date,
):
    if not summaries:
        return {
            "status":
                "no_data",
        }

    days_requested = (
        end_date
        - start_date
    ).days + 1

    sources = sorted(
        {
            str(
                summary.get(
                    "source",
                    "unknown",
                )
            )
            for summary in summaries
        }
    )

    granularities = sorted(
        {
            str(
                summary.get(
                    "data_granularity",
                    "unknown",
                )
            )
            for summary in summaries
        }
    )

    result = {
        "status":
            "ok",

        "start_date":
            format_day(
                start_date
            ),

        "end_date":
            format_day(
                end_date
            ),

        "days_requested":
            days_requested,

        "parts_count":
            len(
                summaries
            ),

        "sources":
            sources,

        "data_granularity":
            (
                granularities[0]
                if len(
                    granularities
                )
                == 1
                else "mixed"
            ),

        "parts":
            [],
    }

    for summary in summaries:
        result[
            "parts"
        ].append(
            {
                "start_date":
                    summary.get(
                        "start_date"
                    ),

                "end_date":
                    summary.get(
                        "end_date"
                    ),

                "source":
                    summary.get(
                        "source"
                    ),

                "data_granularity":
                    summary.get(
                        "data_granularity"
                    ),
            }
        )

    for metric in ADDITIVE_METRICS:
        if not all(
            metric_is_available(
                summary,
                metric,
            )
            for summary in summaries
        ):
            continue

        total = sum(
            float(
                summary[
                    metric
                ]
            )
            for summary in summaries
        )

        if metric in {
            "checks",
            "external_orders",
            "yandex_orders",
            "kuper_orders",
        }:
            result[
                metric
            ] = int(
                round(total)
            )

        else:
            result[
                metric
            ] = round(
                total,
                2,
            )

    checks = result.get(
        "checks"
    )

    check_revenue_net = (
        result.get(
            "check_revenue_net"
        )
    )

    if (
        checks is not None
        and checks > 0
        and check_revenue_net
        is not None
    ):
        result[
            "average_check"
        ] = round(
            check_revenue_net
            / checks,
            2,
        )

    items = result.get(
        "items"
    )

    if (
        checks is not None
        and checks > 0
        and items is not None
    ):
        result[
            "ktch"
        ] = round(
            items
            / checks,
            2,
        )

    # Если это один готовый исторический период,
    # сохраняем его фактические ratio-показатели.
    # Не пытаемся восстанавливать КТЧ нескольких
    # старых месяцев из округлённых значений.
    if len(summaries) == 1:
        single = summaries[0]

        if metric_is_available(
            single,
            "average_check",
        ):
            result[
                "average_check"
            ] = round(
                float(
                    single[
                        "average_check"
                    ]
                ),
                2,
            )

        if metric_is_available(
            single,
            "ktch",
        ):
            result[
                "ktch"
            ] = round(
                float(
                    single[
                        "ktch"
                    ]
                ),
                2,
            )

    total_revenue = result.get(
        "total_revenue"
    )

    if (
        total_revenue is not None
        and days_requested > 0
    ):
        result[
            "revenue_per_data_day"
        ] = round(
            total_revenue
            / days_requested,
            2,
        )

    if (
        checks is not None
        and days_requested > 0
    ):
        result[
            "checks_per_data_day"
        ] = round(
            checks
            / days_requested,
            2,
        )

    if (
        items is not None
        and days_requested > 0
    ):
        result[
            "items_per_data_day"
        ] = round(
            items
            / days_requested,
            2,
        )

    external_total = result.get(
        "external_total"
    )

    if (
        external_total is not None
        and days_requested > 0
    ):
        result[
            "external_revenue_per_data_day"
        ] = round(
            external_total
            / days_requested,
            2,
        )

    return result


def build_unavailable_part(
    start_date,
    end_date,
    reason,
):
    return {
        "status":
            "insufficient_granularity",

        "start_date":
            format_day(
                start_date
            ),

        "end_date":
            format_day(
                end_date
            ),

        "reason":
            reason,
    }


def get_period_summary(
    start_date,
    end_date,
):
    start_date = parse_day(
        start_date
    )

    end_date = parse_day(
        end_date
    )

    if start_date > end_date:
        return {
            "status":
                "invalid_period",

            "message":
                "Начальная дата позже конечной.",
        }

    exact_combined = (
        get_exact_combined_period(
            start_date,
            end_date,
        )
    )

    if exact_combined is not None:
        return aggregate_summaries(
            [
                exact_combined
            ],
            start_date,
            end_date,
        )

    earliest_daily = (
        get_earliest_daily_date()
    )

    latest_daily = (
        get_latest_daily_date()
    )

    summaries = []
    unavailable_parts = []

    current = start_date

    while current <= end_date:
        # --------------------------------------------------
        # ТОЧНАЯ ДНЕВНАЯ ЗОНА
        # --------------------------------------------------

        if (
            earliest_daily is not None
            and latest_daily is not None
            and earliest_daily
            <= current
            <= latest_daily
        ):
            chunk_end = min(
                end_date,
                latest_daily,
            )

            daily = (
                summarize_daily_range(
                    current,
                    chunk_end,
                )
            )

            if (
                daily.get(
                    "status"
                )
                != "ok"
            ):
                unavailable_parts.append(
                    build_unavailable_part(
                        current,
                        chunk_end,
                        (
                            "Внутри дневного диапазона "
                            "не хватает строк."
                        ),
                    )
                )

                break

            summaries.append(
                daily
            )

            current = (
                chunk_end
                + timedelta(days=1)
            )

            continue

        # --------------------------------------------------
        # ОБЪЕДИНЁННЫЙ ИСТОРИЧЕСКИЙ ПЕРИОД
        # --------------------------------------------------

        combined = (
            find_combined_period_starting(
                current,
                end_date,
            )
        )

        if combined is not None:
            summaries.append(
                combined
            )

            current = (
                parse_day(
                    combined[
                        "end_date"
                    ]
                )
                + timedelta(days=1)
            )

            continue

        # --------------------------------------------------
        # ПОЛНЫЙ ИСТОРИЧЕСКИЙ МЕСЯЦ
        # --------------------------------------------------

        if current.day == 1:
            full_month_end = month_end(
                current.year,
                current.month,
            )

            if full_month_end <= end_date:
                month_summary = (
                    get_month_summary(
                        current.year,
                        current.month,
                    )
                )

                if (
                    month_summary.get(
                        "status"
                    )
                    == "ok"
                    and bool(
                        month_summary.get(
                            "is_complete"
                        )
                    )
                ):
                    summaries.append(
                        month_summary
                    )

                    current = (
                        full_month_end
                        + timedelta(days=1)
                    )

                    continue

        # --------------------------------------------------
        # ДАЛЬШЕ БЕЗ ВЫДУМОК ПОСЧИТАТЬ НЕЛЬЗЯ
        # --------------------------------------------------

        if current.day == 1:
            unavailable_end = min(
                end_date,
                month_end(
                    current.year,
                    current.month,
                ),
            )

        else:
            unavailable_end = end_date

        unavailable_parts.append(
            build_unavailable_part(
                current,
                unavailable_end,
                (
                    "Для этого участка есть только "
                    "более грубые исторические данные. "
                    "Нельзя искусственно восстановить "
                    "дневную детализацию."
                ),
            )
        )

        break

    if unavailable_parts:
        return {
            "status":
                "insufficient_granularity",

            "start_date":
                format_day(
                    start_date
                ),

            "end_date":
                format_day(
                    end_date
                ),

            "available_parts":
                summaries,

            "unavailable_parts":
                unavailable_parts,

            "message":
                (
                    "Период нельзя посчитать "
                    "целиком без выдумок."
                ),
        }

    result = aggregate_summaries(
        summaries,
        start_date,
        end_date,
    )

    result[
        "period_kind"
    ] = "custom"

    return result


def comparable_metrics(
    summary_a,
    summary_b,
):
    metrics = {}

    metric_names = [
        "total_revenue",
        "check_revenue_net",
        "checks",
        "items",
        "average_check",
        "ktch",
        "cash",
        "card",
        "returns",
        "self_pickup",
        "yandex_food",
        "kuper",
        "external_total",
        "external_orders",
        "no_receipt",
        "revenue_per_data_day",
        "checks_per_data_day",
        "items_per_data_day",
        "external_revenue_per_data_day",
    ]

    for metric in metric_names:
        if (
            metric_is_available(
                summary_a,
                metric,
            )
            and metric_is_available(
                summary_b,
                metric,
            )
        ):
            metrics[
                metric
            ] = metric_comparison(
                summary_a[
                    metric
                ],
                summary_b[
                    metric
                ],
            )

    return metrics


def compare_sales_periods(
    start_a,
    end_a,
    start_b,
    end_b,
):
    period_a = get_period_summary(
        start_a,
        end_a,
    )

    period_b = get_period_summary(
        start_b,
        end_b,
    )

    if (
        period_a.get(
            "status"
        )
        != "ok"
        or period_b.get(
            "status"
        )
        != "ok"
    ):
        return {
            "status":
                "missing_data",

            "period_a":
                period_a,

            "period_b":
                period_b,

            "message":
                (
                    "Для корректного сравнения "
                    "нужны данные по обоим периодам."
                ),
        }

    start_a_dt = parse_day(
        start_a
    )

    end_a_dt = parse_day(
        end_a
    )

    start_b_dt = parse_day(
        start_b
    )

    end_b_dt = parse_day(
        end_b
    )

    days_a = (
        end_a_dt
        - start_a_dt
    ).days + 1

    days_b = (
        end_b_dt
        - start_b_dt
    ).days + 1

    return {
        "status":
            "ok",

        "period_a":
            period_a,

        "period_b":
            period_b,

        "days_a":
            days_a,

        "days_b":
            days_b,

        "same_duration":
            (
                days_a
                == days_b
            ),

        "metrics_b_vs_a":
            comparable_metrics(
                period_a,
                period_b,
            ),

        "comparison_note":
            (
                "Периоды одинаковой длины."
                if days_a == days_b
                else (
                    "Периоды имеют разную длину. "
                    "Абсолютные суммы нужно "
                    "интерпретировать с учётом этого."
                )
            ),
    }


def get_year_summary(
    year,
    allow_partial=False,
):
    year = int(year)

    latest_day = (
        get_latest_daily_date()
    )

    earliest_history = (
        get_earliest_history_date()
    )

    if (
        latest_day is None
        or earliest_history is None
    ):
        return {
            "status":
                "no_data",

            "year":
                year,
        }

    if (
        year
        < earliest_history.year
        or year
        > latest_day.year
    ):
        return {
            "status":
                "not_found",

            "year":
                year,
        }

    start_date = date(
        year,
        1,
        1,
    )

    if year == latest_day.year:
        end_date = latest_day

    else:
        end_date = date(
            year,
            12,
            31,
        )

    result = get_period_summary(
        start_date,
        end_date,
    )

    result[
        "year"
    ] = year

    if (
        result.get(
            "status"
        )
        == "ok"
    ):
        result[
            "period_kind"
        ] = (
            "year_to_date"
            if year
            == latest_day.year
            else "full_year"
        )

        result[
            "is_complete_year"
        ] = (
            year
            < latest_day.year
        )

        return result

    if not allow_partial:
        return result

    available_parts = []

    for month in range(
        1,
        13,
    ):
        summary = get_month_summary(
            year,
            month,
        )

        if (
            summary.get(
                "status"
            )
            == "ok"
            and bool(
                summary.get(
                    "is_complete"
                )
            )
        ):
            available_parts.append(
                summary
            )

    if not available_parts:
        return result

    starts = [
        parse_day(
            item[
                "start_date"
            ]
        )
        for item in available_parts
    ]

    ends = [
        parse_day(
            item[
                "end_date"
            ]
        )
        for item in available_parts
    ]

    partial = aggregate_summaries(
        available_parts,
        min(starts),
        max(ends),
    )

    partial[
        "status"
    ] = "partial"

    partial[
        "year"
    ] = year

    partial[
        "period_kind"
    ] = "partial_year"

    partial[
        "is_complete_year"
    ] = False

    partial[
        "warning"
    ] = (
        "Это неполный год."
    )

    return partial


def compare_sales_years(
    year_a,
    year_b,
):
    summary_a = get_year_summary(
        year_a
    )

    summary_b = get_year_summary(
        year_b
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

            "year_a":
                summary_a,

            "year_b":
                summary_b,
        }

    return {
        "status":
            "ok",

        "year_a":
            summary_a,

        "year_b":
            summary_b,

        "metrics_b_vs_a":
            comparable_metrics(
                summary_a,
                summary_b,
            ),

        "warning":
            (
                "Один из годов ещё не завершён."
                if (
                    not summary_a.get(
                        "is_complete_year"
                    )
                    or not summary_b.get(
                        "is_complete_year"
                    )
                )
                else None
            ),
    }


def build_day_candidates(
    date_from=None,
    date_to=None,
):
    rows = load_daily_sales()

    if not rows:
        return []

    start_date = (
        parse_day(
            date_from
        )
        if date_from
        else rows[0][
            "_date"
        ].date()
    )

    end_date = (
        parse_day(
            date_to
        )
        if date_to
        else rows[-1][
            "_date"
        ].date()
    )

    result = []

    for row in rows:
        row_date = (
            row["_date"]
            .date()
        )

        if not (
            start_date
            <= row_date
            <= end_date
        ):
            continue

        summary = normalize_day(
            row
        )

        result.append(
            {
                "period_type":
                    "day",

                "label":
                    summary[
                        "date"
                    ],

                "start_date":
                    summary[
                        "date"
                    ],

                "end_date":
                    summary[
                        "date"
                    ],

                "is_complete":
                    True,

                "source":
                    "daily_sales",

                **summary,
            }
        )

    return result


def build_month_candidates(
    date_from=None,
    date_to=None,
    include_partial=False,
):
    earliest = (
        get_earliest_history_date()
    )

    latest = (
        get_latest_daily_date()
    )

    if (
        earliest is None
        or latest is None
    ):
        return []

    requested_start = (
        parse_day(
            date_from
        )
        if date_from
        else earliest
    )

    requested_end = (
        parse_day(
            date_to
        )
        if date_to
        else latest
    )

    start_date = date(
        requested_start.year,
        requested_start.month,
        1,
    )

    end_date = date(
        requested_end.year,
        requested_end.month,
        1,
    )

    result = []

    for year, month in iterate_months(
        start_date,
        end_date,
    ):
        summary = get_month_summary(
            year,
            month,
        )

        if (
            summary.get(
                "status"
            )
            != "ok"
        ):
            continue

        is_complete = bool(
            summary.get(
                "is_complete"
            )
        )

        if (
            not include_partial
            and not is_complete
        ):
            continue

        item = dict(summary)

        item[
            "period_type"
        ] = "month"

        item[
            "label"
        ] = month_label(
            year,
            month,
        )

        item[
            "year"
        ] = year

        item[
            "month"
        ] = month

        item[
            "is_complete"
        ] = is_complete

        result.append(
            item
        )

    return result


def build_year_candidates(
    date_from=None,
    date_to=None,
    include_partial=False,
):
    earliest = (
        get_earliest_history_date()
    )

    latest = (
        get_latest_daily_date()
    )

    if (
        earliest is None
        or latest is None
    ):
        return []

    first_year = (
        parse_day(
            date_from
        ).year
        if date_from
        else earliest.year
    )

    last_year = (
        parse_day(
            date_to
        ).year
        if date_to
        else latest.year
    )

    result = []

    for year in range(
        first_year,
        last_year + 1,
    ):
        summary = get_year_summary(
            year,
            allow_partial=(
                include_partial
            ),
        )

        status = summary.get(
            "status"
        )

        if status == "ok":
            if (
                not include_partial
                and not summary.get(
                    "is_complete_year"
                )
            ):
                continue

        elif (
            status == "partial"
            and include_partial
        ):
            pass

        else:
            continue

        item = dict(summary)

        item[
            "period_type"
        ] = "year"

        item[
            "label"
        ] = str(year)

        result.append(
            item
        )

    return result


def rank_sales_periods(
    granularity,
    metric,
    date_from=None,
    date_to=None,
    order="desc",
    limit=5,
    min_checks=0,
    include_partial=False,
):
    granularity = (
        str(granularity)
        .strip()
        .lower()
    )

    metric = (
        str(metric)
        .strip()
        .lower()
    )

    order = (
        str(order)
        .strip()
        .lower()
    )

    if metric in {
        "profit",
        "profitability",
        "прибыль",
        "маржа",
    }:
        return {
            "status":
                "unsupported_metric",

            "metric":
                metric,

            "message":
                (
                    "Прибыль пока не рассчитывается: "
                    "для неё нужны себестоимость "
                    "и расходы. Можно ранжировать "
                    "по выручке."
                ),
        }

    if metric not in (
        SUPPORTED_RANK_METRICS
    ):
        return {
            "status":
                "unsupported_metric",

            "metric":
                metric,

            "supported_metrics":
                sorted(
                    SUPPORTED_RANK_METRICS
                ),
        }

    if granularity == "day":
        candidates = (
            build_day_candidates(
                date_from=date_from,
                date_to=date_to,
            )
        )

    elif granularity == "month":
        candidates = (
            build_month_candidates(
                date_from=date_from,
                date_to=date_to,
                include_partial=(
                    include_partial
                ),
            )
        )

    elif granularity == "year":
        candidates = (
            build_year_candidates(
                date_from=date_from,
                date_to=date_to,
                include_partial=(
                    include_partial
                ),
            )
        )

    else:
        return {
            "status":
                "unsupported_granularity",

            "granularity":
                granularity,

            "supported":
                [
                    "day",
                    "month",
                    "year",
                ],
        }

    min_checks = max(
        0,
        int(
            min_checks or 0
        ),
    )

    filtered = []

    for item in candidates:
        checks = item.get(
            "checks"
        )

        if min_checks > 0:
            if (
                checks is None
                or float(checks)
                < min_checks
            ):
                continue

        if not metric_is_available(
            item,
            metric,
        ):
            continue

        filtered.append(
            item
        )

    reverse = (
        order != "asc"
    )

    filtered.sort(
        key=lambda item:
            float(
                item[
                    metric
                ]
            ),
        reverse=reverse,
    )

    limit = max(
        1,
        min(
            int(
                limit or 5
            ),
            100,
        ),
    )

    selected = filtered[
        :limit
    ]

    ranking = []

    for position, item in enumerate(
        selected,
        start=1,
    ):
        ranking.append(
            {
                "position":
                    position,

                "period_type":
                    item.get(
                        "period_type"
                    ),

                "label":
                    item.get(
                        "label"
                    ),

                "start_date":
                    item.get(
                        "start_date"
                    ),

                "end_date":
                    item.get(
                        "end_date"
                    ),

                "metric":
                    metric,

                "value":
                    item.get(
                        metric
                    ),

                "checks":
                    item.get(
                        "checks"
                    ),

                "total_revenue":
                    item.get(
                        "total_revenue"
                    ),

                "average_check":
                    item.get(
                        "average_check"
                    ),

                "ktch":
                    item.get(
                        "ktch"
                    ),

                "source":
                    item.get(
                        "source"
                    ),

                "is_complete":
                    item.get(
                        "is_complete",
                        item.get(
                            "is_complete_year"
                        ),
                    ),

                "status":
                    item.get(
                        "status"
                    ),
            }
        )

    return {
        "status":
            "ok",

        "granularity":
            granularity,

        "metric":
            metric,

        "order":
            order,

        "limit":
            limit,

        "min_checks":
            min_checks,

        "include_partial":
            bool(
                include_partial
            ),

        "date_from":
            date_from,

        "date_to":
            date_to,

        "candidates_with_metric":
            len(
                filtered
            ),

        "ranking":
            ranking,

        "coverage":
            get_available_sales_coverage(),

        "interpretation_note":
            (
                "Рейтинг построен только "
                "по реально доступным данным. "
                "Неполные периоды исключаются, "
                "если include_partial=False."
            ),
    }


def print_period(
    title,
    result,
):
    print()
    print("-" * 80)
    print(title)
    print("-" * 80)

    print(
        "status:",
        result.get(
            "status"
        ),
    )

    if (
        result.get(
            "status"
        )
        != "ok"
    ):
        print(
            "message:",
            result.get(
                "message"
            ),
        )

        return

    print(
        "period:",
        result.get(
            "start_date"
        ),
        "-",
        result.get(
            "end_date"
        ),
    )

    print(
        "sources:",
        result.get(
            "sources"
        ),
    )

    print(
        "total_revenue:",
        result.get(
            "total_revenue"
        ),
    )

    print(
        "checks:",
        result.get(
            "checks"
        ),
    )

    print(
        "average_check:",
        result.get(
            "average_check"
        ),
    )

    print(
        "ktch:",
        result.get(
            "ktch"
        ),
    )


def print_ranking(
    title,
    result,
):
    print()
    print("-" * 80)
    print(title)
    print("-" * 80)

    print(
        "status:",
        result.get(
            "status"
        ),
    )

    for item in result.get(
        "ranking",
        [],
    ):
        print(
            f"{item['position']}. "
            f"{item['label']} | "
            f"{item['metric']} = "
            f"{item['value']} | "
            f"checks = "
            f"{item.get('checks')}"
        )


def demo():
    print()
    print("=" * 80)
    print(
        "SALES ANALYTICS — TEST"
    )
    print("=" * 80)

    print()
    print(
        "ПОКРЫТИЕ ДАННЫХ:"
    )

    print(
        get_available_sales_coverage()
    )

    print_period(
        "ЯНВАРЬ–ФЕВРАЛЬ 2025",
        get_period_summary(
            "01.01.2025",
            "28.02.2025",
        ),
    )

    print_period(
        "ТОЛЬКО ЯНВАРЬ 2025 — ДОЛЖЕН БЫТЬ НЕДОСТУПЕН",
        get_period_summary(
            "01.01.2025",
            "31.01.2025",
        ),
    )

    print_period(
        "АПРЕЛЬ 2026 — КТЧ ДОЛЖЕН БЫТЬ 3.30",
        get_period_summary(
            "01.04.2026",
            "30.04.2026",
        ),
    )

    print_period(
        "АПРЕЛЬ + МАЙ 2026",
        get_period_summary(
            "01.04.2026",
            "31.05.2026",
        ),
    )

    print_period(
        "ВЕСЬ 2025 ГОД",
        get_period_summary(
            "01.01.2025",
            "31.12.2025",
        ),
    )

    print()
    print("=" * 80)
    print(
        "ГОДОВЫЕ ИТОГИ"
    )
    print("=" * 80)

    year_2025 = get_year_summary(
        2025
    )

    print(
        "2025 status:",
        year_2025.get(
            "status"
        ),
    )

    print(
        "2025 total_revenue:",
        year_2025.get(
            "total_revenue"
        ),
    )

    print(
        "2025 checks:",
        year_2025.get(
            "checks"
        ),
    )

    print(
        "2025 complete:",
        year_2025.get(
            "is_complete_year"
        ),
    )

    year_2026 = get_year_summary(
        2026
    )

    print()
    print(
        "2026 status:",
        year_2026.get(
            "status"
        ),
    )

    print(
        "2026 total_revenue:",
        year_2026.get(
            "total_revenue"
        ),
    )

    print(
        "2026 complete:",
        year_2026.get(
            "is_complete_year"
        ),
    )

    print()
    print("=" * 80)
    print(
        "СРАВНЕНИЕ ПРОИЗВОЛЬНЫХ ПЕРИОДОВ"
    )
    print("=" * 80)

    comparison = (
        compare_sales_periods(
            "01.07.2026",
            "17.07.2026",
            "01.08.2026",
            "17.08.2026",
        )
    )

    print(
        "status:",
        comparison.get(
            "status"
        ),
    )

    print(
        "total_revenue:",
        comparison
        .get(
            "metrics_b_vs_a",
            {},
        )
        .get(
            "total_revenue"
        ),
    )

    print_ranking(
        "ТОП-5 МЕСЯЦЕВ ПО ВЫРУЧКЕ",
        rank_sales_periods(
            granularity="month",
            metric="total_revenue",
            order="desc",
            limit=5,
        ),
    )

    print_ranking(
        "ТОП-5 МЕСЯЦЕВ ПО СРЕДНЕМУ ЧЕКУ",
        rank_sales_periods(
            granularity="month",
            metric="average_check",
            order="desc",
            limit=5,
        ),
    )

    print_ranking(
        "ТОП-5 ДНЕЙ АВГУСТА ПО ВЫРУЧКЕ",
        rank_sales_periods(
            granularity="day",
            metric="total_revenue",
            date_from="01.08.2026",
            date_to="17.08.2026",
            order="desc",
            limit=5,
        ),
    )

    print_ranking(
        (
            "ТОП-5 ДНЕЙ АВГУСТА "
            "ПО СРЕДНЕМУ ЧЕКУ, "
            "МИНИМУМ 20 ЧЕКОВ"
        ),
        rank_sales_periods(
            granularity="day",
            metric="average_check",
            date_from="01.08.2026",
            date_to="17.08.2026",
            order="desc",
            limit=5,
            min_checks=20,
        ),
    )

    print_ranking(
        "ГОДЫ ПО ВЫРУЧКЕ — ТОЛЬКО ЗАВЕРШЁННЫЕ",
        rank_sales_periods(
            granularity="year",
            metric="total_revenue",
            order="desc",
            limit=5,
            include_partial=False,
        ),
    )

    print()
    print("=" * 80)
    print(
        "ПРОВЕРКА СЛОВА «ПРИБЫЛЬ»"
    )
    print("=" * 80)

    print(
        rank_sales_periods(
            granularity="month",
            metric="profit",
        )
    )


if __name__ == "__main__":
    demo()