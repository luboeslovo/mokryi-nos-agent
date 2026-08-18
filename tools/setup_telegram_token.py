import getpass
import keyring


SERVICE_NAME = "mokryi-nos-agent-telegram"
ACCOUNT_NAME = "bot_token"


def main():
    token = getpass.getpass(
        "Вставь Telegram Bot Token из BotFather и нажми Enter: "
    ).strip()

    if not token:
        raise SystemExit("Токен пустой.")

    if ":" not in token:
        raise SystemExit(
            "Токен выглядит неверно: в Telegram Bot Token обычно есть символ ':'."
        )

    keyring.set_password(
        SERVICE_NAME,
        ACCOUNT_NAME,
        token,
    )

    print("Telegram Bot Token сохранён в защищённом хранилище Windows.")
    print("В код и GitHub токен не записан.")


if __name__ == "__main__":
    main()