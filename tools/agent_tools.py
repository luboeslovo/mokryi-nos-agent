from gigachat.models import (
    ChatFunctionSpecification,
    ChatTool,
)

from customer_tools import (
    find_customer_by_name,
    get_customer_profile,
    get_top_customers,
)

from sales_tools import (
    compare_sales_days,
    compare_sales_months,
    get_daily_sales,
    get_latest_sales_day,
    get_month_summary,
    get_recent_sales,
)

from sales_analytics import (
    compare_sales_periods,
    compare_sales_years,
    get_period_summary,
    get_year_summary,
    rank_sales_periods,
)

from rfm_tools import (
    get_contact_candidates,
    get_rfm_segment,
    get_rfm_summary,
)

from call_tools import (
    get_customer_call_assessment,
    get_next_call_candidate,
)

from memory_tools import (
    get_today_suggested_customer_ids,
)


FUNCTION_SPECS = [
    ChatFunctionSpecification(
        name="get_customer_profile",
        description=(
            "Получает профиль конкретного клиента "
            "по customer_id."
        ),
        parameters={
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": (
                        "ID клиента в CRM"
                    ),
                },
            },
            "required": [
                "customer_id",
            ],
        },
    ),

    ChatFunctionSpecification(
        name="get_top_customers",
        description=(
            "Возвращает самых ценных клиентов магазина "
            "по общей сумме покупок."
        ),
        parameters={
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": (
                        "Сколько клиентов вернуть"
                    ),
                },
            },
            "required": [
                "limit",
            ],
        },
    ),

    ChatFunctionSpecification(
        name="find_customer_by_name",
        description=(
            "Ищет клиента по имени, фамилии "
            "или полному имени."
        ),
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Имя, фамилия или полное имя клиента"
                    ),
                },
                "limit": {
                    "type": "integer",
                    "description": (
                        "Максимальное количество совпадений"
                    ),
                },
            },
            "required": [
                "query",
            ],
        },
    ),

    # ========================================================
    # ПРОДАЖИ — ДНИ
    # ========================================================

    ChatFunctionSpecification(
        name="get_latest_sales_day",
        description=(
            "Возвращает последний закрытый день магазина "
            "и сравнение с предыдущим закрытым днём. "
            "Используй для вопросов про вчера, последний "
            "закрытый день или последние продажи."
        ),
        parameters={
            "type": "object",
            "properties": {},
        },
    ),

    ChatFunctionSpecification(
        name="get_daily_sales",
        description=(
            "Возвращает продажи магазина "
            "за одну конкретную дату. "
            "Используй только когда нужен один день."
        ),
        parameters={
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": (
                        "Дата ДД.ММ.ГГГГ или latest"
                    ),
                },
            },
            "required": [
                "date",
            ],
        },
    ),

    ChatFunctionSpecification(
        name="compare_sales_days",
        description=(
            "Сравнивает два конкретных дня магазина. "
            "Используй только для двух отдельных дат. "
            "Не используй для месяцев, годов "
            "или диапазонов дат."
        ),
        parameters={
            "type": "object",
            "properties": {
                "date_a": {
                    "type": "string",
                    "description": (
                        "Первая дата ДД.ММ.ГГГГ"
                    ),
                },
                "date_b": {
                    "type": "string",
                    "description": (
                        "Вторая дата ДД.ММ.ГГГГ"
                    ),
                },
            },
            "required": [
                "date_a",
                "date_b",
            ],
        },
    ),

    ChatFunctionSpecification(
        name="get_recent_sales",
        description=(
            "Возвращает несколько последних "
            "закрытых дней магазина."
        ),
        parameters={
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": (
                        "Количество последних дней"
                    ),
                },
            },
            "required": [
                "days",
            ],
        },
    ),

    # ========================================================
    # ПРОДАЖИ — МЕСЯЦЫ
    # ========================================================

    ChatFunctionSpecification(
        name="get_month_summary",
        description=(
            "Возвращает показатели одного календарного месяца. "
            "Если текущий месяц ещё не завершён, "
            "возвращает доступную часть месяца. "
            "Используй для вопроса про один конкретный месяц."
        ),
        parameters={
            "type": "object",
            "properties": {
                "year": {
                    "type": "integer",
                    "description": (
                        "Год"
                    ),
                },
                "month": {
                    "type": "integer",
                    "description": (
                        "Номер месяца от 1 до 12"
                    ),
                },
            },
            "required": [
                "year",
                "month",
            ],
        },
    ),

    ChatFunctionSpecification(
        name="compare_sales_months",
        description=(
            "Сравнивает два календарных месяца магазина. "
            "Особенно полезен для текущего незавершённого месяца: "
            "Python автоматически делает честное like-for-like "
            "сравнение одинакового количества дней. "
            "Например, 1–17 августа против 1–17 июля. "
            "Используй для запросов вроде "
            "'сравни август с июлем', "
            "'май лучше апреля?', "
            "'как август идёт относительно июля'."
        ),
        parameters={
            "type": "object",
            "properties": {
                "year_a": {
                    "type": "integer",
                    "description": (
                        "Год первого месяца"
                    ),
                },
                "month_a": {
                    "type": "integer",
                    "description": (
                        "Первый месяц от 1 до 12"
                    ),
                },
                "year_b": {
                    "type": "integer",
                    "description": (
                        "Год второго месяца"
                    ),
                },
                "month_b": {
                    "type": "integer",
                    "description": (
                        "Второй месяц от 1 до 12"
                    ),
                },
            },
            "required": [
                "year_a",
                "month_a",
                "year_b",
                "month_b",
            ],
        },
    ),

    # ========================================================
    # ПРОДАЖИ — УНИВЕРСАЛЬНАЯ АНАЛИТИКА
    # ========================================================

    ChatFunctionSpecification(
        name="get_sales_period_summary",
        description=(
            "Возвращает показатели за произвольный диапазон дат. "
            "Используй для запросов вроде "
            "'сколько продали с апреля по июнь', "
            "'выручка за второй квартал', "
            "'покажи продажи с 5 по 17 августа'. "
            "Python сам объединяет доступные дневные "
            "и исторические месячные данные. "
            "Если для старого диапазона нужна детализация, "
            "которой нет, инструмент честно вернёт ошибку "
            "insufficient_granularity и ничего не выдумает."
        ),
        parameters={
            "type": "object",
            "properties": {
                "start_date": {
                    "type": "string",
                    "description": (
                        "Начальная дата ДД.ММ.ГГГГ"
                    ),
                },
                "end_date": {
                    "type": "string",
                    "description": (
                        "Конечная дата ДД.ММ.ГГГГ"
                    ),
                },
            },
            "required": [
                "start_date",
                "end_date",
            ],
        },
    ),

    ChatFunctionSpecification(
        name="compare_sales_periods",
        description=(
            "Сравнивает два произвольных диапазона дат. "
            "Используй для запросов вроде "
            "'сравни март–май с июнем–августом', "
            "'сравни 1–15 июля с 1–15 августа', "
            "'сравни второй квартал с первым'. "
            "Если пользователь просто сравнивает два "
            "календарных месяца и один из них текущий, "
            "предпочитай compare_sales_months, потому что "
            "он автоматически делает like-for-like."
        ),
        parameters={
            "type": "object",
            "properties": {
                "start_a": {
                    "type": "string",
                    "description": (
                        "Начало первого периода ДД.ММ.ГГГГ"
                    ),
                },
                "end_a": {
                    "type": "string",
                    "description": (
                        "Конец первого периода ДД.ММ.ГГГГ"
                    ),
                },
                "start_b": {
                    "type": "string",
                    "description": (
                        "Начало второго периода ДД.ММ.ГГГГ"
                    ),
                },
                "end_b": {
                    "type": "string",
                    "description": (
                        "Конец второго периода ДД.ММ.ГГГГ"
                    ),
                },
            },
            "required": [
                "start_a",
                "end_a",
                "start_b",
                "end_b",
            ],
        },
    ),

    ChatFunctionSpecification(
        name="get_sales_year_summary",
        description=(
            "Возвращает показатели календарного года. "
            "Для текущего года возвращает данные "
            "с 1 января по последний закрытый день. "
            "Используй для вопросов вроде "
            "'сколько заработали по выручке в 2025 году', "
            "'какая выручка за 2026 год'. "
            "Не называй выручку прибылью."
        ),
        parameters={
            "type": "object",
            "properties": {
                "year": {
                    "type": "integer",
                    "description": (
                        "Календарный год"
                    ),
                },
            },
            "required": [
                "year",
            ],
        },
    ),

    ChatFunctionSpecification(
        name="compare_sales_years",
        description=(
            "Сравнивает два года по доступным данным. "
            "Используй для запросов вроде "
            "'сравни 2025 и 2026 годы'. "
            "Если один год ещё не завершён, "
            "результат содержит предупреждение об этом. "
            "Не скрывай это предупреждение в ответе."
        ),
        parameters={
            "type": "object",
            "properties": {
                "year_a": {
                    "type": "integer",
                    "description": (
                        "Первый год"
                    ),
                },
                "year_b": {
                    "type": "integer",
                    "description": (
                        "Второй год"
                    ),
                },
            },
            "required": [
                "year_a",
                "year_b",
            ],
        },
    ),

    ChatFunctionSpecification(
        name="rank_sales_periods",
        description=(
            "Находит лучшие или худшие дни, месяцы или годы "
            "по выбранному показателю. "
            "Используй для запросов вроде "
            "'самый сильный месяц по выручке', "
            "'топ-5 дней августа', "
            "'месяц с самым большим средним чеком', "
            "'худшие три месяца по выручке', "
            "'день с максимальным количеством чеков'. "
            "granularity: day, month или year. "
            "metric: total_revenue для выручки; "
            "average_check для среднего чека; "
            "checks для количества чеков; "
            "items для количества товаров; "
            "ktch для товаров на чек; "
            "external_total для внешней выручки; "
            "external_orders для внешних заказов; "
            "check_revenue_net для нетто-выручки по чекам. "
            "Если пользователь говорит именно о прибыли "
            "или марже, передай metric='profit'. "
            "Python специально откажется считать прибыль, "
            "пока нет полной себестоимости и расходов. "
            "Никогда не подменяй прибыль выручкой молча."
        ),
        parameters={
            "type": "object",
            "properties": {
                "granularity": {
                    "type": "string",
                    "enum": [
                        "day",
                        "month",
                        "year",
                    ],
                    "description": (
                        "Что ранжировать: "
                        "day, month или year"
                    ),
                },
                "metric": {
                    "type": "string",
                    "description": (
                        "Показатель: total_revenue, "
                        "average_check, checks, items, "
                        "ktch, check_revenue_net, "
                        "external_total, external_orders "
                        "или profit"
                    ),
                },
                "date_from": {
                    "type": "string",
                    "description": (
                        "Необязательная начальная дата "
                        "ДД.ММ.ГГГГ"
                    ),
                },
                "date_to": {
                    "type": "string",
                    "description": (
                        "Необязательная конечная дата "
                        "ДД.ММ.ГГГГ"
                    ),
                },
                "order": {
                    "type": "string",
                    "enum": [
                        "desc",
                        "asc",
                    ],
                    "description": (
                        "desc — лучшие/максимальные, "
                        "asc — худшие/минимальные"
                    ),
                },
                "limit": {
                    "type": "integer",
                    "description": (
                        "Сколько периодов вернуть"
                    ),
                },
                "min_checks": {
                    "type": "integer",
                    "description": (
                        "Необязательный минимальный "
                        "порог количества чеков. "
                        "Полезен для рейтинга "
                        "по среднему чеку."
                    ),
                },
                "include_partial": {
                    "type": "boolean",
                    "description": (
                        "Включать ли незавершённые "
                        "месяцы или годы в рейтинг. "
                        "По умолчанию false."
                    ),
                },
            },
            "required": [
                "granularity",
                "metric",
            ],
        },
    ),

    # ========================================================
    # RFM
    # ========================================================

    ChatFunctionSpecification(
        name="get_rfm_summary",
        description=(
            "Возвращает общую RFM-структуру "
            "клиентской базы."
        ),
        parameters={
            "type": "object",
            "properties": {},
        },
    ),

    ChatFunctionSpecification(
        name="get_rfm_segment",
        description=(
            "Возвращает клиентов конкретного "
            "RFM-сегмента."
        ),
        parameters={
            "type": "object",
            "properties": {
                "segment": {
                    "type": "string",
                    "description": (
                        "Название RFM-сегмента"
                    ),
                },
                "limit": {
                    "type": "integer",
                    "description": (
                        "Количество клиентов"
                    ),
                },
                "sort_by": {
                    "type": "string",
                    "description": (
                        "monetary, recency, "
                        "frequency или overdue"
                    ),
                },
            },
            "required": [
                "segment",
            ],
        },
    ),

    ChatFunctionSpecification(
        name="get_contact_candidates",
        description=(
            "Возвращает список клиентов "
            "для удержания или возврата. "
            "Используй, если пользователь "
            "просит несколько клиентов, "
            "список или топ."
        ),
        parameters={
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": (
                        "Количество клиентов"
                    ),
                },
                "mode": {
                    "type": "string",
                    "description": (
                        "retain или reactivate"
                    ),
                },
            },
            "required": [
                "limit",
                "mode",
            ],
        },
    ),

    ChatFunctionSpecification(
        name="get_next_call_candidate",
        description=(
            "Выбирает одного следующего клиента "
            "для звонка. "
            "Клиенты, уже предложенные сегодня "
            "в этом разговоре, автоматически "
            "исключаются Python-кодом. "
            "Используй для 'кому сейчас позвонить', "
            "'а кому ещё', 'кто следующий'."
        ),
        parameters={
            "type": "object",
            "properties": {
                "mode": {
                    "type": "string",
                    "description": (
                        "retain — удержание; "
                        "reactivate — возврат потерянного"
                    ),
                },
            },
            "required": [
                "mode",
            ],
        },
    ),

    ChatFunctionSpecification(
        name="get_customer_call_assessment",
        description=(
            "Оценивает, стоит ли звонить "
            "конкретному клиенту и насколько "
            "он приоритетен для обзвона. "
            "Используй для вопросов "
            "'стоит ли ему звонить?', "
            "'надо ли ей звонить?', "
            "'насколько клиент приоритетный?'. "
            "Приоритет рассчитывается Python-кодом. "
            "Если истории повторных покупок мало, "
            "инструмент не делает ложных выводов "
            "о покупательском цикле."
        ),
        parameters={
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": (
                        "ID конкретного клиента в CRM"
                    ),
                },
            },
            "required": [
                "customer_id",
            ],
        },
    ),
]


TOOLS = [
    ChatTool(
        functions={
            "specifications":
                FUNCTION_SPECS,
        }
    )
]


def build_latest_day_report():
    latest = get_latest_sales_day()

    if (
        latest.get(
            "status"
        )
        != "ok"
    ):
        return latest

    result = {
        "status":
            "ok",

        "day":
            latest[
                "day"
            ],
    }

    recent = get_recent_sales(
        2
    )

    days = recent.get(
        "days",
        [],
    )

    if len(days) >= 2:
        result[
            "previous_day"
        ] = days[-2]

        result[
            "comparison_with_previous_day"
        ] = compare_sales_days(
            days[-2][
                "date"
            ],
            days[-1][
                "date"
            ],
        )

    return result


def run_tool(
    name,
    arguments,
    conversation_id="console",
):
    if name == "get_customer_profile":
        return get_customer_profile(
            arguments[
                "customer_id"
            ]
        )

    if name == "get_top_customers":
        return get_top_customers(
            arguments.get(
                "limit",
                5,
            )
        )

    if name == "find_customer_by_name":
        return find_customer_by_name(
            arguments[
                "query"
            ],
            arguments.get(
                "limit",
                10,
            ),
        )

    if name == "get_latest_sales_day":
        return build_latest_day_report()

    if name == "get_daily_sales":
        return get_daily_sales(
            arguments.get(
                "date",
                "latest",
            )
        )

    if name == "compare_sales_days":
        return compare_sales_days(
            arguments[
                "date_a"
            ],
            arguments[
                "date_b"
            ],
        )

    if name == "get_recent_sales":
        return get_recent_sales(
            arguments.get(
                "days",
                7,
            )
        )

    if name == "get_month_summary":
        return get_month_summary(
            arguments[
                "year"
            ],
            arguments[
                "month"
            ],
        )

    if name == "compare_sales_months":
        return compare_sales_months(
            arguments[
                "year_a"
            ],
            arguments[
                "month_a"
            ],
            arguments[
                "year_b"
            ],
            arguments[
                "month_b"
            ],
        )

    if name == "get_sales_period_summary":
        return get_period_summary(
            arguments[
                "start_date"
            ],
            arguments[
                "end_date"
            ],
        )

    if name == "compare_sales_periods":
        return compare_sales_periods(
            arguments[
                "start_a"
            ],
            arguments[
                "end_a"
            ],
            arguments[
                "start_b"
            ],
            arguments[
                "end_b"
            ],
        )

    if name == "get_sales_year_summary":
        return get_year_summary(
            arguments[
                "year"
            ]
        )

    if name == "compare_sales_years":
        return compare_sales_years(
            arguments[
                "year_a"
            ],
            arguments[
                "year_b"
            ],
        )

    if name == "rank_sales_periods":
        return rank_sales_periods(
            granularity=arguments[
                "granularity"
            ],
            metric=arguments[
                "metric"
            ],
            date_from=arguments.get(
                "date_from"
            ),
            date_to=arguments.get(
                "date_to"
            ),
            order=arguments.get(
                "order",
                "desc",
            ),
            limit=arguments.get(
                "limit",
                5,
            ),
            min_checks=arguments.get(
                "min_checks",
                0,
            ),
            include_partial=arguments.get(
                "include_partial",
                False,
            ),
        )

    if name == "get_rfm_summary":
        return get_rfm_summary()

    if name == "get_rfm_segment":
        return get_rfm_segment(
            segment=arguments[
                "segment"
            ],
            limit=arguments.get(
                "limit",
                10,
            ),
            sort_by=arguments.get(
                "sort_by",
                "monetary",
            ),
        )

    if name == "get_contact_candidates":
        return get_contact_candidates(
            limit=arguments.get(
                "limit",
                10,
            ),
            mode=arguments.get(
                "mode",
                "retain",
            ),
        )

    if name == "get_next_call_candidate":
        mode = arguments.get(
            "mode",
            "retain",
        )

        excluded = (
            get_today_suggested_customer_ids(
                conversation_id,
                mode=mode,
            )
        )

        return get_next_call_candidate(
            mode=mode,
            exclude_customer_ids=excluded,
        )

    if name == "get_customer_call_assessment":
        return get_customer_call_assessment(
            arguments[
                "customer_id"
            ]
        )

    return {
        "error":
            "unknown_tool",

        "tool":
            name,
    }


def compact_result(
    tool_name,
    result,
):
    if tool_name == "get_top_customers":
        customers = []

        for customer in result.get(
            "customers",
            [],
        ):
            customers.append(
                {
                    "position":
                        customer.get(
                            "position"
                        ),

                    "customer_id":
                        customer.get(
                            "customer_id"
                        ),

                    "name":
                        customer.get(
                            "name"
                        ),

                    "lastname":
                        customer.get(
                            "lastname"
                        ),

                    "purchases":
                        customer.get(
                            "purchases"
                        ),

                    "total_rubles":
                        customer.get(
                            "total_rubles"
                        ),

                    "average_check_rubles":
                        customer.get(
                            "average_check_rubles"
                        ),

                    "first_purchase":
                        customer.get(
                            "first_purchase"
                        ),

                    "last_purchase":
                        customer.get(
                            "last_purchase"
                        ),
                }
            )

        return {
            "ranking":
                result.get(
                    "ranking"
                ),

            "customers":
                customers,
        }

    if tool_name == "get_customer_profile":
        return {
            "customer":
                result.get(
                    "customer"
                ),

            "statistics":
                result.get(
                    "statistics"
                ),

            "top_products":
                result.get(
                    "top_products",
                    [],
                )[:5],
        }

    if tool_name == "find_customer_by_name":
        if (
            result.get(
                "status"
            )
            == "unique_match"
        ):
            profile = result.get(
                "profile",
                {},
            )

            return {
                "status":
                    "unique_match",

                "query":
                    result.get(
                        "query"
                    ),

                "profile": {
                    "customer":
                        profile.get(
                            "customer"
                        ),

                    "statistics":
                        profile.get(
                            "statistics"
                        ),

                    "top_products":
                        profile.get(
                            "top_products",
                            [],
                        )[:5],
                },
            }

    return result


def get_tool_names():
    return [
        specification.name
        for specification in FUNCTION_SPECS
    ]


def print_short_result(
    title,
    result,
):
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)
    print()

    print(
        result
    )


def demo():
    print()
    print("=" * 70)
    print(
        "AGENT TOOLS — TEST"
    )
    print("=" * 70)

    print()
    print(
        "Зарегистрированные инструменты:"
    )

    for name in get_tool_names():
        print(
            f"• {name}"
        )

    print()
    print(
        f"Всего: {len(FUNCTION_SPECS)}"
    )

    print_short_result(
        "АПРЕЛЬ 2025 ПРОТИВ МАЯ 2025",
        run_tool(
            "compare_sales_months",
            {
                "year_a":
                    2025,

                "month_a":
                    4,

                "year_b":
                    2025,

                "month_b":
                    5,
            },
            conversation_id=(
                "__agent_tools_test__"
            ),
        ),
    )

    print_short_result(
        "ПРОИЗВОЛЬНЫЙ ПЕРИОД: АПРЕЛЬ–МАЙ 2026",
        run_tool(
            "get_sales_period_summary",
            {
                "start_date":
                    "01.04.2026",

                "end_date":
                    "31.05.2026",
            },
            conversation_id=(
                "__agent_tools_test__"
            ),
        ),
    )

    print_short_result(
        "СРАВНЕНИЕ ДВУХ ПРОИЗВОЛЬНЫХ ПЕРИОДОВ",
        run_tool(
            "compare_sales_periods",
            {
                "start_a":
                    "01.07.2026",

                "end_a":
                    "17.07.2026",

                "start_b":
                    "01.08.2026",

                "end_b":
                    "17.08.2026",
            },
            conversation_id=(
                "__agent_tools_test__"
            ),
        ),
    )

    print_short_result(
        "2025 ГОД",
        run_tool(
            "get_sales_year_summary",
            {
                "year":
                    2025,
            },
            conversation_id=(
                "__agent_tools_test__"
            ),
        ),
    )

    print_short_result(
        "ТОП-3 МЕСЯЦА ПО ВЫРУЧКЕ",
        run_tool(
            "rank_sales_periods",
            {
                "granularity":
                    "month",

                "metric":
                    "total_revenue",

                "order":
                    "desc",

                "limit":
                    3,
            },
            conversation_id=(
                "__agent_tools_test__"
            ),
        ),
    )

    print_short_result(
        "ТОП-3 ДНЯ АВГУСТА ПО СРЕДНЕМУ ЧЕКУ",
        run_tool(
            "rank_sales_periods",
            {
                "granularity":
                    "day",

                "metric":
                    "average_check",

                "date_from":
                    "01.08.2026",

                "date_to":
                    "17.08.2026",

                "order":
                    "desc",

                "limit":
                    3,

                "min_checks":
                    20,
            },
            conversation_id=(
                "__agent_tools_test__"
            ),
        ),
    )

    print_short_result(
        "ПРИБЫЛЬ — ДОЛЖЕН БЫТЬ ОТКАЗ",
        run_tool(
            "rank_sales_periods",
            {
                "granularity":
                    "month",

                "metric":
                    "profit",

                "limit":
                    3,
            },
            conversation_id=(
                "__agent_tools_test__"
            ),
        ),
    )


if __name__ == "__main__":
    demo()