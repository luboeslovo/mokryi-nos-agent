import csv
import os
from collections import defaultdict
from datetime import datetime, timedelta
from urllib.parse import urlencode

from playwright.sync_api import sync_playwright


PROJECT_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

AUTH_FILE = os.path.join(
    PROJECT_DIR,
    "auth.json",
)

KKM_FILE = os.path.join(
    PROJECT_DIR,
    "kkm_daily.csv",
)

OUTPUT_FILE = os.path.join(
    PROJECT_DIR,
    "sales_sources_daily.csv",
)

SALES_REPORT_URL = (
    "https://it.mokryinos.ru/"
    "reports/sellSum/index"
)

EXTERNAL_ORDERS_URL = (
    "https://it.mokryinos.ru/"
    "delivery/externalOrderFranchisee/index"
)

EXTERNAL_DATE_FILTER = (
    "app_modules_delivery_models_"
    "ExternalOrderForm[createdAt]"
)

EXTERNAL_PAGE_PARAM = (
    "app_modules_delivery_models_"
    "ExternalOrderForm_page"
)

# Источник №2 пока используем только
# для собственных интернет-заказов Мокрого носа.
SELF_PICKUP_SOURCE_ID = "2"

PAGE_SIZE = 50


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

    if not text:
        return 0.0

    try:
        return float(text)

    except ValueError:
        return 0.0


def get_latest_closed_date():
    if not os.path.exists(
        KKM_FILE
    ):
        return (
            datetime.now()
            - timedelta(days=1)
        ).date()

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
                date = datetime.strptime(
                    row["date"],
                    "%d.%m.%Y",
                ).date()

                dates.append(
                    date
                )

            except Exception:
                pass

    if not dates:
        return (
            datetime.now()
            - timedelta(days=1)
        ).date()

    return max(
        dates
    )


def get_total_row_values(page):
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

        values = [
            clean(
                cells
                .nth(j)
                .text_content()
            )
            for j in range(
                cells.count()
            )
        ]

        if not values:
            continue

        if values[0] != "Итого":
            continue

        return values

    return None


def fetch_self_pickup_amounts(
    page,
    start_date,
    end_date,
):
    date_range = (
        start_date.strftime(
            "%d.%m.%Y"
        )
        + " - "
        + end_date.strftime(
            "%d.%m.%Y"
        )
    )

    params = [
        (
            "showReport",
            "1",
        ),
        (
            "filters[dateRange]",
            date_range,
        ),
        (
            "filters[reportMode]",
            "1",
        ),
        (
            "filters[periodicity]",
            "2",
        ),
        (
            "filters[reportGroupBy]",
            "organizations",
        ),
        (
            "filters[salesSource][]",
            SELF_PICKUP_SOURCE_ID,
        ),
        (
            "filters[reportResultBy]",
            "amount",
        ),
    ]

    target_url = (
        SALES_REPORT_URL
        + "?"
        + urlencode(params)
    )

    page.goto(
        target_url,
        wait_until="networkidle",
        timeout=60000,
    )

    if "/login" in page.url:
        raise RuntimeError(
            "CRM отправила на login"
        )

    day_count = (
        end_date
        - start_date
    ).days + 1

    values = get_total_row_values(
        page
    )

    if values is None:
        return [
            0.0
            for _ in range(
                day_count
            )
        ]

    result = [
        parse_money(value)
        for value in values[
            1:
            1 + day_count
        ]
    ]

    while len(result) < day_count:
        result.append(
            0.0
        )

    return result


def build_external_orders_url(
    start_date,
    end_date,
    page_number,
):
    # В CRM обнаружен баг фильтра createdAt:
    # при конечной дате 17.08 заказ 17.08 в 20:27
    # не попадал в выдачу.
    #
    # Поэтому серверу запрашиваем один дополнительный день,
    # а реальную границу периода применяем локально ниже.
    query_end_date = (
        end_date
        + timedelta(days=1)
    )

    date_range = (
        start_date.strftime(
            "%d.%m.%Y"
        )
        + " - "
        + query_end_date.strftime(
            "%d.%m.%Y"
        )
    )

    params = [
        (
            EXTERNAL_DATE_FILTER,
            date_range,
        )
    ]

    if page_number > 1:
        params.append(
            (
                EXTERNAL_PAGE_PARAM,
                str(page_number),
            )
        )

    return (
        EXTERNAL_ORDERS_URL
        + "?"
        + urlencode(params)
    )


def parse_external_order_rows(
    page,
):
    result = []

    rows = page.locator(
        "table tbody tr"
    )

    for i in range(
        rows.count()
    ):
        cells = (
            rows
            .nth(i)
            .locator("td")
        )

        values = [
            clean(
                cells
                .nth(j)
                .text_content()
            )
            for j in range(
                cells.count()
            )
        ]

        if (
            len(values) >= 8
            and not values[0]
        ):
            values = values[1:]

        if len(values) < 7:
            continue

        try:
            order_datetime = (
                datetime.strptime(
                    values[0],
                    "%d.%m.%Y %H:%M",
                )
            )

        except ValueError:
            continue

        result.append(
            {
                "datetime":
                    order_datetime,

                "date":
                    order_datetime.date(),

                "platform":
                    values[1],

                "number":
                    values[2],

                "status":
                    values[3],

                "delivery_type":
                    values[4],

                "branch":
                    values[5],

                "amount":
                    parse_money(
                        values[6]
                    ),
            }
        )

    return result


def classify_platform(
    platform,
):
    value = (
        clean(platform)
        .lower()
    )

    if "купер" in value:
        return "kuper"

    if (
        "яндекс" in value
        or "delivery club" in value
    ):
        return "yandex_food"

    return "other"


def fetch_external_orders(
    page,
    start_date,
    end_date,
):
    all_orders = []
    seen_numbers = set()
    previous_page_numbers = None

    for page_number in range(
        1,
        101,
    ):
        target_url = (
            build_external_orders_url(
                start_date,
                end_date,
                page_number,
            )
        )

        page.goto(
            target_url,
            wait_until="networkidle",
            timeout=60000,
        )

        if "/login" in page.url:
            raise RuntimeError(
                "CRM отправила на login"
            )

        page_rows = (
            parse_external_order_rows(
                page
            )
        )

        if not page_rows:
            break

        page_numbers = tuple(
            order["number"]
            for order in page_rows
        )

        if (
            previous_page_numbers is not None
            and page_numbers
            == previous_page_numbers
        ):
            break

        previous_page_numbers = (
            page_numbers
        )

        new_rows = []

        for order in page_rows:
            # Это реальная граница периода.
            # Дополнительный день нужен только
            # для обхода бага серверного фильтра CRM.
            if not (
                start_date
                <= order["date"]
                <= end_date
            ):
                continue

            number = (
                order["number"]
            )

            if number in seen_numbers:
                continue

            seen_numbers.add(
                number
            )

            new_rows.append(
                order
            )

        all_orders.extend(
            new_rows
        )

        if (
            len(page_rows)
            < PAGE_SIZE
        ):
            break

    return all_orders


def aggregate_orders(
    orders,
):
    daily = defaultdict(
        lambda: {
            "yandex_orders": 0,
            "kuper_orders": 0,
            "other_external_orders": 0,
            "external_orders": 0,

            "yandex_sum": 0.0,
            "kuper_sum": 0.0,
            "other_external_sum": 0.0,
            "external_sum": 0.0,
        }
    )

    delivered = []
    cancelled = []
    ignored = []

    for order in orders:
        status = (
            order["status"]
        )

        if status == "Отменен":
            cancelled.append(
                order
            )
            continue

        if status != "Доставлен":
            ignored.append(
                order
            )
            continue

        delivered.append(
            order
        )

        day = (
            order["date"]
        )

        amount = (
            order["amount"]
        )

        platform = (
            classify_platform(
                order["platform"]
            )
        )

        daily[
            day
        ][
            "external_orders"
        ] += 1

        daily[
            day
        ][
            "external_sum"
        ] += amount

        if platform == "yandex_food":
            daily[
                day
            ][
                "yandex_orders"
            ] += 1

            daily[
                day
            ][
                "yandex_sum"
            ] += amount

        elif platform == "kuper":
            daily[
                day
            ][
                "kuper_orders"
            ] += 1

            daily[
                day
            ][
                "kuper_sum"
            ] += amount

        else:
            daily[
                day
            ][
                "other_external_orders"
            ] += 1

            daily[
                day
            ][
                "other_external_sum"
            ] += amount

    return (
        daily,
        delivered,
        cancelled,
        ignored,
    )


def load_existing():
    result = {}

    if not os.path.exists(
        OUTPUT_FILE
    ):
        return result

    with open(
        OUTPUT_FILE,
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        reader = csv.DictReader(
            file
        )

        for row in reader:
            date_text = (
                row.get(
                    "date",
                    ""
                )
            )

            if not date_text:
                continue

            result[
                date_text
            ] = row

    return result


def remove_period_rows(
    rows,
    start_date,
    end_date,
):
    keys = []

    for key in rows:
        try:
            date = (
                datetime.strptime(
                    key,
                    "%d.%m.%Y",
                )
                .date()
            )

        except ValueError:
            continue

        if (
            start_date
            <= date
            <= end_date
        ):
            keys.append(
                key
            )

    for key in keys:
        del rows[key]


def save_rows(rows):
    fieldnames = [
        "date",
        "self_pickup",
        "yandex_food",
        "kuper",
        "external_total",
        "yandex_orders",
        "kuper_orders",
        "other_external_orders",
        "external_orders",
        "updated_at",
    ]

    ordered = sorted(
        rows.values(),
        key=lambda row:
            datetime.strptime(
                row["date"],
                "%d.%m.%Y",
            )
    )

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

        for row in ordered:
            writer.writerow(
                {
                    field:
                        row.get(
                            field,
                            ""
                        )
                    for field
                    in fieldnames
                }
            )


def update_period(
    page,
    rows,
    year,
    month,
    end_day,
):
    start_date = (
        datetime(
            year,
            month,
            1,
        )
        .date()
    )

    end_date = (
        datetime(
            year,
            month,
            end_day,
        )
        .date()
    )

    print()
    print("=" * 70)

    print(
        f"{start_date:%d.%m.%Y}"
        f" — "
        f"{end_date:%d.%m.%Y}"
    )

    print("=" * 70)

    print()
    print(
        "Получаю собственные заказы МН..."
    )

    self_pickup_values = (
        fetch_self_pickup_amounts(
            page,
            start_date,
            end_date,
        )
    )

    print(
        "self_pickup:",
        f"{sum(self_pickup_values):,.2f} ₽",
    )

    print()
    print(
        "Получаю внешние заказы..."
    )

    orders = (
        fetch_external_orders(
            page,
            start_date,
            end_date,
        )
    )

    (
        daily_orders,
        delivered,
        cancelled,
        ignored,
    ) = (
        aggregate_orders(
            orders
        )
    )

    yandex_orders = [
        order
        for order in delivered
        if classify_platform(
            order["platform"]
        ) == "yandex_food"
    ]

    kuper_orders = [
        order
        for order in delivered
        if classify_platform(
            order["platform"]
        ) == "kuper"
    ]

    other_orders = [
        order
        for order in delivered
        if classify_platform(
            order["platform"]
        ) == "other"
    ]

    yandex_sum = sum(
        order["amount"]
        for order in yandex_orders
    )

    kuper_sum = sum(
        order["amount"]
        for order in kuper_orders
    )

    other_sum = sum(
        order["amount"]
        for order in other_orders
    )

    print()
    print(
        "Всего записей:",
        len(orders),
    )

    print(
        "Доставлено:",
        len(delivered),
    )

    print(
        "Отменено:",
        len(cancelled),
    )

    print(
        "Другие статусы:",
        len(ignored),
    )

    print()
    print("Яндекс:")

    print(
        "  заказов:",
        len(yandex_orders),
    )

    print(
        "  сумма:",
        f"{yandex_sum:,.2f} ₽",
    )

    print("Купер:")

    print(
        "  заказов:",
        len(kuper_orders),
    )

    print(
        "  сумма:",
        f"{kuper_sum:,.2f} ₽",
    )

    if other_orders:
        print()
        print(
            "ВНИМАНИЕ: найдены другие платформы:"
        )

        for order in other_orders:
            print(
                "-",
                order["platform"],
                order["number"],
                f"{order['amount']:.2f}",
            )

        print(
            "Сумма других платформ:",
            f"{other_sum:,.2f} ₽",
        )

    remove_period_rows(
        rows,
        start_date,
        end_date,
    )

    current_date = (
        start_date
    )

    index = 0

    updated_at = (
        datetime.now()
        .isoformat(
            timespec="seconds"
        )
    )

    while (
        current_date
        <= end_date
    ):
        info = (
            daily_orders[
                current_date
            ]
        )

        yandex = round(
            info[
                "yandex_sum"
            ],
            2,
        )

        kuper = round(
            info[
                "kuper_sum"
            ],
            2,
        )

        self_pickup = round(
            self_pickup_values[
                index
            ],
            2,
        )

        date_text = (
            current_date.strftime(
                "%d.%m.%Y"
            )
        )

        rows[
            date_text
        ] = {
            "date":
                date_text,

            "self_pickup":
                f"{self_pickup:.2f}",

            "yandex_food":
                f"{yandex:.2f}",

            "kuper":
                f"{kuper:.2f}",

            "external_total":
                f"{yandex + kuper:.2f}",

            "yandex_orders":
                str(
                    info[
                        "yandex_orders"
                    ]
                ),

            "kuper_orders":
                str(
                    info[
                        "kuper_orders"
                    ]
                ),

            "other_external_orders":
                str(
                    info[
                        "other_external_orders"
                    ]
                ),

            "external_orders":
                str(
                    info[
                        "external_orders"
                    ]
                ),

            "updated_at":
                updated_at,
        }

        current_date += (
            timedelta(
                days=1
            )
        )

        index += 1

    print()
    print(
        "Строк периода обновлено:",
        (
            end_date
            - start_date
        ).days + 1,
    )


def verify_july(
    rows,
):
    july_rows = []

    for row in rows.values():
        try:
            date = (
                datetime.strptime(
                    row["date"],
                    "%d.%m.%Y",
                )
                .date()
            )

        except Exception:
            continue

        if (
            date.year == 2026
            and date.month == 7
        ):
            july_rows.append(
                row
            )

    yandex_sum = sum(
        float(
            row.get(
                "yandex_food",
                0
            )
            or 0
        )
        for row in july_rows
    )

    kuper_sum = sum(
        float(
            row.get(
                "kuper",
                0
            )
            or 0
        )
        for row in july_rows
    )

    yandex_count = sum(
        int(
            row.get(
                "yandex_orders",
                0
            )
            or 0
        )
        for row in july_rows
    )

    kuper_count = sum(
        int(
            row.get(
                "kuper_orders",
                0
            )
            or 0
        )
        for row in july_rows
    )

    external_count = sum(
        int(
            row.get(
                "external_orders",
                0
            )
            or 0
        )
        for row in july_rows
    )

    print()
    print("=" * 70)
    print(
        "КОНТРОЛЬ ИЮЛЯ 2026"
    )
    print("=" * 70)

    print(
        "Яндекс сумма:",
        f"{yandex_sum:,.2f}",
        "| эталон 92,229.00",
    )

    print(
        "Купер сумма:",
        f"{kuper_sum:,.2f}",
        "| эталон 2,533.00",
    )

    print(
        "Внешние всего:",
        f"{yandex_sum + kuper_sum:,.2f}",
        "| эталон 94,762.00",
    )

    print(
        "Яндекс заказов:",
        yandex_count,
        "| эталон 49",
    )

    print(
        "Купер заказов:",
        kuper_count,
        "| эталон 1",
    )

    print(
        "Всего заказов:",
        external_count,
        "| эталон 50",
    )

    checks = [
        abs(
            yandex_sum
            - 92229.00
        ) < 0.01,

        abs(
            kuper_sum
            - 2533.00
        ) < 0.01,

        yandex_count == 49,

        kuper_count == 1,

        external_count == 50,
    ]

    print()

    if all(checks):
        print(
            "ИЮЛЬ: ПОЛНОСТЬЮ СОШЁЛСЯ"
        )

    else:
        print(
            "ИЮЛЬ: ЕСТЬ РАСХОЖДЕНИЕ"
        )


def main():
    print()
    print("=" * 70)

    print(
        "СИНХРОНИЗАЦИЯ "
        "ДНЕВНЫХ КАНАЛОВ ПРОДАЖ"
    )

    print("=" * 70)

    latest_closed = (
        get_latest_closed_date()
    )

    print()
    print(
        "Последний закрытый день ККМ:",
        latest_closed.strftime(
            "%d.%m.%Y"
        ),
    )

    rows = (
        load_existing()
    )

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True
        )

        context = browser.new_context(
            storage_state=AUTH_FILE
        )

        page = (
            context.new_page()
        )

        # Контрольный июль.
        update_period(
            page,
            rows,
            2026,
            7,
            31,
        )

        # Текущий месяц —
        # только закрытые дни.
        if not (
            latest_closed.year == 2026
            and latest_closed.month == 7
        ):
            update_period(
                page,
                rows,
                latest_closed.year,
                latest_closed.month,
                latest_closed.day,
            )

        browser.close()

    verify_july(
        rows
    )

    save_rows(
        rows
    )

    print()
    print("=" * 70)
    print("ГОТОВО")
    print("=" * 70)

    print()
    print(
        "Файл:",
        OUTPUT_FILE,
    )

    print()
    print(
        "Суммы Яндекс/Купер и количество заказов "
        "берутся из одной таблицы внешних заказов."
    )


if __name__ == "__main__":
    main()