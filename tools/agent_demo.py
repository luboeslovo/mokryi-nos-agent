import json

from ollama import Client

from customer_tools import (
    get_customer_profile,
    get_top_customers,
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
                "по его customer_id."
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
                "по общей сумме их покупок."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": (
                            "Сколько покупателей вернуть. "
                            "Например 5 означает топ-5."
                        )
                    }
                },
                "required": ["limit"]
            }
        }
    }
]


QUESTION = """
Кто 5 самых ценных покупателей магазина?

Покажи их по убыванию общей суммы покупок
и коротко скажи, чем они отличаются друг от друга.
"""


messages = [
    {
        "role": "system",
        "content": (
            "Ты аналитик зоомагазина. "
            "У тебя есть несколько инструментов для получения реальных данных. "
            "Сам выбери подходящий инструмент для вопроса пользователя. "
            "Никогда не придумывай цифры."
        )
    },
    {
        "role": "user",
        "content": QUESTION
    }
]


print()
print("ВОПРОС:")
print(QUESTION.strip())

print()
print("1. Qwen выбирает инструмент...")
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


messages.append(response.message)


if not response.message.tool_calls:

    print("Модель НЕ вызвала инструмент.")
    print()
    print(response.message.content)

else:

    call = response.message.tool_calls[0]

    function_name = call.function.name
    arguments = call.function.arguments

    print("2. МОДЕЛЬ ВЫБРАЛА TOOL")
    print()
    print("Название:")
    print(function_name)

    print()
    print("Аргументы:")
    print(arguments)

    print()
    print("3. Python выполняет инструмент...")
    print()


    try:

        if function_name == "get_customer_profile":

            result = get_customer_profile(
                arguments["customer_id"]
            )

        elif function_name == "get_top_customers":

            result = get_top_customers(
                arguments["limit"]
            )

        else:

            result = {
                "error": "unknown_tool",
                "tool": function_name
            }

    except Exception as error:

        result = {
            "error": "tool_execution_failed",
            "message": str(error)
        }


    print("Инструмент выполнен.")
    print()
    print("РЕЗУЛЬТАТ TOOL:")
    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2
        )
    )


    messages.append(
        {
            "role": "tool",
            "tool_name": function_name,
            "content": json.dumps(
                result,
                ensure_ascii=False
            )
        }
    )


    messages.append(
        {
            "role": "system",
            "content": (
                "Инструмент уже выполнен. "
                "Теперь ответь пользователю по полученным данным. "
                "Не придумывай новые цифры. "
                "Ответ должен быть коротким."
            )
        }
    )


    print()
    print("4. Qwen анализирует результат...")
    print()
    print("=" * 80)
    print()


    stream = client.chat(
        model=MODEL,
        messages=messages,
        think=False,
        stream=True,
        options={
            "num_ctx": 1024,
            "num_thread": 2,
            "num_predict": 180,
            "temperature": 0.2
        },
        keep_alive=0
    )


    for chunk in stream:

        text = chunk.message.content

        if text:

            print(
                text,
                end="",
                flush=True
            )


    print()
    print()
    print("=" * 80)
    print("ГОТОВО")