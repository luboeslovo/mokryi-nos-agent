import os
import re
from collections import defaultdict
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


def parse_money(text):

    text = (
        clean(text)
        .replace("\xa0", "")
        .replace(" ", "")
        .replace(",", ".")
    )

    match = re.search(
        r"-?\d+(?:\.\d+)?",
        text
    )

    if not match:
        return 0.0

    return float(
        match.group(0)
    )


def classify_payment(text):

    lower = text.lower()

    if (
        "пластиков" in lower
        or "эквайр" in lower
        or "банковск" in lower
        or "карт" in lower
    ):
        return "card"

    if (
        "налич" in lower
        or "денежными средствами" in lower
    ):
        return "cash"

    return "unknown"


def main():

    print()
    print("=" * 100)
    print(
        "ПРОВЕРКА СПОСОБОВ ОПЛАТЫ "
        "ВСЕХ ВОЗВРАТОВ"
    )
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

    list_url = (
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
            list_url,
            wait_until="networkidle",
            timeout=60000
        )

        if "/login" in page.url:

            print(
                "ОШИБКА: CRM отправила на login"
            )

            browser.close()
            return

        returns = []

        rows = page.locator(
            "table tr"
        )

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

            date_match = re.search(
                r"\b(\d{2}\.\d{2}\.\d{4})\b",
                text
            )

            number_match = re.search(
                r"(КЛШНКВ-\d+)",
                text
            )

            amount_match = re.search(
                r"(\d[\d ]*(?:[.,]\d{2}))$",
                text
            )

            href = None

            links = row.locator(
                "a"
            )

            for j in range(
                links.count()
            ):

                candidate = (
                    links.nth(j)
                    .get_attribute(
                        "href"
                    )
                )

                if (
                    candidate
                    and candidate.startswith(
                        "/checkKkm/"
                    )
                ):
                    href = candidate
                    break

            if (
                not href
                or not date_match
            ):
                continue

            returns.append(
                {
                    "date":
                        date_match.group(1),

                    "number":
                        (
                            number_match.group(1)
                            if number_match
                            else ""
                        ),

                    "amount":
                        (
                            parse_money(
                                amount_match.group(1)
                            )
                            if amount_match
                            else 0.0
                        ),

                    "href":
                        href,
                }
            )

        print()
        print(
            "Возвратов найдено:",
            len(returns)
        )

        print()
        print("-" * 100)

        totals = defaultdict(
            lambda: {
                "cash": 0.0,
                "card": 0.0,
                "unknown": 0.0,
                "count": 0,
            }
        )

        for index, item in enumerate(
            returns,
            start=1
        ):

            detail_url = urljoin(
                BASE_URL,
                item["href"]
            )

            page.goto(
                detail_url,
                wait_until="networkidle",
                timeout=60000
            )

            payment_rows = []

            table_rows = page.locator(
                "table tr"
            )

            for i in range(
                table_rows.count()
            ):

                text = clean(
                    table_rows.nth(i)
                    .text_content()
                )

                lower = text.lower()

                if (
                    "оплата по" in lower
                    or "оплата налич" in lower
                    or "пластиков" in lower
                ):

                    payment_rows.append(
                        text
                    )

            payment_text = (
                " || ".join(
                    payment_rows
                )
            )

            payment_type = (
                classify_payment(
                    payment_text
                )
            )

            month = (
                item["date"][3:10]
            )

            totals[
                month
            ][payment_type] += (
                item["amount"]
            )

            totals[
                month
            ]["count"] += 1

            print(
                f"{index:02d}/{len(returns)} | "
                f"{item['date']} | "
                f"{item['number']:<14} | "
                f"{item['amount']:>9,.2f} ₽ | "
                f"{payment_type.upper():<7} | "
                f"{payment_text}"
            )

        browser.close()

    print()
    print("=" * 100)
    print("ИТОГИ ПО МЕСЯЦАМ")
    print("=" * 100)

    for month in sorted(
        totals
    ):

        data = totals[
            month
        ]

        print()
        print(
            month,
            "| возвратов:",
            data["count"]
        )

        print(
            "  НАЛ:",
            f"{data['cash']:,.2f} ₽"
        )

        print(
            "  БЕЗНАЛ:",
            f"{data['card']:,.2f} ₽"
        )

        print(
            "  НЕ ОПРЕДЕЛЕНО:",
            f"{data['unknown']:,.2f} ₽"
        )

    print()
    print("=" * 100)


if __name__ == "__main__":
    main()