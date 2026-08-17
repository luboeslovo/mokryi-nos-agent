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
    "delivery_sales_monthly.csv",
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

# В ОПиУ:
# P = январь 2026
# Q = февраль
# ...
# W = август
# AA = декабрь

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
            "Скрипт пока настроен на структуру ОПиУ 2026 года."
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

        reader = csv.DictReader(
            file
        )

        for row in reader:

            if row["month"] == month_key:

                return {
                    "month": month_key,
                    "yandex_commission": float(
                        row["yandex_commission"]
                    ),
                    "kuper_commission": float(
                        row["kuper_commission"]
                    ),
                }

    raise RuntimeError(
        f"В delivery_sales_monthly.csv нет месяца {month_key}"
    )


def main():

    print()
    print("=" * 70)
    print(
        "ВЫГРУЗКА КОМИССИЙ ДОСТАВОК В ОПиУ"
    )
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

    # ОПиУ:
    # 17 = Комиссия служб доставок (итог)
    # 18 = Яндекс.Еда
    # 19 = Купер

    target_range = (
        f"'ОПиУ'!{column}18:{column}19"
    )

    values = [
        [
            data[
                "yandex_commission"
            ]
        ],
        [
            data[
                "kuper_commission"
            ]
        ],
    ]

    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=target_range,
        valueInputOption="RAW",
        body={
            "values": values
        },
    ).execute()

    print()
    print(
        "Месяц:",
        data["month"],
    )

    print(
        "Яндекс Еда:",
        f"{data['yandex_commission']:,.2f} ₽",
    )

    print(
        "Купер:",
        f"{data['kuper_commission']:,.2f} ₽",
    )

    print()
    print(
        "Записано в:",
        target_range,
    )

    # Проверяем также итоговую строку 17,
    # которая должна пересчитаться формулой.

    check_range = (
        f"'ОПиУ'!{column}17:{column}19"
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

    rows = result.get(
        "values",
        [],
    )

    print()
    print("=" * 70)
    print("ПРОВЕРКА ОПиУ")
    print("=" * 70)

    labels = [
        "Комиссия служб доставок",
        "Яндекс.Еда",
        "Купер",
    ]

    for label, row in zip(
        labels,
        rows,
    ):

        value = (
            row[0]
            if row
            else None
        )

        print(
            f"{label}: {value}"
        )

    print()
    print("=" * 70)
    print("ГОТОВО")
    print("=" * 70)


if __name__ == "__main__":
    main()