from customer_tools import (
    get_customer_profile,
)

from rfm_tools import (
    get_contact_candidate_pool,
    get_customer_rfm,
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


def normalize_customer_ids(
    values,
):
    if values is None:
        return set()

    if isinstance(
        values,
        str,
    ):
        values = [
            values
        ]

    result = set()

    for value in values:
        customer_id = str(
            value or ""
        ).strip()

        if customer_id:
            result.add(
                customer_id
            )

    return result


def get_contact_signal(
    customer,
):
    """
    Определяет, есть ли вообще повод звонить клиенту сейчас.

    ВАЖНЫЙ ПРИНЦИП:
    ценность и частота клиента не создают повод для звонка.

    Сначала должен существовать сигнал:
    - подтверждённое отклонение от привычного цикла;
    - либо, если цикла пока нет, достаточно большая давность
      последней покупки.

    Только после появления такого сигнала в общий score
    добавляются ценность и частота.
    """

    frequency = to_int(
        customer.get(
            "frequency"
        )
    )

    recency_days = to_int(
        customer.get(
            "recency_days"
        )
    )

    average_interval = to_float(
        customer.get(
            "average_interval_days"
        )
    )

    overdue_ratio = to_float(
        customer.get(
            "cycle_overdue_ratio"
        )
    )

    cycle_available = (
        frequency >= 2
        and average_interval > 0
    )

    # ========================================================
    # ЕСТЬ ПОДТВЕРЖДЁННЫЙ ПОКУПАТЕЛЬСКИЙ ЦИКЛ
    # ========================================================

    if cycle_available:

        if overdue_ratio < 1.5:
            return {
                "points":
                    0.0,

                "status":
                    "do_not_call_now",

                "level":
                    "no_signal",

                "source":
                    "cycle_overdue_ratio",

                "cycle_available":
                    True,

                "recency_days":
                    recency_days,

                "average_interval_days":
                    round(
                        average_interval,
                        2,
                    ),

                "cycle_overdue_ratio":
                    round(
                        overdue_ratio,
                        2,
                    ),

                "reason": (
                    "Пауза пока не превышает привычный "
                    "интервал клиента достаточно сильно. "
                    "Сигнала для обзвона сейчас нет."
                ),
            }

        if overdue_ratio < 2.5:
            points = 25.0
            level = "weak_signal"

        elif overdue_ratio < 4:
            points = 40.0
            level = "meaningful_signal"

        elif overdue_ratio < 7:
            points = 50.0
            level = "strong_signal"

        else:
            points = 60.0
            level = "very_strong_signal"

        return {
            "points":
                points,

            "status":
                "call_candidate",

            "level":
                level,

            "source":
                "cycle_overdue_ratio",

            "cycle_available":
                True,

            "recency_days":
                recency_days,

            "average_interval_days":
                round(
                    average_interval,
                    2,
                ),

            "cycle_overdue_ratio":
                round(
                    overdue_ratio,
                    2,
                ),

            "reason": (
                "Есть история повторных покупок, "
                "и текущая пауза заметно превышает "
                "обычный интервал клиента."
            ),
        }

    # ========================================================
    # НЕТ ДОСТАТОЧНОЙ ИСТОРИИ ДЛЯ РАСЧЁТА ЦИКЛА
    #
    # Здесь используем только осторожный fallback по давности.
    # Никаких утверждений про «привычный цикл» не делаем.
    # ========================================================

    if recency_days < 60:
        return {
            "points":
                0.0,

            "status":
                "do_not_call_now",

            "level":
                "no_signal",

            "source":
                "recency_fallback",

            "cycle_available":
                False,

            "recency_days":
                recency_days,

            "average_interval_days":
                round(
                    average_interval,
                    2,
                ),

            "cycle_overdue_ratio":
                round(
                    overdue_ratio,
                    2,
                ),

            "reason": (
                "Повторной истории недостаточно, "
                "а последняя покупка была менее 60 дней назад. "
                "Сильного сигнала для звонка сейчас нет."
            ),
        }

    if recency_days < 90:
        points = 20.0
        level = "weak_signal"

    elif recency_days <= 180:
        points = 35.0
        level = "meaningful_signal"

    else:
        points = 45.0
        level = "strong_signal"

    return {
        "points":
            points,

        "status":
            "call_candidate",

        "level":
            level,

        "source":
            "recency_fallback",

        "cycle_available":
            False,

        "recency_days":
            recency_days,

        "average_interval_days":
            round(
                average_interval,
                2,
            ),

        "cycle_overdue_ratio":
            round(
                overdue_ratio,
                2,
            ),

        "reason": (
            "Повторной истории недостаточно для определения "
            "привычного цикла. Сигнал основан только на том, "
            "сколько дней прошло с последней покупки."
        ),
    }


def calculate_call_score(
    customer,
):
    """
    Новый скоринг:

    1. Сначала определяется контактный сигнал.
    2. Если сигнала нет -> score = 0.
    3. Только при наличии сигнала добавляются:
       - ценность клиента: до 25 баллов;
       - частота покупок: до 15 баллов.

    RFM-сегмент остаётся важным контекстом и используется
    при формировании пулов retain/reactivate, но сам по себе
    больше НЕ добавляет баллы срочности.
    """

    monetary = to_float(
        customer.get(
            "monetary"
        )
    )

    frequency = to_int(
        customer.get(
            "frequency"
        )
    )

    signal = get_contact_signal(
        customer
    )

    signal_points = to_float(
        signal.get(
            "points"
        )
    )

    if (
        signal.get(
            "status"
        )
        == "do_not_call_now"
        or signal_points <= 0
    ):
        monetary_points = 0.0
        frequency_points = 0.0
        total = 0.0

    else:
        monetary_points = (
            min(
                monetary / 50000,
                1,
            )
            * 25
        )

        frequency_points = (
            min(
                frequency / 30,
                1,
            )
            * 15
        )

        total = (
            signal_points
            + monetary_points
            + frequency_points
        )

    return {
        "total_score":
            round(
                total,
                2,
            ),

        "contact_status":
            signal.get(
                "status"
            ),

        "contact_signal":
            signal,

        # Старые ключи оставляем для совместимости
        # с уже работающими renderer-ами.
        "components": {
            "segment":
                0.0,

            "customer_value":
                round(
                    monetary_points,
                    2,
                ),

            "purchase_frequency":
                round(
                    frequency_points,
                    2,
                ),

            # Старое имя поля сохраняем.
            # Теперь это баллы именно контактного сигнала.
            "cycle_overdue":
                round(
                    signal_points,
                    2,
                ),
        },
    }


def classify_call_priority(
    total_score,
    contact_status=None,
):
    if (
        contact_status
        == "do_not_call_now"
    ):
        return {
            "level":
                "not_now",

            "label":
                "Сейчас не звонить",

            "recommendation": (
                "Сейчас не ставить клиента в обзвон. "
                "Ценность клиента сама по себе не является "
                "поводом для звонка: достаточного сигнала "
                "паузы пока нет."
            ),
        }

    score = to_float(
        total_score
    )

    if score >= 70:
        return {
            "level":
                "high",

            "label":
                "Высокий",

            "recommendation": (
                "Клиента стоит включать "
                "в приоритетный обзвон."
            ),
        }

    if score >= 40:
        return {
            "level":
                "medium",

            "label":
                "Средний",

            "recommendation": (
                "Позвонить имеет смысл, "
                "но после клиентов с более "
                "высоким приоритетом."
            ),
        }

    return {
        "level":
            "low",

        "label":
            "Низкий",

        "recommendation": (
            "Сигнал для контакта есть, но приоритет низкий. "
            "Клиента лучше ставить после более сильных "
            "кандидатов на обзвон."
        ),
    }


def get_customer_call_assessment(
    customer_id,
):
    rfm_result = get_customer_rfm(
        customer_id
    )

    if (
        rfm_result.get(
            "status"
        )
        != "ok"
    ):
        return rfm_result

    customer = rfm_result.get(
        "customer",
        {},
    )

    score = calculate_call_score(
        customer
    )

    contact_status = score.get(
        "contact_status"
    )

    priority = classify_call_priority(
        score.get(
            "total_score"
        ),
        contact_status=contact_status,
    )

    signal = score.get(
        "contact_signal",
        {},
    )

    frequency = to_int(
        customer.get(
            "frequency"
        )
    )

    recency_days = to_int(
        customer.get(
            "recency_days"
        )
    )

    average_interval = to_float(
        customer.get(
            "average_interval_days"
        )
    )

    cycle_overdue = to_float(
        customer.get(
            "cycle_overdue_ratio"
        )
    )

    cycle_signal_available = bool(
        signal.get(
            "cycle_available"
        )
    )

    if cycle_signal_available:
        if (
            contact_status
            == "do_not_call_now"
        ):
            cycle_note = (
                "История повторных покупок есть, "
                "но текущая пауза пока не отклоняется "
                "от привычного цикла достаточно сильно, "
                "чтобы ставить клиента в обзвон."
            )

        else:
            cycle_note = (
                "Есть история повторных покупок, "
                "поэтому обычный интервал клиента "
                "и отклонение от него можно использовать "
                "как фактический сигнал."
            )

    else:
        cycle_note = (
            "Истории повторных покупок недостаточно "
            "для надёжного определения привычного цикла. "
            "Поэтому нельзя утверждать, что пауза "
            "аномальна относительно обычного поведения клиента."
        )

    evidence = [
        {
            "factor":
                "segment",

            "value":
                customer.get(
                    "segment"
                ),

            "score":
                0.0,

            "note": (
                "RFM-сегмент используется как контекст "
                "и для формирования пула кандидатов, "
                "но сам по себе больше не создаёт "
                "срочность звонка."
            ),
        },

        {
            "factor":
                "contact_signal",

            "source":
                signal.get(
                    "source"
                ),

            "recency_days":
                recency_days,

            "average_interval_days":
                round(
                    average_interval,
                    2,
                ),

            "cycle_overdue_ratio":
                round(
                    cycle_overdue,
                    2,
                ),

            "cycle_available":
                cycle_signal_available,

            "status":
                contact_status,

            "score":
                score[
                    "components"
                ][
                    "cycle_overdue"
                ],

            "reason":
                signal.get(
                    "reason"
                ),
        },

        {
            "factor":
                "customer_value",

            "monetary":
                customer.get(
                    "monetary"
                ),

            "average_check":
                customer.get(
                    "average_check"
                ),

            "score":
                score[
                    "components"
                ][
                    "customer_value"
                ],

            "applied":
                (
                    contact_status
                    != "do_not_call_now"
                ),
        },

        {
            "factor":
                "purchase_frequency",

            "frequency":
                frequency,

            "score":
                score[
                    "components"
                ][
                    "purchase_frequency"
                ],

            "applied":
                (
                    contact_status
                    != "do_not_call_now"
                ),
        },
    ]

    return {
        "status":
            "ok",

        "customer":
            customer,

        "contact_status":
            contact_status,

        "call_now":
            (
                contact_status
                != "do_not_call_now"
            ),

        "contact_signal":
            signal,

        "priority": {
            "score":
                score[
                    "total_score"
                ],

            "level":
                priority[
                    "level"
                ],

            "label":
                priority[
                    "label"
                ],

            "recommendation":
                priority[
                    "recommendation"
                ],
        },

        "score_components":
            score[
                "components"
            ],

        "cycle_signal": {
            "available":
                cycle_signal_available,

            "note":
                cycle_note,
        },

        "evidence":
            evidence,

        "interpretation_rules": [
            (
                "Сначала должен появиться фактический "
                "сигнал для контакта. Ценность клиента "
                "сама по себе не является поводом звонить."
            ),
            (
                "Если сигнал для контакта отсутствует, "
                "баллы ценности и частоты не начисляются."
            ),
            (
                "Если у клиента есть повторная история, "
                "основной сигнал — отношение текущей паузы "
                "к его прежнему среднему интервалу."
            ),
            (
                "Если подтверждённого цикла нет, "
                "используется только осторожный сигнал "
                "по давности последней покупки."
            ),
            (
                "RFM-сегмент используется для выбора "
                "целевой группы клиентов, но не создаёт "
                "срочность звонка автоматически."
            ),
            (
                "Причину отсутствия клиента "
                "по этим данным определить нельзя."
            ),
            (
                "Старая история товаров не доказывает "
                "текущую потребность клиента."
            ),
        ],
    }


def build_conversation_plan():
    return {
        "opening_goal": (
            "Напомнить о магазине без давления "
            "и выяснить реальную причину паузы."
        ),

        "opening_template": (
            "Здравствуйте, это «Мокрый нос». "
            "Давно вас не видели и хотели уточнить, "
            "всё ли вас устраивало и актуально ли сейчас "
            "что-то из того, что вы раньше у нас покупали?"
        ),

        "branches": [
            {
                "condition": (
                    "Если клиент говорит, "
                    "что прежние товары ещё актуальны"
                ),

                "questions": [
                    (
                        "Что именно из прежних покупок "
                        "актуально сейчас?"
                    ),
                    (
                        "Когда примерно планируется "
                        "следующая покупка?"
                    ),
                ],

                "next_step": (
                    "Зафиксировать конкретную текущую "
                    "потребность клиента. Не обещать наличие, "
                    "цену или скидку, пока это не проверено."
                ),
            },

            {
                "condition": (
                    "Если клиент говорит, "
                    "что потребность изменилась"
                ),

                "questions": [
                    (
                        "Что именно изменилось?"
                    ),
                    (
                        "Что вы покупаете или ищете сейчас?"
                    ),
                ],

                "next_step": (
                    "Сначала получить новые вводные. "
                    "Не подбирать конкретный товар "
                    "только по старой истории покупок."
                ),
            },

            {
                "condition": (
                    "Если клиент говорит, "
                    "что стало дорого"
                ),

                "questions": [
                    (
                        "Какой именно товар перестал "
                        "устраивать по цене?"
                    ),
                    (
                        "На что вы ориентируетесь "
                        "при выборе сейчас?"
                    ),
                ],

                "next_step": (
                    "Зафиксировать ценовую проблему "
                    "и только после этого проверять "
                    "реальные альтернативы."
                ),
            },

            {
                "condition": (
                    "Если клиент говорит, "
                    "что покупает в другом месте"
                ),

                "questions": [
                    (
                        "Что в другом месте оказалось "
                        "для вас удобнее или выгоднее?"
                    ),
                    (
                        "Что для вас сейчас важнее всего "
                        "при выборе магазина?"
                    ),
                ],

                "next_step": (
                    "Выяснить реальную причину смены магазина. "
                    "Не спорить и не обещать преимущества, "
                    "которые не подтверждены данными."
                ),
            },

            {
                "condition": (
                    "Если клиент говорит "
                    "о негативном опыте"
                ),

                "questions": [
                    (
                        "Что именно произошло?"
                    ),
                    (
                        "Когда это было?"
                    ),
                    (
                        "Что для вас было бы нормальным "
                        "решением этой ситуации?"
                    ),
                ],

                "next_step": (
                    "Зафиксировать проблему. "
                    "Не придумывать компенсацию "
                    "или решение до проверки ситуации."
                ),
            },

            {
                "condition": (
                    "Если клиент говорит, "
                    "что сейчас ничего не нужно"
                ),

                "questions": [
                    (
                        "Хорошо, можно ли нам связаться "
                        "с вами позже?"
                    ),
                    (
                        "Когда примерно это будет уместно?"
                    ),
                ],

                "next_step": (
                    "Не давить на продажу. "
                    "Зафиксировать удобный для клиента "
                    "момент следующего контакта, "
                    "если он его назвал."
                ),
            },
        ],

        "successful_outcomes": [
            (
                "Выяснена настоящая причина долгой паузы."
            ),
            (
                "Понятна текущая потребность клиента."
            ),
            (
                "Клиент сам обозначил план "
                "следующей покупки или визита."
            ),
            (
                "Согласован подходящий клиенту "
                "момент повторного контакта."
            ),
            (
                "Получена полезная обратная связь "
                "о причине ухода или неудобстве."
            ),
            (
                "Выяснено, что сейчас клиенту "
                "ничего не требуется."
            ),
        ],

        "forbidden_inferences": [
            (
                "Не предполагать возраст, породу, "
                "количество или состояние животных."
            ),
            (
                "Не считать старый товар "
                "текущей потребностью."
            ),
            (
                "Не придумывать причину ухода."
            ),
            (
                "Не придумывать аллергии, диагнозы "
                "или особенности питания."
            ),
            (
                "Не придумывать наличие товаров."
            ),
            (
                "Не придумывать текущие цены."
            ),
            (
                "Не придумывать скидки и акции."
            ),
            (
                "Не обещать доставку или другие услуги, "
                "если они не подтверждены данными."
            ),
            (
                "Не придумывать срок повторного звонка. "
                "Его должен назвать сам клиент."
            ),
            (
                "Не обещать отправку прайса, каталога "
                "или другого материала, если такая "
                "возможность не проверена."
            ),
        ],
    }


def get_next_call_candidate(
    mode="retain",
    exclude_customer_ids=None,
):
    excluded_ids = normalize_customer_ids(
        exclude_customer_ids
    )

    # ========================================================
    # БЕРЁМ ВЕСЬ ПУЛ, А НЕ ПЕРВЫЕ 100
    # ========================================================

    candidates_result = (
        get_contact_candidate_pool(
            mode=mode
        )
    )

    if (
        candidates_result.get(
            "status"
        )
        != "ok"
    ):
        return candidates_result

    normalized_mode = (
        candidates_result.get(
            "mode",
            mode,
        )
    )

    all_candidates = (
        candidates_result.get(
            "customers",
            [],
        )
    )

    candidates_with_phone = []

    for customer in all_candidates:
        customer_id = str(
            customer.get(
                "customer_id"
            )
            or ""
        ).strip()

        phone = str(
            customer.get(
                "phone"
            )
            or ""
        ).strip()

        if not customer_id:
            continue

        if not phone:
            continue

        if (
            customer_id
            in excluded_ids
        ):
            continue

        candidates_with_phone.append(
            customer
        )

    if not candidates_with_phone:
        return {
            "status":
                "no_candidates",

            "mode":
                normalized_mode,

            "pool_total_candidates":
                len(
                    all_candidates
                ),

            "excluded_customer_ids":
                sorted(
                    excluded_ids
                ),

            "message": (
                "В полном пуле не осталось "
                "неисключённых клиентов с телефоном."
            ),
        }

    # ========================================================
    # СКОРИМ ВСЕХ
    #
    # Клиенты без реального сигнала звонка
    # вообще не попадают в очередь.
    # ========================================================

    scored = []

    do_not_call_now_count = 0

    for customer in candidates_with_phone:
        score = calculate_call_score(
            customer
        )

        if (
            score.get(
                "contact_status"
            )
            == "do_not_call_now"
        ):
            do_not_call_now_count += 1
            continue

        scored.append(
            {
                "customer":
                    customer,

                "score":
                    score,
            }
        )

    if not scored:
        return {
            "status":
                "no_call_signal",

            "mode":
                normalized_mode,

            "pool_total_candidates":
                len(
                    all_candidates
                ),

            "candidates_with_phone":
                len(
                    candidates_with_phone
                ),

            "do_not_call_now_count":
                do_not_call_now_count,

            "excluded_customer_ids":
                sorted(
                    excluded_ids
                ),

            "message": (
                "В полном пуле сейчас нет клиентов "
                "с достаточным сигналом для звонка."
            ),
        }

    scored.sort(
        key=lambda item: (
            item[
                "score"
            ][
                "total_score"
            ],

            to_float(
                item[
                    "customer"
                ].get(
                    "monetary"
                )
            ),

            to_float(
                item[
                    "customer"
                ].get(
                    "cycle_overdue_ratio"
                )
            ),

            to_int(
                item[
                    "customer"
                ].get(
                    "frequency"
                )
            ),
        ),
        reverse=True,
    )

    winner = scored[
        0
    ]

    customer = winner[
        "customer"
    ]

    winner_score = winner[
        "score"
    ]

    priority = classify_call_priority(
        winner_score.get(
            "total_score"
        ),
        contact_status=winner_score.get(
            "contact_status"
        ),
    )

    profile = (
        get_customer_profile(
            customer[
                "customer_id"
            ]
        )
    )

    top_products = (
        profile.get(
            "top_products",
            [],
        )[:10]
    )

    return {
        "status":
            "ok",

        "mode":
            normalized_mode,

        "pool_total_candidates":
            len(
                all_candidates
            ),

        "candidates_with_phone":
            len(
                candidates_with_phone
            ),

        "do_not_call_now_count":
            do_not_call_now_count,

        "call_candidates_scored":
            len(
                scored
            ),

        "excluded_customer_ids":
            sorted(
                excluded_ids
            ),

        "selection_method": (
            "Проверен весь доступный пул клиентов. "
            "Сначала определяется фактический сигнал "
            "для контакта. Клиенты без такого сигнала "
            "не попадают в очередь. Только после этого "
            "к приоритету добавляются историческая "
            "ценность и частота покупок."
        ),

        "candidate": {
            "customer_id":
                customer.get(
                    "customer_id"
                ),

            "full_name":
                customer.get(
                    "full_name"
                ),

            "phone":
                customer.get(
                    "phone"
                ),

            "segment":
                customer.get(
                    "segment"
                ),

            "last_purchase":
                customer.get(
                    "last_purchase"
                ),

            "recency_days":
                customer.get(
                    "recency_days"
                ),

            "frequency":
                customer.get(
                    "frequency"
                ),

            "monetary":
                customer.get(
                    "monetary"
                ),

            "average_check":
                customer.get(
                    "average_check"
                ),

            "average_interval_days":
                customer.get(
                    "average_interval_days"
                ),

            "cycle_overdue_ratio":
                customer.get(
                    "cycle_overdue_ratio"
                ),

            "contact_status":
                winner_score.get(
                    "contact_status"
                ),

            "contact_signal":
                winner_score.get(
                    "contact_signal"
                ),

            "priority_score":
                winner_score[
                    "total_score"
                ],

            "priority_level":
                priority[
                    "level"
                ],

            "priority_label":
                priority[
                    "label"
                ],

            "priority_score_components":
                winner_score[
                    "components"
                ],
        },

        "top_products":
            top_products,

        "conversation_plan":
            build_conversation_plan(),
    }


def print_assessment(
    title,
    customer_id,
):
    print()
    print("=" * 70)
    print(
        title
    )
    print("=" * 70)

    result = (
        get_customer_call_assessment(
            customer_id
        )
    )

    print(
        result
    )

    if (
        result.get(
            "status"
        )
        == "ok"
    ):
        customer = result.get(
            "customer",
            {},
        )

        priority = result.get(
            "priority",
            {},
        )

        signal = result.get(
            "contact_signal",
            {},
        )

        print()

        print(
            "Клиент:",
            customer.get(
                "full_name"
            ),
        )

        print(
            "Последняя покупка:",
            customer.get(
                "last_purchase"
            ),
        )

        print(
            "Дней без покупки:",
            customer.get(
                "recency_days"
            ),
        )

        print(
            "Покупок:",
            customer.get(
                "frequency"
            ),
        )

        print(
            "Средний интервал:",
            customer.get(
                "average_interval_days"
            ),
        )

        print(
            "Просрочка цикла:",
            customer.get(
                "cycle_overdue_ratio"
            ),
        )

        print(
            "Контактный статус:",
            result.get(
                "contact_status"
            ),
        )

        print(
            "Источник сигнала:",
            signal.get(
                "source"
            ),
        )

        print(
            "Сигнал, баллы:",
            signal.get(
                "points"
            ),
        )

        print(
            "Итоговый score:",
            priority.get(
                "score"
            ),
        )

        print(
            "Приоритет:",
            priority.get(
                "label"
            ),
        )


def demo():
    print()
    print("=" * 70)
    print(
        "CALL TOOLS — URGENCY-FIRST TEST"
    )
    print("=" * 70)

    # ========================================================
    # НЕТ ЦИКЛА, НО ДАВНО НЕ БЫЛА
    # ОЖИДАНИЕ: примерно 35.85, низкий
    # ========================================================

    print_assessment(
        "НАТАЛЬЯ ПЕРЕЧИЦКАЯ — НЕТ ЦИКЛА",
        "1000446",
    )

    # ========================================================
    # ЦЕННЫЕ, НО СЕЙЧАС ЗВОНИТЬ НЕ НАДО
    # ОЖИДАНИЕ: score 0 / Сейчас не звонить
    # ========================================================

    print_assessment(
        "СЕРГЕЙ ЗВЕРЕВ — ПОКУПАЛ 2 ДНЯ НАЗАД",
        "897775",
    )

    print_assessment(
        "МАРИНА Ф — ПОКУПАЛА СЕГОДНЯ",
        "851014",
    )

    print_assessment(
        "АЛИНА ШЛЯГИНА — ПОКУПАЛА 2 ДНЯ НАЗАД",
        "826736",
    )

    print_assessment(
        "АЛЕКСАНДР АЛЕКСАНДРОВ — ЦИКЛ ПОКА НЕ ПРОСРОЧЕН",
        "829105",
    )

    # ========================================================
    # РЕАЛЬНЫЕ СИЛЬНЫЕ СИГНАЛЫ
    # ========================================================

    print_assessment(
        "НИКИТА ЯНЦЕВ — СИЛЬНЫЙ СИГНАЛ",
        "918335",
    )

    print_assessment(
        "ПАВЕЛ ВАСИЛЬЕВ — ОЧЕНЬ СИЛЬНЫЙ СИГНАЛ",
        "844016",
    )

    print_assessment(
        "АНАСТАСИЯ ЕВДОКИМОВА — ОЧЕНЬ СИЛЬНЫЙ СИГНАЛ",
        "870583",
    )

    # ========================================================
    # ПОЛНАЯ ОЧЕРЕДЬ RETAIN
    # ========================================================

    print()
    print("=" * 70)
    print(
        "ПЕРВЫЙ КАНДИДАТ ИЗ ПОЛНОГО RETAIN-ПУЛА"
    )
    print("=" * 70)

    first = get_next_call_candidate(
        mode="retain",
    )

    print(
        first
    )

    if (
        first.get(
            "status"
        )
        == "ok"
    ):
        candidate = first.get(
            "candidate",
            {},
        )

        print()

        print(
            "Полный пул:",
            first.get(
                "pool_total_candidates"
            ),
        )

        print(
            "С телефоном после исключений:",
            first.get(
                "candidates_with_phone"
            ),
        )

        print(
            "Без сигнала сейчас:",
            first.get(
                "do_not_call_now_count"
            ),
        )

        print(
            "Реальных кандидатов на звонок:",
            first.get(
                "call_candidates_scored"
            ),
        )

        print(
            "ПОБЕДИТЕЛЬ:",
            candidate.get(
                "full_name"
            ),
        )

        print(
            "SCORE:",
            candidate.get(
                "priority_score"
            ),
        )

        print(
            "SIGNAL:",
            candidate.get(
                "contact_signal"
            ),
        )

    first_customer_id = (
        first.get(
            "candidate",
            {},
        ).get(
            "customer_id"
        )
    )

    print()
    print("=" * 70)
    print(
        "ВТОРОЙ КАНДИДАТ С ИСКЛЮЧЕНИЕМ ПЕРВОГО"
    )
    print("=" * 70)

    second = get_next_call_candidate(
        mode="retain",
        exclude_customer_ids=[
            first_customer_id
        ]
        if first_customer_id
        else [],
    )

    print(
        second
    )

    if (
        second.get(
            "status"
        )
        == "ok"
    ):
        candidate = second.get(
            "candidate",
            {},
        )

        print()

        print(
            "ПОБЕДИТЕЛЬ:",
            candidate.get(
                "full_name"
            ),
        )

        print(
            "SCORE:",
            candidate.get(
                "priority_score"
            ),
        )

    # ========================================================
    # ПРОВЕРКА ПОЛНОГО REACTIVATE-ПУЛА
    # ========================================================

    print()
    print("=" * 70)
    print(
        "ПЕРВЫЙ КАНДИДАТ ИЗ ПОЛНОГО REACTIVATE-ПУЛА"
    )
    print("=" * 70)

    reactivate = get_next_call_candidate(
        mode="reactivate",
    )

    print(
        reactivate
    )

    if (
        reactivate.get(
            "status"
        )
        == "ok"
    ):
        candidate = reactivate.get(
            "candidate",
            {},
        )

        print()

        print(
            "Полный пул:",
            reactivate.get(
                "pool_total_candidates"
            ),
        )

        print(
            "ПОБЕДИТЕЛЬ:",
            candidate.get(
                "full_name"
            ),
        )

        print(
            "SCORE:",
            candidate.get(
                "priority_score"
            ),
        )


if __name__ == "__main__":
    demo()