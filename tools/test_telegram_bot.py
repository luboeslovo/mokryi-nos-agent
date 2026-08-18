import json
import urllib.request

import keyring


SERVICE_NAME = "mokryi-nos-agent-telegram"
ACCOUNT_NAME = "bot_token"


def main():
    token = keyring.get_password(
        SERVICE_NAME,
        ACCOUNT_NAME,
    )

    if not token:
        raise SystemExit(
            "Telegram Bot Token не найден в защищённом хранилище Windows."
        )

    url = f"https://api.telegram.org/bot{token}/getMe"

    try:
        with urllib.request.urlopen(url, timeout=20) as response:
            data = json.loads(
                response.read().decode("utf-8")
            )
    except Exception as exc:
        raise SystemExit(
            f"Не удалось обратиться к Telegram API: {exc}"
        )

    if not data.get("ok"):
        raise SystemExit(
            f"Telegram вернул ошибку: {data}"
        )

    bot = data["result"]

    print("Telegram API: OK")
    print(f"Имя бота: {bot.get('first_name')}")
    print(f"Username: @{bot.get('username')}")
    print(f"Bot ID: {bot.get('id')}")


if __name__ == "__main__":
    main()