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

from rfm_tools import (
    get_contact_candidates,
    get_rfm_segment,
    get_rfm_summary,
)

from call_tools import (
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
                    "description": "ID клиента в CRM",
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
                    "description": "Сколько клиентов вернуть",
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

    ChatFunctionSpecification(
        name="get_latest_sales_day",
        description=(
            "Возвращает последний закрытый день магазина "
            "и сравнение с предыдущим закрытым днём. "
            "Используй для вопросов про вчера "
            "и последний закрытый день."
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
            "за одну конкретную дату."
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
            "Сравнивает два КОНКРЕТНЫХ ДНЯ магазина. "
            "Используй только когда пользователь "
            "говорит про отдельные даты или дни. "
            "Никогда не используй для сравнения месяцев."
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
                    "description": "Количество дней",
                },
            },
            "required": [
                "days",
            ],
        },
    ),

    ChatFunctionSpecification(
        name="get_month_summary",
        description=(
            "Возвращает показатели одного месяца. "
            "Если месяц ещё не завершён, "
            "возвращает доступную часть месяца."
        ),
        parameters={
            "type": "object",
            "properties": {
                "year": {
                    "type": "integer",
                    "description": "Год",
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
            "Сравнивает ДВА МЕСЯЦА магазина. "
            "Если более поздний месяц ещё не завершён, "
            "Python автоматически сравнивает одинаковые "
            "периоды, например 1–17 августа "
            "против 1–17 июля. "
            "Используй для 'сравни август с июлем', "
            "'июль лучше июня?', "
            "'как август идёт относительно июля'. "
            "Не заменяй месяцы отдельными днями."
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
            "Возвращает СПИСОК клиентов "
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
            "Выбирает ОДНОГО следующего клиента "
            "для звонка. "
            "Клиенты, уже предложенные сегодня "
            "в этом разговоре, автоматически "
            "исключаются Python-кодом. "
            "Используй для 'кому сейчас позвонить', "
            "'а кому ещё', 'кто следующий', "
            "'кому после него'."
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
            latest["day"],
    }

    recent = get_recent_sales(
        2
    )

    days = recent.get(
        "days",
        [],
    )

    if len(
        days
    ) >= 2:
        result[
            "previous_day"
        ] = days[-2]

        result[
            "comparison_with_previous_day"
        ] = compare_sales_days(
            days[-2]["date"],
            days[-1]["date"],
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


def demo():
    print()
    print("=" * 70)
    print("AGENT TOOLS — TEST")
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

    print()
    print("=" * 70)
    print(
        "ПОСЛЕДНИЙ ДЕНЬ"
    )
    print("=" * 70)
    print()

    print(
        run_tool(
            "get_latest_sales_day",
            {},
            conversation_id="__agent_tools_test__",
        )
    )

    print()
    print("=" * 70)
    print(
        "АВГУСТ ПРОТИВ ИЮЛЯ"
    )
    print("=" * 70)
    print()

    result = run_tool(
        "compare_sales_months",
        {
            "year_a":
                2026,

            "month_a":
                7,

            "year_b":
                2026,

            "month_b":
                8,
        },
        conversation_id="__agent_tools_test__",
    )

    print(
        {
            "status":
                result.get(
                    "status"
                ),

            "comparison_type":
                result.get(
                    "comparison_type"
                ),

            "comparison_end_day":
                result.get(
                    "comparison_end_day"
                ),

            "total_revenue":
                result
                .get(
                    "metrics",
                    {},
                )
                .get(
                    "total_revenue"
                ),

            "checks":
                result
                .get(
                    "metrics",
                    {},
                )
                .get(
                    "checks"
                ),
        }
    )


if __name__ == "__main__":
    demo()