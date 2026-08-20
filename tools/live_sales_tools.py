import csv
import os
from datetime import datetime
from zoneinfo import ZoneInfo


PROJECT_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

CHECKS_CSV_PATH = os.path.join(
    PROJECT_DIR,
    "checks_raw.csv",
)

STORE_TIMEZONE = ZoneInfo(
    "Europe/Moscow"
)

SALE_TYPE = "Чек ККМ"
RETURN_TYPE = "Возврат Чека ККМ"


def round_money(value):
    return round(
        float(value or 0),
        2,
    )


def get_store_now():
    return datetime.now(
        STORE_TIMEZONE
    )


def parse_check_datetime(value):
    value = str(
        value or ""
    ).strip()

    if not value:
        return None

    try:
        return datetime.strptime(
            value,
            "%d.%m.%Y %H:%M",
        )
    except ValueError:
        return None


def parse_amount(value):
    value = str(
        value or ""
    ).strip()

    if not value:
        return 0.0

    value = (
        value
        .replace("\xa0", "")
        .replace(" ", "")
        .replace(",", ".")
    )

    try:
        return float(
            value
        )
    except ValueError:
        return 0.0


def get_current_sales():
    """
    Текущие продажи магазина за сегодняшний незакрытый день.

    Источник:
        checks_raw.csv

    Важно:
    - это live snapshot, а не закрытый управленческий день;
    - данные становятся свежими после запуска sync_checks.py;
    - внешние доставки и продажи без чека сюда пока не входят;
    - возвраты вычитаются из кассовой выручки;
    - количество чеков = только чеки продаж;
    - возвраты считаются отдельно.
    """

    now = get_store_now()

    today_display = now.strftime(
        "%d.%m.%Y"
    )

    if not os.path.exists(
        CHECKS_CSV_PATH
    ):
        return {
            "status": "no_checks_file",
            "date": today_display,
            "source": "checks_raw.csv",
        }

    sales_checks = 0
    sales_revenue = 0.0

    return_checks = 0
    returns = 0.0

    latest_today_check_at = None
    latest_check_in_file = None

    other_types = {}

    with open(
        CHECKS_CSV_PATH,
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        reader = csv.DictReader(
            file
        )

        for row in reader:
            check_datetime = (
                parse_check_datetime(
                    row.get(
                        "date"
                    )
                )
            )

            if check_datetime is None:
                continue

            if (
                latest_check_in_file is None
                or check_datetime
                > latest_check_in_file
            ):
                latest_check_in_file = (
                    check_datetime
                )

            if (
                check_datetime.strftime(
                    "%d.%m.%Y"
                )
                != today_display
            ):
                continue

            if (
                latest_today_check_at is None
                or check_datetime
                > latest_today_check_at
            ):
                latest_today_check_at = (
                    check_datetime
                )

            check_type = str(
                row.get(
                    "type"
                )
                or ""
            ).strip()

            amount = parse_amount(
                row.get(
                    "amount"
                )
            )

            if check_type == SALE_TYPE:
                sales_checks += 1
                sales_revenue += amount

            elif check_type == RETURN_TYPE:
                return_checks += 1
                returns += amount

            else:
                if check_type not in other_types:
                    other_types[
                        check_type
                    ] = {
                        "count": 0,
                        "amount": 0.0,
                    }

                other_types[
                    check_type
                ][
                    "count"
                ] += 1

                other_types[
                    check_type
                ][
                    "amount"
                ] += amount

    sales_revenue = round_money(
        sales_revenue
    )

    returns = round_money(
        returns
    )

    check_revenue_net = round_money(
        sales_revenue
        - returns
    )

    if sales_checks:
        average_check = round_money(
            check_revenue_net
            / sales_checks
        )
    else:
        average_check = 0.0

    other_check_types = []

    for (
        check_type,
        values,
    ) in other_types.items():
        other_check_types.append(
            {
                "type": check_type,
                "count": values[
                    "count"
                ],
                "amount": round_money(
                    values[
                        "amount"
                    ]
                ),
            }
        )

    file_updated_at = datetime.fromtimestamp(
        os.path.getmtime(
            CHECKS_CSV_PATH
        ),
        tz=STORE_TIMEZONE,
    )

    return {
        "status": "ok",
        "source": "checks_raw.csv",
        "snapshot_type": "current_unclosed_day",

        "date": today_display,

        "generated_at": now.strftime(
            "%d.%m.%Y %H:%M:%S"
        ),

        "source_updated_at": (
            file_updated_at.strftime(
                "%d.%m.%Y %H:%M:%S"
            )
        ),

        "checks": sales_checks,

        "sales_revenue": (
            sales_revenue
        ),

        "return_checks": (
            return_checks
        ),

        "returns": returns,

        "check_revenue_net": (
            check_revenue_net
        ),

        "average_check": (
            average_check
        ),

        "latest_today_check_at": (
            latest_today_check_at.strftime(
                "%d.%m.%Y %H:%M"
            )
            if latest_today_check_at
            else None
        ),

        "latest_check_in_database": (
            latest_check_in_file.strftime(
                "%d.%m.%Y %H:%M"
            )
            if latest_check_in_file
            else None
        ),

        "other_check_types": (
            other_check_types
        ),

        "includes_external_orders": False,
        "includes_no_receipt": False,

        "note": (
            "Текущий незакрытый день. "
            "Показатели рассчитаны по свежим чекам CRM "
            "из checks_raw.csv. "
            "Внешние заказы и продажи без чека "
            "в live-сумму пока не включены."
        ),
    }


def main():
    result = get_current_sales()

    print()
    print("=" * 70)
    print("LIVE SALES — TEST")
    print("=" * 70)
    print()

    for key, value in result.items():
        print(
            f"{key}: {value}"
        )


if __name__ == "__main__":
    main()