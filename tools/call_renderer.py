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


def format_phone(phone):
    digits = "".join(
        char
        for char in str(phone or "")
        if char.isdigit()
    )

    if (
        len(digits) == 11
        and digits[0] in {"7", "8"}
    ):
        return (
            f"+7 ({digits[1:4]}) "
            f"{digits[4:7]}-"
            f"{digits[7:9]}-"
            f"{digits[9:11]}"
        )

    return str(phone or "")


def format_customer_name(value):
    text = str(value or "").strip()

    if not text:
        return "Клиент"

    return " ".join(
        part.capitalize()
        for part in text.split()
    )


def purchase_word(count):
    count = int(count)

    if (
        count % 10 == 1
        and count % 100 != 11
    ):
        return "покупка"

    if (
        count % 10 in {2, 3, 4}
        and count % 100 not in {12, 13, 14}
    ):
        return "покупки"

    return "покупок"


def render_next_call_card(result):
    if result.get("status") != "ok":
        return (
            "Сейчас не получилось выбрать "
            "следующего подходящего клиента."
        )

    candidate = result.get(
        "candidate",
        {},
    )

    plan = result.get(
        "conversation_plan",
        {},
    )

    products = result.get(
        "top_products",
        [],
    )

    name = format_customer_name(
        candidate.get("full_name")
    )

    phone = format_phone(
        candidate.get("phone")
    )

    frequency = int(
        candidate.get("frequency", 0)
        or 0
    )

    monetary = format_money(
        candidate.get("monetary", 0)
    )

    average_check = format_money(
        candidate.get("average_check", 0)
    )

    recency_days = candidate.get(
        "recency_days",
        0,
    )

    average_interval = candidate.get(
        "average_interval_days",
        0,
    )

    overdue = candidate.get(
        "cycle_overdue_ratio",
        0,
    )

    segment = candidate.get(
        "segment",
        "",
    )

    score = candidate.get(
        "priority_score",
        "",
    )

    lines = []

    lines.append(
        "1. КОМУ ПОЗВОНИТЬ"
    )

    lines.append(
        f"{name} — {phone}"
    )

    lines.append("")

    lines.append(
        "2. ПОЧЕМУ КЛИЕНТ В ПРИОРИТЕТЕ"
    )

    lines.append(
        f"Сегмент: «{segment}». "
        f"У клиента {frequency} "
        f"{purchase_word(frequency)} "
        f"на общую сумму {monetary}, "
        f"средний чек — {average_check}. "
        f"Последняя покупка была "
        f"{recency_days} дней назад, "
        f"при обычном интервале примерно "
        f"{average_interval} дня. "
        f"Текущая пауза примерно в "
        f"{overdue} раза длиннее "
        f"обычного цикла. "
        f"Приоритет звонка: {score}/100."
    )

    lines.append("")

    lines.append(
        "3. ЧТО МЫ ТОЧНО ЗНАЕМ"
    )

    lines.append(
        f"Покупок: {frequency}."
    )

    lines.append(
        f"Общая сумма: {monetary}."
    )

    lines.append(
        f"Последняя покупка: "
        f"{candidate.get('last_purchase', '')}."
    )

    if products:
        lines.append(
            "Основные товары в истории:"
        )

        for product in products[:4]:
            product_name = product.get(
                "product_name",
                "",
            )

            quantity = float(
                product.get(
                    "quantity",
                    0,
                )
                or 0
            )

            total_rubles = format_money(
                product.get(
                    "total_rubles",
                    0,
                )
            )

            lines.append(
                f"• {product_name} — "
                f"{quantity:g} шт., "
                f"{total_rubles}"
            )

    lines.append("")

    lines.append(
        "4. КАК НАЧАТЬ РАЗГОВОР"
    )

    if products:
        top_product = products[0].get(
            "product_name",
            "",
        )

        opening = (
            f"Здравствуйте, это «Мокрый нос». "
            f"Раньше вы довольно регулярно "
            f"покупали у нас товары, "
            f"в том числе «{top_product}», "
            f"а давно вас не видели. "
            f"Хотел уточнить, всё ли вас устраивало "
            f"и актуально ли сейчас что-то "
            f"из того, что вы раньше брали?"
        )

    else:
        opening = plan.get(
            "opening_template",
            "",
        )

    lines.append(
        f"«{opening}»"
    )

    lines.append("")

    lines.append(
        "5. КАК РАЗВИВАТЬ РАЗГОВОР"
    )

    for branch in plan.get(
        "branches",
        [],
    ):
        lines.append("")

        lines.append(
            branch.get(
                "condition",
                "",
            )
            + ":"
        )

        for item in branch.get(
            "questions",
            [],
        ):
            lines.append(
                f"• {item}"
            )

        next_step = branch.get(
            "next_step",
            "",
        )

        if next_step:
            lines.append(
                f"Дальше: {next_step}"
            )

    lines.append("")

    lines.append(
        "6. ЦЕЛЬ ЗВОНКА"
    )

    lines.append(
        "Главная задача — понять реальную "
        "причину паузы и текущую потребность. "
        "Продажа во время первого разговора "
        "не обязательна."
    )

    outcomes = plan.get(
        "successful_outcomes",
        [],
    )

    if outcomes:
        lines.append(
            "Хорошим результатом будет:"
        )

        for outcome in outcomes[:5]:
            lines.append(
                f"• {outcome}"
            )

    lines.append("")

    lines.append(
        "Важно: старые покупки показывают "
        "только историю клиента. "
        "Они не доказывают его текущую потребность. "
        "Сначала выясняем ситуацию, "
        "потом подбираем предложение."
    )

    return "\n".join(lines)


def render_last_call_reason(result):
    if (
        not result
        or result.get("status") != "ok"
    ):
        return (
            "У меня нет сохранённых данных "
            "о последнем выбранном клиенте."
        )

    candidate = result.get(
        "candidate",
        {},
    )

    name = format_customer_name(
        candidate.get("full_name")
    )

    frequency = int(
        candidate.get("frequency", 0)
        or 0
    )

    components = candidate.get(
        "priority_score_components",
        {},
    )

    lines = []

    lines.append(
        f"Клиент {name} выбран не по одному "
        f"признаку, а по совокупности факторов."
    )

    lines.append("")

    lines.append(
        f"• Сегмент — «{candidate.get('segment', '')}»: "
        f"{components.get('segment', 0)} баллов."
    )

    lines.append(
        f"• Историческая ценность: "
        f"{frequency} "
        f"{purchase_word(frequency)} "
        f"на "
        f"{format_money(candidate.get('monetary', 0))}, "
        f"средний чек "
        f"{format_money(candidate.get('average_check', 0))}. "
        f"Компонент ценности — "
        f"{components.get('customer_value', 0)} балла."
    )

    lines.append(
        f"• Частота покупок — "
        f"{components.get('purchase_frequency', 0)} баллов."
    )

    lines.append(
        f"• Пауза: последняя покупка была "
        f"{candidate.get('recency_days', 0)} дней назад, "
        f"обычный интервал — примерно "
        f"{candidate.get('average_interval_days', 0)} дня. "
        f"Пауза длиннее обычного цикла примерно в "
        f"{candidate.get('cycle_overdue_ratio', 0)} раза. "
        f"За этот фактор — "
        f"{components.get('cycle_overdue', 0)} балла."
    )

    lines.append("")

    lines.append(
        f"Итоговый приоритет — "
        f"{candidate.get('priority_score', 0)}/100."
    )

    lines.append("")

    lines.append(
        "Причину паузы мы при этом не знаем. "
        "Скоринг показывает только сильное "
        "отклонение от прежнего поведения "
        "и ценность клиента."
    )

    return "\n".join(lines)


def render_customer_call_assessment(result):
    if (
        not result
        or result.get("status") != "ok"
    ):
        return (
            "Не получилось оценить приоритет "
            "звонка этому клиенту."
        )

    customer = result.get(
        "customer",
        {},
    )

    priority = result.get(
        "priority",
        {},
    )

    components = result.get(
        "score_components",
        {},
    )

    cycle_signal = result.get(
        "cycle_signal",
        {},
    )

    first_name = str(
        customer.get("name", "")
        or ""
    ).strip()

    last_name = str(
        customer.get("lastname", "")
        or ""
    ).strip()

    if first_name or last_name:
        name = format_customer_name(
            f"{first_name} {last_name}"
        )
    else:
        name = format_customer_name(
            customer.get("full_name")
        )

    frequency = int(
        customer.get("frequency", 0)
        or 0
    )

    score = priority.get(
        "score",
        0,
    )

    priority_label = priority.get(
        "label",
        "",
    )

    recommendation = priority.get(
        "recommendation",
        "",
    )

    segment = customer.get(
        "segment",
        "",
    )

    recency_days = customer.get(
        "recency_days",
        0,
    )

    monetary = format_money(
        customer.get(
            "monetary",
            0,
        )
    )

    average_check = format_money(
        customer.get(
            "average_check",
            0,
        )
    )

    lines = []

    lines.append(
        f"{name}: приоритет звонка — "
        f"{priority_label.lower()} "
        f"({score}/100)."
    )

    lines.append("")

    if recommendation:
        lines.append(
            recommendation
        )

        lines.append("")

    lines.append(
        "Почему:"
    )

    lines.append(
        f"• Сегмент «{segment}» — "
        f"{components.get('segment', 0)} баллов."
    )

    lines.append(
        f"• История покупок: {frequency} "
        f"{purchase_word(frequency)} "
        f"на общую сумму {monetary}, "
        f"средний чек — {average_check}. "
        f"Компонент ценности — "
        f"{components.get('customer_value', 0)} балла."
    )

    lines.append(
        f"• Частота покупок — "
        f"{components.get('purchase_frequency', 0)} балла."
    )

    lines.append(
        f"• Последняя покупка была "
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
            f"• Обычный интервал между покупками — "
            f"примерно {average_interval} дня; "
            f"текущая пауза примерно в "
            f"{overdue} раза длиннее этого интервала. "
            f"Компонент паузы — "
            f"{components.get('cycle_overdue', 0)} балла."
        )

    else:
        lines.append(
            "• Подтверждённого покупательского цикла нет: "
            "истории повторных покупок недостаточно. "
            "Поэтому нельзя утверждать, что текущая пауза "
            "аномальна относительно обычного поведения клиента. "
            f"Компонент паузы — "
            f"{components.get('cycle_overdue', 0)} баллов."
        )

    lines.append("")

    lines.append(
        "Что это значит:"
    )

    if priority.get(
        "level"
    ) == "high":
        lines.append(
            "Клиента имеет смысл поставить "
            "в начало очереди на обзвон."
        )

    elif priority.get(
        "level"
    ) == "medium":
        lines.append(
            "Позвонить имеет смысл, "
            "но есть клиенты с более сильным приоритетом."
        )

    else:
        lines.append(
            "Позвонить можно, но я бы сначала обзвонил "
            "клиентов с более сильной историей покупок "
            "и более высоким score."
        )

    lines.append("")

    lines.append(
        "Причину отсутствия клиента мы не знаем. "
        "Из этих данных нельзя делать выводы "
        "о текущей потребности, животном клиента "
        "или причине, по которой он перестал покупать."
    )

    return "\n".join(lines)


def demo():
    from call_tools import (
        get_customer_call_assessment,
        get_next_call_candidate,
    )

    print()
    print("=" * 70)
    print("CALL RENDERER — TEST")
    print("=" * 70)
    print()

    result = get_next_call_candidate(
        mode="retain",
        exclude_customer_ids=[],
    )

    print(
        render_next_call_card(
            result
        )
    )

    print()
    print("=" * 70)
    print("ПОЧЕМУ ИМЕННО ЭТОТ КЛИЕНТ")
    print("=" * 70)
    print()

    print(
        render_last_call_reason(
            result
        )
    )

    print()
    print("=" * 70)
    print("ОЦЕНКА КОНКРЕТНОГО КЛИЕНТА")
    print("=" * 70)
    print()

    assessment = (
        get_customer_call_assessment(
            "1000446"
        )
    )

    print(
        render_customer_call_assessment(
            assessment
        )
    )


if __name__ == "__main__":
    demo()