import json

from ollama import Client

from customer_tools import (
    get_customer_profile,
    get_top_customers,
    find_customer_by_name,
)


MODEL = "qwen3:4b-instruct"


client = Client(
    host="http://127.0.0.1:11434",
    trust_env=False
)


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_customer_profile",
            "description": (
                "Получает подробную информацию об одном конкретном покупателе "
                "по его customer_id. Используй этот инструмент, если пользователь "
                "указал именно customer_id."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {
                        "type": "string",
                        "description": "ID конкретного покупателя в CRM"
                    }
                },
                "required": ["customer_id"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "get_top_customers",
            "description": (
                "Получает рейтинг самых ценных покупателей магазина "
                "по общей сумме их положительных покупок."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Сколько покупателей показать"
                    }
                },
                "required": ["limit"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "find_customer_by_name",
            "description": (
                "Ищет покупателя по имени, фамилии или имени и фамилии. "
                "Используй этот инструмент, когда пользователь называет человека "
                "по имени, а не по customer_id. Если найден один человек, "
                "инструмент сразу возвращает его профиль и покупки."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Имя, фамилия или полное имя покупателя, "
                            "например Сергей Зверев"
                        )
                    },
                    "limit": {
                        "type": "integer",
                        "description": (
                            "Максимальное количество кандидатов "
                            "при неоднозначном поиске"
                        )
                    }
                },
                "required": ["query"]
            }
        }
    }
]


def run_tool(name, arguments):

    if name == "get_customer_profile":
        return get_customer_profile(
            arguments["customer_id"]
        )

    if name == "get_top_customers":
        return get_top_customers(
            arguments["limit"]
        )

    if name == "find_customer_by_name":
        return find_customer_by_name(
            arguments["query"],
            arguments.get("limit", 10)
        )

    return {
        "error": "unknown_tool",
        "tool": name
    }


def make_compact_result(tool_name, result):

    if tool_name == "get_top_customers":

        customers = []

        for customer in result.get("customers", []):

            customers.append({
                "position": customer.get("position"),
                "customer_id": customer.get("customer_id"),
                "name": customer.get("name"),
                "lastname": customer.get("lastname"),
                "purchases": customer.get("purchases"),
                "total_rubles": customer.get("total_rubles"),
                "average_check_rubles": customer.get(
                    "average_check_rubles"
                ),
                "first_purchase": customer.get("first_purchase"),
                "last_purchase": customer.get("last_purchase")
            })

        return {
            "ranking": result.get("ranking"),
            "customers": customers
        }


    if tool_name == "get_customer_profile":

        return {
            "customer": result.get("customer"),
            "statistics": result.get("statistics"),
            "top_products": result.get("top_products", [])[:5]
        }


    if tool_name == "find_customer_by_name":

        if result.get("status") == "unique_match":

            profile = result.get("profile", {})

            return {
                "status": "unique_match",
                "query": result.get("query"),
                "profile": {
                    "customer": profile.get("customer"),
                    "statistics": profile.get("statistics"),
                    "top_products": profile.get(
                        "top_products",
                        []
                    )[:5]
                }
            }

        return result


    return result


print()
print("АГЕНТ ЗООМАГАЗИНА")
print("=" * 60)
print()
print("Напиши вопрос.")
print("Для выхода напиши: выход")
print()


while True:

    question = input("Ты: ").strip()

    if question.lower() in {
        "выход",
        "exit",
        "quit"
    }:
        print("Пока!")
        break

    if not question:
        continue


    messages = [
        {
            "role": "system",
            "content": (
                "Ты аналитик зоомагазина. "
                "У тебя есть инструменты для получения реальных данных "
                "из локальной базы магазина. "
                "Сам выбирай подходящий инструмент. "
                "Если дан customer_id, используй инструмент поиска по customer_id. "
                "Если человек назван по имени или фамилии, используй поиск по имени. "
                "Никогда не придумывай цифры или факты."
            )
        },
        {
            "role": "user",
            "content": question
        }
    ]


    print()
    print("Qwen думает...")
    print()


    response = client.chat(
        model=MODEL,
        messages=messages,
        tools=TOOLS,
        think=False,
        stream=False,
        options={
            "num_ctx": 1024,
            "num_thread": 2,
            "num_predict": 100,
            "temperature": 0
        },
        keep_alive="2m"
    )


    if response.message.tool_calls:

        all_results = []

        for call in response.message.tool_calls:

            name = call.function.name
            arguments = call.function.arguments

            print(
                f"[tool] {name}({arguments})"
            )

            try:

                result = run_tool(
                    name,
                    arguments
                )

            except Exception as error:

                result = {
                    "error": "tool_execution_failed",
                    "message": str(error)
                }


            compact_result = make_compact_result(
                name,
                result
            )

            all_results.append({
                "tool": name,
                "result": compact_result
            })


        tool_data = json.dumps(
            all_results,
            ensure_ascii=False,
            separators=(",", ":")
        )


        final_messages = [
            {
                "role": "system",
                "content": (
                    "Ты аналитик зоомагазина. "
                    "Ответь на вопрос пользователя только на основе "
                    "данных Python-инструмента ниже. "
                    "Ничего не придумывай и ничего не угадывай. "
                    "Не путай имена, позиции и числа разных клиентов. "
                    "Если найдено несколько людей с похожим именем, "
                    "не выбирай человека самостоятельно — покажи варианты. "
                    "Если каких-то данных нет, прямо скажи об этом."
                )
            },
            {
                "role": "user",
                "content": (
                    f"ВОПРОС:\n{question}\n\n"
                    f"РЕАЛЬНЫЕ ДАННЫЕ ИЗ PYTHON:\n{tool_data}\n\n"
                    "Сформулируй короткий и понятный ответ."
                )
            }
        ]


        print()
        print("Агент:")
        print()


        stream = client.chat(
            model=MODEL,
            messages=final_messages,
            think=False,
            stream=True,
            options={
                "num_ctx": 1536,
                "num_thread": 2,
                "num_predict": 260,
                "temperature": 0.1
            },
            keep_alive=0
        )


        for chunk in stream:

            if chunk.message.content:

                print(
                    chunk.message.content,
                    end="",
                    flush=True
                )


        print()
        print()


    else:

        print("Агент:")
        print()
        print(response.message.content)
        print()