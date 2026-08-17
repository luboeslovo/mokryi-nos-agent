import asyncio
import os

import keyring
from playwright.async_api import async_playwright


SERVICE = "mokryi-nos-crm"

PROJECT_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

AUTH_FILE = os.path.join(
    PROJECT_DIR,
    "auth.json"
)

CRM_URL = (
    "https://it.mokryinos.ru/"
    "checkKkm/index"
)

LOGIN_SELECTOR = (
    "#app_modules_userModule_models_LoginForm_login"
)

PASSWORD_SELECTOR = (
    "#app_modules_userModule_models_LoginForm_password"
)

BUTTON_SELECTOR = "#login-btn"


async def main():

    username = keyring.get_password(
        SERVICE,
        "username"
    )

    password = keyring.get_password(
        SERVICE,
        "password"
    )

    if not username or not password:
        raise SystemExit(
            "Логин или пароль CRM не найдены "
            "в хранилище Windows."
        )

    print()
    print("=" * 70)
    print("АВТОМАТИЧЕСКАЯ АВТОРИЗАЦИЯ CRM")
    print("=" * 70)

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True
        )

        context = await browser.new_context()

        page = await context.new_page()

        await page.goto(
            CRM_URL,
            wait_until="domcontentloaded"
        )

        if "/login" in page.url.lower():

            print()
            print("Выполняю вход...")

            await page.locator(
                LOGIN_SELECTOR
            ).fill(
                username
            )

            await page.locator(
                PASSWORD_SELECTOR
            ).fill(
                password
            )

            await page.locator(
                BUTTON_SELECTOR
            ).click()

            for _ in range(20):

                await asyncio.sleep(0.5)

                if "/login" not in page.url.lower():
                    break

        await page.goto(
            CRM_URL,
            wait_until="domcontentloaded"
        )

        if "/login" in page.url.lower():

            await browser.close()

            print()
            print("=" * 70)
            print("АВТОРИЗАЦИЯ НЕ УДАЛАСЬ")
            print("=" * 70)

            raise SystemExit(1)

        await context.storage_state(
            path=AUTH_FILE
        )

        print()
        print("=" * 70)
        print("АВТОРИЗАЦИЯ УСПЕШНА")
        print("=" * 70)
        print()
        print("Новый auth.json сохранён.")
        print(f"Файл: {AUTH_FILE}")

        await browser.close()


if __name__ == "__main__":

    asyncio.run(
        main()
    )