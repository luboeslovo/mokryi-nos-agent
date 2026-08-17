import csv
import os
import sqlite3
from datetime import datetime


PROJECT_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

DB_FILE = os.path.join(
    PROJECT_DIR,
    "check_items.sqlite"
)

OUTPUT_FILE = os.path.join(
    PROJECT_DIR,
    "check_items.csv"
)

TEMP_FILE = os.path.join(
    PROJECT_DIR,
    "check_items.csv.tmp"
)


FIELDNAMES = [
    "check_id",
    "check_number",
    "date",
    "customer",
    "check_type",
    "product_id",
    "product_name",
    "unit",
    "quantity",
    "amount_before_discount",
    "discount",
    "amount",
    "signed_amount",
]


def parse_date(value):

    if not value:
        return None

    formats = [
        "%d.%m.%Y %H:%M",
        "%d.%m.%Y %H:%M:%S",
        "%d.%m.%Y",
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


def main():

    print()
    print("=" * 70)
    print(
        "ЭКСПОРТ ТОВАРОВ ЧЕКОВ "
        "ИЗ SQLITE В CSV"
    )
    print("=" * 70)

    if not os.path.exists(
        DB_FILE
    ):
        raise FileNotFoundError(
            f"Не найдена база:\n{DB_FILE}"
        )

    connection = sqlite3.connect(
        DB_FILE
    )

    cursor = connection.cursor()

    table_exists = cursor.execute(
        """
        SELECT COUNT(*)
        FROM sqlite_master
        WHERE type = 'table'
          AND name = 'items'
        """
    ).fetchone()[0]

    if not table_exists:

        connection.close()

        raise RuntimeError(
            "В базе нет таблицы items"
        )

    rows = cursor.execute(
        """
        SELECT
            check_id,
            check_number,
            date,
            customer,
            check_type,
            product_id,
            product_name,
            unit,
            quantity,
            amount_before_discount,
            discount,
            amount,
            signed_amount
        FROM items
        """
    ).fetchall()

    connection.close()

    print()
    print(
        "Строк в SQLite:",
        len(rows)
    )

    dated_rows = []

    undated_rows = []

    for row in rows:

        dt = parse_date(
            row[2]
        )

        if dt is None:

            undated_rows.append(
                row
            )

        else:

            dated_rows.append(
                (
                    dt,
                    row
                )
            )

    dated_rows.sort(
        key=lambda pair: pair[0],
        reverse=True
    )

    ordered_rows = [
        row
        for _, row in dated_rows
    ]

    ordered_rows.extend(
        undated_rows
    )

    with open(
        TEMP_FILE,
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        writer = csv.writer(
            file
        )

        writer.writerow(
            FIELDNAMES
        )

        writer.writerows(
            ordered_rows
        )

    os.replace(
        TEMP_FILE,
        OUTPUT_FILE
    )

    dates = [
        dt
        for dt, _ in dated_rows
    ]

    print()
    print(
        "CSV обновлён:"
    )
    print(
        OUTPUT_FILE
    )

    print(
        "Строк записано:",
        len(ordered_rows)
    )

    if dates:

        print(
            "Самая ранняя дата:",
            min(dates).strftime(
                "%d.%m.%Y %H:%M"
            )
        )

        print(
            "Самая поздняя дата:",
            max(dates).strftime(
                "%d.%m.%Y %H:%M"
            )
        )

    if undated_rows:

        print()
        print(
            "ВНИМАНИЕ:"
        )

        print(
            "Строк с нераспознанной датой:",
            len(undated_rows)
        )

    check_ids_by_day = {
        "15.08.2026": set(),
        "16.08.2026": set(),
    }

    item_rows_by_day = {
        "15.08.2026": 0,
        "16.08.2026": 0,
    }

    quantity_by_day = {
        "15.08.2026": 0.0,
        "16.08.2026": 0.0,
    }

    for row in ordered_rows:

        date_text = str(
            row[2] or ""
        )

        for day in (
            "15.08.2026",
            "16.08.2026",
        ):

            if date_text.startswith(
                day
            ):

                check_ids_by_day[
                    day
                ].add(
                    str(
                        row[0]
                    )
                )

                item_rows_by_day[
                    day
                ] += 1

                try:

                    quantity_by_day[
                        day
                    ] += float(
                        row[8] or 0
                    )

                except (
                    TypeError,
                    ValueError,
                ):
                    pass

    print()
    print("=" * 70)
    print(
        "КОНТРОЛЬ ПОСЛЕДНИХ ДНЕЙ"
    )
    print("=" * 70)

    for day in (
        "15.08.2026",
        "16.08.2026",
    ):

        print()
        print(day)

        print(
            "Чеков с товарами:",
            len(
                check_ids_by_day[
                    day
                ]
            )
        )

        print(
            "Строк товаров:",
            item_rows_by_day[
                day
            ]
        )

        print(
            "Количество товаров:",
            quantity_by_day[
                day
            ]
        )

    print()
    print("=" * 70)
    print("ГОТОВО")
    print("=" * 70)


if __name__ == "__main__":
    main()