import asyncio

from playwright.async_api import async_playwright


LOGIN_URL = "https://it.mokryinos.ru/login"


async def main():

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=False
        )

        page = await browser.new_page()

        await page.goto(
            LOGIN_URL,
            wait_until="domcontentloaded"
        )

        print()
        print("=" * 70)
        print("ПОЛЯ ФОРМЫ ВХОДА CRM")
        print("=" * 70)

        inputs = await page.locator(
            "input"
        ).all()

        for index, element in enumerate(
            inputs,
            start=1
        ):

            print()
            print(
                f"INPUT {index}"
            )

            print(
                "type:",
                await element.get_attribute("type")
            )

            print(
                "name:",
                await element.get_attribute("name")
            )

            print(
                "id:",
                await element.get_attribute("id")
            )

            print(
                "placeholder:",
                await element.get_attribute(
                    "placeholder"
                )
            )

        buttons = await page.locator(
            "button, input[type=submit]"
        ).all()

        print()
        print("=" * 70)
        print("КНОПКИ")
        print("=" * 70)

        for index, element in enumerate(
            buttons,
            start=1
        ):

            print()
            print(
                f"BUTTON {index}"
            )

            print(
                "text:",
                (
                    await element.inner_text()
                ).strip()
            )

            print(
                "type:",
                await element.get_attribute("type")
            )

            print(
                "name:",
                await element.get_attribute("name")
            )

            print(
                "id:",
                await element.get_attribute("id")
            )

        print()
        print("=" * 70)
        print(
            "Закрой браузер или нажми Enter."
        )

        await asyncio.to_thread(
            input
        )

        await browser.close()


if __name__ == "__main__":

    asyncio.run(
        main()
    )