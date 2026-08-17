import csv
import os
from datetime import datetime

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


PROJECT_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

CSV_FILE = os.path.join(
    PROJECT_DIR,
    "writeoffs_monthly.csv",
)

TOKEN_FILE = os.path.join(
    PROJECT_DIR,
    "token.json",
)

SPREADSHEET_ID_FILE = os.path.join(
    PROJECT_DIR,
    "rfm_spreadsheet_id.txt",
)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets"
]

MONTH_COLUMNS_2026 = {
    1: "P",
    2: "Q",
    3: "R",
    4: "S",
    5: "T",
    6: "U",
    7: "V",
    8: "W",
    9: "X",
    10: "Y",
    11: "Z",
    12: "AA",
}


def load_current_month():

    now = datetime.now()

    if now.year != 2026:
        raise RuntimeError(
            "Скрипт пока настроен на ОПиУ 2026 года."
        )

    month_key = (
        f"{now.year:04d}-{now.month:02d}"
    )

    with open(
        CSV_FILE,
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        reader = csv.DictReader(file)

        for row in reader:

            if row["month"] == month_key:

                return {
                    "month": month_key,
                    "inventory": float(
                        row["inventory"]
                    ),
                    "consumables": float(
                        row["consumables"]
                    ),
                    "expired": float(
                        row["expired"]
                    ),
                    "samples": float(
                        row["samples"]
                    ),
                    "defect": float(
                        row["defect"]
                    ),
                }

    raise RuntimeError(
        f"Нет данных за {month_key}"
    )


def main():

    print()
    print("=" * 70)
    print("ВЫГРУЗКА СПИСАНИЙ В ОПиУ")
    print("=" * 70)

    data = load_current_month()

    now = datetime.now()

    column = MONTH_COLUMNS_2026[
        now.month
    ]

    with open(
        SPREADSHEET_ID_FILE,
        "r",
        encoding="utf-8",
    ) as file:

        spreadsheet_id = (
            file.read().strip()
        )

    credentials = (
        Credentials.from_authorized_user_file(
            TOKEN_FILE,
            SCOPES,
        )
    )

    service = build(
        "sheets",
        "v4",
        credentials=credentials,
    )

    # Строки ОПиУ:
    # 31 Инвентаризация
    # 32 Расходные материалы — справочно
    # 33 Просрочка
    # 34 Просрок возмещаемый — НЕ трогаем
    # 35 Образцы
    # 36 Брак

    updates = {
        31: data["inventory"],
        32: data["consumables"],
        33: data["expired"],
        35: data["samples"],
        36: data["defect"],
    }

    body = {
        "valueInputOption": "RAW",
        "data": [],
    }

    for row, value in updates.items():

        body["data"].append(
            {
                "range":
                    f"'ОПиУ'!{column}{row}",

                "values": [
                    [value]
                ],
            }
        )

    service.spreadsheets().values().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body=body,
    ).execute()

    check_range = (
        f"'ОПиУ'!{column}30:{column}36"
    )

    result = (
        service
        .spreadsheets()
        .values()
        .get(
            spreadsheetId=spreadsheet_id,
            range=check_range,
            valueRenderOption="UNFORMATTED_VALUE",
        )
        .execute()
    )

    values = result.get(
        "values",
        []
    )

    labels = [
        "Итого Инвентаризация",
        "Инвентаризация",
        "Расходные материалы",
        "Просрочка",
        "Просрок возмещаемый",
        "Образцы",
        "Брак",
    ]

    print()
    print("Месяц:", data["month"])

    print()
    print("=" * 70)
    print("ПРОВЕРКА ОПиУ")
    print("=" * 70)

    for index, label in enumerate(
        labels
    ):

        if index < len(values):
            row = values[index]
            value = row[0] if row else None
        else:
            value = None

        print(
            f"{label}: {value}"
        )

    print()
    print("=" * 70)
    print("ГОТОВО")
    print("=" * 70)


if __name__ == "__main__":
    main()