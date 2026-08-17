import csv
import os
import sqlite3
from collections import defaultdict
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP


# ============================================================
# ПУТИ
# ============================================================

PROJECT_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

CHECKS_FILE = os.path.join(
    PROJECT_DIR,
    "checks_with_customer_id.csv"
)

CUSTOMERS_DB = os.path.join(
    PROJECT_DIR,
    "customer_cards.sqlite"
)

ITEMS_DB = os.path.join(
    PROJECT_DIR,
    "check_items.sqlite"
)

ANALYTICS_DB = os.path.join(
    PROJECT_DIR,
    "analytics.sqlite"
)

METRICS_CSV = os.path.join(
    PROJECT_DIR,
    "customer_metrics.csv"
)


# ============================================================
# ОБЩИЕ / ТЕХНИЧЕСКИЕ КАРТЫ
# ============================================================

SHARED_CUSTOMER_IDS = {
    "806542"
}


# ============================================================
# ДЕНЬГИ
# ============================================================

def money_to_cents(value):

    if value is None:
        return 0

    text = str(value).strip()

    if not text:
        return 0

    text = (
        text
        .replace(" ", "")
        .replace(",", ".")
    )

    try:

        amount = Decimal(text)

    except Exception:

        return 0

    return int(
        (
            amount
            * Decimal("100")
        ).quantize(
            Decimal("1"),
            rounding=ROUND_HALF_UP
        )
    )


def cents_to_rubles(cents):

    return (
        Decimal(cents)
        / Decimal("100")
    )


def format_money(cents):

    value = cents_to_rubles(
        cents
    )

    return (
        f"{value:,.2f}"
        .replace(",", " ")
        + " ₽"
    )


# ============================================================
# ДАТЫ
# ============================================================

def parse_date(value):

    if not value:
        return None

    value = value.strip()

    formats = [
        "%d.%m.%Y %H:%M",
        "%d.%m.%Y %H:%M:%S",
    ]

    for fmt in formats:

        try:

            return datetime.strptime(
                value,
                fmt
            )

        except ValueError:
            pass

    return None


# ============================================================
# СОЗДАНИЕ analytics.sqlite
# ============================================================

def create_database():

    if os.path.exists(
        ANALYTICS_DB
    ):

        os.remove(
            ANALYTICS_DB
        )

    connection = sqlite3.connect(
        ANALYTICS_DB
    )

    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE customers (
            customer_id TEXT PRIMARY KEY,
            check_name TEXT,
            name TEXT,
            lastname TEXT,
            birthdate TEXT,
            sex_id TEXT,
            sex_name TEXT,
            phone TEXT,
            email TEXT,
            loyalty_id TEXT,
            loyalty_name TEXT,
            note TEXT,
            delivery_address TEXT,
            source_title TEXT,
            updated_at TEXT,
            customer_status TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE checks (
            check_id TEXT PRIMARY KEY,
            date TEXT,
            datetime_iso TEXT,
            number TEXT,
            customer TEXT,
            type TEXT,
            organization TEXT,
            branch TEXT,
            user TEXT,
            amount_cents INTEGER,
            customer_id TEXT,
            resolution_status TEXT,
            resolution_method TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE items (
            crm_item_id TEXT,
            check_id TEXT,
            check_number TEXT,
            date TEXT,
            customer TEXT,
            check_type TEXT,
            product_id TEXT,
            product_name TEXT,
            unit TEXT,
            quantity REAL,
            amount_before_discount_cents INTEGER,
            discount_cents INTEGER,
            amount_cents INTEGER,
            signed_amount_cents INTEGER
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE customer_metrics (
            customer_id TEXT PRIMARY KEY,
            first_purchase TEXT,
            last_purchase TEXT,
            recency_days INTEGER,
            frequency INTEGER,
            purchase_sum_cents INTEGER,
            return_sum_cents INTEGER,
            monetary_cents INTEGER,
            average_check_cents INTEGER,
            average_interval_days REAL,
            active_span_days INTEGER
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE customer_flags (
            customer_id TEXT PRIMARY KEY,
            flag TEXT,
            note TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE INDEX idx_checks_customer
        ON checks(customer_id)
        """
    )

    cursor.execute(
        """
        CREATE INDEX idx_checks_date
        ON checks(datetime_iso)
        """
    )

    cursor.execute(
        """
        CREATE INDEX idx_items_check
        ON items(check_id)
        """
    )

    cursor.execute(
        """
        CREATE INDEX idx_items_product
        ON items(product_id)
        """
    )

    connection.commit()

    return connection


# ============================================================
# КАРТОЧКИ КЛИЕНТОВ
# ============================================================

def import_customers(
    analytics_connection
):

    source = sqlite3.connect(
        CUSTOMERS_DB
    )

    source.row_factory = (
        sqlite3.Row
    )

    source_cursor = (
        source.cursor()
    )

    source_cursor.execute(
        """
        SELECT *
        FROM customers
        """
    )

    rows = (
        source_cursor.fetchall()
    )

    target = (
        analytics_connection.cursor()
    )

    imported = 0

    for row in rows:

        customer_id = str(
            row["customer_id"]
        )

        if (
            customer_id
            in SHARED_CUSTOMER_IDS
        ):

            status = "shared_card"

        else:

            status = "normal"

        target.execute(
            """
            INSERT INTO customers (
                customer_id,
                check_name,
                name,
                lastname,
                birthdate,
                sex_id,
                sex_name,
                phone,
                email,
                loyalty_id,
                loyalty_name,
                note,
                delivery_address,
                source_title,
                updated_at,
                customer_status
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                customer_id,
                row["check_name"],
                row["name"],
                row["lastname"],
                row["birthdate"],
                row["sex_id"],
                row["sex_name"],
                row["phone"],
                row["email"],
                row["loyalty_id"],
                row["loyalty_name"],
                row["note"],
                row["delivery_address"],
                row["source_title"],
                row["updated_at"],
                status,
            )
        )

        imported += 1

    for customer_id in (
        SHARED_CUSTOMER_IDS
    ):

        target.execute(
            """
            INSERT OR REPLACE INTO customer_flags (
                customer_id,
                flag,
                note
            )
            VALUES (?, ?, ?)
            """,
            (
                customer_id,
                "shared_card",
                (
                    "Общая карта для покупателей, "
                    "которые не используют собственную "
                    "карту лояльности. Не включать в RFM."
                ),
            )
        )

    analytics_connection.commit()

    source.close()

    return imported


# ============================================================
# ЧЕКИ
# ============================================================

def import_checks(
    analytics_connection
):

    target = (
        analytics_connection.cursor()
    )

    count = 0
    latest_datetime = None

    with open(
        CHECKS_FILE,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.DictReader(
            file
        )

        for row in reader:

            dt = parse_date(
                row.get(
                    "date",
                    ""
                )
            )

            if (
                dt is not None
                and (
                    latest_datetime is None
                    or dt > latest_datetime
                )
            ):

                latest_datetime = dt

            customer_id = str(
                row.get(
                    "customer_id",
                    ""
                )
            ).strip()

            resolution_status = (
                row.get(
                    "resolution_status",
                    ""
                )
            )

            resolution_method = (
                row.get(
                    "resolution_method",
                    ""
                )
            )

            # Дополнительная защита:
            # общую карту никогда не считаем клиентом.

            if (
                customer_id
                in SHARED_CUSTOMER_IDS
            ):

                customer_id = ""

                resolution_status = (
                    "anonymous"
                )

                resolution_method = (
                    "shared_card"
                )

            target.execute(
                """
                INSERT INTO checks (
                    check_id,
                    date,
                    datetime_iso,
                    number,
                    customer,
                    type,
                    organization,
                    branch,
                    user,
                    amount_cents,
                    customer_id,
                    resolution_status,
                    resolution_method
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    row.get(
                        "check_id",
                        ""
                    ),
                    row.get(
                        "date",
                        ""
                    ),
                    (
                        dt.isoformat(
                            sep=" "
                        )
                        if dt
                        else ""
                    ),
                    row.get(
                        "number",
                        ""
                    ),
                    row.get(
                        "customer",
                        ""
                    ),
                    row.get(
                        "type",
                        ""
                    ),
                    row.get(
                        "organization",
                        ""
                    ),
                    row.get(
                        "branch",
                        ""
                    ),
                    row.get(
                        "user",
                        ""
                    ),
                    money_to_cents(
                        row.get(
                            "amount",
                            ""
                        )
                    ),
                    customer_id,
                    resolution_status,
                    resolution_method,
                )
            )

            count += 1

    analytics_connection.commit()

    return (
        count,
        latest_datetime
    )


# ============================================================
# ТОВАРЫ
# ============================================================

def import_items(
    analytics_connection
):

    source = sqlite3.connect(
        ITEMS_DB
    )

    source.row_factory = (
        sqlite3.Row
    )

    source_cursor = (
        source.cursor()
    )

    source_cursor.execute(
        """
        SELECT *
        FROM items
        """
    )

    target = (
        analytics_connection.cursor()
    )

    count = 0

    for row in source_cursor:

        target.execute(
            """
            INSERT INTO items (
                crm_item_id,
                check_id,
                check_number,
                date,
                customer,
                check_type,
                product_id,
                product_name,
                unit,
                quantity,
                amount_before_discount_cents,
                discount_cents,
                amount_cents,
                signed_amount_cents
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?
            )
            """,
            (
                row["crm_item_id"],
                row["check_id"],
                row["check_number"],
                row["date"],
                row["customer"],
                row["check_type"],
                row["product_id"],
                row["product_name"],
                row["unit"],
                row["quantity"],
                money_to_cents(
                    row[
                        "amount_before_discount"
                    ]
                ),
                money_to_cents(
                    row["discount"]
                ),
                money_to_cents(
                    row["amount"]
                ),
                money_to_cents(
                    row["signed_amount"]
                ),
            )
        )

        count += 1

    analytics_connection.commit()

    source.close()

    return count


# ============================================================
# RFM / КЛИЕНТСКИЕ МЕТРИКИ
# ============================================================

def build_customer_metrics(
    connection
):

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            customer_id,
            datetime_iso,
            type,
            amount_cents
        FROM checks
        WHERE
            resolution_status = 'resolved'
            AND customer_id <> ''
        ORDER BY
            customer_id,
            datetime_iso
        """
    )

    history = defaultdict(
        lambda: {
            "purchases": [],
            "returns": [],
        }
    )

    for (
        customer_id,
        datetime_iso,
        check_type,
        amount_cents
    ) in cursor.fetchall():

        if (
            customer_id
            in SHARED_CUSTOMER_IDS
        ):
            continue

        if not datetime_iso:
            continue

        dt = datetime.fromisoformat(
            datetime_iso
        )

        if (
            "возврат"
            in (
                check_type
                or ""
            ).lower()
        ):

            history[
                customer_id
            ][
                "returns"
            ].append(
                (
                    dt,
                    amount_cents
                )
            )

        else:

            history[
                customer_id
            ][
                "purchases"
            ].append(
                (
                    dt,
                    amount_cents
                )
            )

    analysis_date = datetime.now()

    metrics_count = 0

    for (
        customer_id,
        customer_history
    ) in history.items():

        purchases = (
            customer_history[
                "purchases"
            ]
        )

        returns = (
            customer_history[
                "returns"
            ]
        )

        if not purchases:
            continue

        purchase_dates = [
            item[0]
            for item in purchases
        ]

        purchase_sum = sum(
            item[1]
            for item in purchases
        )

        return_sum = sum(
            item[1]
            for item in returns
        )

        frequency = len(
            purchases
        )

        monetary = (
            purchase_sum
            - return_sum
        )

        first_purchase = min(
            purchase_dates
        )

        last_purchase = max(
            purchase_dates
        )

        recency_days = (
            analysis_date
            - last_purchase
        ).days

        average_check = int(
            round(
                purchase_sum
                / frequency
            )
        )

        active_span_days = (
            last_purchase
            - first_purchase
        ).days

        average_interval_days = None

        if len(
            purchase_dates
        ) >= 2:

            sorted_dates = sorted(
                purchase_dates
            )

            intervals = []

            for index in range(
                1,
                len(sorted_dates)
            ):

                delta = (
                    sorted_dates[index]
                    - sorted_dates[
                        index - 1
                    ]
                )

                intervals.append(
                    delta.total_seconds()
                    / 86400
                )

            if intervals:

                average_interval_days = (
                    sum(intervals)
                    / len(intervals)
                )

        cursor.execute(
            """
            INSERT INTO customer_metrics (
                customer_id,
                first_purchase,
                last_purchase,
                recency_days,
                frequency,
                purchase_sum_cents,
                return_sum_cents,
                monetary_cents,
                average_check_cents,
                average_interval_days,
                active_span_days
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?
            )
            """,
            (
                customer_id,
                first_purchase.isoformat(
                    sep=" "
                ),
                last_purchase.isoformat(
                    sep=" "
                ),
                recency_days,
                frequency,
                purchase_sum,
                return_sum,
                monetary,
                average_check,
                average_interval_days,
                active_span_days,
            )
        )

        metrics_count += 1

    connection.commit()

    return (
        metrics_count,
        analysis_date
    )


# ============================================================
# EXPORT customer_metrics.csv
# ============================================================

def export_customer_metrics(
    connection
):

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            m.customer_id,
            c.check_name,
            c.name,
            c.lastname,
            c.phone,
            m.first_purchase,
            m.last_purchase,
            m.recency_days,
            m.frequency,
            m.purchase_sum_cents,
            m.return_sum_cents,
            m.monetary_cents,
            m.average_check_cents,
            m.average_interval_days,
            m.active_span_days
        FROM customer_metrics m
        LEFT JOIN customers c
            ON c.customer_id = m.customer_id
        ORDER BY
            m.monetary_cents DESC
        """
    )

    rows = cursor.fetchall()

    fieldnames = [
        "customer_id",
        "check_name",
        "name",
        "lastname",
        "phone",
        "first_purchase",
        "last_purchase",
        "recency_days",
        "frequency",
        "purchase_sum",
        "return_sum",
        "monetary",
        "average_check",
        "average_interval_days",
        "active_span_days",
    ]

    with open(
        METRICS_CSV,
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        writer = csv.writer(
            file
        )

        writer.writerow(
            fieldnames
        )

        for row in rows:

            writer.writerow(
                [
                    row[0],
                    row[1],
                    row[2],
                    row[3],
                    row[4],
                    row[5],
                    row[6],
                    row[7],
                    row[8],
                    (
                        f"{cents_to_rubles(row[9]):.2f}"
                    ),
                    (
                        f"{cents_to_rubles(row[10]):.2f}"
                    ),
                    (
                        f"{cents_to_rubles(row[11]):.2f}"
                    ),
                    (
                        f"{cents_to_rubles(row[12]):.2f}"
                    ),
                    (
                        ""
                        if row[13] is None
                        else f"{row[13]:.2f}"
                    ),
                    row[14],
                ]
            )


# ============================================================
# ПРОВЕРКИ
# ============================================================

def integrity_checks(
    connection
):

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM checks ch
        LEFT JOIN customers c
            ON c.customer_id = ch.customer_id
        WHERE
            ch.resolution_status = 'resolved'
            AND ch.customer_id <> ''
            AND c.customer_id IS NULL
        """
    )

    resolved_without_card = (
        cursor.fetchone()[0]
    )

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM items i
        LEFT JOIN checks c
            ON c.check_id = i.check_id
        WHERE c.check_id IS NULL
        """
    )

    items_without_check = (
        cursor.fetchone()[0]
    )

    return (
        resolved_without_card,
        items_without_check
    )


# ============================================================
# СВОДНЫЕ ПОКАЗАТЕЛИ
# ============================================================

def print_summary(
    connection,
    latest_datetime,
    analysis_date
):

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM checks
        """
    )

    checks_total = (
        cursor.fetchone()[0]
    )

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM items
        """
    )

    items_total = (
        cursor.fetchone()[0]
    )

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM customer_metrics
        """
    )

    customers_with_metrics = (
        cursor.fetchone()[0]
    )

    cursor.execute(
        """
        SELECT
            COALESCE(
                SUM(monetary_cents),
                0
            )
        FROM customer_metrics
        """
    )

    customer_m = (
        cursor.fetchone()[0]
    )

    cursor.execute(
        """
        SELECT
            COUNT(*),
            COALESCE(
                SUM(amount_cents),
                0
            )
        FROM checks
        WHERE
            LOWER(type)
            NOT LIKE '%возврат%'
    """
    )

    (
        purchase_check_count,
        purchase_check_sum
    ) = cursor.fetchone()

    global_average_check = 0

    if purchase_check_count:

        global_average_check = int(
            round(
                purchase_check_sum
                / purchase_check_count
            )
        )

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM checks
        WHERE resolution_method = 'shared_card'
        """
    )

    shared_card_checks = (
        cursor.fetchone()[0]
    )

    cursor.execute(
        """
        SELECT
            resolution_status,
            COUNT(*)
        FROM checks
        GROUP BY resolution_status
        ORDER BY resolution_status
        """
    )

    status_rows = (
        cursor.fetchall()
    )

    print()
    print("=" * 70)

    print("АНАЛИТИКА ПЕРЕСОБРАНА")

    print()
    print(
        f"Чеков: "
        f"{checks_total}"
    )

    print(
        f"Последний чек: "
        f"{latest_datetime}"
    )

    print(
        f"Товарных строк: "
        f"{items_total}"
    )

    print(
        f"Дата анализа: "
        f"{analysis_date}"
    )

    print()
    print(
        "СТАТУСЫ ЧЕКОВ:"
    )

    for status, count in status_rows:

        print(
            f"{status}: {count}"
        )

    print()
    print(
        f"Чеков общей карты: "
        f"{shared_card_checks}"
    )

    print(
        "Они входят в продажи магазина, "
        "но НЕ входят в RFM клиентов."
    )

    print()
    print(
        f"Реальных клиентов "
        f"с покупками: "
        f"{customers_with_metrics}"
    )

    print(
        "Суммарный M "
        "идентифицированных клиентов: "
        f"{format_money(customer_m)}"
    )

    print(
        "Средний чек магазина "
        "(все положительные чеки): "
        f"{format_money(global_average_check)}"
    )

    print("=" * 70)


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print(
        "Создаю analytics.sqlite..."
    )

    connection = create_database()

    print(
        "Загружаю карточки клиентов..."
    )

    customer_count = import_customers(
        connection
    )

    print(
        f"Карточек загружено: "
        f"{customer_count}"
    )

    print(
        "Загружаю чеки..."
    )

    (
        checks_count,
        latest_datetime
    ) = import_checks(
        connection
    )

    print(
        f"Чеков загружено: "
        f"{checks_count}"
    )

    print(
        "Загружаю товары..."
    )

    items_count = import_items(
        connection
    )

    print(
        f"Товарных строк загружено: "
        f"{items_count}"
    )

    print(
        "Считаю клиентские метрики..."
    )

    (
        metrics_count,
        analysis_date
    ) = build_customer_metrics(
        connection
    )

    print(
        f"Клиентов с метриками: "
        f"{metrics_count}"
    )

    export_customer_metrics(
        connection
    )

    (
        missing_cards,
        orphan_items
    ) = integrity_checks(
        connection
    )

    print()
    print(
        "ПРОВЕРКА СВЯЗЕЙ:"
    )

    print(
        "Resolved-чеков без карточки: "
        f"{missing_cards}"
    )

    print(
        "Товарных строк без чека: "
        f"{orphan_items}"
    )

    print_summary(
        connection,
        latest_datetime,
        analysis_date
    )

    print()
    print(
        "Создано:"
    )

    print(
        "analytics.sqlite"
    )

    print(
        "customer_metrics.csv"
    )

    connection.close()


if __name__ == "__main__":

    main()