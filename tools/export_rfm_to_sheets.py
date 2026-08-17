import csv
from collections import Counter
from datetime import datetime
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


PROJECT_DIR = Path(__file__).resolve().parent.parent

CSV_FILE = PROJECT_DIR / "customer_rfm.csv"
CREDENTIALS_FILE = PROJECT_DIR / "credentials.json"
TOKEN_FILE = PROJECT_DIR / "token.json"
SPREADSHEET_ID_FILE = PROJECT_DIR / "rfm_spreadsheet_id.txt"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets"
]

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
    for index, segment in enumerate(SEGMENT_ORDER)
}

SEGMENT_COLORS = {
    "VIP": (1.00, 0.90, 0.55),
    "Лояльный": (0.78, 0.93, 0.80),
    "Новый": (0.80, 0.89, 1.00),
    "Активный": (0.87, 0.95, 0.87),
    "Нужно удержать": (1.00, 0.88, 0.68),
    "Остывает": (1.00, 0.95, 0.72),
    "Ценный под риском": (1.00, 0.72, 0.72),
    "Под риском": (1.00, 0.82, 0.68),
    "Потерянный ценный": (0.93, 0.72, 0.78),
    "Потерянный": (0.88, 0.88, 0.88),
}

HEADERS = [
    "ID клиента",
    "Имя в чеке",
    "Имя",
    "Фамилия",
    "Телефон",
    "Первая покупка",
    "Последняя покупка",
    "Дней с покупки",
    "Покупок",
    "Потрачено",
    "Средний чек",
    "Средний интервал, дней",
    "R",
    "F",
    "M",
    "RFM",
    "Балл RFM",
    "Сегмент",
    "Просрочка цикла",
]


def get_credentials():

    creds = None

    if TOKEN_FILE.exists():

        creds = Credentials.from_authorized_user_file(
            TOKEN_FILE,
            SCOPES,
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
                SCOPES,
            )

            creds = flow.run_local_server(
                port=0
            )

        TOKEN_FILE.write_text(
            creds.to_json(),
            encoding="utf-8",
        )

    return creds


def to_int(value):

    if value in (None, ""):
        return ""

    return int(
        float(value)
    )


def to_float(value):

    if value in (None, ""):
        return ""

    return float(value)


def load_rfm():

    if not CSV_FILE.exists():

        raise FileNotFoundError(
            f"Не найден файл: {CSV_FILE}"
        )

    with CSV_FILE.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        raw_rows = list(
            csv.DictReader(file)
        )

    raw_rows.sort(
        key=lambda row: (
            SEGMENT_PRIORITY.get(
                row["segment"],
                999,
            ),
            -to_float(
                row["monetary"]
            ),
        )
    )

    rows = []

    for row in raw_rows:

        rows.append(
            [
                row["customer_id"],
                row["check_name"],
                row["name"],
                row["lastname"],
                row["phone"],
                row["first_purchase"],
                row["last_purchase"],
                to_int(row["recency_days"]),
                to_int(row["frequency"]),
                to_float(row["monetary"]),
                to_float(row["average_check"]),
                to_float(
                    row["average_interval_days"]
                ),
                to_int(row["r_score"]),
                to_int(row["f_score"]),
                to_int(row["m_score"]),
                row["rfm_code"],
                to_int(row["rfm_total"]),
                row["segment"],
                to_float(
                    row["cycle_overdue_ratio"]
                ),
            ]
        )

    return raw_rows, rows


def build_summary(raw_rows):

    counts = Counter(
        row["segment"]
        for row in raw_rows
    )

    total = len(raw_rows)

    recent_30 = sum(
        to_int(row["recency_days"]) <= 30
        for row in raw_rows
    )

    repeat_clients = sum(
        to_int(row["frequency"]) >= 2
        for row in raw_rows
    )

    risk_total = (
        counts["Нужно удержать"]
        + counts["Ценный под риском"]
        + counts["Под риском"]
    )

    lost_total = (
        counts["Потерянный ценный"]
        + counts["Потерянный"]
    )

    summary = [
        [
            "RFM — Мокрый нос",
            "",
        ],
        [
            "Обновлено",
            datetime.now().strftime(
                "%d.%m.%Y %H:%M"
            ),
        ],
        [
            "Всего клиентов",
            total,
        ],
        [
            "Были за последние 30 дней",
            recent_30,
        ],
        [
            "Повторных клиентов (2+ покупок)",
            repeat_clients,
        ],
        [
            "VIP",
            counts["VIP"],
        ],
        [
            "Лояльных",
            counts["Лояльный"],
        ],
        [
            "Под риском всего",
            risk_total,
        ],
        [
            "Потерянных всего",
            lost_total,
        ],
        [
            "",
            "",
        ],
        [
            "Сегмент",
            "Клиентов",
        ],
    ]

    for segment in SEGMENT_ORDER:

        summary.append(
            [
                segment,
                counts[segment],
            ]
        )

    summary.extend(
        [
            [
                "",
                "",
            ],
            [
                "Как читать показатели",
                "",
            ],
            [
                "R",
                (
                    "Давность покупки: "
                    "5 = 0–30 дней; "
                    "4 = 31–60; "
                    "3 = 61–90; "
                    "2 = 91–150; "
                    "1 = 151+"
                ),
            ],
            [
                "F",
                (
                    "Частота: "
                    "1 = 1 покупка; "
                    "2 = 2; "
                    "3 = 3–5; "
                    "4 = 6–10; "
                    "5 = 11+"
                ),
            ],
            [
                "M",
                (
                    "Денежная ценность "
                    "от 1 до 5 по квинтилям "
                    "текущей клиентской базы"
                ),
            ],
            [
                "Просрочка цикла",
                (
                    "1.0 = клиент пришёл "
                    "примерно в свой обычный срок; "
                    ">1 = уже позже своего "
                    "обычного интервала"
                ),
            ],
            [
                "VIP",
                (
                    "Последняя покупка ≤30 дней, "
                    "6+ покупок и top 10% "
                    "по денежной ценности"
                ),
            ],
        ]
    )

    return summary


def get_sheet_info(service, spreadsheet_id):

    result = (
        service
        .spreadsheets()
        .get(
            spreadsheetId=spreadsheet_id,
            fields="sheets(properties(sheetId,title,gridProperties))",
        )
        .execute()
    )

    result_by_title = {}

    for sheet in result["sheets"]:

        properties = sheet[
            "properties"
        ]

        result_by_title[
            properties["title"]
        ] = properties

    return result_by_title


def rgb(color_tuple):

    red, green, blue = color_tuple

    return {
        "red": red,
        "green": green,
        "blue": blue,
    }


def main():

    print()
    print("=" * 70)
    print("ВЫГРУЗКА RFM В GOOGLE SHEETS")
    print("=" * 70)

    if not SPREADSHEET_ID_FILE.exists():

        raise FileNotFoundError(
            "Не найден rfm_spreadsheet_id.txt"
        )

    spreadsheet_id = (
        SPREADSHEET_ID_FILE
        .read_text(
            encoding="utf-8"
        )
        .strip()
    )

    raw_rows, rows = load_rfm()

    print()
    print(
        f"Клиентов для выгрузки: {len(rows)}"
    )

    creds = get_credentials()

    service = build(
        "sheets",
        "v4",
        credentials=creds,
    )

    sheets = get_sheet_info(
        service,
        spreadsheet_id,
    )

    if "RFM" not in sheets:

        raise RuntimeError(
            "В таблице нет листа RFM"
        )

    if "Сводка" not in sheets:

        raise RuntimeError(
            "В таблице нет листа Сводка"
        )

    rfm_sheet_id = sheets[
        "RFM"
    ]["sheetId"]

    summary_sheet_id = sheets[
        "Сводка"
    ]["sheetId"]

    required_rows = len(rows) + 100

    current_rows = sheets[
        "RFM"
    ]["gridProperties"]["rowCount"]

    resize_requests = []

    if current_rows < required_rows:

        resize_requests.append(
            {
                "updateSheetProperties": {
                    "properties": {
                        "sheetId": rfm_sheet_id,
                        "gridProperties": {
                            "rowCount": required_rows,
                        },
                    },
                    "fields": (
                        "gridProperties.rowCount"
                    ),
                }
            }
        )

    if resize_requests:

        (
            service
            .spreadsheets()
            .batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={
                    "requests": resize_requests
                },
            )
            .execute()
        )

    (
        service
        .spreadsheets()
        .values()
        .clear(
            spreadsheetId=spreadsheet_id,
            range="'RFM'!A:S",
            body={},
        )
        .execute()
    )

    (
        service
        .spreadsheets()
        .values()
        .clear(
            spreadsheetId=spreadsheet_id,
            range="'Сводка'!A:E",
            body={},
        )
        .execute()
    )

    rfm_values = [
        HEADERS
    ] + rows

    (
        service
        .spreadsheets()
        .values()
        .update(
            spreadsheetId=spreadsheet_id,
            range="'RFM'!A1",
            valueInputOption="RAW",
            body={
                "values": rfm_values
            },
        )
        .execute()
    )

    summary_values = build_summary(
        raw_rows
    )

    (
        service
        .spreadsheets()
        .values()
        .update(
            spreadsheetId=spreadsheet_id,
            range="'Сводка'!A1",
            valueInputOption="RAW",
            body={
                "values": summary_values
            },
        )
        .execute()
    )

    data_end_row = len(rows) + 1

    format_requests = []

    format_requests.append(
        {
            "updateSheetProperties": {
                "properties": {
                    "sheetId": rfm_sheet_id,
                    "gridProperties": {
                        "frozenRowCount": 1,
                    },
                },
                "fields": (
                    "gridProperties."
                    "frozenRowCount"
                ),
            }
        }
    )

    format_requests.append(
        {
            "repeatCell": {
                "range": {
                    "sheetId": rfm_sheet_id,
                    "startRowIndex": 0,
                    "endRowIndex": 1,
                    "startColumnIndex": 0,
                    "endColumnIndex": 19,
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {
                            "red": 0.15,
                            "green": 0.33,
                            "blue": 0.25,
                        },
                        "textFormat": {
                            "foregroundColor": {
                                "red": 1,
                                "green": 1,
                                "blue": 1,
                            },
                            "bold": True,
                        },
                        "horizontalAlignment": (
                            "CENTER"
                        ),
                        "verticalAlignment": (
                            "MIDDLE"
                        ),
                        "wrapStrategy": "WRAP",
                    }
                },
                "fields": (
                    "userEnteredFormat"
                ),
            }
        }
    )

    format_requests.append(
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": rfm_sheet_id,
                    "dimension": "ROWS",
                    "startIndex": 0,
                    "endIndex": 1,
                },
                "properties": {
                    "pixelSize": 42
                },
                "fields": "pixelSize",
            }
        }
    )

    widths = [
        95,
        170,
        105,
        130,
        120,
        145,
        145,
        105,
        80,
        110,
        110,
        145,
        55,
        55,
        55,
        70,
        90,
        155,
        145,
    ]

    for column_index, width in enumerate(
        widths
    ):

        format_requests.append(
            {
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": rfm_sheet_id,
                        "dimension": "COLUMNS",
                        "startIndex": column_index,
                        "endIndex": (
                            column_index + 1
                        ),
                    },
                    "properties": {
                        "pixelSize": width
                    },
                    "fields": "pixelSize",
                }
            }
        )

    format_requests.append(
        {
            "repeatCell": {
                "range": {
                    "sheetId": rfm_sheet_id,
                    "startRowIndex": 1,
                    "endRowIndex": data_end_row,
                    "startColumnIndex": 0,
                    "endColumnIndex": 19,
                },
                "cell": {
                    "userEnteredFormat": {
                        "verticalAlignment": (
                            "MIDDLE"
                        )
                    }
                },
                "fields": (
                    "userEnteredFormat."
                    "verticalAlignment"
                ),
            }
        }
    )

    for column_index in [
        0,
        4,
        15,
    ]:

        format_requests.append(
            {
                "repeatCell": {
                    "range": {
                        "sheetId": rfm_sheet_id,
                        "startRowIndex": 1,
                        "endRowIndex": data_end_row,
                        "startColumnIndex": (
                            column_index
                        ),
                        "endColumnIndex": (
                            column_index + 1
                        ),
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "numberFormat": {
                                "type": "TEXT",
                                "pattern": "@",
                            }
                        }
                    },
                    "fields": (
                        "userEnteredFormat."
                        "numberFormat"
                    ),
                }
            }
        )

    for column_index in [
        9,
        10,
    ]:

        format_requests.append(
            {
                "repeatCell": {
                    "range": {
                        "sheetId": rfm_sheet_id,
                        "startRowIndex": 1,
                        "endRowIndex": data_end_row,
                        "startColumnIndex": (
                            column_index
                        ),
                        "endColumnIndex": (
                            column_index + 1
                        ),
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "numberFormat": {
                                "type": "NUMBER",
                                "pattern": (
                                    '#,##0.00 "₽"'
                                ),
                            }
                        }
                    },
                    "fields": (
                        "userEnteredFormat."
                        "numberFormat"
                    ),
                }
            }
        )

    for column_index in [
        11,
        18,
    ]:

        format_requests.append(
            {
                "repeatCell": {
                    "range": {
                        "sheetId": rfm_sheet_id,
                        "startRowIndex": 1,
                        "endRowIndex": data_end_row,
                        "startColumnIndex": (
                            column_index
                        ),
                        "endColumnIndex": (
                            column_index + 1
                        ),
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "numberFormat": {
                                "type": "NUMBER",
                                "pattern": "0.00",
                            }
                        }
                    },
                    "fields": (
                        "userEnteredFormat."
                        "numberFormat"
                    ),
                }
            }
        )

    format_requests.append(
        {
            "repeatCell": {
                "range": {
                    "sheetId": rfm_sheet_id,
                    "startRowIndex": 1,
                    "endRowIndex": data_end_row,
                    "startColumnIndex": 17,
                    "endColumnIndex": 18,
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {
                            "red": 1,
                            "green": 1,
                            "blue": 1,
                        },
                        "textFormat": {
                            "bold": True,
                        },
                    }
                },
                "fields": (
                    "userEnteredFormat."
                    "backgroundColor,"
                    "userEnteredFormat."
                    "textFormat.bold"
                ),
            }
        }
    )

    row_index = 1

    for segment in SEGMENT_ORDER:

        segment_count = sum(
            row["segment"] == segment
            for row in raw_rows
        )

        if segment_count == 0:
            continue

        start = row_index
        end = row_index + segment_count

        format_requests.append(
            {
                "repeatCell": {
                    "range": {
                        "sheetId": rfm_sheet_id,
                        "startRowIndex": start,
                        "endRowIndex": end,
                        "startColumnIndex": 17,
                        "endColumnIndex": 18,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": rgb(
                                SEGMENT_COLORS[
                                    segment
                                ]
                            ),
                            "textFormat": {
                                "bold": True,
                            },
                        }
                    },
                    "fields": (
                        "userEnteredFormat."
                        "backgroundColor,"
                        "userEnteredFormat."
                        "textFormat.bold"
                    ),
                }
            }
        )

        row_index = end

    format_requests.append(
        {
            "setBasicFilter": {
                "filter": {
                    "range": {
                        "sheetId": rfm_sheet_id,
                        "startRowIndex": 0,
                        "endRowIndex": data_end_row,
                        "startColumnIndex": 0,
                        "endColumnIndex": 19,
                    }
                }
            }
        }
    )

    format_requests.append(
        {
            "repeatCell": {
                "range": {
                    "sheetId": summary_sheet_id,
                    "startRowIndex": 0,
                    "endRowIndex": 1,
                    "startColumnIndex": 0,
                    "endColumnIndex": 2,
                },
                "cell": {
                    "userEnteredFormat": {
                        "textFormat": {
                            "bold": True,
                            "fontSize": 16,
                        }
                    }
                },
                "fields": (
                    "userEnteredFormat."
                    "textFormat"
                ),
            }
        }
    )

    format_requests.append(
        {
            "repeatCell": {
                "range": {
                    "sheetId": summary_sheet_id,
                    "startRowIndex": 10,
                    "endRowIndex": 11,
                    "startColumnIndex": 0,
                    "endColumnIndex": 2,
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {
                            "red": 0.15,
                            "green": 0.33,
                            "blue": 0.25,
                        },
                        "textFormat": {
                            "foregroundColor": {
                                "red": 1,
                                "green": 1,
                                "blue": 1,
                            },
                            "bold": True,
                        },
                    }
                },
                "fields": (
                    "userEnteredFormat"
                ),
            }
        }
    )

    format_requests.append(
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": summary_sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": 0,
                    "endIndex": 1,
                },
                "properties": {
                    "pixelSize": 230
                },
                "fields": "pixelSize",
            }
        }
    )

    format_requests.append(
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": summary_sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": 1,
                    "endIndex": 2,
                },
                "properties": {
                    "pixelSize": 520
                },
                "fields": "pixelSize",
            }
        }
    )

    format_requests.append(
        {
            "repeatCell": {
                "range": {
                    "sheetId": summary_sheet_id,
                    "startRowIndex": 0,
                    "endRowIndex": (
                        len(summary_values)
                    ),
                    "startColumnIndex": 0,
                    "endColumnIndex": 2,
                },
                "cell": {
                    "userEnteredFormat": {
                        "wrapStrategy": "WRAP",
                        "verticalAlignment": (
                            "MIDDLE"
                        ),
                    }
                },
                "fields": (
                    "userEnteredFormat."
                    "wrapStrategy,"
                    "userEnteredFormat."
                    "verticalAlignment"
                ),
            }
        }
    )

    (
        service
        .spreadsheets()
        .batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={
                "requests": format_requests
            },
        )
        .execute()
    )

    url = (
        "https://docs.google.com/"
        f"spreadsheets/d/{spreadsheet_id}/edit"
    )

    print()
    print("=" * 70)
    print("RFM ВЫГРУЖЕНА")
    print("=" * 70)

    print()
    print(
        f"Клиентов: {len(rows)}"
    )

    print()
    print("Листы обновлены:")
    print("RFM")
    print("Сводка")

    print()
    print("Ссылка:")
    print(url)

    print()
    print("=" * 70)


if __name__ == "__main__":
    main()
