import json

import keyring

from gigachat import GigaChat
from gigachat.models import (
    ChatCompletionRequest,
    ChatFunctionSpecification,
    ChatMessage,
    ChatTool,
)

from customer_tools import (
    find_customer_by_name,
    get_customer_profile,
    get_top_customers,
)

from sales_tools import (
    compare_sales_days,
    get_daily_sales,
    get_latest_sales_day,
    get_month_summary,
    get_recent_sales,
)


SERVICE_NAME = "mokryi-nos-agent-gigachat"
ACCOUNT_NAME = "authorization_key"

SCOPE = "GIGACHAT_API_PERS"
MODEL = "GigaChat-3-Ultra"


def get_authorization_key():
    authorization_key = keyring.get_password(
        SERVICE_NAME,
        ACCOUNT_NAME,
    )

    if not authorization_key:
        raise RuntimeError(
            "Authorization key GigaChat не найден "
            "в защищённом хранилище Windows."
        )

    return authorization_key


client = GigaChat(
    credentials=get_authorization_key(),
    scope=SCOPE,
    model=MODEL,
    verify_ssl_certs=False,
    timeout=60,
)


FUNCTION_SPECS = [
    ChatFunctionSpecification(
        name="get_customer_profile",
        description=(
            "Получает подробный профиль конкретного клиента "
            "зоомагазина по customer_id. "
            "Используй, когда customer_id уже известен."
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
            "по общей сумме положительных покупок. "
            "Используй для вопросов про топ клиентов, "
            "лучших покупателей и самых крупных клиентов."
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
            "или полному имени. "
            "Используй, если пользователь называет "
            "клиента по имени, а customer_id неизвестен."
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
                        "Максимальное количество "
                        "кандидатов при поиске"
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
            "Возвращает показатели последнего закрытого "
            "дня магазина И точное сравнение "
            "с предыдущим закрытым днём. "
            "Используй для общих вопросов: "
            "'как вчера торговали', "
            "'как прошёл вчерашний день', "
            "'ну че как вчера', "
            "'вчера хорошо торговали?', "
            "'что было вчера'. "
            "Благодаря сравнению можно обоснованно "
            "оценить, был последний день сильнее "
            "или слабее предыдущего."
        ),
        parameters={
            "type": "object",
            "properties": {},
        },
    ),

    ChatFunctionSpecification(
        name="get_daily_sales",
        description=(
            "Возвращает показатели магазина "
            "за конкретную дату: "
            "полную выручку, кассовые продажи, "
            "количество чеков, товары, КТЧ, "
            "средний чек, наличные, карту, возвраты, "
            "Яндекс, Купер и внешние заказы. "
            "Используй, когда нужна одна конкретная дата "
            "без обязательного сравнения."
        ),
        parameters={
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": (
                        "Дата в формате ДД.ММ.ГГГГ. "
                        "Для последнего закрытого дня "
                        "можно использовать latest."
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
            "Python сам определяет, какая дата раньше, "
            "а какая позже, и считает изменение "
            "позднего дня относительно более раннего. "
            "Возвращает точные абсолютные "
            "и процентные изменения. "
            "Используй для вопросов вроде "
            "'сравни 16 и 17 августа'."
        ),
        parameters={
            "type": "object",
            "properties": {
                "date_a": {
                    "type": "string",
                    "description": (
                        "Первая дата в формате ДД.ММ.ГГГГ"
                    ),
                },
                "date_b": {
                    "type": "string",
                    "description": (
                        "Вторая дата в формате ДД.ММ.ГГГГ"
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
            "Возвращает показатели нескольких последних "
            "закрытых дней магазина. "
            "Используй для анализа динамики "
            "нескольких дней, например "
            "'как торговали последние 7 дней'."
        ),
        parameters={
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": (
                        "Количество последних дней "
                        "от 1 до 31"
                    ),
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
            "Возвращает сводные показатели магазина "
            "за месяц: полную выручку, "
            "кассовую выручку, чеки, товары, "
            "средний чек, КТЧ, Яндекс, "
            "внешние заказы и возвраты. "
            "Для незавершённого месяца учитывает "
            "только имеющиеся закрытые дни."
        ),
        parameters={
            "type": "object",
            "properties": {
                "year": {
                    "type": "integer",
                    "description": (
                        "Год, например 2026"
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

    if latest.get("status") != "ok":
        return latest

    result = {
        "status": "ok",
        "day": latest["day"],
    }

    recent = get_recent_sales(
        2
    )

    recent_days = recent.get(
        "days",
        [],
    )

    if len(recent_days) < 2:
        return result

    previous_day = recent_days[-2]
    latest_day = recent_days[-1]

    comparison = compare_sales_days(
        previous_day["date"],
        latest_day["date"],
    )

    result[
        "previous_day"
    ] = previous_day

    result[
        "comparison_with_previous_day"
    ] = comparison

    return result


def run_tool(
    name,
    arguments,
):
    if name == "get_customer_profile":
        return get_customer_profile(
            arguments["customer_id"]
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
            arguments["query"],
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
            arguments["date_a"],
            arguments["date_b"],
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
            arguments["year"],
            arguments["month"],
        )

    return {
        "error": "unknown_tool",
        "tool": name,
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


def extract_function_call(
    message,
):
    function_call = getattr(
        message,
        "function_call",
        None,
    )

    if function_call is not None:
        return function_call

    content = getattr(
        message,
        "content",
        None,
    )

    if not content:
        return None

    for part in content:
        function_call = getattr(
            part,
            "function_call",
            None,
        )

        if function_call is not None:
            return function_call

    return None


def extract_text(
    response,
):
    messages = getattr(
        response,
        "messages",
        None,
    )

    if not messages:
        return ""

    message = messages[0]

    content = getattr(
        message,
        "content",
        None,
    )

    if isinstance(
        content,
        str,
    ):
        return content.strip()

    if not content:
        return ""

    parts = []

    for part in content:
        text = getattr(
            part,
            "text",
            None,
        )

        if text:
            parts.append(
                text
            )

    return "\n".join(
        parts
    ).strip()


def normalize_arguments(
    arguments,
):
    if arguments is None:
        return {}

    if isinstance(
        arguments,
        dict,
    ):
        return arguments

    if isinstance(
        arguments,
        str,
    ):
        try:
            return json.loads(
                arguments
            )

        except json.JSONDecodeError:
            return {}

    try:
        return dict(
            arguments
        )

    except Exception:
        return {}


def get_latest_data_date():
    try:
        result = (
            get_latest_sales_day()
        )

        if (
            result.get(
                "status"
            )
            == "ok"
        ):
            return (
                result
                .get(
                    "day",
                    {},
                )
                .get(
                    "date"
                )
            )

    except Exception:
        pass

    return None


def answer_question(
    question,
):
    question = str(
        question or ""
    ).strip()

    if not question:
        return (
            "Напиши вопрос о магазине."
        )

    latest_data_date = (
        get_latest_data_date()
    )

    date_context = ""

    if latest_data_date:
        date_context = (
            "\nПоследний закрытый день "
            f"в дневной аналитике: "
            f"{latest_data_date}. "
            "Слова 'вчера' и 'последний день' "
            "относи именно к этой дате."
        )

    system_prompt = (
        "Ты AI-аналитик зоомагазина "
        "«Мокрый нос».\n"
        "\n"
        "У тебя есть функции с реальными "
        "данными магазина.\n"
        "Для фактов о магазине, клиентах "
        "или продажах обязательно используй "
        "подходящую функцию.\n"
        "Не придумывай цифры.\n"
        "\n"
        "Если пользователь спрашивает в целом, "
        "как прошёл вчерашний или последний день, "
        "используй get_latest_sales_day. "
        "Эта функция возвращает и сам день, "
        "и точное сравнение с предыдущим днём.\n"
        "\n"
        "Для клиента по имени используй "
        "find_customer_by_name.\n"
        "Для customer_id используй "
        "get_customer_profile.\n"
        "\n"
        "total_revenue — полная выручка магазина.\n"
        "check_revenue_net — кассовые продажи "
        "после возвратов.\n"
        "external_total — внешние заказы.\n"
        "КТЧ — среднее количество товаров "
        "в одном чеке.\n"
        "\n"
        "Не называй день хорошим, плохим, "
        "сильным или слабым только по абсолютной "
        "сумме выручки. Для такой оценки используй "
        "сравнение с предыдущим днём.\n"
        "\n"
        "Не выполняй самостоятельно арифметику, "
        "если Python уже вернул готовые "
        "процентные изменения.\n"
        "\n"
        "Отвечай по-русски."
        + date_context
    )

    request = ChatCompletionRequest(
        messages=[
            ChatMessage(
                role="system",
                content=system_prompt,
            ),
            ChatMessage(
                role="user",
                content=question,
            ),
        ],
        tools=TOOLS,
    )

    first_response = (
        client.chat.create(
            request
        )
    )

    first_message = (
        first_response
        .messages[0]
    )

    function_call = (
        extract_function_call(
            first_message
        )
    )

    if function_call is None:
        text = extract_text(
            first_response
        )

        if text:
            return text

        return (
            "Не получилось сформировать ответ."
        )

    tool_name = (
        function_call.name
    )

    arguments = normalize_arguments(
        function_call.arguments
    )

    print(
        f"[tool] {tool_name}({arguments})"
    )

    try:
        tool_result = run_tool(
            tool_name,
            arguments,
        )

    except Exception as error:
        tool_result = {
            "error":
                "tool_execution_failed",

            "message":
                (
                    f"{type(error).__name__}: "
                    f"{error}"
                ),
        }

    real_data = compact_result(
        tool_name,
        tool_result,
    )

    real_data_json = json.dumps(
        real_data,
        ensure_ascii=False,
        separators=(
            ",",
            ":",
        ),
    )

    final_system_prompt = (
        "Ты AI-аналитик зоомагазина "
        "«Мокрый нос».\n"
        "\n"
        "Тебе передан результат Python-функции "
        "с реальными данными магазина.\n"
        "Ответь на исходный вопрос ТОЛЬКО "
        "на основе этих данных.\n"
        "\n"
        "Ничего не придумывай.\n"
        "Не добавляй неподтверждённые причины.\n"
        "\n"
        "Если присутствует "
        "comparison_with_previous_day, "
        "используй это сравнение, когда оцениваешь, "
        "как прошёл день.\n"
        "\n"
        "В структуре сравнения:\n"
        "earlier — значение более раннего дня;\n"
        "later — значение более позднего дня;\n"
        "difference_later_minus_earlier — "
        "поздний день минус ранний;\n"
        "change_percent_vs_earlier — "
        "точное изменение позднего дня "
        "относительно раннего;\n"
        "direction — направление изменения.\n"
        "\n"
        "НЕ пересчитывай процент самостоятельно. "
        "Используй change_percent_vs_earlier "
        "как источник истины.\n"
        "\n"
        "Не говори, что чеков стало меньше, "
        "если later больше earlier, и наоборот.\n"
        "\n"
        "Если рост показателя виден в данных, "
        "можно сказать, что показатель вырос. "
        "Но не утверждай конкретную причину роста, "
        "если данных для причинного вывода нет.\n"
        "\n"
        "Например, если одновременно выросли "
        "средний чек и КТЧ, можно сказать, "
        "что рост выручки сопровождался "
        "более крупными покупками. "
        "Но не придумывай, почему покупатели "
        "стали покупать больше.\n"
        "\n"
        "total_revenue — полная выручка.\n"
        "check_revenue_net — кассовые продажи "
        "после возвратов.\n"
        "external_total — внешние заказы.\n"
        "КТЧ — среднее количество товаров "
        "в одном чеке.\n"
        "\n"
        "Если найдено несколько клиентов "
        "с похожим именем, покажи варианты "
        "и не выбирай человека сам.\n"
        "\n"
        "Не показывай внутренние Python-названия "
        "полей пользователю.\n"
        "Пиши естественно, компактно "
        "и по-русски."
    )

    final_request = (
        ChatCompletionRequest(
            messages=[
                ChatMessage(
                    role="system",
                    content=(
                        final_system_prompt
                    ),
                ),
                ChatMessage(
                    role="user",
                    content=(
                        "ИСХОДНЫЙ ВОПРОС:\n"
                        f"{question}\n"
                        "\n"
                        "ВЫЗВАННАЯ ФУНКЦИЯ:\n"
                        f"{tool_name}\n"
                        "\n"
                        "РЕАЛЬНЫЕ ДАННЫЕ "
                        "ИЗ PYTHON:\n"
                        f"{real_data_json}\n"
                        "\n"
                        "Сформулируй ответ "
                        "пользователю."
                    ),
                ),
            ],
        )
    )

    final_response = (
        client.chat.create(
            final_request
        )
    )

    text = extract_text(
        final_response
    )

    if not text:
        return (
            "Не получилось сформировать ответ."
        )

    return text


def console_chat():
    print()
    print(
        "АГЕНТ ЗООМАГАЗИНА"
    )
    print("=" * 60)
    print()
    print(
        f"Модель: {MODEL}"
    )
    print(
        "Напиши вопрос."
    )
    print(
        "Для выхода напиши: выход"
    )
    print()

    while True:
        try:
            question = input(
                "Ты: "
            ).strip()

        except KeyboardInterrupt:
            print()
            print(
                "Пока!"
            )
            break

        if question.lower() in {
            "выход",
            "exit",
            "quit",
        }:
            print(
                "Пока!"
            )
            break

        if not question:
            continue

        print()
        print(
            "Агент думает..."
        )
        print()

        try:
            answer = answer_question(
                question
            )

        except Exception as error:
            answer = (
                "Ошибка агента: "
                f"{type(error).__name__}: "
                f"{error}"
            )

        print(
            "Агент:"
        )
        print()
        print(
            answer
        )
        print()


if __name__ == "__main__":
    console_chat()