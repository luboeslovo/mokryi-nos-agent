import csv
import os
import sqlite3
from collections import defaultdict
from datetime import datetime


PROJECT_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

DB_PATH = os.path.join(
    PROJECT_DIR,
    "analytics.sqlite"
)

CSV_PATH = os.path.join(
    PROJECT_DIR,
    "customer_products.csv"
)


TECHNICAL_PRODUCT_IDS = {
    "13836",  # Пакет майка
    "17567",  # Пакет майка большой
}


def parse_datetime(value):

    if not value:
        return None

    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def main():

    conn = sqlite3.connect(
        DB_PATH
    )

    cursor = conn.cursor()

    latest_value = cursor.execute(
        """
        SELECT MAX(datetime_iso)
        FROM checks
        """
    ).fetchone()[0]

    analysis_date = parse_datetime(
        latest_value
    )

    rows = cursor.execute(
        """
        SELECT
            c.customer_id,
            c.check_id,
            c.datetime_iso,
            i.product_id,
            i.product_name,
            i.quantity,
            i.signed_amount_cents
        FROM checks c
        JOIN items i
            ON i.check_id = c.check_id
        WHERE
            c.customer_id IS NOT NULL
            AND TRIM(c.customer_id) <> ''
            AND c.resolution_status = 'resolved'
            AND COALESCE(i.signed_amount_cents, 0) > 0
        """
    ).fetchall()

    products = defaultdict(
        lambda: {
            "checks": set(),
            "dates": set(),
            "quantity": 0.0,
            "monetary_cents": 0,
            "product_name": "",
            "product_id": "",
        }
    )

    excluded_rows = 0

    for (
        customer_id,
        check_id,
        datetime_iso,
        product_id,
        product_name,
        quantity,
        signed_amount_cents,
    ) in rows:

        product_id = (
            str(product_id).strip()
            if product_id is not None
            else ""
        )

        product_name = (
            str(product_name).strip()
            if product_name is not None
            else ""
        )

        if product_id in TECHNICAL_PRODUCT_IDS:

            excluded_rows += 1
            continue

        if not product_id and not product_name:
            continue

        product_key = (
            product_id
            if product_id
            else product_name
        )

        key = (
            str(customer_id),
            product_key
        )

        data = products[key]

        data["product_id"] = product_id
        data["product_name"] = product_name

        data["checks"].add(
            str(check_id)
        )

        dt = parse_datetime(
            datetime_iso
        )

        if dt is not None:
            data["dates"].add(
                dt
            )

        data["quantity"] += float(
            quantity or 0
        )

        data["monetary_cents"] += int(
            signed_amount_cents or 0
        )

    result = []

    for (
        customer_id,
        _
    ), data in products.items():

        dates = sorted(
            data["dates"]
        )

        first_purchase = (
            dates[0]
            if dates
            else None
        )

        last_purchase = (
            dates[-1]
            if dates
            else None
        )

        intervals = []

        for previous, current in zip(
            dates,
            dates[1:]
        ):

            interval = (
                current - previous
            ).total_seconds() / 86400

            if interval > 0:
                intervals.append(
                    interval
                )

        if intervals:

            avg_interval_days = (
                sum(intervals)
                / len(intervals)
            )

        else:

            avg_interval_days = None

        if (
            analysis_date is not None
            and last_purchase is not None
        ):

            days_since_last = (
                analysis_date.date()
                - last_purchase.date()
            ).days

        else:

            days_since_last = None

        if (
            avg_interval_days
            and days_since_last is not None
        ):

            overdue_ratio = (
                days_since_last
                / avg_interval_days
            )

        else:

            overdue_ratio = None

        result.append(
            (
                customer_id,
                data["product_id"],
                data["product_name"],
                len(data["checks"]),
                round(
                    data["quantity"],
                    3
                ),
                data["monetary_cents"],
                (
                    first_purchase.isoformat(
                        sep=" "
                    )
                    if first_purchase
                    else None
                ),
                (
                    last_purchase.isoformat(
                        sep=" "
                    )
                    if last_purchase
                    else None
                ),
                (
                    round(
                        avg_interval_days,
                        2
                    )
                    if avg_interval_days is not None
                    else None
                ),
                days_since_last,
                (
                    round(
                        overdue_ratio,
                        2
                    )
                    if overdue_ratio is not None
                    else None
                ),
            )
        )

    cursor.execute(
        """
        DROP TABLE IF EXISTS customer_products
        """
    )

    cursor.execute(
        """
        CREATE TABLE customer_products (
            customer_id TEXT,
            product_id TEXT,
            product_name TEXT,
            purchase_count INTEGER,
            total_quantity REAL,
            monetary_cents INTEGER,
            first_purchase TEXT,
            last_purchase TEXT,
            average_interval_days REAL,
            days_since_last INTEGER,
            overdue_ratio REAL
        )
        """
    )

    cursor.executemany(
        """
        INSERT INTO customer_products (
            customer_id,
            product_id,
            product_name,
            purchase_count,
            total_quantity,
            monetary_cents,
            first_purchase,
            last_purchase,
            average_interval_days,
            days_since_last,
            overdue_ratio
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        result
    )

    cursor.execute(
        """
        CREATE INDEX
        IF NOT EXISTS idx_customer_products_customer
        ON customer_products(customer_id)
        """
    )

    conn.commit()

    with open(
        CSV_PATH,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as file:

        writer = csv.writer(
            file
        )

        writer.writerow(
            [
                "customer_id",
                "product_id",
                "product_name",
                "purchase_count",
                "total_quantity",
                "monetary",
                "first_purchase",
                "last_purchase",
                "average_interval_days",
                "days_since_last",
                "overdue_ratio",
            ]
        )

        for row in result:

            csv_row = list(
                row
            )

            csv_row[5] = round(
                csv_row[5] / 100,
                2
            )

            writer.writerow(
                csv_row
            )

    clients_count = len(
        {
            row[0]
            for row in result
        }
    )

    print()
    print("=" * 70)
    print("ТОВАРНЫЕ ПРОФИЛИ КЛИЕНТОВ ПОСТРОЕНЫ")
    print("=" * 70)

    print()
    print(
        "Клиентов:",
        clients_count
    )

    print(
        "Связок клиент × товар:",
        len(result)
    )

    print(
        "Исключено строк технических товаров:",
        excluded_rows
    )

    print()
    print(
        "Создана таблица:",
        "customer_products"
    )

    print(
        "Создан файл:",
        "customer_products.csv"
    )

    print("=" * 70)

    conn.close()


if __name__ == "__main__":
    main()