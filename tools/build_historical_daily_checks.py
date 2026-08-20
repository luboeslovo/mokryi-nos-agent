import csv
import os
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation


PROJECT_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

CHECKS_FILE = os.path.join(
    PROJECT_DIR,
    "checks_raw.csv",
)

ITEMS_FILE = os.path.join(
    PROJECT_DIR,
    "check_items.csv",
)

KKM_FILE = os.path.join(
    PROJECT_DIR,
    "kkm_daily.csv",
)

OUTPUT_FILE = os.path.join(
    PROJECT_DIR,
    "historical_daily_checks.csv",
)


SALE_CHECK_TYPE = "Чек ККМ"

RETURN_CHECK_TYPE = (
    "Возврат Чека ККМ"
)

ZERO = Decimal("0")


def parse_decimal(value):

    if value is None:
        return ZERO

    text = (
        str(value)
        .replace("\xa0", "")
        .replace(" ", "")
        .replace(",", ".")
        .strip()
    )

    if not text:
        return ZERO

    try:
        return Decimal(text)

    except InvalidOperation:
        return ZERO


def parse_date(value):

    text = str(
        value or ""
    ).strip()

    formats = [
        "%d.%m.%Y %H:%M",
        "%d.%m.%Y %H:%M:%S",
        "%d.%m.%Y",
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M:%S",
    ]

    for fmt in formats:

        try:
            return datetime.strptime(
                text,
                fmt,
            ).date()

        except ValueError:
            pass

    raise ValueError(
        f"Не удалось распознать дату: {text!r}"
    )


def money(value):

    return f"{value:.2f}"


def quantity_text(value):

    if value == value.to_integral():

        return str(
            int(value)
        )

    return format(
        value.normalize(),
        "f",
    )


def require_files():

    required = [
        CHECKS_FILE,
        ITEMS_FILE,
        KKM_FILE,
    ]

    missing = [
        path
        for path in required
        if not os.path.exists(path)
    ]

    if missing:

        raise FileNotFoundError(
            "Не найдены необходимые файлы:\n"
            + "\n".join(
                missing
            )
        )


def get_latest_closed_date():

    dates = []

    with open(
        KKM_FILE,
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        reader = csv.DictReader(
            file
        )

        for row in reader:

            try:
                date = parse_date(
                    row.get(
                        "date"
                    )
                )

            except Exception:
                continue

            dates.append(
                date
            )

    if not dates:

        raise RuntimeError(
            "В kkm_daily.csv нет дат."
        )

    return max(
        dates
    )


def load_checks():

    by_day = defaultdict(
        lambda: {
            "sales_revenue":
                ZERO,

            "returns":
                ZERO,

            "checks":
                0,

            "return_checks":
                0,
        }
    )

    check_ids = set()

    dates = []

    unknown_types = defaultdict(
        int
    )

    with open(
        CHECKS_FILE,
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        reader = csv.DictReader(
            file
        )

        for row in reader:

            check_id = str(
                row.get(
                    "check_id",
                    "",
                )
            ).strip()

            if not check_id:
                continue

            if check_id in check_ids:

                raise RuntimeError(
                    "Дублируется check_id: "
                    f"{check_id}"
                )

            check_ids.add(
                check_id
            )

            date = parse_date(
                row.get(
                    "date"
                )
            )

            dates.append(
                date
            )

            check_type = str(
                row.get(
                    "type",
                    "",
                )
            ).strip()

            amount = parse_decimal(
                row.get(
                    "amount"
                )
            )

            if (
                check_type
                == SALE_CHECK_TYPE
            ):

                by_day[
                    date
                ][
                    "sales_revenue"
                ] += amount

                by_day[
                    date
                ][
                    "checks"
                ] += 1

            elif (
                check_type
                == RETURN_CHECK_TYPE
            ):

                by_day[
                    date
                ][
                    "returns"
                ] += amount

                by_day[
                    date
                ][
                    "return_checks"
                ] += 1

            else:

                unknown_types[
                    check_type
                ] += 1

    if not dates:

        raise RuntimeError(
            "checks_raw.csv пуст."
        )

    return (
        by_day,
        check_ids,
        min(
            dates
        ),
        max(
            dates
        ),
        dict(
            unknown_types
        ),
    )


def load_items():

    by_day = defaultdict(
        lambda: {
            "items":
                ZERO,

            "returned_items":
                ZERO,

            "item_rows":
                0,

            "return_item_rows":
                0,
        }
    )

    item_check_ids = set()

    unknown_types = defaultdict(
        int
    )

    with open(
        ITEMS_FILE,
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        reader = csv.DictReader(
            file
        )

        for row in reader:

            check_id = str(
                row.get(
                    "check_id",
                    "",
                )
            ).strip()

            if check_id:

                item_check_ids.add(
                    check_id
                )

            date = parse_date(
                row.get(
                    "date"
                )
            )

            check_type = str(
                row.get(
                    "check_type",
                    "",
                )
            ).strip()

            quantity = parse_decimal(
                row.get(
                    "quantity"
                )
            )

            if (
                check_type
                == SALE_CHECK_TYPE
            ):

                by_day[
                    date
                ][
                    "items"
                ] += quantity

                by_day[
                    date
                ][
                    "item_rows"
                ] += 1

            elif (
                check_type
                == RETURN_CHECK_TYPE
            ):

                by_day[
                    date
                ][
                    "returned_items"
                ] += quantity

                by_day[
                    date
                ][
                    "return_item_rows"
                ] += 1

            else:

                unknown_types[
                    check_type
                ] += 1

    return (
        by_day,
        item_check_ids,
        dict(
            unknown_types
        ),
    )


def build_rows():

    latest_closed = (
        get_latest_closed_date()
    )

    (
        checks_by_day,
        check_ids,
        first_check_date,
        latest_check_date,
        unknown_check_types,
    ) = load_checks()

    (
        items_by_day,
        item_check_ids,
        unknown_item_types,
    ) = load_items()

    missing_items = (
        check_ids
        - item_check_ids
    )

    extra_items = (
        item_check_ids
        - check_ids
    )

    if missing_items:

        raise RuntimeError(
            "Есть чеки без товарных строк: "
            f"{len(missing_items)}"
        )

    if extra_items:

        raise RuntimeError(
            "Есть товарные строки для "
            "неизвестных чеков: "
            f"{len(extra_items)}"
        )

    if latest_closed > latest_check_date:

        raise RuntimeError(
            "Последний закрытый день ККМ "
            "новее checks_raw.csv."
        )

    print()
    print("=" * 70)

    print(
        "ИСТОРИЧЕСКАЯ ДНЕВНАЯ "
        "АНАЛИТИКА ПО ЧЕКАМ"
    )

    print("=" * 70)

    print()

    print(
        "Первый чек:",
        first_check_date.strftime(
            "%d.%m.%Y"
        ),
    )

    print(
        "Последний чек в CRM:",
        latest_check_date.strftime(
            "%d.%m.%Y"
        ),
    )

    print(
        "Последний закрытый день:",
        latest_closed.strftime(
            "%d.%m.%Y"
        ),
    )

    print(
        "Чеков:",
        len(
            check_ids
        ),
    )

    print(
        "Чеков с товарами:",
        len(
            item_check_ids
        ),
    )

    if unknown_check_types:

        print(
            "Неизвестные типы чеков:",
            unknown_check_types,
        )

    if unknown_item_types:

        print(
            "Неизвестные типы "
            "товарных строк:",
            unknown_item_types,
        )

    output = []

    current_date = (
        first_check_date
    )

    updated_at = (
        datetime.now()
        .isoformat(
            timespec="seconds"
        )
    )

    while (
        current_date
        <= latest_closed
    ):

        check_row = (
            checks_by_day[
                current_date
            ]
        )

        item_row = (
            items_by_day[
                current_date
            ]
        )

        sales_revenue = (
            check_row[
                "sales_revenue"
            ]
        )

        returns = (
            check_row[
                "returns"
            ]
        )

        check_revenue_net = (
            sales_revenue
            - returns
        )

        checks = (
            check_row[
                "checks"
            ]
        )

        return_checks = (
            check_row[
                "return_checks"
            ]
        )

        items = (
            item_row[
                "items"
            ]
        )

        returned_items = (
            item_row[
                "returned_items"
            ]
        )

        item_rows = (
            item_row[
                "item_rows"
            ]
        )

        return_item_rows = (
            item_row[
                "return_item_rows"
            ]
        )

        if checks > 0:

            average_check = (
                check_revenue_net
                / Decimal(
                    checks
                )
            )

            ktch = (
                items
                / Decimal(
                    checks
                )
            )

        else:

            average_check = ZERO
            ktch = ZERO

        output.append(
            {
                "date":
                    current_date.strftime(
                        "%d.%m.%Y"
                    ),

                "sales_revenue":
                    money(
                        sales_revenue
                    ),

                "returns":
                    money(
                        -returns
                    ),

                "check_revenue_net":
                    money(
                        check_revenue_net
                    ),

                "checks":
                    str(
                        checks
                    ),

                "return_checks":
                    str(
                        return_checks
                    ),

                "items":
                    quantity_text(
                        items
                    ),

                "returned_items":
                    quantity_text(
                        returned_items
                    ),

                "item_rows":
                    str(
                        item_rows
                    ),

                "return_item_rows":
                    str(
                        return_item_rows
                    ),

                "average_check":
                    f"{average_check:.2f}",

                "ktch":
                    f"{ktch:.2f}",

                "data_scope":
                    "checks_and_items",

                "full_revenue_available":
                    "0",

                "source":
                    (
                        "checks_raw.csv"
                        "+check_items.csv"
                    ),

                "updated_at":
                    updated_at,
            }
        )

        current_date += timedelta(
            days=1
        )

    return output


def save_rows(rows):

    fieldnames = [
        "date",
        "sales_revenue",
        "returns",
        "check_revenue_net",
        "checks",
        "return_checks",
        "items",
        "returned_items",
        "item_rows",
        "return_item_rows",
        "average_check",
        "ktch",
        "data_scope",
        "full_revenue_available",
        "source",
        "updated_at",
    ]

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        writer.writerows(
            rows
        )


def verify(rows):

    if not rows:

        raise RuntimeError(
            "Историческая таблица пуста."
        )

    first = rows[0]
    last = rows[-1]

    total_checks = sum(
        int(
            row[
                "checks"
            ]
        )
        for row in rows
    )

    total_return_checks = sum(
        int(
            row[
                "return_checks"
            ]
        )
        for row in rows
    )

    print()
    print("=" * 70)
    print("КОНТРОЛЬ")
    print("=" * 70)

    print()

    print(
        "Строк:",
        len(
            rows
        ),
    )

    print(
        "Первая дата:",
        first[
            "date"
        ],
    )

    print(
        "Последняя дата:",
        last[
            "date"
        ],
    )

    print(
        "Продажных чеков:",
        total_checks,
    )

    print(
        "Возвратных чеков:",
        total_return_checks,
    )

    print()

    print(
        "Исторический слой содержит "
        "только точные чековые показатели."
    )

    print(
        "Яндекс, Купер, самовывоз и продажи "
        "без чека в него НЕ добавляются."
    )

    print(
        "Поэтому check_revenue_net нельзя "
        "автоматически называть полной "
        "выручкой магазина."
    )


def main():

    require_files()

    rows = build_rows()

    save_rows(
        rows
    )

    verify(
        rows
    )

    print()
    print("=" * 70)
    print("ГОТОВО")
    print("=" * 70)

    print()

    print(
        "Файл:",
        OUTPUT_FILE
    )


if __name__ == "__main__":

    main()