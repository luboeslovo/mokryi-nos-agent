from pathlib import Path

from openpyxl import load_workbook

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


PROJECT_DIR = Path(__file__).resolve().parent.parent

EXCEL_FILE = (
    PROJECT_DIR
    / "Сводная Дни,Месяцы (1)(1).xlsx"
)

CREDENTIALS_FILE = (
    PROJECT_DIR
    / "credentials.json"
)

TOKEN_FILE = (
    PROJECT_DIR
    / "token.json"
)

SPREADSHEET_ID_FILE = (
    PROJECT_DIR
    / "rfm_spreadsheet_id.txt"
)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets"
]

TARGET_SHEET = "ПО ДНЯМ НЕДЕЛИ"

SOURCE_REFERENCE = "'ПО ЧИСЛАМ'!"

BATCH_SIZE = 100


def print_header(text):

    print()
    print("=" * 78)
    print(text)
    print("=" * 78)
    print()


def get_credentials():

    creds = None

    if TOKEN_FILE.exists():

        creds = (
            Credentials
            .from_authorized_user_file(
                TOKEN_FILE,
                SCOPES,
            )
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

            flow = (
                InstalledAppFlow
                .from_client_secrets_file(
                    CREDENTIALS_FILE,
                    SCOPES,
                )
            )

            creds = (
                flow.run_local_server(
                    port=0
                )
            )

        TOKEN_FILE.write_text(
            creds.to_json(),
            encoding="utf-8",
        )

    return creds


def get_spreadsheet_id():

    if not SPREADSHEET_ID_FILE.exists():

        raise FileNotFoundError(
            "Не найден "
            "rfm_spreadsheet_id.txt"
        )

    spreadsheet_id = (
        SPREADSHEET_ID_FILE
        .read_text(
            encoding="utf-8"
        )
        .strip()
    )

    if not spreadsheet_id:

        raise RuntimeError(
            "rfm_spreadsheet_id.txt пустой"
        )

    return spreadsheet_id


def load_cross_sheet_formulas():

    if not EXCEL_FILE.exists():

        raise FileNotFoundError(
            "Не найден исходный Excel:\n"
            f"{EXCEL_FILE}"
        )

    workbook = load_workbook(
        EXCEL_FILE,
        data_only=False,
        read_only=False,
    )

    if TARGET_SHEET not in workbook.sheetnames:

        workbook.close()

        raise RuntimeError(
            f"В Excel нет листа "
            f"«{TARGET_SHEET}»"
        )

    worksheet = workbook[
        TARGET_SHEET
    ]

    formulas = []

    for row in worksheet.iter_rows():

        for cell in row:

            value = cell.value

            if not isinstance(
                value,
                str,
            ):

                continue

            if not value.startswith(
                "="
            ):

                continue

            if SOURCE_REFERENCE not in value:

                continue

            formulas.append(
                {
                    "cell": (
                        cell.coordinate
                    ),
                    "formula": value,
                }
            )

    workbook.close()

    return formulas


def write_formulas(
    service,
    spreadsheet_id,
    formulas,
):

    total = len(
        formulas
    )

    written = 0

    for start in range(
        0,
        total,
        BATCH_SIZE,
    ):

        batch = formulas[
            start:
            start + BATCH_SIZE
        ]

        data = []

        for item in batch:

            cell = item[
                "cell"
            ]

            formula = item[
                "formula"
            ]

            data.append(
                {
                    "range": (
                        f"'{TARGET_SHEET}'!"
                        f"{cell}"
                    ),
                    "majorDimension": (
                        "ROWS"
                    ),
                    "values": [
                        [
                            formula
                        ]
                    ],
                }
            )

        (
            service
            .spreadsheets()
            .values()
            .batchUpdate(
                spreadsheetId=(
                    spreadsheet_id
                ),
                body={
                    "valueInputOption": (
                        "USER_ENTERED"
                    ),
                    "data": data,
                },
            )
            .execute()
        )

        written += len(
            batch
        )

        print(
            f"Восстановлено: "
            f"{written} / {total}"
        )


def count_ref_errors(
    service,
    spreadsheet_id,
):

    result = (
        service
        .spreadsheets()
        .values()
        .get(
            spreadsheetId=(
                spreadsheet_id
            ),
            range=(
                f"'{TARGET_SHEET}'!"
                "A1:I200"
            ),
            valueRenderOption=(
                "FORMATTED_VALUE"
            ),
        )
        .execute()
    )

    values = result.get(
        "values",
        [],
    )

    errors = []

    for row_index, row in enumerate(
        values,
        start=1,
    ):

        for column_index, value in enumerate(
            row,
            start=1,
        ):

            if "#REF!" not in str(
                value
            ):

                continue

            errors.append(
                (
                    row_index,
                    column_index,
                    value,
                )
            )

    return errors


def main():

    print_header(
        "ВОССТАНОВЛЕНИЕ МЕЖЛИСТОВЫХ "
        "ФОРМУЛ"
    )

    print(
        f"Excel: {EXCEL_FILE.name}"
    )

    print(
        f"Лист: {TARGET_SHEET}"
    )

    formulas = (
        load_cross_sheet_formulas()
    )

    print()
    print(
        "Найдено формул, "
        "ссылающихся на "
        "«ПО ЧИСЛАМ»: "
        f"{len(formulas)}"
    )

    if not formulas:

        raise RuntimeError(
            "Не найдено ни одной "
            "межлистовой формулы."
        )

    print()
    print(
        "Первые формулы:"
    )

    for item in formulas[:5]:

        print(
            f"{item['cell']}: "
            f"{item['formula']}"
        )

    spreadsheet_id = (
        get_spreadsheet_id()
    )

    creds = get_credentials()

    service = build(
        "sheets",
        "v4",
        credentials=creds,
    )

    print_header(
        "ЗАПИСЫВАЮ ФОРМУЛЫ "
        "В GOOGLE SHEETS"
    )

    write_formulas(
        service,
        spreadsheet_id,
        formulas,
    )

    print_header(
        "ПРОВЕРЯЮ #REF!"
    )

    errors = count_ref_errors(
        service,
        spreadsheet_id,
    )

    if errors:

        print(
            f"Осталось #REF!: "
            f"{len(errors)}"
        )

        print()

        print(
            "Первые проблемные ячейки:"
        )

        for (
            row_index,
            column_index,
            value,
        ) in errors[:20]:

            print(
                f"строка {row_index}, "
                f"столбец {column_index}: "
                f"{value}"
            )

        raise RuntimeError(
            "Некоторые #REF! "
            "остались."
        )

    print(
        "#REF! не найдено."
    )

    print_header(
        "ФОРМУЛЫ ВОССТАНОВЛЕНЫ"
    )

    print(
        f"Восстановлено формул: "
        f"{len(formulas)}"
    )

    print()

    print(
        "Оформление листов "
        "не изменялось."
    )

    print()

    print(
        "https://docs.google.com/"
        "spreadsheets/d/"
        f"{spreadsheet_id}/edit"
    )


if __name__ == "__main__":

    main()