import time

import keyring
from gigachat import GigaChat


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


def main():
    print()
    print("=" * 70)
    print("GIGACHAT API — ТЕСТ")
    print("=" * 70)
    print()
    print(f"Модель: {MODEL}")
    print("Отправляю запрос...")
    print()

    started_at = time.perf_counter()

    with GigaChat(
        credentials=get_authorization_key(),
        scope=SCOPE,
        model=MODEL,
        verify_ssl_certs=False,
    ) as client:

        response = client.chat.create(
            "Ответь по-русски одним словом: тест"
        )

    elapsed = (
        time.perf_counter()
        - started_at
    )

    text = (
        response
        .messages[0]
        .content[0]
        .text
    )

    print("Ответ:")
    print(text)
    print()
    print(
        f"Время ответа: {elapsed:.2f} сек."
    )


if __name__ == "__main__":
    main()