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


MONTH_NAMES_GENITIVE = {
    1: "января",
    2: "февраля",
    3: "марта",
    4: "апреля",
    5: "мая",
    6: "июня",
    7: "июля",
    8: "августа",
    9: "сентября",
    10: "октября",
    11: "ноября",
    12: "декабря",
}


METRIC_LABELS = {
    "total_revenue":
        "общая выручка",

    "check_revenue_net":
        "выручка по чекам после возвратов",

    "checks":
        "количество чеков",

    "items":
        "количество товаров",

    "average_check":
        "средний чек",

    "ktch":
        "товаров в чеке",

    "cash":
        "наличные",

    "card":
        "безнал",

    "returns":
        "возвраты",

    "self_pickup":
        "самовывоз",

    "yandex_food":
        "Яндекс",

    "kuper":
        "Купер",

    "external_total":
        "выручка внешних заказов",

    "external_orders":
        "количество внешних заказов",

    "no_receipt":
        "продажи без чека",

    "revenue_per_data_day":
        "выручка в день",

    "checks_per_data_day":
        "чеков в день",

    "items_per_data_day":
        "товаров в день",

    "external_revenue_per_data_day":
        "выручка внешних заказов в день",
}


MONEY_METRICS = {
    "total_revenue",
    "check_revenue_net",
    "average_check",
    "cash",
    "card",
    "returns",
    "self_pickup",
    "yandex_food",
    "kuper",
    "external_total",
    "no_receipt",
    "revenue_per_data_day",
    "external_revenue_per_data_day",
}


INTEGER_METRICS = {
    "checks",
    "external_orders",
}


def format_money(value):
    try:
        value = float(
            value
        )

    except Exception:
        return str(
            value
        )

    return (
        f"{value:,.0f}"
        .replace(
            ",",
            " ",
        )
        + " ₽"
    )


def format_number(
    value,
    digits=2,
):
    try:
        value = float(
            value
        )

    except Exception:
        return str(
            value
        )

    return (
        f"{value:.{digits}f}"
        .replace(
            ".",
            ",",
        )
    )


def format_integer(value):
    try:
        return (
            f"{int(round(float(value))):,}"
            .replace(
                ",",
                " ",
            )
        )

    except Exception:
        return str(
            value
        )


def format_percent(value):
    if value is None:
        return "—"

    value = float(
        value
    )

    prefix = ""

    if value > 0:
        prefix = "+"

    return (
        prefix
        + format_number(
            value,
            2,
        )
        + "%"
    )


def format_metric_value(
    metric,
    value,
):
    if value is None:
        return "—"

    if metric in MONEY_METRICS:
        return format_money(
            value
        )

    if metric in INTEGER_METRICS:
        return format_integer(
            value
        )

    if metric == "items":
        return format_number(
            value,
            0,
        )

    if metric == "ktch":
        return format_number(
            value,
            2,
        )

    if metric in {
        "checks_per_data_day",
        "items_per_data_day",
    }:
        return format_number(
            value,
            2,
        )

    return format_number(
        value,
        2,
    )


def month_label(
    year,
    month,
):
    try:
        year = int(
            year
        )

        month = int(
            month
        )

    except Exception:
        return (
            f"{month}.{year}"
        )

    return (
        f"{MONTH_NAMES.get(month, str(month))} "
        f"{year}"
    )


def period_label(
    result,
):
    start_date = result.get(
        "start_date"
    )

    end_date = result.get(
        "end_date"
    )

    if (
        start_date
        and end_date
    ):
        if (
            start_date
            == end_date
        ):
            return start_date

        return (
            f"{start_date} — "
            f"{end_date}"
        )

    return "период"


def render_comparison_metric(
    label,
    comparison,
    metric,
):
    if not comparison:
        return None

    earlier = comparison.get(
        "earlier"
    )

    later = comparison.get(
        "later"
    )

    percent = comparison.get(
        "change_percent_vs_earlier"
    )

    return (
        f"• {label}: "
        f"{format_metric_value(metric, earlier)} → "
        f"{format_metric_value(metric, later)} "
        f"({format_percent(percent)})."
    )


def append_main_metrics(
    lines,
    result,
):
    fields = [
        (
            "total_revenue",
            "Общая выручка",
        ),
        (
            "check_revenue_net",
            "Выручка по чекам после возвратов",
        ),
        (
            "checks",
            "Чеков",
        ),
        (
            "items",
            "Товаров продано",
        ),
        (
            "average_check",
            "Средний чек",
        ),
        (
            "ktch",
            "Товаров в чеке",
        ),
        (
            "external_total",
            "Выручка внешних заказов",
        ),
        (
            "external_orders",
            "Внешних заказов",
        ),
    ]

    for metric, label in fields:
        if metric not in result:
            continue

        value = result.get(
            metric
        )

        if value is None:
            continue

        lines.append(
            f"• {label}: "
            f"{format_metric_value(metric, value)}"
        )


def render_month_comparison(result):
    status = result.get(
        "status"
    )

    if status == "missing_data":
        missing = []

        period_a = result.get(
            "period_a",
            {},
        )

        period_b = result.get(
            "period_b",
            {},
        )

        if (
            period_a.get(
                "status"
            )
            != "ok"
        ):
            missing.append(
                month_label(
                    period_a.get(
                        "year"
                    ),
                    period_a.get(
                        "month"
                    ),
                )
            )

        if (
            period_b.get(
                "status"
            )
            != "ok"
        ):
            missing.append(
                month_label(
                    period_b.get(
                        "year"
                    ),
                    period_b.get(
                        "month"
                    ),
                )
            )

        if missing:
            return (
                "Корректно сравнить месяцы пока нельзя: "
                "нет данных за "
                + ", ".join(
                    missing
                )
                + "."
            )

        return (
            "Корректно сравнить эти месяцы "
            "пока нельзя: данных недостаточно."
        )

    if (
        status
        == "missing_like_for_like_data"
    ):
        return (
            "Месяцы найдены, но не хватает "
            "дневных данных для честного "
            "сравнения одинаковых периодов."
        )

    if status != "ok":
        return (
            "Не получилось корректно "
            "сравнить эти месяцы."
        )

    earlier_period = result.get(
        "earlier_period",
        {},
    )

    later_period = result.get(
        "later_period",
        {},
    )

    earlier_year = earlier_period.get(
        "year"
    )

    earlier_month = earlier_period.get(
        "month"
    )

    later_year = later_period.get(
        "year"
    )

    later_month = later_period.get(
        "month"
    )

    earlier_label = month_label(
        earlier_year,
        earlier_month,
    )

    later_label = month_label(
        later_year,
        later_month,
    )

    metrics = result.get(
        "metrics",
        {},
    )

    comparison_type = result.get(
        "comparison_type"
    )

    comparison_end_day = result.get(
        "comparison_end_day"
    )

    lines = []

    if (
        comparison_type
        == "like_for_like_partial_month"
    ):
        later_genitive = (
            MONTH_NAMES_GENITIVE.get(
                int(
                    later_month
                ),
                str(
                    later_month
                ),
            )
        )

        earlier_genitive = (
            MONTH_NAMES_GENITIVE.get(
                int(
                    earlier_month
                ),
                str(
                    earlier_month
                ),
            )
        )

        lines.append(
            f"{later_label.capitalize()} "
            f"ещё не завершён, поэтому сравниваю "
            f"одинаковые периоды: "
            f"1–{comparison_end_day} "
            f"{later_genitive} против "
            f"1–{comparison_end_day} "
            f"{earlier_genitive}."
        )

    else:
        lines.append(
            f"Сравниваю полный "
            f"{later_label} с полным "
            f"{earlier_label}."
        )

    lines.append(
        ""
    )

    comparison_fields = [
        (
            "total_revenue",
            "Общая выручка",
        ),
        (
            "check_revenue_net",
            "Выручка по чекам после возвратов",
        ),
        (
            "checks",
            "Чеки",
        ),
        (
            "items",
            "Товаров продано",
        ),
        (
            "average_check",
            "Средний чек",
        ),
        (
            "ktch",
            "Товаров в чеке",
        ),
        (
            "external_total",
            "Выручка внешних заказов",
        ),
        (
            "external_orders",
            "Внешние заказы",
        ),
    ]

    for metric, label in comparison_fields:
        comparison = metrics.get(
            metric
        )

        line = render_comparison_metric(
            label,
            comparison,
            metric,
        )

        if line:
            lines.append(
                line
            )

    total_revenue = metrics.get(
        "total_revenue"
    )

    if total_revenue:
        revenue_change = (
            total_revenue.get(
                "change_percent_vs_earlier"
            )
        )

        if revenue_change is not None:
            lines.append(
                ""
            )

            if revenue_change > 0:
                lines.append(
                    f"Главный итог: "
                    f"{later_label} выше "
                    f"{earlier_label} по выручке "
                    f"на {format_percent(revenue_change)}."
                )

            elif revenue_change < 0:
                lines.append(
                    f"Главный итог: "
                    f"{later_label} ниже "
                    f"{earlier_label} по выручке "
                    f"на {format_percent(revenue_change)}."
                )

            else:
                lines.append(
                    "Главный итог: выручка "
                    "не изменилась."
                )

    if (
        comparison_type
        == "like_for_like_partial_month"
    ):
        lines.append(
            ""
        )

        lines.append(
            "Полную сумму текущего месяца "
            "с полным предыдущим месяцем "
            "для оценки динамики не сравниваю — "
            "это было бы некорректно."
        )

    return "\n".join(
        lines
    )


def render_period_summary(result):
    status = result.get(
        "status"
    )

    if (
        status
        == "insufficient_granularity"
    ):
        lines = [
            (
                "Этот период целиком посчитать "
                "без выдумок нельзя."
            )
        ]

        unavailable = result.get(
            "unavailable_parts",
            [],
        )

        for item in unavailable:
            lines.append(
                (
                    f"Недоступный участок: "
                    f"{item.get('start_date')} — "
                    f"{item.get('end_date')}."
                )
            )

        return "\n".join(
            lines
        )

    if status == "invalid_period":
        return (
            "Начальная дата периода "
            "оказалась позже конечной."
        )

    if status != "ok":
        return (
            "Для этого периода "
            "не хватает данных."
        )

    lines = [
        (
            f"Продажи за "
            f"{period_label(result)}:"
        ),
        "",
    ]

    append_main_metrics(
        lines,
        result,
    )

    sources = result.get(
        "sources",
        [],
    )

    if (
        "historical_combined"
        in sources
    ):
        lines.append(
            ""
        )

        lines.append(
            "Часть периода взята из "
            "исторической объединённой строки. "
            "Она используется только целиком "
            "и не разбивается искусственно."
        )

    return "\n".join(
        lines
    )


def render_period_comparison(result):
    status = result.get(
        "status"
    )

    if status != "ok":
        return (
            "Корректно сравнить эти периоды "
            "не получилось: по одному из них "
            "не хватает подходящих данных."
        )

    period_a = result.get(
        "period_a",
        {},
    )

    period_b = result.get(
        "period_b",
        {},
    )

    metrics = result.get(
        "metrics_b_vs_a",
        {},
    )

    lines = [
        (
            f"Сравниваю "
            f"{period_label(period_a)} "
            f"и {period_label(period_b)}."
        )
    ]

    if not result.get(
        "same_duration"
    ):
        lines.append(
            (
                "Периоды разной длины, поэтому "
                "абсолютные суммы нужно читать "
                "с учётом этого."
            )
        )

    lines.append(
        ""
    )

    comparison_fields = [
        (
            "total_revenue",
            "Общая выручка",
        ),
        (
            "check_revenue_net",
            "Выручка по чекам после возвратов",
        ),
        (
            "checks",
            "Чеки",
        ),
        (
            "items",
            "Товаров продано",
        ),
        (
            "average_check",
            "Средний чек",
        ),
        (
            "ktch",
            "Товаров в чеке",
        ),
        (
            "external_total",
            "Выручка внешних заказов",
        ),
        (
            "external_orders",
            "Внешние заказы",
        ),
    ]

    for metric, label in comparison_fields:
        comparison = metrics.get(
            metric
        )

        line = render_comparison_metric(
            label,
            comparison,
            metric,
        )

        if line:
            lines.append(
                line
            )

    total_revenue = metrics.get(
        "total_revenue"
    )

    if total_revenue:
        change = total_revenue.get(
            "change_percent_vs_earlier"
        )

        if change is not None:
            lines.append(
                ""
            )

            if change > 0:
                lines.append(
                    (
                        "Главный итог: второй период "
                        "выше первого по выручке "
                        f"на {format_percent(change)}."
                    )
                )

            elif change < 0:
                lines.append(
                    (
                        "Главный итог: второй период "
                        "ниже первого по выручке "
                        f"на {format_percent(change)}."
                    )
                )

            else:
                lines.append(
                    "Главный итог: выручка одинаковая."
                )

    return "\n".join(
        lines
    )


def render_year_summary(result):
    status = result.get(
        "status"
    )

    year = result.get(
        "year"
    )

    if status == "partial":
        return (
            f"По {year} году есть только "
            "неполный набор месяцев. "
            "Полный итог года называть нельзя."
        )

    if (
        status
        in {
            "not_found",
            "no_data",
        }
    ):
        return (
            f"Данных за {year} год нет."
        )

    if status != "ok":
        return (
            f"Не получилось посчитать "
            f"{year} год."
        )

    complete = bool(
        result.get(
            "is_complete_year"
        )
    )

    if complete:
        title = (
            f"Итоги {year} года:"
        )

    else:
        title = (
            f"{year} год по последний "
            f"закрытый день "
            f"({result.get('end_date')}):"
        )

    lines = [
        title,
        "",
    ]

    append_main_metrics(
        lines,
        result,
    )

    if not complete:
        lines.append(
            ""
        )

        lines.append(
            "Год ещё не завершён, поэтому "
            "это не полный годовой итог."
        )

    return "\n".join(
        lines
    )


def render_year_comparison(result):
    status = result.get(
        "status"
    )

    if status != "ok":
        return (
            "Корректно сравнить эти годы "
            "не получилось: данных недостаточно."
        )

    year_a = result.get(
        "year_a",
        {},
    )

    year_b = result.get(
        "year_b",
        {},
    )

    metrics = result.get(
        "metrics_b_vs_a",
        {},
    )

    label_a = str(
        year_a.get(
            "year",
            "первый год",
        )
    )

    label_b = str(
        year_b.get(
            "year",
            "второй год",
        )
    )

    lines = [
        (
            f"Сравниваю {label_a} "
            f"и {label_b}:"
        ),
        "",
    ]

    comparison_fields = [
        (
            "total_revenue",
            "Общая выручка",
        ),
        (
            "check_revenue_net",
            "Выручка по чекам после возвратов",
        ),
        (
            "checks",
            "Чеки",
        ),
        (
            "items",
            "Товаров продано",
        ),
        (
            "average_check",
            "Средний чек",
        ),
        (
            "external_total",
            "Выручка внешних заказов",
        ),
        (
            "external_orders",
            "Внешние заказы",
        ),
    ]

    for metric, label in comparison_fields:
        comparison = metrics.get(
            metric
        )

        line = render_comparison_metric(
            label,
            comparison,
            metric,
        )

        if line:
            lines.append(
                line
            )

    warning = result.get(
        "warning"
    )

    if warning:
        lines.append(
            ""
        )

        lines.append(
            (
                "Важно: один из годов "
                "ещё не завершён, поэтому "
                "сравнение полных годовых "
                "итогов пока невозможно."
            )
        )

    return "\n".join(
        lines
    )


def ranking_title(
    granularity,
    metric,
    order,
):
    noun = {
        "day":
            "дни",

        "month":
            "месяцы",

        "year":
            "годы",
    }.get(
        granularity,
        "периоды",
    )

    metric_label = (
        METRIC_LABELS.get(
            metric,
            metric,
        )
    )

    if order == "asc":
        prefix = "Минимальные"

    else:
        prefix = "Максимальные"

    return (
        f"{prefix} {noun} "
        f"по показателю "
        f"«{metric_label}»:"
    )


def render_sales_ranking(result):
    status = result.get(
        "status"
    )

    if (
        status
        == "unsupported_metric"
    ):
        metric = result.get(
            "metric"
        )

        if metric in {
            "profit",
            "profitability",
            "прибыль",
            "маржа",
        }:
            return (
                "Прибыль пока корректно "
                "ранжировать нельзя: "
                "для этого нужны полноценные "
                "данные по себестоимости "
                "и расходам. "
                "Выручку прибылью не подменяю."
            )

        return (
            "Этот показатель пока "
            "не поддерживается для рейтинга."
        )

    if (
        status
        == "unsupported_granularity"
    ):
        return (
            "Можно ранжировать продажи "
            "по дням, месяцам или годам."
        )

    if status != "ok":
        return (
            "Не получилось построить рейтинг."
        )

    ranking = result.get(
        "ranking",
        [],
    )

    metric = result.get(
        "metric"
    )

    granularity = result.get(
        "granularity"
    )

    order = result.get(
        "order",
        "desc",
    )

    if not ranking:
        return (
            "Для такого рейтинга "
            "нет подходящих данных."
        )

    lines = [
        ranking_title(
            granularity,
            metric,
            order,
        ),
        "",
    ]

    for item in ranking:
        position = item.get(
            "position"
        )

        label = item.get(
            "label"
        )

        value = item.get(
            "value"
        )

        line = (
            f"{position}. "
            f"{label} — "
            f"{format_metric_value(metric, value)}"
        )

        checks = item.get(
            "checks"
        )

        if (
            checks is not None
            and metric != "checks"
        ):
            line += (
                f" "
                f"({format_integer(checks)} чеков)"
            )

        lines.append(
            line
        )

    min_checks = int(
        result.get(
            "min_checks",
            0,
        )
        or 0
    )

    if min_checks > 0:
        lines.append(
            ""
        )

        lines.append(
            f"В рейтинг включены только "
            f"периоды минимум с "
            f"{min_checks} чеками."
        )

    if result.get(
        "include_partial"
    ):
        lines.append(
            ""
        )

        lines.append(
            "В рейтинг разрешено включать "
            "незавершённые периоды."
        )

    return "\n".join(
        lines
    )


def render_sales_tool_result(
    tool_name,
    result,
):
    if (
        tool_name
        == "compare_sales_months"
    ):
        return render_month_comparison(
            result
        )

    if (
        tool_name
        == "get_sales_period_summary"
    ):
        return render_period_summary(
            result
        )

    if (
        tool_name
        == "compare_sales_periods"
    ):
        return render_period_comparison(
            result
        )

    if (
        tool_name
        == "get_sales_year_summary"
    ):
        return render_year_summary(
            result
        )

    if (
        tool_name
        == "compare_sales_years"
    ):
        return render_year_comparison(
            result
        )

    if (
        tool_name
        == "rank_sales_periods"
    ):
        return render_sales_ranking(
            result
        )

    return None


def demo():
    from sales_tools import (
        compare_sales_months,
    )

    from sales_analytics import (
        compare_sales_periods,
        get_period_summary,
        get_year_summary,
        rank_sales_periods,
    )

    print()
    print("=" * 70)
    print(
        "SALES RENDERER — TEST"
    )
    print("=" * 70)

    print()
    print(
        "1. СРАВНЕНИЕ МЕСЯЦЕВ"
    )
    print()

    print(
        render_month_comparison(
            compare_sales_months(
                2026,
                7,
                2026,
                8,
            )
        )
    )

    print()
    print("=" * 70)
    print(
        "2. ПРОИЗВОЛЬНЫЙ ПЕРИОД"
    )
    print()

    print(
        render_period_summary(
            get_period_summary(
                "01.04.2026",
                "31.05.2026",
            )
        )
    )

    print()
    print("=" * 70)
    print(
        "3. СРАВНЕНИЕ ПЕРИОДОВ"
    )
    print()

    print(
        render_period_comparison(
            compare_sales_periods(
                "01.07.2026",
                "17.07.2026",
                "01.08.2026",
                "17.08.2026",
            )
        )
    )

    print()
    print("=" * 70)
    print(
        "4. 2025 ГОД"
    )
    print()

    print(
        render_year_summary(
            get_year_summary(
                2025
            )
        )
    )

    print()
    print("=" * 70)
    print(
        "5. ТОП МЕСЯЦЕВ"
    )
    print()

    print(
        render_sales_ranking(
            rank_sales_periods(
                granularity="month",
                metric="total_revenue",
                order="desc",
                limit=3,
            )
        )
    )

    print()
    print("=" * 70)
    print(
        "6. ТОП ДНЕЙ ПО СРЕДНЕМУ ЧЕКУ"
    )
    print()

    print(
        render_sales_ranking(
            rank_sales_periods(
                granularity="day",
                metric="average_check",
                date_from="01.08.2026",
                date_to="17.08.2026",
                order="desc",
                limit=3,
                min_checks=20,
            )
        )
    )

    print()
    print("=" * 70)
    print(
        "7. ПРИБЫЛЬ — ДОЛЖЕН БЫТЬ ОТКАЗ"
    )
    print()

    print(
        render_sales_ranking(
            rank_sales_periods(
                granularity="month",
                metric="profit",
                limit=3,
            )
        )
    )


if __name__ == "__main__":
    demo()