import csv
import os
import sqlite3

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
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

CREDENTIALS_FILE = os.path.join(
    PROJECT_DIR,
    "credentials.json"
)

SPREADSHEET_ID_FILE = os.path.join(
    PROJECT_DIR,
    "rfm_spreadsheet_id.txt"
)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets"
]

SHEET_TITLE = "Покупки клиентов"


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

    creds = None

    if os.path.exists(TOKEN_FILE):

        creds = Credentials.from_authorized_user_file(
            TOKEN_FILE,
            SCOPES
        )

    if not creds or not creds.valid:

        if (
            creds
            and creds.expired
            and creds.refresh_token
        ):

            creds.refresh(
                Request()
            )

        else:

            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE,
                SCOPES
            )

            creds = flow.run_local_server(
                port=0
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


def get_rfm_customer_order():

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

    return {
        str(row["customer_id"]): index
        for index, row in enumerate(rows)
    }


def get_rows():

    conn = sqlite3.connect(
        DB_PATH
    )

    cursor = conn.cursor()

    rows = cursor.execute(
        """
        SELECT
            cp.customer_id,

            CASE
                WHEN TRIM(
                    COALESCE(c.lastname, '')
                    || ' '
                    || COALESCE(c.name, '')
                ) <> ''
                THEN TRIM(
                    COALESCE(c.lastname, '')
                    || ' '
                    || COALESCE(c.name, '')
                )

                ELSE COALESCE(
                    c.check_name,
                    ''
                )
            END AS customer_name,

            COALESCE(
                c.phone,
                ''
            ) AS phone,

            cp.product_name,
            cp.purchase_count,
            cp.total_quantity,

            ROUND(
                cp.monetary_cents / 100.0,
                2
            ) AS monetary,

            SUBSTR(
                cp.first_purchase,
                1,
                10
            ) AS first_purchase,

            SUBSTR(
                cp.last_purchase,
                1,
                10
            ) AS last_purchase,

            cp.average_interval_days,
            cp.days_since_last,
            cp.overdue_ratio,

            cp.monetary_cents

        FROM customer_products cp

        LEFT JOIN customers c
            ON c.customer_id = cp.customer_id
        """
    ).fetchall()

    conn.close()

    customer_order = (
        get_rfm_customer_order()
    )

    rows.sort(
        key=lambda row: (
            customer_order.get(
                str(row[0]),
                999999
            ),
            -int(row[4] or 0),
            -int(row[12] or 0),
            row[3] or "",
        )
    )

    return [
        row[:12]
        for row in rows
    ]


def get_sheet_info(
    service,
    spreadsheet_id
):

    result = (
        service
        .spreadsheets()
        .get(
            spreadsheetId=spreadsheet_id,
            fields=(
                "sheets("
                "properties("
                "sheetId,"
                "title,"
                "gridProperties"
                ")"
                ")"
            )
        )
        .execute()
    )

    sheets = {}

    for sheet in result.get(
        "sheets",
        []
    ):

        properties = sheet[
            "properties"
        ]

        sheets[
            properties["title"]
        ] = properties

    return sheets


def ensure_sheet(
    service,
    spreadsheet_id,
    sheets
):

    if SHEET_TITLE in sheets:

        return sheets[
            SHEET_TITLE
        ]["sheetId"]

    response = (
        service
        .spreadsheets()
        .batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={
                "requests": [
                    {
                        "addSheet": {
                            "properties": {
                                "title": SHEET_TITLE,
                                "gridProperties": {
                                    "rowCount": 20000,
                                    "columnCount": 12
                                }
                            }
                        }
                    }
                ]
            }
        )
        .execute()
    )

    return (
        response[
            "replies"
        ][0][
            "addSheet"
        ][
            "properties"
        ][
            "sheetId"
        ]
    )


def clear_sheet(
    service,
    spreadsheet_id
):

    (
        service
        .spreadsheets()
        .values()
        .clear(
            spreadsheetId=spreadsheet_id,
            range=f"'{SHEET_TITLE}'!A:L",
            body={}
        )
        .execute()
    )


def write_rows(
    service,
    spreadsheet_id,
    rows
):

    header = [
        "customer_id",
        "Клиент",
        "Телефон",
        "Товар",
        "Покупок",
        "Количество",
        "Потрачено, ₽",
        "Первая покупка",
        "Последняя покупка",
        "Средний интервал, дней",
        "Дней с последней покупки",
        "Коэффициент просрочки",
    ]

    (
        service
        .spreadsheets()
        .values()
        .update(
            spreadsheetId=spreadsheet_id,
            range=f"'{SHEET_TITLE}'!A1",
            valueInputOption="RAW",
            body={
                "values": [
                    header
                ]
            }
        )
        .execute()
    )

    chunk_size = 1000

    for start in range(
        0,
        len(rows),
        chunk_size
    ):

        chunk = rows[
            start:start + chunk_size
        ]

        start_row = (
            start + 2
        )

        (
            service
            .spreadsheets()
            .values()
            .update(
                spreadsheetId=spreadsheet_id,
                range=(
                    f"'{SHEET_TITLE}'!"
                    f"A{start_row}"
                ),
                valueInputOption="RAW",
                body={
                    "values": [
                        list(row)
                        for row in chunk
                    ]
                }
            )
            .execute()
        )

        print(
            "Выгружено:",
            min(
                start + chunk_size,
                len(rows)
            ),
            "/",
            len(rows)
        )


def format_sheet(
    service,
    spreadsheet_id,
    sheet_id,
    row_count
):

    requests = [
        {
            "updateSheetProperties": {
                "properties": {
                    "sheetId": sheet_id,
                    "gridProperties": {
                        "frozenRowCount": 1
                    }
                },
                "fields": (
                    "gridProperties."
                    "frozenRowCount"
                )
            }
        },
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 0,
                    "endRowIndex": 1,
                    "startColumnIndex": 0,
                    "endColumnIndex": 12
                },
                "cell": {
                    "userEnteredFormat": {
                        "textFormat": {
                            "bold": True
                        },
                        "horizontalAlignment": "CENTER",
                        "verticalAlignment": "MIDDLE",
                        "wrapStrategy": "WRAP"
                    }
                },
                "fields": (
                    "userEnteredFormat("
                    "textFormat,"
                    "horizontalAlignment,"
                    "verticalAlignment,"
                    "wrapStrategy"
                    ")"
                )
            }
        },
        {
            "setBasicFilter": {
                "filter": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 0,
                        "endRowIndex": row_count + 1,
                        "startColumnIndex": 0,
                        "endColumnIndex": 12
                    }
                }
            }
        },
        {
            "autoResizeDimensions": {
                "dimensions": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": 0,
                    "endIndex": 12
                }
            }
        }
    ]

    (
        service
        .spreadsheets()
        .batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={
                "requests": requests
            }
        )
        .execute()
    )


def main():

    print()
    print("=" * 70)
    print("ВЫГРУЗКА ПОКУПОК КЛИЕНТОВ В GOOGLE SHEETS")
    print("=" * 70)

    rows = get_rows()

    print()
    print(
        "Строк клиент × товар:",
        len(rows)
    )

    print(
        "Порядок клиентов:",
        "такой же, как в RFM"
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

    sheets = get_sheet_info(
        service,
        spreadsheet_id
    )

    sheet_id = ensure_sheet(
        service,
        spreadsheet_id,
        sheets
    )

    clear_sheet(
        service,
        spreadsheet_id
    )

    write_rows(
        service,
        spreadsheet_id,
        rows
    )

    format_sheet(
        service,
        spreadsheet_id,
        sheet_id,
        len(rows)
    )

    print()
    print("=" * 70)
    print("ПОКУПКИ КЛИЕНТОВ ВЫГРУЖЕНЫ")
    print("=" * 70)

    print()
    print(
        "Строк:",
        len(rows)
    )

    print(
        "Лист:",
        SHEET_TITLE
    )

    print(
        "Сортировка клиентов:",
        "как в RFM"
    )

    print("=" * 70)


if __name__ == "__main__":

    main()