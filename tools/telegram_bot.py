import json
import time
import urllib.parse
import urllib.request

import keyring

from agent_chat import answer_question


SERVICE_NAME = "mokryi-nos-agent-telegram"
ACCOUNT_NAME = "bot_token"

TELEGRAM_MESSAGE_LIMIT = 4000


def get_bot_token():
    token = keyring.get_password(
        SERVICE_NAME,
        ACCOUNT_NAME,
    )

    if not token:
        raise RuntimeError(
            "Telegram Bot Token не найден "
            "в защищённом хранилище Windows."
        )

    return token


TOKEN = get_bot_token()
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"


def telegram_request(
    method,
    params=None,
    timeout=60,
):
    if params is None:
        params = {}

    url = f"{BASE_URL}/{method}"

    data = urllib.parse.urlencode(
        params
    ).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=data,
        method="POST",
    )

    with urllib.request.urlopen(
        request,
        timeout=timeout,
    ) as response:
        result = json.loads(
            response.read().decode("utf-8")
        )

    if not result.get("ok"):
        raise RuntimeError(
            f"Telegram API error: {result}"
        )

    return result["result"]


def send_chat_action(
    chat_id,
    action="typing",
):
    telegram_request(
        "sendChatAction",
        {
            "chat_id": chat_id,
            "action": action,
        },
    )


def split_message(text):
    text = str(text or "").strip()

    if not text:
        return [
            "Не получилось сформировать ответ."
        ]

    if len(text) <= TELEGRAM_MESSAGE_LIMIT:
        return [text]

    parts = []

    remaining = text

    while remaining:
        if len(remaining) <= TELEGRAM_MESSAGE_LIMIT:
            parts.append(
                remaining
            )
            break

        cut = remaining.rfind(
            "\n",
            0,
            TELEGRAM_MESSAGE_LIMIT,
        )

        if cut < 1000:
            cut = remaining.rfind(
                " ",
                0,
                TELEGRAM_MESSAGE_LIMIT,
            )

        if cut < 1000:
            cut = TELEGRAM_MESSAGE_LIMIT

        part = remaining[:cut].strip()

        if part:
            parts.append(
                part
            )

        remaining = remaining[
            cut:
        ].strip()

    return parts


def send_message(
    chat_id,
    text,
):
    for part in split_message(
        text
    ):
        telegram_request(
            "sendMessage",
            {
                "chat_id": chat_id,
                "text": part,
            },
        )


def handle_message(
    message,
):
    chat = message.get(
        "chat",
        {},
    )

    chat_id = chat.get(
        "id"
    )

    user = message.get(
        "from",
        {},
    )

    username = user.get(
        "username"
    )

    first_name = user.get(
        "first_name"
    )

    text = message.get(
        "text"
    )

    print()
    print("=" * 70)
    print(
        f"Chat ID: {chat_id}"
    )
    print(
        f"Имя: {first_name}"
    )

    if username:
        print(
            f"Username: @{username}"
        )
    else:
        print(
            "Username: нет"
        )

    print(
        f"Сообщение: {text}"
    )
    print("=" * 70)

    if not text:
        send_message(
            chat_id,
            (
                "Пока я умею работать "
                "только с текстовыми сообщениями."
            ),
        )
        return

    text = text.strip()

    if text.startswith(
        "/start"
    ):
        send_message(
            chat_id,
            (
                "Привет! Я Мокрый нос AI.\n\n"
                "Я подключён к данным магазина "
                "и могу отвечать на вопросы по аналитике.\n\n"
                "Например:\n"
                "• покажи топ 5 клиентов\n"
                "• что покупает Сергей Зверев?\n"
                "• найди клиента Иванова\n\n"
                "Сейчас набор доступных данных "
                "ещё расширяется."
            ),
        )
        return

    if text.startswith(
        "/help"
    ):
        send_message(
            chat_id,
            (
                "Просто напиши вопрос обычным языком.\n\n"
                "Сейчас я умею работать прежде всего "
                "с клиентской аналитикой. "
                "Продажи по дням, RFM, ОПиУ и другие "
                "данные добавим следующими инструментами."
            ),
        )
        return

    try:
        send_chat_action(
            chat_id
        )

        print()
        print(
            "Агент думает..."
        )

        answer = answer_question(
            text
        )

        print()
        print(
            "Ответ агента:"
        )
        print(
            answer
        )

        send_message(
            chat_id,
            answer,
        )

    except Exception as error:
        print()
        print(
            "ОШИБКА АГЕНТА:"
        )
        print(
            f"{type(error).__name__}: {error}"
        )

        send_message(
            chat_id,
            (
                "Не получилось обработать вопрос. "
                "Ошибка записана в консоль бота."
            ),
        )


def main():
    print()
    print("=" * 70)
    print(
        "МОКРЫЙ НОС AI — TELEGRAM"
    )
    print("=" * 70)
    print()
    print(
        "Telegram-бот запущен."
    )
    print(
        "AI-агент подключён."
    )
    print(
        "Для остановки нажми Ctrl+C."
    )
    print()

    offset = None

    while True:
        try:
            params = {
                "timeout": 30,
            }

            if offset is not None:
                params[
                    "offset"
                ] = offset

            updates = telegram_request(
                "getUpdates",
                params,
                timeout=40,
            )

            for update in updates:
                offset = (
                    update[
                        "update_id"
                    ]
                    + 1
                )

                message = update.get(
                    "message"
                )

                if not message:
                    continue

                handle_message(
                    message
                )

        except KeyboardInterrupt:
            print()
            print(
                "Бот остановлен."
            )
            break

        except Exception as error:
            print()
            print(
                "Ошибка Telegram-цикла:"
            )
            print(
                f"{type(error).__name__}: {error}"
            )
            print(
                "Повтор через 5 секунд..."
            )

            time.sleep(
                5
            )


if __name__ == "__main__":
    main()