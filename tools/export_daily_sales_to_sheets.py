import csv
import re
from calendar import monthrange
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


PROJECT_DIR = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)

CSV_FILE = (
    PROJECT_DIR
    / "daily_sales.csv"
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

SHEET_NUMBERS = "ПО ЧИСЛАМ"
SHEET_WEEKDAYS = "ПО ДНЯМ НЕДЕЛИ"


MONTH_NAMES = {
    1: "Январь",
    2: "Февраль",
    3: "Март",
    4: "Апрель",
    5: "Май",
    6: "Июнь",
    7: "Июль",
    8: "Август",
    9: "Сентябрь",
    10: "Октябрь",
    11: "Ноябрь",
    12: "Декабрь",
}


DETAIL_LABELS = [
    "Продажи по чекам (НАЛ)",
    "Продажи по чекам (БЕЗНАЛ)",
    "Продажи по чекам (НАЛ) Инт.заказы МН",
    "Продажи по чекам (БЕЗНАЛ) Инт.заказы МН",
    "Возврат по чекам (нал)",
    "Возврат по чекам (экв.)",
    "Продажи по внешним заказам МН",
    "Продажи по внешним заказам Яндекс",
    "Продажи по внешним заказам Купер",
    "Продажи без чека",
]


MANAGED_ROWS = {
    1: "cash",
    2: "card",
    5: "cash_return",
    6: "card_return",
    7: "self_pickup",
    8: "yandex_food",
    9: "kuper",
    10: "no_receipt",
}


ZERO = Decimal("0")


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


def parse_decimal(value):

    text = (
        str(value or "")
        .replace("\xa0", "")
        .replace(" ", "")
        .replace(",", ".")
        .strip()
    )

    if not text:
        return ZERO

    try:
        return Decimal(
            text
        )

    except InvalidOperation:
        return ZERO


def parse_date(value):

    return datetime.strptime(
        str(value).strip(),
        "%d.%m.%Y",
    ).date()


def google_number(value):

    number = parse_decimal(
        value
    )

    if number == ZERO:
        return ""

    return float(
        number
    )


def column_letter(number):

    result = ""

    while number:

        number, remainder = divmod(
            number - 1,
            26,
        )

        result = (
            chr(
                65 + remainder
            )
            + result
        )

    return result


def sum_decimal(
    rows,
    field,
):

    result = ZERO

    for row in rows.values():

        result += parse_decimal(
            row.get(
                field
            )
        )

    return result


def sum_int(
    rows,
    field,
):

    result = 0

    for row in rows.values():

        text = str(
            row.get(
                field,
                "",
            )
            or ""
        ).strip()

        if not text:
            continue

        result += int(
            Decimal(
                text
            )
        )

    return result


def load_current_month():

    if not CSV_FILE.exists():

        raise FileNotFoundError(
            f"Не найден файл:\n{CSV_FILE}"
        )

    all_rows = []

    with CSV_FILE.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        reader = csv.DictReader(
            file
        )

        for row in reader:

            try:
                row_date = parse_date(
                    row["date"]
                )

            except Exception:
                continue

            all_rows.append(
                (
                    row_date,
                    row,
                )
            )

    if not all_rows:

        raise RuntimeError(
            "daily_sales.csv пуст."
        )

    latest_date = max(
        row_date
        for row_date, row
        in all_rows
    )

    rows = {}

    for row_date, row in all_rows:

        if (
            row_date.year
            == latest_date.year
            and row_date.month
            == latest_date.month
        ):

            rows[
                row_date.day
            ] = row

    missing_days = [
        day
        for day in range(
            1,
            latest_date.day + 1,
        )
        if day not in rows
    ]

    if missing_days:

        raise RuntimeError(
            "В текущем месяце "
            "отсутствуют дни: "
            + ", ".join(
                str(day)
                for day in missing_days
            )
        )

    incomplete = []

    for day in range(
        1,
        latest_date.day + 1,
    ):

        row = rows[
            day
        ]

        for field in (
            "checks",
            "items",
        ):

            if not str(
                row.get(
                    field,
                    "",
                )
                or ""
            ).strip():

                incomplete.append(
                    f"{day:02d}: {field}"
                )

    if incomplete:

        raise RuntimeError(
            "daily_sales.csv ещё не полностью "
            "готов для выгрузки:\n"
            + "\n".join(
                incomplete
            )
        )

    return (
        latest_date,
        rows,
    )


def get_sheet_info(
    service,
    spreadsheet_id,
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
            ),
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
            properties[
                "title"
            ]
        ] = properties

    return sheets


def get_values(
    service,
    spreadsheet_id,
    range_name,
    render="FORMULA",
):

    return (
        service
        .spreadsheets()
        .values()
        .get(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueRenderOption=render,
        )
        .execute()
        .get(
            "values",
            [],
        )
    )


def normalize_text(value):

    return str(
        value or ""
    ).strip()


def find_numbers_block(
    service,
    spreadsheet_id,
    year,
    month,
):

    month_name = (
        MONTH_NAMES[
            month
        ]
    )

    total_label = (
        f"ИТОГО "
        f"({month_name} {year})"
    )

    values = get_values(
        service,
        spreadsheet_id,
        f"'{SHEET_NUMBERS}'!A1:A1000",
    )

    total_row = None

    for row_number, row in enumerate(
        values,
        start=1,
    ):

        value = (
            normalize_text(
                row[0]
            )
            if row
            else ""
        )

        if value == total_label:

            total_row = row_number

    if total_row is None:
        return None

    return {
        "header_row":
            total_row - 11,

        "detail_start":
            total_row - 10,

        "detail_end":
            total_row - 1,

        "total_row":
            total_row,

        "created":
            False,
    }


def validate_numbers_block(
    service,
    spreadsheet_id,
    block,
    year,
    month,
):

    month_name = (
        MONTH_NAMES[
            month
        ]
    )

    expected = [
        month_name,
        *DETAIL_LABELS,
        (
            f"ИТОГО "
            f"({month_name} {year})"
        ),
    ]

    start = (
        block[
            "header_row"
        ]
    )

    end = (
        block[
            "total_row"
        ]
    )

    values = get_values(
        service,
        spreadsheet_id,
        (
            f"'{SHEET_NUMBERS}'!"
            f"A{start}:A{end}"
        ),
    )

    actual = []

    for index in range(
        len(expected)
    ):

        value = ""

        if (
            index < len(values)
            and values[index]
        ):

            value = normalize_text(
                values[index][0]
            )

        actual.append(
            value
        )

    for offset, (
        actual_value,
        expected_value,
    ) in enumerate(
        zip(
            actual,
            expected,
        )
    ):

        row_number = (
            start
            + offset
        )

        if (
            actual_value
            != expected_value
        ):

            raise RuntimeError(
                f"Строка {row_number}: "
                f"ожидалось "
                f"{expected_value!r}, "
                f"получено "
                f"{actual_value!r}."
            )


def find_latest_total_row(
    service,
    spreadsheet_id,
):

    values = get_values(
        service,
        spreadsheet_id,
        f"'{SHEET_NUMBERS}'!A1:A1000",
    )

    latest = None

    pattern = re.compile(
        r"^ИТОГО \(.+ \d{4}\)$"
    )

    for row_number, row in enumerate(
        values,
        start=1,
    ):

        if not row:
            continue

        value = normalize_text(
            row[0]
        )

        if pattern.match(
            value
        ):

            latest = row_number

    if latest is None:

        raise RuntimeError(
            "Не удалось найти "
            "последний месячный блок "
            "в «ПО ЧИСЛАМ»."
        )

    return latest


def create_numbers_block(
    service,
    spreadsheet_id,
    numbers_sheet_id,
    year,
    month,
):

    month_name = (
        MONTH_NAMES[
            month
        ]
    )

    source_total = (
        find_latest_total_row(
            service,
            spreadsheet_id,
        )
    )

    source_header = (
        source_total - 11
    )

    source_blank = (
        source_total + 1
    )

    destination_header = (
        source_total + 2
    )

    destination_total = (
        destination_header + 11
    )

    destination_blank = (
        destination_total + 1
    )

    print()
    print(
        "Нового блока месяца "
        "в «ПО ЧИСЛАМ» ещё нет."
    )

    print(
        "Создаю:",
        month_name,
        year,
    )

    request = {
        "copyPaste": {
            "source": {
                "sheetId":
                    numbers_sheet_id,

                "startRowIndex":
                    source_header - 1,

                "endRowIndex":
                    source_blank,

                "startColumnIndex":
                    0,

                "endColumnIndex":
                    47,
            },

            "destination": {
                "sheetId":
                    numbers_sheet_id,

                "startRowIndex":
                    destination_header - 1,

                "endRowIndex":
                    destination_blank,

                "startColumnIndex":
                    0,

                "endColumnIndex":
                    47,
            },

            "pasteType":
                "PASTE_NORMAL",

            "pasteOrientation":
                "NORMAL",
        }
    }

    (
        service
        .spreadsheets()
        .batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={
                "requests": [
                    request
                ]
            },
        )
        .execute()
    )

    total_label = (
        f"ИТОГО "
        f"({month_name} {year})"
    )

    (
        service
        .spreadsheets()
        .values()
        .batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={
                "valueInputOption":
                    "RAW",

                "data": [
                    {
                        "range": (
                            f"'{SHEET_NUMBERS}'!"
                            f"A{destination_header}"
                        ),
                        "values": [
                            [
                                month_name
                            ]
                        ],
                    },
                    {
                        "range": (
                            f"'{SHEET_NUMBERS}'!"
                            f"A{destination_total}"
                        ),
                        "values": [
                            [
                                total_label
                            ]
                        ],
                    },
                ],
            },
        )
        .execute()
    )

    (
        service
        .spreadsheets()
        .values()
        .batchClear(
            spreadsheetId=spreadsheet_id,
            body={
                "ranges": [
                    (
                        f"'{SHEET_NUMBERS}'!"
                        f"K{destination_header + 1}:"
                        f"AO{destination_total - 1}"
                    ),
                    (
                        f"'{SHEET_NUMBERS}'!"
                        f"E{destination_total}"
                    ),
                    (
                        f"'{SHEET_NUMBERS}'!"
                        f"G{destination_total}:"
                        f"I{destination_total}"
                    ),
                ]
            },
        )
        .execute()
    )

    return {
        "header_row":
            destination_header,

        "detail_start":
            destination_header + 1,

        "detail_end":
            destination_total - 1,

        "total_row":
            destination_total,

        "created":
            True,
    }


def ensure_numbers_block(
    service,
    spreadsheet_id,
    numbers_sheet_id,
    year,
    month,
):

    block = find_numbers_block(
        service,
        spreadsheet_id,
        year,
        month,
    )

    if block is None:

        block = create_numbers_block(
            service,
            spreadsheet_id,
            numbers_sheet_id,
            year,
            month,
        )

    validate_numbers_block(
        service,
        spreadsheet_id,
        block,
        year,
        month,
    )

    return block


def build_daily_values(
    rows,
    latest_day,
    field,
):

    return [
        google_number(
            rows[
                day
            ].get(
                field
            )
        )
        for day in range(
            1,
            latest_day + 1,
        )
    ]


def write_numbers_month(
    service,
    spreadsheet_id,
    block,
    latest_date,
    rows,
):

    latest_day = (
        latest_date.day
    )

    checks = sum_int(
        rows,
        "checks",
    )

    items = sum_decimal(
        rows,
        "items",
    )

    external_orders = sum_int(
        rows,
        "external_orders",
    )

    check_revenue_net = sum_decimal(
        rows,
        "check_revenue_net",
    )

    total_revenue = sum_decimal(
        rows,
        "total_revenue",
    )

    if checks > 0:

        ktch = (
            items
            / Decimal(
                checks
            )
        )

        average_check = (
            check_revenue_net
            / Decimal(
                checks
            )
        )

    else:

        ktch = ZERO
        average_check = ZERO

    print()
    print("=" * 72)
    print(
        "ДАННЫЕ ТЕКУЩЕГО МЕСЯЦА"
    )
    print("=" * 72)

    print(
        "Период:",
        (
            f"01–{latest_day:02d}."
            f"{latest_date.month:02d}."
            f"{latest_date.year}"
        ),
    )

    print(
        "Чеков:",
        checks,
    )

    print(
        "Товаров:",
        items,
    )

    print(
        "КТЧ:",
        f"{ktch:.2f}",
    )

    print(
        "Средний чек:",
        f"{average_check:.2f}",
    )

    print(
        "Внешних заказов:",
        external_orders,
    )

    print(
        "Выручка:",
        f"{total_revenue:,.2f}",
    )

    clear_ranges = []

    if block[
        "created"
    ]:

        clear_ranges.append(
            (
                f"'{SHEET_NUMBERS}'!"
                f"K{block['detail_start']}:"
                f"AO{block['detail_end']}"
            )
        )

    else:

        for offset in (
            MANAGED_ROWS.keys()
        ):

            row_number = (
                block[
                    "header_row"
                ]
                + offset
            )

            clear_ranges.append(
                (
                    f"'{SHEET_NUMBERS}'!"
                    f"K{row_number}:"
                    f"AO{row_number}"
                )
            )

    (
        service
        .spreadsheets()
        .values()
        .batchClear(
            spreadsheetId=spreadsheet_id,
            body={
                "ranges":
                    clear_ranges
            },
        )
        .execute()
    )

    start_column = "K"

    end_column = column_letter(
        10 + latest_day
    )

    data = []

    for offset, field in (
        MANAGED_ROWS.items()
    ):

        row_number = (
            block[
                "header_row"
            ]
            + offset
        )

        data.append(
            {
                "range": (
                    f"'{SHEET_NUMBERS}'!"
                    f"{start_column}"
                    f"{row_number}:"
                    f"{end_column}"
                    f"{row_number}"
                ),

                "values": [
                    build_daily_values(
                        rows,
                        latest_day,
                        field,
                    )
                ],
            }
        )

    total_row = (
        block[
            "total_row"
        ]
    )

    data.extend(
        [
            {
                "range": (
                    f"'{SHEET_NUMBERS}'!"
                    f"E{total_row}"
                ),
                "values": [
                    [
                        external_orders
                    ]
                ],
            },
            {
                "range": (
                    f"'{SHEET_NUMBERS}'!"
                    f"G{total_row}:"
                    f"I{total_row}"
                ),
                "values": [
                    [
                        float(
                            round(
                                ktch,
                                2,
                            )
                        ),
                        checks,
                        float(
                            round(
                                average_check,
                                2,
                            )
                        ),
                    ]
                ],
            },
        ]
    )

    (
        service
        .spreadsheets()
        .values()
        .batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={
                "valueInputOption":
                    "RAW",

                "data":
                    data,
            },
        )
        .execute()
    )

    return {
        "checks":
            checks,

        "items":
            items,

        "ktch":
            ktch,

        "average_check":
            average_check,

        "external_orders":
            external_orders,

        "total_revenue":
            total_revenue,
    }


def verify_numbers_month(
    service,
    spreadsheet_id,
    block,
    latest_date,
    expected_total,
):

    total_row = (
        block[
            "total_row"
        ]
    )

    last_column = column_letter(
        10 + latest_date.day
    )

    ranges = [
        (
            f"'{SHEET_NUMBERS}'!"
            f"B{total_row}:"
            f"J{total_row}"
        ),
        (
            f"'{SHEET_NUMBERS}'!"
            f"{last_column}{total_row}"
        ),
    ]

    result = (
        service
        .spreadsheets()
        .values()
        .batchGet(
            spreadsheetId=spreadsheet_id,
            ranges=ranges,
            valueRenderOption=(
                "UNFORMATTED_VALUE"
            ),
        )
        .execute()
        .get(
            "valueRanges",
            [],
        )
    )

    summary = []

    if result:

        values = result[
            0
        ].get(
            "values",
            [],
        )

        if values:
            summary = values[
                0
            ]

    monthly_total = (
        parse_decimal(
            summary[0]
        )
        if summary
        else ZERO
    )

    print()
    print("=" * 72)
    print(
        "ПРОВЕРКА «ПО ЧИСЛАМ»"
    )
    print("=" * 72)

    print(
        "Строка ИТОГО B:J:"
    )

    print(
        summary
    )

    print()

    print(
        "daily_sales:",
        f"{expected_total:,.2f}",
    )

    print(
        "Google Sheets:",
        f"{monthly_total:,.2f}",
    )

    difference = (
        monthly_total
        - expected_total
    )

    if (
        abs(
            difference
        )
        <= Decimal("0.01")
    ):

        print(
            "ИТОГ МЕСЯЦА: OK"
        )

    else:

        raise RuntimeError(
            "Итог месяца в Google Sheets "
            "не совпал с daily_sales.csv. "
            f"Разница: {difference}"
        )


def weekday_position(
    current_date,
):

    # C = СБ
    # D = ВС
    # E = ПН
    # F = ВТ
    # G = СР
    # H = ЧТ
    # I = ПТ

    return (
        current_date.weekday()
        + 2
    ) % 7


def build_week_rows(
    year,
    month,
    numbers_total_row,
):

    month_name = (
        MONTH_NAMES[
            month
        ]
    )

    days_in_month = monthrange(
        year,
        month,
    )[1]

    result = []

    current_day = 1

    while (
        current_day
        <= days_in_month
    ):

        current_date = date(
            year,
            month,
            current_day,
        )

        start_position = (
            weekday_position(
                current_date
            )
        )

        end_day = min(
            days_in_month,
            current_day
            + (
                6
                - start_position
            ),
        )

        if (
            current_day
            == end_day
        ):

            period_text = (
                f"{current_day:02d}"
            )

        else:

            period_text = (
                f"{current_day:02d}"
                f"-"
                f"{end_day:02d}"
            )

        weekday_cells = [
            ""
            for _ in range(7)
        ]

        for day_number in range(
            current_day,
            end_day + 1,
        ):

            day_date = date(
                year,
                month,
                day_number,
            )

            position = (
                weekday_position(
                    day_date
                )
            )

            numbers_column = (
                column_letter(
                    10 + day_number
                )
            )

            weekday_cells[
                position
            ] = (
                f"='{SHEET_NUMBERS}'!"
                f"{numbers_column}"
                f"{numbers_total_row}"
            )

        result.append(
            [
                month_name,
                period_text,
                *weekday_cells,
            ]
        )

        current_day = (
            end_day + 1
        )

    return result


def formula_references_row(
    formula,
    row_number,
):

    if not isinstance(
        formula,
        str,
    ):

        return False

    if not formula.startswith(
        "="
    ):

        return False

    match = re.search(
        r"!\$?[A-Z]+\$?(\d+)$",
        formula,
    )

    if not match:
        return False

    return (
        int(
            match.group(1)
        )
        == row_number
    )


def find_weekday_block(
    service,
    spreadsheet_id,
    numbers_total_row,
):

    values = get_values(
        service,
        spreadsheet_id,
        (
            f"'{SHEET_WEEKDAYS}'!"
            "A1:I1000"
        ),
    )

    matching_rows = []

    for row_number, row in enumerate(
        values,
        start=1,
    ):

        for value in row[
            2:9
        ]:

            if formula_references_row(
                value,
                numbers_total_row,
            ):

                matching_rows.append(
                    row_number
                )

                break

    if not matching_rows:
        return None

    return {
        "start_row":
            min(
                matching_rows
            ),

        "end_row":
            max(
                matching_rows
            ),
    }


def last_nonempty_weekday_row(
    service,
    spreadsheet_id,
):

    values = get_values(
        service,
        spreadsheet_id,
        (
            f"'{SHEET_WEEKDAYS}'!"
            "A1:I1000"
        ),
    )

    last = 0

    for row_number, row in enumerate(
        values,
        start=1,
    ):

        if any(
            normalize_text(
                value
            )
            for value in row
        ):

            last = row_number

    if last == 0:

        raise RuntimeError(
            "Лист «ПО ДНЯМ НЕДЕЛИ» "
            "пуст."
        )

    return (
        last,
        values,
    )


def previous_month_block_start(
    values,
    last_row,
):

    if (
        last_row < 1
        or last_row > len(
            values
        )
    ):

        return last_row

    row = values[
        last_row - 1
    ]

    if not row:

        return last_row

    month_name = normalize_text(
        row[0]
    )

    start = last_row

    while start > 1:

        previous = values[
            start - 2
        ]

        previous_month = (
            normalize_text(
                previous[0]
            )
            if previous
            else ""
        )

        if (
            previous_month
            != month_name
        ):

            break

        start -= 1

    return start


def copy_weekday_formats(
    service,
    spreadsheet_id,
    weekdays_sheet_id,
    source_start,
    source_end,
    destination_start,
    destination_count,
):

    source_count = (
        source_end
        - source_start
        + 1
    )

    if source_count <= 0:
        return

    requests = []

    for index in range(
        destination_count
    ):

        if index == 0:

            source_row = (
                source_start
            )

        elif (
            index
            == destination_count - 1
        ):

            source_row = (
                source_end
            )

        elif (
            source_count >= 3
        ):

            source_row = (
                source_start + 1
            )

        else:

            source_row = (
                source_start
            )

        destination_row = (
            destination_start
            + index
        )

        requests.append(
            {
                "copyPaste": {
                    "source": {
                        "sheetId":
                            weekdays_sheet_id,

                        "startRowIndex":
                            source_row - 1,

                        "endRowIndex":
                            source_row,

                        "startColumnIndex":
                            0,

                        "endColumnIndex":
                            9,
                    },

                    "destination": {
                        "sheetId":
                            weekdays_sheet_id,

                        "startRowIndex":
                            destination_row - 1,

                        "endRowIndex":
                            destination_row,

                        "startColumnIndex":
                            0,

                        "endColumnIndex":
                            9,
                    },

                    "pasteType":
                        "PASTE_FORMAT",

                    "pasteOrientation":
                        "NORMAL",
                }
            }
        )

    if requests:

        (
            service
            .spreadsheets()
            .batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={
                    "requests":
                        requests
                },
            )
            .execute()
        )


def ensure_weekday_space(
    service,
    spreadsheet_id,
    weekdays_sheet_id,
    existing_block,
    required_count,
):

    if existing_block:

        existing_count = (
            existing_block[
                "end_row"
            ]
            - existing_block[
                "start_row"
            ]
            + 1
        )

        start_row = (
            existing_block[
                "start_row"
            ]
        )

        if (
            required_count
            > existing_count
        ):

            copy_weekday_formats(
                service,
                spreadsheet_id,
                weekdays_sheet_id,
                start_row,
                existing_block[
                    "end_row"
                ],
                (
                    start_row
                    + existing_count
                ),
                (
                    required_count
                    - existing_count
                ),
            )

        return (
            start_row,
            existing_count,
        )

    (
        last_row,
        values,
    ) = (
        last_nonempty_weekday_row(
            service,
            spreadsheet_id,
        )
    )

    source_start = (
        previous_month_block_start(
            values,
            last_row,
        )
    )

    source_end = (
        last_row
    )

    destination_start = (
        last_row + 1
    )

    copy_weekday_formats(
        service,
        spreadsheet_id,
        weekdays_sheet_id,
        source_start,
        source_end,
        destination_start,
        required_count,
    )

    return (
        destination_start,
        0,
    )


def write_weekday_month(
    service,
    spreadsheet_id,
    weekdays_sheet_id,
    latest_date,
    numbers_total_row,
):

    rows = build_week_rows(
        latest_date.year,
        latest_date.month,
        numbers_total_row,
    )

    existing_block = (
        find_weekday_block(
            service,
            spreadsheet_id,
            numbers_total_row,
        )
    )

    (
        start_row,
        existing_count,
    ) = ensure_weekday_space(
        service,
        spreadsheet_id,
        weekdays_sheet_id,
        existing_block,
        len(rows),
    )

    clear_count = max(
        existing_count,
        len(rows),
    )

    if clear_count > 0:

        (
            service
            .spreadsheets()
            .values()
            .clear(
                spreadsheetId=spreadsheet_id,
                range=(
                    f"'{SHEET_WEEKDAYS}'!"
                    f"A{start_row}:"
                    f"I{start_row + clear_count - 1}"
                ),
                body={},
            )
            .execute()
        )

    (
        service
        .spreadsheets()
        .values()
        .update(
            spreadsheetId=spreadsheet_id,
            range=(
                f"'{SHEET_WEEKDAYS}'!"
                f"A{start_row}:"
                f"I{start_row + len(rows) - 1}"
            ),
            valueInputOption="USER_ENTERED",
            body={
                "values":
                    rows
            },
        )
        .execute()
    )

    return {
        "start_row":
            start_row,

        "end_row":
            start_row
            + len(rows)
            - 1,

        "rows":
            rows,
    }


def verify_weekday_month(
    service,
    spreadsheet_id,
    block,
):

    start = (
        block[
            "start_row"
        ]
    )

    end = (
        block[
            "end_row"
        ]
    )

    formulas = get_values(
        service,
        spreadsheet_id,
        (
            f"'{SHEET_WEEKDAYS}'!"
            f"A{start}:I{end}"
        ),
        render="FORMULA",
    )

    print()
    print("=" * 72)
    print(
        "ПРОВЕРКА «ПО ДНЯМ НЕДЕЛИ»"
    )
    print("=" * 72)

    for row_number, row in enumerate(
        formulas,
        start=start,
    ):

        print(
            row_number,
            "|",
            row,
        )

    if len(
        formulas
    ) != len(
        block[
            "rows"
        ]
    ):

        raise RuntimeError(
            "Количество строк "
            "недельного блока не совпало."
        )

    print()
    print(
        "Недельный блок: OK"
    )


def main():

    print()
    print("=" * 72)
    print(
        "ВЫГРУЗКА ДНЕВНЫХ ПРОДАЖ "
        "В GOOGLE SHEETS"
    )
    print("=" * 72)

    if not (
        SPREADSHEET_ID_FILE
        .exists()
    ):

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

    (
        latest_date,
        rows,
    ) = load_current_month()

    print()
    print(
        "Последний закрытый день:",
        latest_date.strftime(
            "%d.%m.%Y"
        ),
    )

    print(
        "Текущий блок:",
        (
            MONTH_NAMES[
                latest_date.month
            ]
        ),
        latest_date.year,
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

    for required_sheet in (
        SHEET_NUMBERS,
        SHEET_WEEKDAYS,
    ):

        if required_sheet not in sheets:

            raise RuntimeError(
                "В Google Sheets нет листа "
                f"{required_sheet!r}."
            )

    numbers_sheet_id = (
        sheets[
            SHEET_NUMBERS
        ][
            "sheetId"
        ]
    )

    weekdays_sheet_id = (
        sheets[
            SHEET_WEEKDAYS
        ][
            "sheetId"
        ]
    )

    print()
    print("=" * 72)
    print(
        "1. ПО ЧИСЛАМ"
    )
    print("=" * 72)

    numbers_block = (
        ensure_numbers_block(
            service,
            spreadsheet_id,
            numbers_sheet_id,
            latest_date.year,
            latest_date.month,
        )
    )

    print(
        "Блок:",
        (
            f"{numbers_block['header_row']}"
            f"–"
            f"{numbers_block['total_row']}"
        ),
    )

    metrics = (
        write_numbers_month(
            service,
            spreadsheet_id,
            numbers_block,
            latest_date,
            rows,
        )
    )

    verify_numbers_month(
        service,
        spreadsheet_id,
        numbers_block,
        latest_date,
        metrics[
            "total_revenue"
        ],
    )

    print()
    print("=" * 72)
    print(
        "2. ПО ДНЯМ НЕДЕЛИ"
    )
    print("=" * 72)

    weekday_block = (
        write_weekday_month(
            service,
            spreadsheet_id,
            weekdays_sheet_id,
            latest_date,
            numbers_block[
                "total_row"
            ],
        )
    )

    verify_weekday_month(
        service,
        spreadsheet_id,
        weekday_block,
    )

    print()
    print("=" * 72)
    print(
        "ВЫГРУЗКА УСПЕШНО ЗАВЕРШЕНА"
    )
    print("=" * 72)

    print()

    print(
        "ПО ЧИСЛАМ:",
        (
            f"{numbers_block['header_row']}"
            f"–"
            f"{numbers_block['total_row']}"
        ),
    )

    print(
        "ПО ДНЯМ НЕДЕЛИ:",
        (
            f"{weekday_block['start_row']}"
            f"–"
            f"{weekday_block['end_row']}"
        ),
    )

    print()

    print(
        "Следующий месяц будет "
        "создан автоматически."
    )

    print(
        "Недели строятся "
        "по правилу СБ–ПТ."
    )

    print()

    print(
        "https://docs.google.com/"
        "spreadsheets/d/"
        f"{spreadsheet_id}/edit"
    )


if __name__ == "__main__":

    main()