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

KKM_FILE = os.path.join(
    PROJECT_DIR,
    "kkm_daily.csv",
)

RETURNS_FILE = os.path.join(
    PROJECT_DIR,
    "returns_daily.csv",
)

SALES_SOURCES_FILE = os.path.join(
    PROJECT_DIR,
    "sales_sources_daily.csv",
)

SALES_MANUAL_FILE = os.path.join(
    PROJECT_DIR,
    "sales_manual.csv",
)

CHECKS_FILE = os.path.join(
    PROJECT_DIR,
    "checks_raw.csv",
)

ITEMS_FILE = os.path.join(
    PROJECT_DIR,
    "check_items.csv",
)

OUTPUT_FILE = os.path.join(
    PROJECT_DIR,
    "daily_sales.csv",
)


SALE_CHECK_TYPE = "Чек ККМ"
RETURN_CHECK_TYPE = "Возврат Чека ККМ"

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
        KKM_FILE,
        RETURNS_FILE,
        SALES_SOURCES_FILE,
        SALES_MANUAL_FILE,
        CHECKS_FILE,
        ITEMS_FILE,
    ]

    missing = [
        path
        for path in required
        if not os.path.exists(path)
    ]

    if missing:

        raise FileNotFoundError(
            "Не найдены необходимые файлы:\n"
            + "\n".join(missing)
        )


def load_kkm():

    rows = {}

    with open(
        KKM_FILE,
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        reader = csv.DictReader(file)

        for row in reader:

            try:
                date = parse_date(
                    row["date"]
                )

            except Exception:
                continue

            rows[date] = {
                "cash_net":
                    parse_decimal(
                        row.get("cash")
                    ),

                "card_net":
                    parse_decimal(
                        row.get("card")
                    ),

                "total_net":
                    parse_decimal(
                        row.get("total")
                    ),
            }

    if not rows:
        raise RuntimeError(
            "kkm_daily.csv пуст"
        )

    return rows


def load_returns():

    rows = {}

    with open(
        RETURNS_FILE,
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        reader = csv.DictReader(file)

        for row in reader:

            try:
                date = parse_date(
                    row["date"]
                )

            except Exception:
                continue

            rows[date] = {
                "cash_return":
                    parse_decimal(
                        row.get(
                            "cash_return"
                        )
                    ),

                "card_return":
                    parse_decimal(
                        row.get(
                            "card_return"
                        )
                    ),

                "total_return":
                    parse_decimal(
                        row.get(
                            "total_return"
                        )
                    ),
            }

    return rows


def load_sales_sources():

    rows = {}

    with open(
        SALES_SOURCES_FILE,
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        reader = csv.DictReader(file)

        for row in reader:

            try:
                date = parse_date(
                    row["date"]
                )

            except Exception:
                continue

            rows[date] = {
                "self_pickup":
                    parse_decimal(
                        row.get(
                            "self_pickup"
                        )
                    ),

                "yandex_food":
                    parse_decimal(
                        row.get(
                            "yandex_food"
                        )
                    ),

                "kuper":
                    parse_decimal(
                        row.get(
                            "kuper"
                        )
                    ),

                "external_total":
                    parse_decimal(
                        row.get(
                            "external_total"
                        )
                    ),

                "yandex_orders":
                    int(
                        parse_decimal(
                            row.get(
                                "yandex_orders"
                            )
                        )
                    ),

                "kuper_orders":
                    int(
                        parse_decimal(
                            row.get(
                                "kuper_orders"
                            )
                        )
                    ),

                "other_external_orders":
                    int(
                        parse_decimal(
                            row.get(
                                "other_external_orders"
                            )
                        )
                    ),

                "external_orders":
                    int(
                        parse_decimal(
                            row.get(
                                "external_orders"
                            )
                        )
                    ),
            }

    return rows


def load_manual_sales():

    rows = {}

    with open(
        SALES_MANUAL_FILE,
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        reader = csv.DictReader(file)

        for row in reader:

            try:
                date = parse_date(
                    row["date"]
                )

            except Exception:
                continue

            rows[date] = {
                "no_receipt":
                    parse_decimal(
                        row.get(
                            "no_receipt"
                        )
                    )
            }

    return rows


def load_checks():

    sale_checks = defaultdict(set)
    return_checks = defaultdict(set)

    dates = []

    with open(
        CHECKS_FILE,
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        reader = csv.DictReader(file)

        for row in reader:

            try:
                date = parse_date(
                    row["date"]
                )

            except Exception:
                continue

            dates.append(date)

            check_id = (
                row.get("check_id")
                or row.get("number")
                or ""
            ).strip()

            check_type = (
                row.get("type")
                or ""
            ).strip()

            if check_type == SALE_CHECK_TYPE:

                sale_checks[
                    date
                ].add(
                    check_id
                )

            elif check_type == RETURN_CHECK_TYPE:

                return_checks[
                    date
                ].add(
                    check_id
                )

    max_date = (
        max(dates)
        if dates
        else None
    )

    return (
        sale_checks,
        return_checks,
        max_date,
    )


def load_items():

    sale_quantity = defaultdict(
        lambda: ZERO
    )

    sale_rows = defaultdict(int)

    return_quantity = defaultdict(
        lambda: ZERO
    )

    dates = []

    with open(
        ITEMS_FILE,
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        reader = csv.DictReader(file)

        for row in reader:

            try:
                date = parse_date(
                    row["date"]
                )

            except Exception:
                continue

            dates.append(date)

            check_type = (
                row.get(
                    "check_type"
                )
                or ""
            ).strip()

            quantity = parse_decimal(
                row.get(
                    "quantity"
                )
            )

            if check_type == SALE_CHECK_TYPE:

                sale_quantity[
                    date
                ] += quantity

                sale_rows[
                    date
                ] += 1

            elif check_type == RETURN_CHECK_TYPE:

                return_quantity[
                    date
                ] += quantity

    max_date = (
        max(dates)
        if dates
        else None
    )

    return (
        sale_quantity,
        sale_rows,
        return_quantity,
        max_date,
    )


def build_daily_rows():

    kkm = load_kkm()
    returns = load_returns()
    sources = load_sales_sources()
    manual_sales = load_manual_sales()

    (
        sale_checks,
        return_checks,
        checks_max_date,
    ) = load_checks()

    (
        sale_quantity,
        sale_rows,
        return_quantity,
        items_max_date,
    ) = load_items()

    first_date = min(kkm)
    latest_closed = max(kkm)

    print()

    print(
        "Первый день ККМ:",
        first_date.strftime(
            "%d.%m.%Y"
        ),
    )

    print(
        "Последний закрытый день ККМ:",
        latest_closed.strftime(
            "%d.%m.%Y"
        ),
    )

    if checks_max_date:

        print(
            "Последний день checks_raw:",
            checks_max_date.strftime(
                "%d.%m.%Y"
            ),
        )

    if items_max_date:

        print(
            "Последний день check_items:",
            items_max_date.strftime(
                "%d.%m.%Y"
            ),
        )

    if (
        checks_max_date
        and checks_max_date < latest_closed
    ):

        print()
        print("ВНИМАНИЕ:")
        print(
            "checks_raw.csv отстаёт от ККМ."
        )

    if (
        items_max_date
        and items_max_date < latest_closed
    ):

        print()
        print("ВНИМАНИЕ:")

        print(
            "check_items.csv отстаёт от ККМ."
        )

        print(
            "Для дней после "
            f"{items_max_date:%d.%m.%Y} "
            "items и КТЧ будут оставлены пустыми."
        )

    output = []

    current_date = first_date

    updated_at = (
        datetime.now()
        .isoformat(
            timespec="seconds"
        )
    )

    while current_date <= latest_closed:

        kkm_row = kkm.get(
            current_date,
            {},
        )

        return_row = returns.get(
            current_date,
            {},
        )

        source_row = sources.get(
            current_date,
            {},
        )

        manual_row = manual_sales.get(
            current_date,
            {},
        )

        # ----------------------------------------------------
        # ККМ отдаёт уже НЕТТО после возвратов.
        # ----------------------------------------------------

        kkm_cash_net = parse_decimal(
            kkm_row.get(
                "cash_net"
            )
        )

        kkm_card_net = parse_decimal(
            kkm_row.get(
                "card_net"
            )
        )

        kkm_total_net = (
            kkm_cash_net
            + kkm_card_net
        )

        cash_return = parse_decimal(
            return_row.get(
                "cash_return"
            )
        )

        card_return = parse_decimal(
            return_row.get(
                "card_return"
            )
        )

        total_return = parse_decimal(
            return_row.get(
                "total_return"
            )
        )

        # ----------------------------------------------------
        # Для листа ПО ЧИСЛАМ нам нужны продажи ДО возврата,
        # потому что возвраты стоят отдельными строками.
        #
        # Например 12.08:
        # ККМ безнал нетто = 16515.27
        # возврат = -144
        # продажа до возврата = 16659.27
        # ----------------------------------------------------

        cash = (
            kkm_cash_net
            - cash_return
        )

        card = (
            kkm_card_net
            - card_return
        )

        check_revenue = (
            cash
            + card
        )

        check_revenue_net = (
            check_revenue
            + total_return
        )

        # Дополнительная страховка:
        # это должно совпасть с ККМ нетто.

        kkm_difference = (
            check_revenue_net
            - kkm_total_net
        )

        if abs(
            kkm_difference
        ) > Decimal("0.01"):

            print(
                "ВНИМАНИЕ:",
                current_date.strftime(
                    "%d.%m.%Y"
                ),
                "нетто после возвратов "
                "не совпало с ККМ:",
                money(
                    kkm_difference
                ),
            )

        checks_complete = (
            checks_max_date is not None
            and current_date
            <= checks_max_date
        )

        items_complete = (
            items_max_date is not None
            and current_date
            <= items_max_date
        )

        if checks_complete:

            checks = len(
                sale_checks[
                    current_date
                ]
            )

            returns_count = len(
                return_checks[
                    current_date
                ]
            )

        else:

            checks = None
            returns_count = None

        if items_complete:

            items = (
                sale_quantity[
                    current_date
                ]
            )

            item_rows = (
                sale_rows[
                    current_date
                ]
            )

            returned_items = (
                return_quantity[
                    current_date
                ]
            )

        else:

            items = None
            item_rows = None
            returned_items = None

        # Средний чек считаем по НЕТТО-выручке чеков,
        # как в исходной таблице.

        if (
            checks is not None
            and checks > 0
        ):

            average_check = (
                check_revenue_net
                / Decimal(
                    checks
                )
            )

        elif checks == 0:

            average_check = ZERO

        else:

            average_check = None

        if (
            checks is not None
            and checks > 0
            and items is not None
        ):

            ktch = (
                items
                / Decimal(
                    checks
                )
            )

        elif (
            checks == 0
            and items is not None
        ):

            ktch = ZERO

        else:

            ktch = None

        self_pickup = parse_decimal(
            source_row.get(
                "self_pickup"
            )
        )

        yandex = parse_decimal(
            source_row.get(
                "yandex_food"
            )
        )

        kuper = parse_decimal(
            source_row.get(
                "kuper"
            )
        )

        external_total = parse_decimal(
            source_row.get(
                "external_total"
            )
        )

        yandex_orders = int(
            source_row.get(
                "yandex_orders",
                0,
            )
            or 0
        )

        kuper_orders = int(
            source_row.get(
                "kuper_orders",
                0,
            )
            or 0
        )

        other_external_orders = int(
            source_row.get(
                "other_external_orders",
                0,
            )
            or 0
        )

        external_orders = int(
            source_row.get(
                "external_orders",
                0,
            )
            or 0
        )

        # Здесь возврат уже учтён в check_revenue_net.
        # Второй раз его НЕ вычитаем.

        automated_revenue = (
            check_revenue_net
            + self_pickup
            + external_total
        )

        no_receipt = parse_decimal(
            manual_row.get(
                "no_receipt"
            )
        )

        total_revenue = (
            automated_revenue
            + no_receipt
        )

        output.append(
            {
                "date":
                    current_date.strftime(
                        "%d.%m.%Y"
                    ),

                "cash":
                    money(
                        cash
                    ),

                "card":
                    money(
                        card
                    ),

                "check_revenue":
                    money(
                        check_revenue
                    ),

                "cash_return":
                    money(
                        cash_return
                    ),

                "card_return":
                    money(
                        card_return
                    ),

                "total_return":
                    money(
                        total_return
                    ),

                "check_revenue_net":
                    money(
                        check_revenue_net
                    ),

                "kkm_cash_net":
                    money(
                        kkm_cash_net
                    ),

                "kkm_card_net":
                    money(
                        kkm_card_net
                    ),

                "kkm_total_net":
                    money(
                        kkm_total_net
                    ),

                "checks":
                    (
                        str(checks)
                        if checks is not None
                        else ""
                    ),

                "return_checks":
                    (
                        str(
                            returns_count
                        )
                        if returns_count
                        is not None
                        else ""
                    ),

                "items":
                    (
                        quantity_text(
                            items
                        )
                        if items is not None
                        else ""
                    ),

                "item_rows":
                    (
                        str(
                            item_rows
                        )
                        if item_rows
                        is not None
                        else ""
                    ),

                "returned_items":
                    (
                        quantity_text(
                            returned_items
                        )
                        if returned_items
                        is not None
                        else ""
                    ),

                "ktch":
                    (
                        f"{ktch:.2f}"
                        if ktch is not None
                        else ""
                    ),

                "average_check":
                    (
                        f"{average_check:.2f}"
                        if average_check is not None
                        else ""
                    ),

                "self_pickup":
                    money(
                        self_pickup
                    ),

                "yandex_food":
                    money(
                        yandex
                    ),

                "kuper":
                    money(
                        kuper
                    ),

                "external_total":
                    money(
                        external_total
                    ),

                "yandex_orders":
                    str(
                        yandex_orders
                    ),

                "kuper_orders":
                    str(
                        kuper_orders
                    ),

                "other_external_orders":
                    str(
                        other_external_orders
                    ),

                "external_orders":
                    str(
                        external_orders
                    ),

                "automated_revenue":
                    money(
                        automated_revenue
                    ),

                "no_receipt":
                    money(
                        no_receipt
                    ),

                "total_revenue":
                    money(
                        total_revenue
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
        "cash",
        "card",
        "check_revenue",
        "cash_return",
        "card_return",
        "total_return",
        "check_revenue_net",
        "kkm_cash_net",
        "kkm_card_net",
        "kkm_total_net",
        "checks",
        "return_checks",
        "items",
        "item_rows",
        "returned_items",
        "ktch",
        "average_check",
        "self_pickup",
        "yandex_food",
        "kuper",
        "external_total",
        "yandex_orders",
        "kuper_orders",
        "other_external_orders",
        "external_orders",
        "automated_revenue",
        "no_receipt",
        "total_revenue",
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


def rows_for_month(
    rows,
    year,
    month,
):

    result = []

    for row in rows:

        date = parse_date(
            row["date"]
        )

        if (
            date.year == year
            and date.month == month
        ):
            result.append(
                row
            )

    return result


def sum_money(
    rows,
    field,
):

    return sum(
        (
            parse_decimal(
                row.get(
                    field
                )
            )
            for row in rows
        ),
        ZERO,
    )


def sum_int(
    rows,
    field,
):

    total = 0

    for row in rows:

        value = (
            row.get(
                field
            )
            or ""
        ).strip()

        if not value:
            continue

        total += int(
            Decimal(
                value
            )
        )

    return total


def sum_quantity(
    rows,
    field,
):

    return sum(
        (
            parse_decimal(
                row.get(
                    field
                )
            )
            for row in rows
            if (
                row.get(
                    field
                )
                or ""
            ).strip()
        ),
        ZERO,
    )


def verify_july(rows):

    rows = rows_for_month(
        rows,
        2026,
        7,
    )

    if not rows:

        print()
        print(
            "Нет данных июля 2026."
        )
        return

    cash = sum_money(
        rows,
        "cash",
    )

    card = sum_money(
        rows,
        "card",
    )

    check_revenue = sum_money(
        rows,
        "check_revenue",
    )

    total_return = sum_money(
        rows,
        "total_return",
    )

    check_revenue_net = sum_money(
        rows,
        "check_revenue_net",
    )

    checks = sum_int(
        rows,
        "checks",
    )

    items = sum_quantity(
        rows,
        "items",
    )

    yandex = sum_money(
        rows,
        "yandex_food",
    )

    kuper = sum_money(
        rows,
        "kuper",
    )

    external_total = sum_money(
        rows,
        "external_total",
    )

    external_orders = sum_int(
        rows,
        "external_orders",
    )

    automated_revenue = sum_money(
        rows,
        "automated_revenue",
    )

    no_receipt = sum_money(
        rows,
        "no_receipt",
    )

    total_revenue = sum_money(
        rows,
        "total_revenue",
    )

    if checks:

        ktch = (
            items
            / Decimal(
                checks
            )
        )

        average_check = (
            check_revenue_net
            / Decimal(
                checks
            )
        )

    else:

        ktch = ZERO
        average_check = ZERO

    print()
    print("=" * 70)
    print("КОНТРОЛЬ ИЮЛЯ 2026")
    print("=" * 70)

    print(
        "Наличные:",
        f"{cash:,.2f}",
        "| эталон 106,832.00",
    )

    print(
        "Карта:",
        f"{card:,.2f}",
        "| эталон 567,893.41",
    )

    print(
        "Продажи по чекам:",
        f"{check_revenue:,.2f}",
        "| эталон 674,725.41",
    )

    print(
        "Возвраты:",
        f"{total_return:,.2f}",
        "| эталон 0.00",
    )

    print(
        "Чеки нетто:",
        f"{check_revenue_net:,.2f}",
        "| эталон 674,725.41",
    )

    print(
        "Количество чеков:",
        checks,
        "| эталон 839",
    )

    print(
        "Количество товаров:",
        quantity_text(
            items
        ),
        "| эталон 2949",
    )

    print(
        "КТЧ:",
        f"{ktch:.2f}",
        "| эталон 3.51",
    )

    print(
        "Средний чек:",
        f"{average_check:.2f}",
        "| эталон 804.20",
    )

    print(
        "Яндекс:",
        f"{yandex:,.2f}",
        "| эталон 92,229.00",
    )

    print(
        "Купер:",
        f"{kuper:,.2f}",
        "| эталон 2,533.00",
    )

    print(
        "Внешние продажи:",
        f"{external_total:,.2f}",
        "| эталон 94,762.00",
    )

    print(
        "Внешних заказов:",
        external_orders,
        "| эталон 50",
    )

    print(
        "Автоматическая выручка:",
        f"{automated_revenue:,.2f}",
        "| эталон CRM PL 769,487.41",
    )

    print(
        "Продажи без чека:",
        f"{no_receipt:,.2f}",
        "| эталон 2,885.00",
    )

    print(
        "Полная выручка:",
        f"{total_revenue:,.2f}",
        "| эталон 772,372.41",
    )

    checks_ok = [
        cash == Decimal("106832.00"),
        card == Decimal("567893.41"),
        check_revenue == Decimal("674725.41"),
        total_return == ZERO,
        check_revenue_net == Decimal("674725.41"),
        checks == 839,
        items == Decimal("2949"),
        round(ktch, 2) == Decimal("3.51"),
        round(
            average_check,
            2,
        ) == Decimal("804.20"),
        yandex == Decimal("92229.00"),
        kuper == Decimal("2533.00"),
        external_total == Decimal("94762.00"),
        external_orders == 50,
        automated_revenue
        == Decimal("769487.41"),
        no_receipt
        == Decimal("2885.00"),
        total_revenue
        == Decimal("772372.41"),
    ]

    print()

    if all(checks_ok):

        print(
            "ИЮЛЬ: ВСЕ ПОКАЗАТЕЛИ СОШЛИСЬ"
        )

    else:

        print(
            "ИЮЛЬ: ЕСТЬ РАСХОЖДЕНИЕ"
        )


def verify_august_12(rows):

    target = None

    for row in rows:

        if (
            row["date"]
            == "12.08.2026"
        ):
            target = row
            break

    if target is None:
        return

    print()
    print("=" * 70)
    print("КОНТРОЛЬ 12.08.2026")
    print("=" * 70)

    print(
        "Наличные до возвратов:",
        target["cash"],
        "| Excel 3461.00",
    )

    print(
        "Безнал до возвратов:",
        target["card"],
        "| Excel 16659.27",
    )

    print(
        "Возврат безнал:",
        target["card_return"],
        "| Excel -144.00",
    )

    print(
        "ККМ нетто:",
        target["kkm_total_net"],
        "| эталон 19976.27",
    )

    print(
        "Яндекс:",
        target["yandex_food"],
        "| Excel 694.00",
    )

    print(
        "ИТОГО:",
        target["total_revenue"],
        "| Excel 20670.27",
    )

    ok = (
        parse_decimal(
            target["cash"]
        )
        == Decimal("3461.00")

        and parse_decimal(
            target["card"]
        )
        == Decimal("16659.27")

        and parse_decimal(
            target["card_return"]
        )
        == Decimal("-144.00")

        and parse_decimal(
            target["kkm_total_net"]
        )
        == Decimal("19976.27")

        and parse_decimal(
            target["yandex_food"]
        )
        == Decimal("694.00")

        and parse_decimal(
            target["total_revenue"]
        )
        == Decimal("20670.27")
    )

    print()

    if ok:

        print(
            "12.08: ВОЗВРАТ УЧТЁН ПРАВИЛЬНО"
        )

    else:

        print(
            "12.08: ЕСТЬ РАСХОЖДЕНИЕ"
        )


def main():

    print()
    print("=" * 70)

    print(
        "СБОРКА ЕДИНОЙ ДНЕВНОЙ "
        "ТАБЛИЦЫ ПРОДАЖ"
    )

    print("=" * 70)

    require_files()

    rows = build_daily_rows()

    save_rows(
        rows
    )

    print()

    print(
        "Строк создано:",
        len(rows),
    )

    print(
        "Файл:",
        OUTPUT_FILE,
    )

    verify_july(
        rows
    )

    verify_august_12(
        rows
    )

    print()
    print("=" * 70)
    print("ГОТОВО")
    print("=" * 70)


if __name__ == "__main__":
    main()