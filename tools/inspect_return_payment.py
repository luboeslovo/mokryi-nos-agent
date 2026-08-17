import os
from urllib.parse import urlencode, urljoin

from playwright.sync_api import sync_playwright


PROJECT_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

AUTH_FILE = os.path.join(
    PROJECT_DIR,
    "auth.json"
)

BASE_URL = "https://it.mokryinos.ru/"

LIST_URL = urljoin(
    BASE_URL,
    "checkKkm/index"
)


def clean(text):
    return " ".join(
        (text or "").split()
    )


def main():

    print()
    print("=" * 100)
    print("ПОСЛЕДНИЙ ВОЗВРАТ — СПОСОБ ОПЛАТЫ")
    print("=" * 100)

    params = [
        (
            "CheckKkm[type]",
            "71"
        ),
        (
            "pageSize",
            "500"
        ),
    ]

    url = (
        LIST_URL
        + "?"
        + urlencode(params)
    )

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        context = browser.new_context(
            storage_state=AUTH_FILE
        )

        page = context.new_page()

        page.goto(
            url,
            wait_until="networkidle",
            timeout=60000
        )

        if "/login" in page.url:

            print(
                "ОШИБКА: CRM отправила на login"
            )

            browser.close()
            return

        print()
        print("URL списка:")
        print(page.url)

        print()
        print("=" * 100)
        print("ВОЗВРАТЫ")
        print("=" * 100)

        rows = page.locator(
            "table tr"
        )

        return_links = []

        for i in range(
            rows.count()
        ):

            row = rows.nth(i)

            text = clean(
                row.text_content()
            )

            if (
                "Возврат Чека ККМ"
                not in text
            ):
                continue

            links = row.locator(
                "a"
            )

            href = None

            for j in range(
                links.count()
            ):

                candidate = links.nth(
                    j
                ).get_attribute(
                    "href"
                )

                if (
                    candidate
                    and candidate.startswith(
                        "/checkKkm/"
                    )
                ):

                    href = candidate
                    break

            if not href:
                continue

            return_links.append(
                (
                    text,
                    href,
                )
            )

        print(
            "Найдено возвратов:",
            len(return_links)
        )

        for i, (
            text,
            href,
        ) in enumerate(
            return_links[:10],
            start=1
        ):

            print()
            print(
                f"{i:02d} | {text}"
            )

            print(
                f"     -> {href}"
            )

        if not return_links:

            print()
            print(
                "Реальных возвратов "
                "по фильтру не найдено."
            )

            browser.close()
            return

        latest_text, latest_href = (
            return_links[0]
        )

        detail_url = urljoin(
            BASE_URL,
            latest_href
        )

        print()
        print("=" * 100)
        print("ОТКРЫВАЮ САМЫЙ СВЕЖИЙ ВОЗВРАТ")
        print("=" * 100)

        print(
            latest_text
        )

        print(
            detail_url
        )

        page.goto(
            detail_url,
            wait_until="networkidle",
            timeout=60000
        )

        if "/login" in page.url:

            print(
                "ОШИБКА: CRM отправила на login"
            )

            browser.close()
            return

        print()
        print("Финальный URL:")
        print(page.url)

        print()
        print("TITLE:")
        print(page.title())

        print()
        print("=" * 100)
        print("НЕПУСТЫЕ ПОЛЯ КАРТОЧКИ")
        print("=" * 100)

        fields = page.locator(
            "input, select, textarea"
        )

        for i in range(
            fields.count()
        ):

            field = fields.nth(i)

            tag = field.evaluate(
                "el => el.tagName"
            )

            name = field.get_attribute(
                "name"
            )

            field_id = field.get_attribute(
                "id"
            )

            value = ""

            try:
                value = field.input_value()
            except Exception:
                pass

            value = clean(
                value
            )

            if not value:
                continue

            print(
                f"{tag:<8} | "
                f"name={name!r} | "
                f"id={field_id!r} | "
                f"value={value!r}"
            )

        print()
        print("=" * 100)
        print("СТРОКИ С ИНФОРМАЦИЕЙ ОБ ОПЛАТЕ")
        print("=" * 100)

        keywords = [
            "налич",
            "безнал",
            "эквайр",
            "оплат",
            "касс",
            "возврат",
            "банк",
            "карта",
        ]

        detail_rows = page.locator(
            "table tr"
        )

        found_rows = 0

        for i in range(
            detail_rows.count()
        ):

            text = clean(
                detail_rows.nth(i)
                .text_content()
            )

            lower = text.lower()

            if not any(
                keyword in lower
                for keyword in keywords
            ):
                continue

            print(
                f"{i:03d} | {text}"
            )

            found_rows += 1

        if found_rows == 0:

            print(
                "Подходящих строк "
                "в таблицах не найдено."
            )

        print()
        print("=" * 100)
        print("ФРАГМЕНТЫ ТЕКСТА СТРАНИЦЫ")
        print("=" * 100)

        body = clean(
            page.locator(
                "body"
            ).text_content()
        )

        lower_body = body.lower()

        printed = set()

        for keyword in keywords:

            start = 0

            while True:

                position = lower_body.find(
                    keyword,
                    start
                )

                if position == -1:
                    break

                fragment = body[
                    max(
                        0,
                        position - 120
                    ):
                    position + 250
                ]

                fragment = clean(
                    fragment
                )

                if fragment not in printed:

                    print()
                    print(
                        f"[{keyword}]"
                    )

                    print(
                        fragment
                    )

                    printed.add(
                        fragment
                    )

                start = (
                    position
                    + len(keyword)
                )

                if len(
                    printed
                ) >= 20:
                    break

            if len(
                printed
            ) >= 20:
                break

        print()
        print("=" * 100)

        browser.close()


if __name__ == "__main__":
    main()