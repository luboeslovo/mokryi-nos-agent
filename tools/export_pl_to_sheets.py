import csv
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


PROJECT_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

PL_FILE = os.path.join(
    PROJECT_DIR,
    "pl_monthly.csv"
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

SHEET_TITLE = "CRM PL"


FIELDS = [
    "Выручка",
    "Себестоимость",
    "Валовая прибыль",
    "Коммерческие расходы",
    "Прибыль от продаж",
    "Управленческие расходы",
    "Операционная прибыль (EBITDA)",
    "Прибыль до налогообложения",
    "Налоги",
    "Чистая прибыль",
]


MONTH_NAMES = {
    "01": "Январь",
    "02": "Февраль",
    "03": "Март",
    "04": "Апрель",
    "05": "Май",
    "06": "Июнь",
    "07": "Июль",
    "08": "Август",
    "09": "Сентябрь",
    "10": "Октябрь",
    "11": "Ноябрь",
    "12": "Декабрь",
}


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


def load_pl():

    with open(
        PL_FILE,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        rows = list(
            csv.DictReader(file)
        )

    rows.sort(
        key=lambda row: row["month"]
    )

    return rows


def month_title(month):

    year, month_number = (
        month.split("-")
    )

    return (
        f"{MONTH_NAMES[month_number]} "
        f"{year}"
    )


def build_values(rows):

    header = [
        "Показатель",
    ]

    for row in rows:

        header.append(
            month_title(
                row["month"]
            )
        )

    values = [
        header
    ]

    for field in FIELDS:

        line = [
            field
        ]

        for row in rows:

            try:
                value = float(
                    row[field]
                )
            except (
                TypeError,
                ValueError,
            ):
                value = 0

            line.append(
                value
            )

        values.append(
            line
        )

    return values


def get_sheet(
    service,
    spreadsheet_id
):

    metadata = (
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

            return properties[
                "sheetId"
            ]

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
                                    "rowCount": 100,
                                    "columnCount": 40,
                                },
                            }
                        }
                    }
                ]
            }
        )
        .execute()
    )

    return (
        response["replies"][0]
        ["addSheet"]
        ["properties"]
        ["sheetId"]
    )


def main():

    print()
    print("=" * 70)
    print("ВЫГРУЗКА CRM PL В GOOGLE SHEETS")
    print("=" * 70)

    rows = load_pl()

    print()
    print(
        "Месяцев:",
        len(rows)
    )

    values = build_values(
        rows
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

    sheet_id = get_sheet(
        service,
        spreadsheet_id
    )

    (
        service
        .spreadsheets()
        .values()
        .clear(
            spreadsheetId=spreadsheet_id,
            range=f"'{SHEET_TITLE}'!A:AN",
            body={}
        )
        .execute()
    )

    (
        service
        .spreadsheets()
        .values()
        .update(
            spreadsheetId=spreadsheet_id,
            range=f"'{SHEET_TITLE}'!A1",
            valueInputOption="RAW",
            body={
                "values": values
            }
        )
        .execute()
    )

    column_count = (
        len(rows) + 1
    )

    row_count = (
        len(FIELDS) + 1
    )

    (
        service
        .spreadsheets()
        .batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={
                "requests": [
                    {
                        "updateSheetProperties": {
                            "properties": {
                                "sheetId": sheet_id,
                                "gridProperties": {
                                    "frozenRowCount": 1,
                                    "frozenColumnCount": 1,
                                },
                            },
                            "fields": (
                                "gridProperties."
                                "frozenRowCount,"
                                "gridProperties."
                                "frozenColumnCount"
                            ),
                        }
                    },
                    {
                        "repeatCell": {
                            "range": {
                                "sheetId": sheet_id,
                                "startRowIndex": 0,
                                "endRowIndex": 1,
                                "startColumnIndex": 0,
                                "endColumnIndex": column_count,
                            },
                            "cell": {
                                "userEnteredFormat": {
                                    "textFormat": {
                                        "bold": True,
                                        "foregroundColor": {
                                            "red": 1,
                                            "green": 1,
                                            "blue": 1,
                                        },
                                    },
                                    "backgroundColor": {
                                        "red": 0.12,
                                        "green": 0.28,
                                        "blue": 0.45,
                                    },
                                    "horizontalAlignment": "CENTER",
                                }
                            },
                            "fields": (
                                "userEnteredFormat"
                            ),
                        }
                    },
                    {
                        "repeatCell": {
                            "range": {
                                "sheetId": sheet_id,
                                "startRowIndex": 1,
                                "endRowIndex": row_count,
                                "startColumnIndex": 0,
                                "endColumnIndex": 1,
                            },
                            "cell": {
                                "userEnteredFormat": {
                                    "textFormat": {
                                        "bold": True,
                                    }
                                }
                            },
                            "fields": (
                                "userEnteredFormat."
                                "textFormat"
                            ),
                        }
                    },
                    {
                        "repeatCell": {
                            "range": {
                                "sheetId": sheet_id,
                                "startRowIndex": 1,
                                "endRowIndex": row_count,
                                "startColumnIndex": 1,
                                "endColumnIndex": column_count,
                            },
                            "cell": {
                                "userEnteredFormat": {
                                    "numberFormat": {
                                        "type": "NUMBER",
                                        "pattern": (
                                            '#,##0.00;'
                                            '[Red](#,##0.00);-'
                                        ),
                                    }
                                }
                            },
                            "fields": (
                                "userEnteredFormat."
                                "numberFormat"
                            ),
                        }
                    },
                    {
                        "autoResizeDimensions": {
                            "dimensions": {
                                "sheetId": sheet_id,
                                "dimension": "COLUMNS",
                                "startIndex": 0,
                                "endIndex": column_count,
                            }
                        }
                    },
                ]
            }
        )
        .execute()
    )

    print()
    print("=" * 70)
    print("CRM PL ВЫГРУЖЕН")
    print("=" * 70)

    print()
    print(
        "Лист:",
        SHEET_TITLE
    )

    print(
        "Месяцев:",
        len(rows)
    )

    print()


if __name__ == "__main__":
    main()