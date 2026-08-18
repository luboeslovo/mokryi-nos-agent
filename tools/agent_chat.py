from agent_core import (
    MODEL,
    answer_question,
)


def console_chat():
    conversation_id = "console"

    print()
    print("АГЕНТ ЗООМАГАЗИНА")
    print("=" * 60)
    print()
    print(f"Модель: {MODEL}")
    print("Память диалога: ВКЛ")
    print("Напиши вопрос.")
    print("Для выхода напиши: выход")
    print()

    while True:
        try:
            question = input(
                "Ты: "
            ).strip()

        except KeyboardInterrupt:
            print()
            print("Пока!")
            break

        if question.lower() in {
            "выход",
            "exit",
            "quit",
        }:
            print("Пока!")
            break

        if not question:
            continue

        print()
        print("Агент думает...")
        print()

        try:
            answer = answer_question(
                question,
                conversation_id=conversation_id,
            )

        except Exception as error:
            answer = (
                "Ошибка агента: "
                f"{type(error).__name__}: "
                f"{error}"
            )

        print("Агент:")
        print()
        print(answer)
        print()


if __name__ == "__main__":
    console_chat()