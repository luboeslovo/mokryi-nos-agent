import time
from datetime import datetime
from pathlib import Path

from openpyxl import load_workbook

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload


PROJECT_DIR = Path(__file__).resolve().parent.parent

EXCEL_FILE = (
    PROJECT_DIR
    / "Сводная Дни,Месяцы (1)(1).xlsx"
)

CREDENTIALS_FILE = (
    PROJECT_DIR
    / "credentials.json"
)

IMPORT_TOKEN_FILE = (
    PROJECT_DIR
    / "excel_import_token.json"
)

SPREADSHEET_ID_FILE = (
    PROJECT_DIR
    / "rfm_spreadsheet_id.txt"
)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

SHEETS_TO_IMPORT = [
    "ПО ЧИСЛАМ",
    "ПО ДНЯМ НЕДЕЛИ",
]

XLSX_MIME = (
    "application/vnd.openxmlformats-officedocument."
    "spreadsheetml.sheet"
)

GOOGLE_SHEETS_MIME = (
    "application/vnd.google-apps.spreadsheet"
)

FORMULA_BATCH_SIZE = 100


def print_header(text):

    print()
    print("=" * 78)
    print(text)
    print("=" * 78)
    print()


def get_credentials():

    creds = None

    if IMPORT_TOKEN_FILE.exists():

        try:

            creds = (
                Credentials
                .from_authorized_user_file(
                    IMPORT_TOKEN_FILE,
                    SCOPES,
                )
            )

            if not creds.has_scopes(
                SCOPES
            ):

                creds = None

        except Exception:

            creds = None

    if (
        creds
        and creds.expired
        and creds.refresh_token
    ):

        try:

            creds.refresh(
                Request()
            )

        except Exception:

            creds = None

    if not creds or not creds.valid:

        if not CREDENTIALS_FILE.exists():

            raise FileNotFoundError(
                "Не найден credentials.json"
            )

        print(
            "Нужна авторизация Google "
            "Sheets + Drive."
        )

        print(
            "Основной token.json "
            "НЕ изменяется."
        )

        print()

        flow = (
            InstalledAppFlow
            .from_client_secrets_file(
                CREDENTIALS_FILE,
                SCOPES,
            )
        )

        creds = flow.run_local_server(
            port=0
        )

        IMPORT_TOKEN_FILE.write_text(
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


def get_sheets(
    sheets_service,
    spreadsheet_id,
):

    result = (
        sheets_service
        .spreadsheets()
        .get(
            spreadsheetId=spreadsheet_id,
            fields=(
                "sheets("
                "properties("
                "sheetId,"
                "title,"
                "index,"
                "gridProperties"
                ")"
                ")"
            ),
        )
        .execute()
    )

    output = {}

    for sheet in result.get(
        "sheets",
        [],
    ):

        props = sheet[
            "properties"
        ]

        output[
            props["title"]
        ] = props

    return output


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

    formulas = []

    for target_sheet in SHEETS_TO_IMPORT:

        if (
            target_sheet
            not in workbook.sheetnames
        ):

            workbook.close()

            raise RuntimeError(
                "В Excel нет листа "
                f"«{target_sheet}»"
            )

        worksheet = workbook[
            target_sheet
        ]

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

                references_imported_sheet = False

                for source_sheet in SHEETS_TO_IMPORT:

                    quoted_reference = (
                        f"'{source_sheet}'!"
                    )

                    plain_reference = (
                        f"{source_sheet}!"
                    )

                    if (
                        quoted_reference
                        in value
                        or plain_reference
                        in value
                    ):

                        references_imported_sheet = True

                        break

                if not references_imported_sheet:

                    continue

                formulas.append(
                    {
                        "sheet": target_sheet,
                        "cell": cell.coordinate,
                        "formula": value,
                    }
                )

    workbook.close()

    return formulas


def upload_excel_as_google_sheet(
    drive_service,
):

    timestamp = (
        datetime.now()
        .strftime(
            "%Y%m%d_%H%M%S"
        )
    )

    temp_name = (
        "TEMP Мокрый нос Excel import "
        f"{timestamp}"
    )

    metadata = {
        "name": temp_name,
        "mimeType": (
            GOOGLE_SHEETS_MIME
        ),
    }

    media = MediaFileUpload(
        str(EXCEL_FILE),
        mimetype=XLSX_MIME,
        resumable=True,
    )

    print(
        "Загружаю Excel во временную "
        "Google-таблицу..."
    )

    created = (
        drive_service
        .files()
        .create(
            body=metadata,
            media_body=media,
            fields="id,name,mimeType",
        )
        .execute()
    )

    return created["id"]


def wait_for_google_conversion(
    sheets_service,
    spreadsheet_id,
):

    last_error = None

    for attempt in range(
        1,
        16,
    ):

        try:

            result = (
                sheets_service
                .spreadsheets()
                .get(
                    spreadsheetId=(
                        spreadsheet_id
                    ),
                    fields=(
                        "spreadsheetId,"
                        "properties(title),"
                        "sheets("
                        "properties("
                        "sheetId,title"
                        ")"
                        ")"
                    ),
                )
                .execute()
            )

            return result

        except HttpError as exc:

            last_error = exc

            print(
                "Жду завершения "
                f"конвертации... "
                f"{attempt}/15"
            )

            time.sleep(
                1
            )

    raise RuntimeError(
        "Google не завершил "
        "конвертацию Excel."
    ) from last_error


def copy_sheet(
    sheets_service,
    source_spreadsheet_id,
    source_sheet_id,
    target_spreadsheet_id,
):

    result = (
        sheets_service
        .spreadsheets()
        .sheets()
        .copyTo(
            spreadsheetId=(
                source_spreadsheet_id
            ),
            sheetId=source_sheet_id,
            body={
                "destinationSpreadsheetId": (
                    target_spreadsheet_id
                )
            },
        )
        .execute()
    )

    return result


def delete_sheets(
    sheets_service,
    spreadsheet_id,
    sheet_ids,
):

    if not sheet_ids:

        return

    requests = []

    for sheet_id in sheet_ids:

        requests.append(
            {
                "deleteSheet": {
                    "sheetId": sheet_id
                }
            }
        )

    (
        sheets_service
        .spreadsheets()
        .batchUpdate(
            spreadsheetId=(
                spreadsheet_id
            ),
            body={
                "requests": requests
            },
        )
        .execute()
    )


def switch_to_new_sheets(
    sheets_service,
    spreadsheet_id,
    old_sheets,
    copied_sheets,
):

    timestamp = (
        datetime.now()
        .strftime(
            "%Y%m%d_%H%M%S"
        )
    )

    backup_sheets = {}

    requests = []

    # Старые листы пока НЕ удаляем.
    # Сначала просто переименовываем их.
    for title in SHEETS_TO_IMPORT:

        old = old_sheets.get(
            title
        )

        if not old:

            continue

        backup_title = (
            f"__BACKUP_{title}_{timestamp}"
        )

        backup_sheets[
            title
        ] = {
            "sheetId": old["sheetId"],
            "title": backup_title,
            "originalTitle": title,
        }

        requests.append(
            {
                "updateSheetProperties": {
                    "properties": {
                        "sheetId": (
                            old["sheetId"]
                        ),
                        "title": (
                            backup_title
                        ),
                    },
                    "fields": "title",
                }
            }
        )

    # Новым копиям даём нормальные имена.
    for title in SHEETS_TO_IMPORT:

        copied = copied_sheets[
            title
        ]

        requests.append(
            {
                "updateSheetProperties": {
                    "properties": {
                        "sheetId": (
                            copied["sheetId"]
                        ),
                        "title": title,
                    },
                    "fields": "title",
                }
            }
        )

    (
        sheets_service
        .spreadsheets()
        .batchUpdate(
            spreadsheetId=(
                spreadsheet_id
            ),
            body={
                "requests": requests
            },
        )
        .execute()
    )

    return backup_sheets


def write_cross_sheet_formulas(
    sheets_service,
    spreadsheet_id,
    formulas,
):

    total = len(
        formulas
    )

    if not total:

        print(
            "Межлистовых формул "
            "не найдено."
        )

        return

    written = 0

    for start in range(
        0,
        total,
        FORMULA_BATCH_SIZE,
    ):

        batch = formulas[
            start:
            start + FORMULA_BATCH_SIZE
        ]

        data = []

        for item in batch:

            data.append(
                {
                    "range": (
                        f"'{item['sheet']}'!"
                        f"{item['cell']}"
                    ),
                    "majorDimension": "ROWS",
                    "values": [
                        [
                            item[
                                "formula"
                            ]
                        ]
                    ],
                }
            )

        (
            sheets_service
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
            "Восстановлено формул: "
            f"{written} / {total}"
        )


def find_ref_errors_in_formula_cells(
    sheets_service,
    spreadsheet_id,
    formulas,
):

    if not formulas:

        return []

    errors = []

    for start in range(
        0,
        len(formulas),
        FORMULA_BATCH_SIZE,
    ):

        batch = formulas[
            start:
            start + FORMULA_BATCH_SIZE
        ]

        ranges = []

        for item in batch:

            ranges.append(
                f"'{item['sheet']}'!"
                f"{item['cell']}"
            )

        result = (
            sheets_service
            .spreadsheets()
            .values()
            .batchGet(
                spreadsheetId=(
                    spreadsheet_id
                ),
                ranges=ranges,
                valueRenderOption=(
                    "FORMATTED_VALUE"
                ),
            )
            .execute()
        )

        value_ranges = result.get(
            "valueRanges",
            [],
        )

        for item, value_range in zip(
            batch,
            value_ranges,
        ):

            values = value_range.get(
                "values",
                [],
            )

            value = ""

            if (
                values
                and values[0]
            ):

                value = values[0][0]

            if "#REF!" in str(
                value
            ):

                errors.append(
                    {
                        "sheet": (
                            item["sheet"]
                        ),
                        "cell": (
                            item["cell"]
                        ),
                        "value": value,
                    }
                )

    return errors


def delete_backups(
    sheets_service,
    spreadsheet_id,
    backup_sheets,
):

    ids = [
        item["sheetId"]
        for item
        in backup_sheets.values()
    ]

    delete_sheets(
        sheets_service,
        spreadsheet_id,
        ids,
    )


def rollback_sheets(
    sheets_service,
    spreadsheet_id,
    copied_sheets,
    backup_sheets,
):

    print()
    print(
        "Возвращаю старые рабочие "
        "листы..."
    )

    timestamp = (
        datetime.now()
        .strftime(
            "%Y%m%d_%H%M%S"
        )
    )

    requests = []

    # Сначала убираем новые листы
    # с оригинальных названий.
    for title in SHEETS_TO_IMPORT:

        copied = copied_sheets.get(
            title
        )

        if not copied:

            continue

        failed_title = (
            f"__FAILED_{title}_{timestamp}"
        )

        requests.append(
            {
                "updateSheetProperties": {
                    "properties": {
                        "sheetId": (
                            copied["sheetId"]
                        ),
                        "title": (
                            failed_title
                        ),
                    },
                    "fields": "title",
                }
            }
        )

    # Старым backup-листам
    # возвращаем оригинальные названия.
    for title, backup in (
        backup_sheets.items()
    ):

        requests.append(
            {
                "updateSheetProperties": {
                    "properties": {
                        "sheetId": (
                            backup["sheetId"]
                        ),
                        "title": title,
                    },
                    "fields": "title",
                }
            }
        )

    if requests:

        (
            sheets_service
            .spreadsheets()
            .batchUpdate(
                spreadsheetId=(
                    spreadsheet_id
                ),
                body={
                    "requests": requests
                },
            )
            .execute()
        )

    failed_ids = [
        item["sheetId"]
        for item
        in copied_sheets.values()
    ]

    delete_sheets(
        sheets_service,
        spreadsheet_id,
        failed_ids,
    )

    print(
        "Старые листы восстановлены."
    )


def move_imported_sheets_to_end(
    sheets_service,
    spreadsheet_id,
):

    all_sheets = get_sheets(
        sheets_service,
        spreadsheet_id,
    )

    sheet_count = len(
        all_sheets
    )

    requests = []

    desired_positions = {
        "ПО ЧИСЛАМ": max(
            sheet_count - 2,
            0,
        ),
        "ПО ДНЯМ НЕДЕЛИ": max(
            sheet_count - 1,
            0,
        ),
    }

    for title in SHEETS_TO_IMPORT:

        sheet = all_sheets.get(
            title
        )

        if not sheet:

            continue

        requests.append(
            {
                "updateSheetProperties": {
                    "properties": {
                        "sheetId": (
                            sheet["sheetId"]
                        ),
                        "index": (
                            desired_positions[
                                title
                            ]
                        ),
                    },
                    "fields": "index",
                }
            }
        )

    if requests:

        (
            sheets_service
            .spreadsheets()
            .batchUpdate(
                spreadsheetId=(
                    spreadsheet_id
                ),
                body={
                    "requests": requests
                },
            )
            .execute()
        )


def cleanup_temp_file(
    drive_service,
    file_id,
):

    if not file_id:

        return

    try:

        (
            drive_service
            .files()
            .delete(
                fileId=file_id
            )
            .execute()
        )

        print(
            "Временная Google-таблица "
            "удалена."
        )

    except Exception as exc:

        print(
            "Не удалось удалить "
            "временный Google-файл:"
        )

        print(
            exc
        )


def main():

    print_header(
        "ТОЧНЫЙ ПЕРЕНОС EXCEL "
        "В GOOGLE SHEETS"
    )

    if not EXCEL_FILE.exists():

        raise FileNotFoundError(
            "Не найден Excel-файл:\n"
            f"{EXCEL_FILE}"
        )

    print(
        "Исходный Excel:"
    )

    print(
        EXCEL_FILE
    )

    # --------------------------------------------------
    # Считываем межлистовые формулы
    # ДО любых изменений Google Sheets.
    # --------------------------------------------------

    formulas = (
        load_cross_sheet_formulas()
    )

    print()
    print(
        "Межлистовых формул "
        "в исходном Excel: "
        f"{len(formulas)}"
    )

    if formulas:

        print()
        print(
            "Первые формулы:"
        )

        for item in formulas[:5]:

            print(
                f"{item['sheet']}!"
                f"{item['cell']}: "
                f"{item['formula']}"
            )

    target_spreadsheet_id = (
        get_spreadsheet_id()
    )

    creds = get_credentials()

    sheets_service = build(
        "sheets",
        "v4",
        credentials=creds,
    )

    drive_service = build(
        "drive",
        "v3",
        credentials=creds,
    )

    temp_spreadsheet_id = None

    copied_sheets = {}

    backup_sheets = {}

    replacement_started = False

    success = False

    try:

        # --------------------------------------------------
        # 1. Проверяем текущую Google-таблицу
        # --------------------------------------------------

        print_header(
            "1. ПРОВЕРЯЮ ЦЕЛЕВУЮ "
            "GOOGLE-ТАБЛИЦУ"
        )

        target_sheets_before = (
            get_sheets(
                sheets_service,
                target_spreadsheet_id,
            )
        )

        print(
            "Текущие листы:"
        )

        for title in target_sheets_before:

            print(
                f"- {title}"
            )

        # --------------------------------------------------
        # 2. Загружаем XLSX и конвертируем
        # --------------------------------------------------

        print_header(
            "2. КОНВЕРТИРУЮ XLSX "
            "СРЕДСТВАМИ GOOGLE"
        )

        temp_spreadsheet_id = (
            upload_excel_as_google_sheet(
                drive_service
            )
        )

        print(
            "Временная таблица создана:"
        )

        print(
            temp_spreadsheet_id
        )

        wait_for_google_conversion(
            sheets_service,
            temp_spreadsheet_id,
        )

        source_sheets = get_sheets(
            sheets_service,
            temp_spreadsheet_id,
        )

        print()
        print(
            "Google распознал листы:"
        )

        for title in source_sheets:

            print(
                f"- {title}"
            )

        for title in SHEETS_TO_IMPORT:

            if title not in source_sheets:

                raise RuntimeError(
                    "После конвертации "
                    "не найден лист "
                    f"«{title}»"
                )

        # --------------------------------------------------
        # 3. Копируем листы целиком
        # --------------------------------------------------

        print_header(
            "3. КОПИРУЮ ЛИСТЫ "
            "С ОФОРМЛЕНИЕМ"
        )

        for title in SHEETS_TO_IMPORT:

            source = source_sheets[
                title
            ]

            print(
                f"Копирую «{title}»..."
            )

            copied = copy_sheet(
                sheets_service,
                temp_spreadsheet_id,
                source["sheetId"],
                target_spreadsheet_id,
            )

            copied_sheets[
                title
            ] = copied

            print(
                "Скопирован."
            )

        # --------------------------------------------------
        # 4. Старые листы превращаем в backup,
        #    новые получают оригинальные имена.
        # --------------------------------------------------

        print_header(
            "4. ПЕРЕКЛЮЧАЮСЬ "
            "НА НОВЫЕ ЛИСТЫ"
        )

        backup_sheets = (
            switch_to_new_sheets(
                sheets_service,
                target_spreadsheet_id,
                target_sheets_before,
                copied_sheets,
            )
        )

        replacement_started = True

        print(
            "Старые версии временно "
            "сохранены как backup."
        )

        print(
            "Новые листы получили "
            "рабочие названия."
        )

        # --------------------------------------------------
        # 5. Восстанавливаем межлистовые формулы
        # --------------------------------------------------

        print_header(
            "5. ВОССТАНАВЛИВАЮ "
            "МЕЖЛИСТОВЫЕ ФОРМУЛЫ"
        )

        write_cross_sheet_formulas(
            sheets_service,
            target_spreadsheet_id,
            formulas,
        )

        # --------------------------------------------------
        # 6. Проверяем восстановленные формулы
        # --------------------------------------------------

        print_header(
            "6. ПРОВЕРЯЮ #REF!"
        )

        errors = (
            find_ref_errors_in_formula_cells(
                sheets_service,
                target_spreadsheet_id,
                formulas,
            )
        )

        if errors:

            print(
                "Найдены ошибки #REF!: "
                f"{len(errors)}"
            )

            print()

            for item in errors[:20]:

                print(
                    f"{item['sheet']}!"
                    f"{item['cell']}: "
                    f"{item['value']}"
                )

            raise RuntimeError(
                "Межлистовые формулы "
                "восстановились не полностью."
            )

        print(
            "#REF! в восстановленных "
            "формулах не найдено."
        )

        # --------------------------------------------------
        # 7. Только после успешной проверки
        #    удаляем backup.
        # --------------------------------------------------

        print_header(
            "7. УДАЛЯЮ СТАРЫЕ "
            "BACKUP-ЛИСТЫ"
        )

        if backup_sheets:

            delete_backups(
                sheets_service,
                target_spreadsheet_id,
                backup_sheets,
            )

            backup_sheets = {}

            print(
                "Старые версии удалены."
            )

        else:

            print(
                "Старых версий не было."
            )

        # --------------------------------------------------
        # 8. Ставим листы рядом в конец книги
        # --------------------------------------------------

        move_imported_sheets_to_end(
            sheets_service,
            target_spreadsheet_id,
        )

        # --------------------------------------------------
        # 9. Финальная проверка
        # --------------------------------------------------

        print_header(
            "8. ФИНАЛЬНАЯ ПРОВЕРКА"
        )

        final_sheets = get_sheets(
            sheets_service,
            target_spreadsheet_id,
        )

        for title in SHEETS_TO_IMPORT:

            if title not in final_sheets:

                raise RuntimeError(
                    "После импорта "
                    "не найден лист "
                    f"«{title}»"
                )

            props = final_sheets[
                title
            ]

            grid = props.get(
                "gridProperties",
                {},
            )

            print(
                f"{title}: "
                f"{grid.get('rowCount', '?')} строк × "
                f"{grid.get('columnCount', '?')} столбцов"
            )

        print()
        print(
            "Межлистовых формул "
            "восстановлено: "
            f"{len(formulas)}"
        )

        success = True

        print_header(
            "ИМПОРТ УСПЕШНО ЗАВЕРШЁН"
        )

        print(
            "Обновлены:"
        )

        for title in SHEETS_TO_IMPORT:

            print(
                f"- {title}"
            )

        print()
        print(
            "Перенесены:"
        )

        print(
            "- данные"
        )

        print(
            "- формулы"
        )

        print(
            "- межлистовые ссылки"
        )

        print(
            "- шрифты"
        )

        print(
            "- размеры текста"
        )

        print(
            "- жирность"
        )

        print(
            "- цвета текста"
        )

        print(
            "- заливки"
        )

        print(
            "- границы"
        )

        print(
            "- выравнивания"
        )

        print(
            "- ширины столбцов"
        )

        print(
            "- высоты строк"
        )

        print(
            "- объединённые ячейки"
        )

        print(
            "- числовые форматы"
        )

        print(
            "- условное форматирование"
        )

        print()
        print(
            "Остальные рабочие листы "
            "не изменялись."
        )

        print()
        print(
            "https://docs.google.com/"
            "spreadsheets/d/"
            f"{target_spreadsheet_id}/edit"
        )

    except Exception:

        print()
        print("=" * 78)
        print(
            "ИМПОРТ ЗАВЕРШИЛСЯ ОШИБКОЙ"
        )
        print("=" * 78)

        # Если мы уже переключили имена,
        # пытаемся вернуть старую рабочую версию.
        if (
            replacement_started
            and backup_sheets
        ):

            try:

                rollback_sheets(
                    sheets_service,
                    target_spreadsheet_id,
                    copied_sheets,
                    backup_sheets,
                )

                copied_sheets = {}

                backup_sheets = {}

            except Exception as rollback_error:

                print()
                print(
                    "ВНИМАНИЕ: автоматический "
                    "rollback тоже дал ошибку:"
                )

                print(
                    rollback_error
                )

        # Если ошибка произошла раньше переключения,
        # удаляем промежуточные копии.
        elif copied_sheets:

            try:

                ids = [
                    item["sheetId"]
                    for item
                    in copied_sheets.values()
                ]

                delete_sheets(
                    sheets_service,
                    target_spreadsheet_id,
                    ids,
                )

                print(
                    "Промежуточные копии "
                    "удалены."
                )

            except Exception as cleanup_error:

                print(
                    "Ошибка удаления "
                    "промежуточных копий:"
                )

                print(
                    cleanup_error
                )

        raise

    finally:

        if temp_spreadsheet_id:

            print()
            print(
                "Удаляю временную "
                "Google-таблицу..."
            )

            cleanup_temp_file(
                drive_service,
                temp_spreadsheet_id,
            )

        if success:

            print()
            print(
                "Готово. Отдельно запускать "
                "repair_sales_formulas.py "
                "больше не нужно."
            )


if __name__ == "__main__":

    main()