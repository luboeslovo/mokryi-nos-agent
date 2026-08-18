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


def format_money(value):
    try:
        value = float(value)
    except Exception:
        return str(value)

    return (
        f"{value:,.0f}"
        .replace(",", " ")
        + " ₽"
    )


def format_number(
    value,
    digits=2,
):
    try:
        value = float(value)
    except Exception:
        return str(value)

    return (
        f"{value:.{digits}f}"
        .replace(".", ",")
    )


def format_percent(value):
    if value is None:
        return "—"

    value = float(value)

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


def month_label(
    year,
    month,
):
    try:
        year = int(year)
        month = int(month)
    except Exception:
        return f"{month}.{year}"

    return (
        f"{MONTH_NAMES.get(month, str(month))} "
        f"{year}"
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
                "в дневной аналитике нет данных за "
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
            f"ещё не завершён, поэтому "
            f"сравниваю одинаковые периоды: "
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

    lines.append("")

    total_revenue = metrics.get(
        "total_revenue"
    )

    if total_revenue:
        lines.append(
            "• Общая выручка: "
            f"{format_money(total_revenue['earlier'])} → "
            f"{format_money(total_revenue['later'])} "
            f"({format_percent(total_revenue['change_percent_vs_earlier'])})."
        )

    check_revenue = metrics.get(
        "check_revenue_net"
    )

    if check_revenue:
        lines.append(
            "• Кассовая выручка после возвратов: "
            f"{format_money(check_revenue['earlier'])} → "
            f"{format_money(check_revenue['later'])} "
            f"({format_percent(check_revenue['change_percent_vs_earlier'])})."
        )

    checks = metrics.get(
        "checks"
    )

    if checks:
        lines.append(
            "• Чеки: "
            f"{checks['earlier']:.0f} → "
            f"{checks['later']:.0f} "
            f"({format_percent(checks['change_percent_vs_earlier'])})."
        )

    items = metrics.get(
        "items"
    )

    if items:
        lines.append(
            "• Товаров продано: "
            f"{items['earlier']:.0f} → "
            f"{items['later']:.0f} "
            f"({format_percent(items['change_percent_vs_earlier'])})."
        )

    average_check = metrics.get(
        "average_check"
    )

    if average_check:
        lines.append(
            "• Средний чек: "
            f"{format_money(average_check['earlier'])} → "
            f"{format_money(average_check['later'])} "
            f"({format_percent(average_check['change_percent_vs_earlier'])})."
        )

    ktch = metrics.get(
        "ktch"
    )

    if ktch:
        lines.append(
            "• Товаров в чеке: "
            f"{format_number(ktch['earlier'])} → "
            f"{format_number(ktch['later'])} "
            f"({format_percent(ktch['change_percent_vs_earlier'])})."
        )

    external_total = metrics.get(
        "external_total"
    )

    if external_total:
        lines.append(
            "• Выручка внешних заказов: "
            f"{format_money(external_total['earlier'])} → "
            f"{format_money(external_total['later'])} "
            f"({format_percent(external_total['change_percent_vs_earlier'])})."
        )

    external_orders = metrics.get(
        "external_orders"
    )

    if external_orders:
        lines.append(
            "• Внешние заказы: "
            f"{external_orders['earlier']:.0f} → "
            f"{external_orders['later']:.0f} "
            f"({format_percent(external_orders['change_percent_vs_earlier'])})."
        )

    lines.append("")

    revenue_change = None

    if total_revenue:
        revenue_change = (
            total_revenue.get(
                "change_percent_vs_earlier"
            )
        )

    if revenue_change is not None:
        if revenue_change > 0:
            lines.append(
                f"Главный итог: "
                f"{later_label} по сопоставимому "
                f"периоду идёт выше "
                f"{earlier_label} по выручке "
                f"на {format_percent(revenue_change)}."
            )

        elif revenue_change < 0:
            lines.append(
                f"Главный итог: "
                f"{later_label} по сопоставимому "
                f"периоду идёт ниже "
                f"{earlier_label} по выручке "
                f"на {format_percent(revenue_change)}."
            )

        else:
            lines.append(
                "Главный итог: выручка "
                "по сопоставимому периоду "
                "не изменилась."
            )

    observations = []

    if checks:
        checks_change = checks.get(
            "change_percent_vs_earlier"
        )

        if (
            checks_change is not None
            and checks_change > 0
        ):
            observations.append(
                "чеков стало больше"
            )

        elif (
            checks_change is not None
            and checks_change < 0
        ):
            observations.append(
                "чеков стало меньше"
            )

    if average_check:
        average_check_change = (
            average_check.get(
                "change_percent_vs_earlier"
            )
        )

        if (
            average_check_change is not None
            and average_check_change < 0
        ):
            observations.append(
                "средний чек снизился"
            )

        elif (
            average_check_change is not None
            and average_check_change > 0
        ):
            observations.append(
                "средний чек вырос"
            )

    if ktch:
        ktch_change = ktch.get(
            "change_percent_vs_earlier"
        )

        if (
            ktch_change is not None
            and ktch_change < 0
        ):
            observations.append(
                "товаров в одном чеке "
                "стало меньше"
            )

        elif (
            ktch_change is not None
            and ktch_change > 0
        ):
            observations.append(
                "товаров в одном чеке "
                "стало больше"
            )

    if observations:
        lines.append(
            "По структуре продаж: "
            + ", ".join(
                observations
            )
            + "."
        )

    if external_total:
        external_change = (
            external_total.get(
                "change_percent_vs_earlier"
            )
        )

        if (
            external_change is not None
            and external_change > 0
        ):
            lines.append(
                "Отдельно растут внешние заказы: "
                f"{format_percent(external_change)} "
                "по выручке."
            )

    if (
        comparison_type
        == "like_for_like_partial_month"
    ):
        lines.append(
            "Полную сумму текущего месяца "
            "с полным предыдущим месяцем "
            "для оценки динамики не сравниваю — "
            "это было бы некорректно."
        )

    return "\n".join(
        lines
    )


def demo():
    from sales_tools import (
        compare_sales_months,
    )

    result = compare_sales_months(
        2026,
        7,
        2026,
        8,
    )

    print()
    print("=" * 70)
    print("SALES RENDERER — TEST")
    print("=" * 70)
    print()
    print(
        render_month_comparison(
            result
        )
    )


if __name__ == "__main__":
    demo()