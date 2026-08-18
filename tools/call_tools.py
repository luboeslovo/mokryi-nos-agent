from customer_tools import (
    get_customer_profile,
)

from rfm_tools import (
    get_contact_candidates,
)


SEGMENT_SCORE = {
    "Ценный под риском": 35,
    "Нужно удержать": 30,
    "Под риском": 25,
    "Остывает": 20,
    "Потерянный ценный": 25,
    "Потерянный": 10,
}


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


def calculate_call_score(
    customer,
):
    segment = customer.get(
        "segment"
    )

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

    overdue = to_float(
        customer.get(
            "cycle_overdue_ratio"
        )
    )

    segment_points = (
        SEGMENT_SCORE.get(
            segment,
            0,
        )
    )

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

    overdue_points = (
        min(
            overdue / 10,
            1,
        )
        * 25
    )

    total = (
        segment_points
        + monetary_points
        + frequency_points
        + overdue_points
    )

    return {
        "total_score":
            round(
                total,
                2,
            ),

        "components": {
            "segment":
                round(
                    segment_points,
                    2,
                ),

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

            "cycle_overdue":
                round(
                    overdue_points,
                    2,
                ),
        },
    }


def build_conversation_plan():
    return {
        "opening_goal": (
            "Напомнить о магазине без давления "
            "и выяснить причину необычно долгой паузы."
        ),

        "opening_template": (
            "Здравствуйте, это «Мокрый нос». "
            "Раньше вы довольно регулярно покупали "
            "у нас товары, а давно вас не видели. "
            "Хотел уточнить, всё ли вас устраивало "
            "и актуально ли сейчас что-то "
            "из того, что вы раньше брали?"
        ),

        "branches": [
            {
                "condition":
                    "Если клиент говорит, что прежние товары ещё актуальны",

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
                    "потребность клиента. "
                    "Не обещать наличие, цену или скидку, "
                    "пока это не проверено."
                ),
            },

            {
                "condition":
                    "Если клиент говорит, что потребность изменилась",

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
                "condition":
                    "Если клиент говорит, что стало дорого",

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
                "condition":
                    "Если клиент говорит, что покупает в другом месте",

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
                "condition":
                    "Если клиент говорит о негативном опыте",

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
                "condition":
                    "Если клиент говорит, что сейчас ничего не нужно",

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
                "Выяснена настоящая причина "
                "долгой паузы."
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
                "или другого материала, "
                "если такая возможность не проверена."
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

    candidates_result = (
        get_contact_candidates(
            limit=100,
            mode=mode,
        )
    )

    if (
        candidates_result.get(
            "status"
        )
        != "ok"
    ):
        return candidates_result

    all_candidates = (
        candidates_result.get(
            "customers",
            []
        )
    )

    candidates = []

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

        if customer_id in excluded_ids:
            continue

        candidates.append(
            customer
        )

    if not candidates:
        return {
            "status":
                "no_candidates",

            "mode":
                mode,

            "excluded_customer_ids":
                sorted(
                    excluded_ids
                ),

            "message": (
                "Среди загруженных кандидатов "
                "не осталось новых клиентов "
                "с телефоном."
            ),
        }

    scored = []

    for customer in candidates:
        score = calculate_call_score(
            customer
        )

        scored.append(
            {
                "customer":
                    customer,

                "score":
                    score,
            }
        )

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

    winner = scored[0]

    customer = winner[
        "customer"
    ]

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
            []
        )[:10]
    )

    return {
        "status":
            "ok",

        "mode":
            mode,

        "excluded_customer_ids":
            sorted(
                excluded_ids
            ),

        "selection_method": (
            "Кандидат выбран среди клиентов "
            "с телефоном по совокупности четырёх факторов: "
            "приоритет RFM-сегмента, общая ценность клиента, "
            "частота покупок и превышение его обычного "
            "интервала между покупками. "
            "Клиенты из exclude_customer_ids "
            "исключены из выбора."
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

            "priority_score":
                winner[
                    "score"
                ][
                    "total_score"
                ],

            "priority_score_components":
                winner[
                    "score"
                ][
                    "components"
                ],
        },

        "top_products":
            top_products,

        "conversation_plan":
            build_conversation_plan(),
    }


def demo():
    print()
    print("=" * 70)
    print(
        "CALL TOOLS — TEST"
    )
    print("=" * 70)

    print()
    print(
        "Первый кандидат:"
    )

    first = get_next_call_candidate(
        mode="retain",
    )

    print(
        first
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
    print(
        "Следующий кандидат "
        "с исключением первого:"
    )

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


if __name__ == "__main__":
    demo()