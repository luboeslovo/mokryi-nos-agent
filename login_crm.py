import asyncio
import os

from playwright.async_api import async_playwright


PROJECT_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

AUTH_FILE = os.path.join(
    PROJECT_DIR,
    "auth.json"
)

CRM_URL = (
    "https://it.mokryinos.ru/"
    "checkKkm/index"
)


async def main():

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=False
        )

        context = await browser.new_context()

        page = await context.new_page()

        print()
        print("=" * 70)
        print("АВТОРИЗАЦИЯ CRM")
        print("=" * 70)

        await page.goto(
            CRM_URL,
            wait_until="domcontentloaded"
        )

        print()
        print(
            "Войди в CRM в открывшемся браузере."
        )

        print(
            "После успешного входа "
            "скрипт сам сохранит auth.json."
        )

        while True:

            await asyncio.sleep(1)

            current_url = page.url.lower()

            if (
                "/login" not in current_url
                and "it.mokryinos.ru" in current_url
            ):
                break

        await page.goto(
            CRM_URL,
            wait_until="domcontentloaded"
        )

        if "/login" in page.url.lower():

            print()
            print(
                "Не удалось подтвердить "
                "авторизацию."
            )

            await browser.close()

            raise SystemExit(1)

        await context.storage_state(
            path=AUTH_FILE
        )

        print()
        print("=" * 70)

        print(
            "Авторизация сохранена."
        )

        print(
            f"Файл: {AUTH_FILE}"
        )

        print("=" * 70)

        await browser.close()


if __name__ == "__main__":

    asyncio.run(
        main()
    )