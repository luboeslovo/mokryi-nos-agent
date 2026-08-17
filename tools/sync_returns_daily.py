import csv
import os
import sqlite3
from calendar import monthrange
from datetime import datetime

from playwright.sync_api import sync_playwright


PROJECT_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

DB_FILE = os.path.join(
    PROJECT_DIR,
    "analytics.sqlite"
)

KKM_FILE = os.path.join(
    PROJECT_DIR,
    "kkm_daily.csv"
)

OUT_FILE = os.path.join(
    PROJECT_DIR,
    "returns_daily.csv"
)

AUTH_FILE = os.path.join(
    PROJECT_DIR,
    "auth.json"
)

BASE_URL = (
    "https://it.mokryinos.ru/"
)


def clean(text):
    return " ".join(
        (text or "").split()
    )


def parse_money(text):
    value = clean(text)

    if not value:
        return 0.0

    value = (
        value
        .replace("\xa0", "")
        .replace(" ", "")
        .replace(",", ".")
        .replace("₽", "")
    )

    return float(value)


def parse_date(value):
    value = clean(value)

    formats = [
        "%Y-%m-%d",
        "%d.%m.%Y",
        "%d.%m.%Y %H:%M",
        "%Y-%m-%d %H:%M:%S",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(
                value,
                fmt
            )
        except ValueError:
            pass

    raise ValueError(
        f"Неизвестный формат даты: "
        f"{value!r}"
    )


def get_latest_closed_date():

    if not os.path.exists(
        KKM_FILE
    ):
        raise RuntimeError(
            "Не найден kkm_daily.csv. "
            "Сначала запусти "
            "sync_kkm_daily.py"
        )

    dates = []

    with open(
        KKM_FILE,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.DictReader(
            file
        )

        if not reader.fieldnames:
            raise RuntimeError(
                "kkm_daily.csv пустой"
            )

        if "date" in reader.fieldnames:
            date_field = "date"
        elif "Дата" in reader.fieldnames:
            date_field = "Дата"
        else:
            date_field = (
                reader.fieldnames[0]
            )

        for row in reader:

            value = clean(
                row.get(
                    date_field,
                    ""
                )
            )

            if not value:
                continue

            dates.append(
                parse_date(value)
            )

    if not dates:
        raise RuntimeError(
            "В kkm_daily.csv "
            "не найдено дат"
        )

    return max(dates)


def get_returns(
    year,
    month,
    day_limit
):

    month_key = (
        f"{month:02d}.{year:04d}"
    )

    connection = (
        sqlite3.connect(
            DB_FILE
        )
    )

    try:

        rows = (
            connection.execute(
                """
                SELECT
                    check_id,
                    date,
                    amount_cents
                FROM checks
                WHERE type = ?
                  AND substr(
                      date,
                      4,
                      7
                  ) = ?
                ORDER BY datetime_iso
                """,
                (
                    "Возврат Чека ККМ",
                    month_key,
                ),
            )
            .fetchall()
        )

    finally:

        connection.close()

    result = []

    for (
        check_id,
        date_text,
        amount_cents,
    ) in rows:

        dt = datetime.strptime(
            date_text,
            "%d.%m.%Y %H:%M"
        )

        if dt.day > day_limit:
            continue

        result.append(
            {
                "check_id": str(
                    check_id
                ),
                "date": dt,
                "amount": round(
                    (
                        amount_cents
                        or 0
                    )
                    / 100.0,
                    2
                ),
            }
        )

    return result


def read_payment_methods(
    page,
    check_id
):

    url = (
        BASE_URL
        + "checkKkm/"
        + str(check_id)
    )

    page.goto(
        url,
        wait_until="networkidle",
        timeout=60000
    )

    if "/login" in page.url:

        raise RuntimeError(
            "CRM отправила на login. "
            "Запусти "
            "tools\\auto_login_crm.py"
        )

    try:

        page.wait_for_function(
            """
            () =>
                document.body &&
                document.body.innerText &&
                document.body.innerText.includes(
                    'Метод платежа'
                )
            """,
            timeout=15000
        )

    except Exception:
        pass

    cash = 0.0
    card = 0.0

    found = False

    rows = page.locator(
        "table tr"
    )

    for i in range(
        rows.count()
    ):

        cells = (
            rows
            .nth(i)
            .locator(
                "th, td"
            )
        )

        if cells.count() < 2:
            continue

        values = []

        for j in range(
            cells.count()
        ):

            values.append(
                clean(
                    cells
                    .nth(j)
                    .text_content()
                )
            )

        for j, value in enumerate(
            values
        ):

            lower = (
                value.lower()
            )

            is_cash = (
                lower == "наличные"
                or lower.startswith(
                    "наличные "
                )
            )

            is_card = (
                "оплата по "
                "пластиковой карте"
                in lower
            )

            if not (
                is_cash
                or is_card
            ):
                continue

            if (
                j + 1
                >= len(values)
            ):
                continue

            amount = parse_money(
                values[j + 1]
            )

            if is_cash:
                cash += amount
            else:
                card += amount

            found = True

    if not found:

        raise RuntimeError(
            "Не удалось определить "
            "метод возврата "
            f"check_id={check_id}"
        )

    return (
        round(
            cash,
            2
        ),
        round(
            card,
            2
        ),
    )


def build_month(
    page,
    year,
    month,
    day_limit
):

    print()

    print(
        f"Обрабатываю "
        f"{month:02d}.{year} "
        f"по {day_limit} число..."
    )

    returns = get_returns(
        year,
        month,
        day_limit
    )

    print(
        f"Возвратов: "
        f"{len(returns)}"
    )

    daily = {}

    for day in range(
        1,
        day_limit + 1
    ):

        date_key = (
            f"{year:04d}-"
            f"{month:02d}-"
            f"{day:02d}"
        )

        daily[date_key] = {
            "cash": 0.0,
            "card": 0.0,
        }

    for index, item in enumerate(
        returns,
        start=1
    ):

        cash, card = (
            read_payment_methods(
                page,
                item[
                    "check_id"
                ]
            )
        )

        detected = round(
            cash + card,
            2
        )

        expected = round(
            item["amount"],
            2
        )

        if abs(
            detected
            - expected
        ) > 0.01:

            raise RuntimeError(
                "Сумма способов оплаты "
                "не совпала с возвратом "
                f"check_id="
                f"{item['check_id']}: "
                f"возврат="
                f"{expected:.2f}, "
                f"оплата="
                f"{detected:.2f}"
            )

        date_key = (
            item["date"]
            .strftime(
                "%Y-%m-%d"
            )
        )

        daily[
            date_key
        ][
            "cash"
        ] += cash

        daily[
            date_key
        ][
            "card"
        ] += card

        parts = []

        if cash:

            parts.append(
                f"НАЛ "
                f"{cash:,.2f}"
            )

        if card:

            parts.append(
                f"БЕЗНАЛ "
                f"{card:,.2f}"
            )

        print(
            f"{index}/"
            f"{len(returns)}"
            f" | "
            f"{item['date'].strftime('%d.%m.%Y')}"
            f" | "
            f"{item['check_id']}"
            f" | "
            + ", ".join(parts)
        )

    result = []

    cash_total = 0.0
    card_total = 0.0

    updated_at = (
        datetime.now()
        .isoformat(
            timespec="seconds"
        )
    )

    for date_key in sorted(
        daily
    ):

        cash = round(
            daily[
                date_key
            ][
                "cash"
            ],
            2
        )

        card = round(
            daily[
                date_key
            ][
                "card"
            ],
            2
        )

        cash_total += cash
        card_total += card

        if cash:
            cash_out = -cash
        else:
            cash_out = 0.0

        if card:
            card_out = -card
        else:
            card_out = 0.0

        total_out = round(
            cash_out
            + card_out,
            2
        )

        result.append(
            {
                "date": date_key,
                "cash_return": (
                    f"{cash_out:.2f}"
                ),
                "card_return": (
                    f"{card_out:.2f}"
                ),
                "total_return": (
                    f"{total_out:.2f}"
                ),
                "updated_at": (
                    updated_at
                ),
            }
        )

    if cash_total:
        cash_print = (
            -cash_total
        )
    else:
        cash_print = 0.0

    if card_total:
        card_print = (
            -card_total
        )
    else:
        card_print = 0.0

    total_print = round(
        cash_print
        + card_print,
        2
    )

    print()

    print(
        f"Возврат НАЛ: "
        f"{cash_print:,.2f} ₽"
    )

    print(
        f"Возврат БЕЗНАЛ: "
        f"{card_print:,.2f} ₽"
    )

    print(
        f"Всего возвратов: "
        f"{total_print:,.2f} ₽"
    )

    return result


def load_old_rows():

    if not os.path.exists(
        OUT_FILE
    ):
        return []

    with open(
        OUT_FILE,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        return list(
            csv.DictReader(
                file
            )
        )


def save_rows(
    old_rows,
    new_rows,
    rebuilt_months
):

    kept = []

    for row in old_rows:

        date_text = clean(
            row.get(
                "date",
                ""
            )
        )

        if not date_text:
            continue

        try:

            dt = parse_date(
                date_text
            )

        except ValueError:
            continue

        month_key = (
            dt.year,
            dt.month,
        )

        if (
            month_key
            in rebuilt_months
        ):
            continue

        kept.append(row)

    all_rows = (
        kept
        + new_rows
    )

    all_rows.sort(
        key=lambda row:
        row["date"]
    )

    fieldnames = [
        "date",
        "cash_return",
        "card_return",
        "total_return",
        "updated_at",
    ]

    with open(
        OUT_FILE,
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()

        writer.writerows(
            all_rows
        )


def main():

    print()

    print(
        "=" * 70
    )

    print(
        "СИНХРОНИЗАЦИЯ "
        "ДНЕВНЫХ ВОЗВРАТОВ"
    )

    print(
        "=" * 70
    )

    print()

    closed_date = (
        get_latest_closed_date()
    )

    print(
        "Последний закрытый "
        "день ККМ: "
        + closed_date.strftime(
            "%d.%m.%Y"
        )
    )

    months = [
        (
            2026,
            7,
            monthrange(
                2026,
                7
            )[1],
        )
    ]

    current_month = (
        closed_date.year,
        closed_date.month,
    )

    if current_month == (
        2026,
        7,
    ):

        months = [
            (
                closed_date.year,
                closed_date.month,
                closed_date.day,
            )
        ]

    else:

        months.append(
            (
                closed_date.year,
                closed_date.month,
                closed_date.day,
            )
        )

    old_rows = (
        load_old_rows()
    )

    new_rows = []

    rebuilt_months = set()

    with sync_playwright() as p:

        browser = (
            p.chromium.launch(
                headless=True
            )
        )

        context = (
            browser.new_context(
                storage_state=AUTH_FILE
            )
        )

        page = (
            context.new_page()
        )

        try:

            for (
                year,
                month,
                day_limit,
            ) in months:

                rows = build_month(
                    page,
                    year,
                    month,
                    day_limit
                )

                new_rows.extend(
                    rows
                )

                rebuilt_months.add(
                    (
                        year,
                        month,
                    )
                )

        finally:

            browser.close()

    save_rows(
        old_rows,
        new_rows,
        rebuilt_months
    )

    print()

    print(
        "=" * 70
    )

    print(
        "ГОТОВО"
    )

    print(
        "=" * 70
    )

    print()

    print(
        "Файл: "
        + OUT_FILE
    )


if __name__ == "__main__":
    main()