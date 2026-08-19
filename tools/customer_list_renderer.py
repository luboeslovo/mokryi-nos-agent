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


def format_customer_name(customer):
    full_name = str(
        customer.get(
            "full_name",
            "",
        )
        or ""
    ).strip()

    if full_name:
        return " ".join(
            part.capitalize()
            for part in full_name.split()
        )

    name = str(
        customer.get(
            "name",
            "",
        )
        or ""
    ).strip()

    lastname = str(
        customer.get(
            "lastname",
            "",
        )
        or ""
    ).strip()

    value = " ".join(
        part
        for part in [
            name,
            lastname,
        ]
        if part
    )

    if not value:
        return "Клиент"

    return " ".join(
        part.capitalize()
        for part in value.split()
    )


def get_priority_score(assessment):
    return float(
        assessment
        .get(
            "priority",
            {},
        )
        .get(
            "score",
            0,
        )
        or 0
    )


def render_customer_list_call_assessment(
    result,
):
    if (
        not result
        or result.get("status") != "ok"
    ):
        return (
            "Не получилось оценить клиентов "
            "из последнего списка."
        )

    assessments = [
        item
        for item in result.get(
            "assessments",
            [],
        )
        if item.get("status") == "ok"
    ]

    if not assessments:
        return (
            "В последнем списке не нашлось клиентов, "
            "для которых удалось рассчитать "
            "приоритет звонка."
        )

    assessments.sort(
        key=get_priority_score,
        reverse=True,
    )

    lines = []

    lines.append(
        "Проверил клиентов из последнего списка "
        "по тому же скорингу звонков."
    )

    lines.append("")

    for position, assessment in enumerate(
        assessments,
        start=1,
    ):
        customer = assessment.get(
            "customer",
            {},
        )

        priority = assessment.get(
            "priority",
            {},
        )

        cycle_signal = assessment.get(
            "cycle_signal",
            {},
        )

        name = format_customer_name(
            customer
        )

        score = priority.get(
            "score",
            0,
        )

        label = str(
            priority.get(
                "label",
                "",
            )
            or ""
        )

        level = priority.get(
            "level",
            "",
        )

        if level == "high":
            decision = (
                "звонить в первую очередь"
            )

        elif level == "medium":
            decision = (
                "звонить имеет смысл"
            )

        else:
            decision = (
                "низкий приоритет"
            )

        frequency = int(
            customer.get(
                "frequency",
                0,
            )
            or 0
        )

        monetary = format_money(
            customer.get(
                "monetary",
                0,
            )
        )

        recency_days = customer.get(
            "recency_days",
            0,
        )

        segment = customer.get(
            "segment",
            "",
        )

        lines.append(
            f"{position}. {name} — "
            f"{score}/100, "
            f"{label.lower()}."
        )

        lines.append(
            f"   {decision}. "
            f"Сегмент: «{segment}»; "
            f"покупок: {frequency}; "
            f"сумма покупок: {monetary}; "
            f"последняя покупка: "
            f"{recency_days} дней назад."
        )

        if cycle_signal.get(
            "available"
        ):
            average_interval = customer.get(
                "average_interval_days",
                0,
            )

            overdue = customer.get(
                "cycle_overdue_ratio",
                0,
            )

            lines.append(
                f"   Обычный интервал: "
                f"примерно {average_interval} дня; "
                f"текущая пауза — примерно "
                f"{overdue} раза от этого интервала."
            )

        lines.append("")

    priority_clients = [
        item
        for item in assessments
        if (
            item
            .get(
                "priority",
                {},
            )
            .get(
                "level"
            )
            in {
                "high",
                "medium",
            }
        )
    ]

    if priority_clients:
        best = priority_clients[0]

        best_customer = best.get(
            "customer",
            {},
        )

        best_priority = best.get(
            "priority",
            {},
        )

        best_name = format_customer_name(
            best_customer
        )

        lines.append(
            "Итог:"
        )

        lines.append(
            f"Из этого списка я бы в первую очередь "
            f"звонил клиенту {best_name}: "
            f"{best_priority.get('score', 0)}/100."
        )

        if len(priority_clients) > 1:
            other_names = [
                format_customer_name(
                    item.get(
                        "customer",
                        {},
                    )
                )
                for item in priority_clients[1:]
            ]

            lines.append(
                "Также имеет смысл рассмотреть: "
                + ", ".join(
                    other_names
                )
                + "."
            )

    else:
        lines.append(
            "Итог:"
        )

        lines.append(
            "Среди клиентов из этого списка "
            "нет ни одного со средним или высоким "
            "приоритетом звонка. "
            "Я бы сначала искал более сильных "
            "кандидатов в общей базе."
        )

    lines.append("")

    lines.append(
        "Причины отсутствия клиентов скоринг "
        "не определяет: он оценивает только "
        "историю покупок, RFM-сегмент, частоту, "
        "ценность и отклонение от покупательского цикла, "
        "когда такой цикл можно рассчитать."
    )

    return "\n".join(
        lines
    )


def demo():
    from call_tools import (
        get_customer_call_assessment,
    )

    from customer_tools import (
        get_top_customers,
    )

    top_result = get_top_customers(
        5
    )

    assessments = []

    for customer in top_result.get(
        "customers",
        [],
    ):
        customer_id = customer.get(
            "customer_id"
        )

        if not customer_id:
            continue

        assessment = (
            get_customer_call_assessment(
                customer_id
            )
        )

        assessments.append(
            assessment
        )

    result = {
        "status":
            "ok",

        "assessments":
            assessments,
    }

    print()
    print("=" * 70)
    print(
        "CUSTOMER LIST CALL ASSESSMENT — TEST"
    )
    print("=" * 70)
    print()

    print(
        render_customer_list_call_assessment(
            result
        )
    )


if __name__ == "__main__":
    demo()