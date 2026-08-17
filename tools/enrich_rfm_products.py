import csv
import os
import sqlite3
from collections import defaultdict

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


PROJECT_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

DB_PATH = os.path.join(
    PROJECT_DIR,
    "analytics.sqlite"
)

RFM_CSV_PATH = os.path.join(
    PROJECT_DIR,
    "customer_rfm.csv"
)

TOKEN_FILE = os.path.join(
    PROJECT_DIR,
    "token.json"
)

SPREADSHEET_ID_FILE = os.path.join(
    PROJECT_DIR,
    "rfm_spreadsheet_id.txt"
)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets"
]

SHEET_TITLE = "RFM"

TECHNICAL_PRODUCT_IDS = {
    "13836",
    "17567",
}


SEGMENT_ORDER = [
    "VIP",
    "Лояльный",
    "Новый",
    "Активный",
    "Нужно удержать",
    "Остывает",
    "Ценный под риском",
    "Под риском",
    "Потерянный ценный",
    "Потерянный",
]

SEGMENT_PRIORITY = {
    segment: index
    for index, segment in enumerate(
        SEGMENT_ORDER
    )
}


def to_float(value):

    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def get_credentials():

    creds = Credentials.from_authorized_user_file(
        TOKEN_FILE,
        SCOPES
    )

    if creds.expired and creds.refresh_token:

        creds.refresh(
            Request()
        )

        with open(
            TOKEN_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            file.write(
                creds.to_json()
            )

    return creds


def get_spreadsheet_id():

    with open(
        SPREADSHEET_ID_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        return file.read().strip()


def get_rfm_order():

    with open(
        RFM_CSV_PATH,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        rows = list(
            csv.DictReader(file)
        )

    rows.sort(
        key=lambda row: (
            SEGMENT_PRIORITY.get(
                row["segment"],
                999
            ),
            -to_float(
                row["monetary"]
            ),
        )
    )

    return [
        str(row["customer_id"])
        for row in rows
    ]


def get_product_profiles(conn):

    rows = conn.execute(
        """
        SELECT
            customer_id,
            product_name,
            purchase_count,
            monetary_cents,
            average_interval_days,
            last_purchase

        FROM customer_products

        ORDER BY
            customer_id,
            purchase_count DESC,
            monetary_cents DESC
        """
    ).fetchall()

    products = defaultdict(list)

    for row in rows:

        products[str(row[0])].append(
            {
                "name": row[1] or "",
                "count": row[2] or 0,
                "monetary_cents": row[3] or 0,
                "interval": row[4],
                "last_purchase": row[5] or "",
            }
        )

    return products


def get_latest_check_ids(conn):

    rows = conn.execute(
        """
        SELECT
            customer_id,
            check_id,
            datetime_iso

        FROM checks

        WHERE
            customer_id IS NOT NULL
            AND customer_id <> ''
            AND resolution_status = 'resolved'
            AND amount_cents > 0

        ORDER BY
            customer_id,
            datetime_iso DESC,
            check_id DESC
        """
    ).fetchall()

    latest = {}

    for customer_id, check_id, datetime_iso in rows:

        customer_id = str(
            customer_id
        )

        if customer_id not in latest:

            latest[customer_id] = (
                check_id,
                datetime_iso
            )

    return latest


def get_latest_baskets(
    conn,
    latest_checks
):

    basket_by_customer = {}

    for customer_id, (
        check_id,
        _
    ) in latest_checks.items():

        rows = conn.execute(
            """
            SELECT
                product_id,
                product_name,
                SUM(quantity)

            FROM items

            WHERE
                check_id = ?
                AND signed_amount_cents > 0

            GROUP BY
                product_id,
                product_name

            ORDER BY
                signed_amount_cents DESC
            """,
            (
                check_id,
            )
        ).fetchall()

        basket = []

        for (
            product_id,
            product_name,
            quantity
        ) in rows:

            if str(product_id) in TECHNICAL_PRODUCT_IDS:
                continue

            if not product_name:
                continue

            quantity = (
                quantity
                if quantity is not None
                else 0
            )

            if abs(
                quantity - round(quantity)
            ) < 0.001:

                quantity_text = str(
                    int(round(quantity))
                )

            else:

                quantity_text = (
                    f"{quantity:.2f}"
                    .rstrip("0")
                    .rstrip(".")
                )

            if quantity > 1:

                basket.append(
                    f"{product_name} ×{quantity_text}"
                )

            else:

                basket.append(
                    product_name
                )

        basket_by_customer[
            customer_id
        ] = "; ".join(
            basket
        )

    return basket_by_customer


def make_top3(products):

    if not products:
        return ""

    result = []

    for product in products[:3]:

        result.append(
            f"{product['name']} "
            f"({product['count']} покупок)"
        )

    return "; ".join(
        result
    )


def make_main_cycle(products):

    if not products:
        return ""

    product = products[0]

    name = product["name"]

    count = product["count"]

    interval = product["interval"]

    last_purchase = (
        product["last_purchase"][:10]
        if product["last_purchase"]
        else ""
    )

    parts = [
        f"{name}",
        f"{count} покупок",
    ]

    if interval is not None:

        parts.append(
            f"≈ раз в {interval:g} дн."
        )

    if last_purchase:

        parts.append(
            f"последняя {last_purchase}"
        )

    return " — ".join(
        [
            parts[0],
            ", ".join(
                parts[1:]
            )
        ]
    )


def build_rows():

    conn = sqlite3.connect(
        DB_PATH
    )

    products = get_product_profiles(
        conn
    )

    latest_checks = (
        get_latest_check_ids(
            conn
        )
    )

    baskets = get_latest_baskets(
        conn,
        latest_checks
    )

    conn.close()

    customer_order = (
        get_rfm_order()
    )

    rows = []

    for customer_id in customer_order:

        customer_products = products.get(
            customer_id,
            []
        )

        rows.append(
            [
                make_top3(
                    customer_products
                ),

                baskets.get(
                    customer_id,
                    ""
                ),

                make_main_cycle(
                    customer_products
                ),
            ]
        )

    return rows


def main():

    print()
    print("=" * 70)
    print("ДОБАВЛЯЮ ТОВАРНЫЙ ПРОФИЛЬ В RFM")
    print("=" * 70)

    rows = build_rows()

    print()
    print(
        "Клиентов:",
        len(rows)
    )

    creds = get_credentials()

    service = build(
        "sheets",
        "v4",
        credentials=creds
    )

    spreadsheet_id = (
        get_spreadsheet_id()
    )

    values = [
        [
            "Топ-3 товара",
            "Последняя корзина",
            "Главный товар: цикл",
        ]
    ]

    values.extend(
        rows
    )

    (
        service
        .spreadsheets()
        .values()
        .update(
            spreadsheetId=spreadsheet_id,
            range=f"'{SHEET_TITLE}'!T1",
            valueInputOption="RAW",
            body={
                "values": values
            }
        )
        .execute()
    )

    metadata = (
        service
        .spreadsheets()
        .get(
            spreadsheetId=spreadsheet_id,
            fields=(
                "sheets("
                "properties("
                "sheetId,"
                "title"
                ")"
                ")"
            )
        )
        .execute()
    )

    sheet_id = None

    for sheet in metadata.get(
        "sheets",
        []
    ):

        properties = sheet[
            "properties"
        ]

        if properties[
            "title"
        ] == SHEET_TITLE:

            sheet_id = properties[
                "sheetId"
            ]

            break

    if sheet_id is not None:

        (
            service
            .spreadsheets()
            .batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={
                    "requests": [
                        {
                            "repeatCell": {
                                "range": {
                                    "sheetId": sheet_id,
                                    "startRowIndex": 0,
                                    "endRowIndex": 1,
                                    "startColumnIndex": 19,
                                    "endColumnIndex": 22,
                                },
                                "cell": {
                                    "userEnteredFormat": {
                                        "textFormat": {
                                            "bold": True
                                        },
                                        "horizontalAlignment": "CENTER",
                                        "verticalAlignment": "MIDDLE",
                                        "wrapStrategy": "WRAP",
                                    }
                                },
                                "fields": (
                                    "userEnteredFormat("
                                    "textFormat,"
                                    "horizontalAlignment,"
                                    "verticalAlignment,"
                                    "wrapStrategy"
                                    ")"
                                ),
                            }
                        },
                        {
                            "repeatCell": {
                                "range": {
                                    "sheetId": sheet_id,
                                    "startRowIndex": 1,
                                    "endRowIndex": len(rows) + 1,
                                    "startColumnIndex": 19,
                                    "endColumnIndex": 22,
                                },
                                "cell": {
                                    "userEnteredFormat": {
                                        "verticalAlignment": "TOP",
                                        "wrapStrategy": "WRAP",
                                    }
                                },
                                "fields": (
                                    "userEnteredFormat("
                                    "verticalAlignment,"
                                    "wrapStrategy"
                                    ")"
                                ),
                            }
                        },
                    ]
                }
            )
            .execute()
        )

    print()
    print("=" * 70)
    print("ТОВАРНЫЕ КОЛОНКИ RFM ОБНОВЛЕНЫ")
    print("=" * 70)

    print()
    print("T: Топ-3 товара")
    print("U: Последняя корзина")
    print("V: Главный товар: цикл")
    print()


if __name__ == "__main__":

    main()