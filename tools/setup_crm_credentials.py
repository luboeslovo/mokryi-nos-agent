import getpass

import keyring


SERVICE = "mokryi-nos-crm"


def main():

    print()
    print("=" * 60)
    print("СОХРАНЕНИЕ ДАННЫХ CRM")
    print("=" * 60)

    username = input(
        "Логин CRM: "
    ).strip()

    password = getpass.getpass(
        "Пароль CRM: "
    )

    if not username:
        raise SystemExit(
            "Логин пустой."
        )

    if not password:
        raise SystemExit(
            "Пароль пустой."
        )

    keyring.set_password(
        SERVICE,
        "username",
        username
    )

    keyring.set_password(
        SERVICE,
        "password",
        password
    )

    print()
    print("=" * 60)
    print("ДАННЫЕ СОХРАНЕНЫ")
    print("=" * 60)
    print()
    print(
        "Логин и пароль сохранены "
        "в защищённом хранилище Windows."
    )
    print(
        "В файлы проекта пароль не записывался."
    )


if __name__ == "__main__":
    main()