import getpass

import keyring


SERVICE_NAME = "mokryi-nos-agent-gigachat"
ACCOUNT_NAME = "authorization_key"


def main():
    print()
    print("=" * 70)
    print("GIGACHAT API — СОХРАНЕНИЕ КЛЮЧА")
    print("=" * 70)
    print()
    print(
        "Вставь Authorization key GigaChat."
    )
    print(
        "На экране символы отображаться не будут."
    )
    print()

    authorization_key = getpass.getpass(
        "GigaChat Authorization key: "
    ).strip()

    if not authorization_key:
        raise RuntimeError(
            "Ключ не введён."
        )

    keyring.set_password(
        SERVICE_NAME,
        ACCOUNT_NAME,
        authorization_key,
    )

    saved_key = keyring.get_password(
        SERVICE_NAME,
        ACCOUNT_NAME,
    )

    if saved_key != authorization_key:
        raise RuntimeError(
            "Не удалось проверить сохранённый ключ."
        )

    print()
    print(
        "Ключ GigaChat успешно сохранён "
        "в защищённом хранилище Windows."
    )
    print(
        "Сам ключ в код проекта не записывался."
    )


if __name__ == "__main__":
    main()