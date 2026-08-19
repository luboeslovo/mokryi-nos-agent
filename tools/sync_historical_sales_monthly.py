import csv
import re
from calendar import monthrange
from datetime import datetime
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

OUTPUT_FILE = (
    PROJECT_DIR
    / "historical_sales_monthly.csv"
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

SHEET_NAME = "ПО ЧИСЛАМ"
SOURCE_RANGE = "A1:J400"


MONTHS = {
    "январь": 1,
    "февраль": 2,
    "март": 3,
    "апрель": 4,
    "май": 5,
    "июнь": 6,
    "июль": 7,
    "август": 8,
    "сентябрь": 9,
    "октябрь": 10,
    "ноябрь": 11,
    "декабрь": 12,
}


FIELDNAMES = [
    "year",
    "month",
    "month_name",
    "period_type",
    "start_date",
    "end_date",
    "is_complete",
    "total_revenue",
    "check_revenue_net",
    "checks",
    "average_check",
    "ktch",
    "external_total",
    "external_orders",
    "external_share_percent",
    "average_daily_check_revenue",
    "cash",
    "card",
    "internal_cash",
    "internal_card",
    "cash_returns",
    "card_returns",
    "returns",
    "self_pickup",
    "yandex_food",
    "kuper",
    "no_receipt",
    "source",
    "source_row",
    "source_label",
    "updated_at",
]


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

    if (
        not creds
        or not creds.valid
    ):
        if (
            creds
            and creds.expired
            and creds.refresh_token
        ):
            creds.refresh(
                Request()
            )

        else:
            if not CREDENTIALS_FILE.exists():
                raise FileNotFoundError(
                    "Не найден credentials.json"
                )

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
            "rfm_spreadsheet_id.txt пуст"
        )

    return spreadsheet_id


def clean(value):
    return " ".join(
        str(
            value
            if value is not None
            else ""
        ).split()
    )


def to_float(value):
    if value is None:
        return 0.0

    if isinstance(
        value,
        (
            int,
            float,
        ),
    ):
        return float(
            value
        )

    text = clean(
        value
    )

    if not text:
        return 0.0

    text = (
        text
        .replace(
            "\xa0",
            "",
        )
        .replace(
            " ",
            "",
        )
        .replace(
            ",",
            ".",
        )
        .replace(
            "%",
            "",
        )
    )

    try:
        return float(
            text
        )

    except ValueError:
        return 0.0


def to_int(value):
    return int(
        round(
            to_float(
                value
            )
        )
    )


def money(value):
    return f"{to_float(value):.2f}"


def number_text(value):
    value = to_float(
        value
    )

    return (
        f"{value:.6f}"
        .rstrip("0")
        .rstrip(".")
    )


def normalize_label(value):
    return (
        clean(
            value
        )
        .lower()
        .replace(
            "ё",
            "е",
        )
        .replace(
            "–",
            "-",
        )
        .replace(
            "—",
            "-",
        )
    )


def find_month_numbers(
    text,
):
    normalized = normalize_label(
        text
    )

    result = []

    for name, number in (
        MONTHS.items()
    ):
        if name in normalized:
            result.append(
                number
            )

    return sorted(
        set(
            result
        )
    )


def find_month(
    text,
):
    months = find_month_numbers(
        text
    )

    if len(months) != 1:
        return None

    return months[0]


def find_year(
    text,
):
    match = re.search(
        r"\b(20\d{2})\b",
        clean(
            text
        ),
    )

    if not match:
        return None

    return int(
        match.group(1)
    )


def is_total_row(
    label,
):
    normalized = (
        normalize_label(
            label
        )
    )

    return normalized.startswith(
        "итого ("
    )


def is_combined_period(
    label,
):
    return (
        len(
            find_month_numbers(
                label
            )
        )
        > 1
    )


def read_sheet_rows(
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
                f"'{SHEET_NAME}'!"
                f"{SOURCE_RANGE}"
            ),
            valueRenderOption=(
                "UNFORMATTED_VALUE"
            ),
        )
        .execute()
    )

    return result.get(
        "values",
        [],
    )


def get_cell(
    row,
    index,
    default=None,
):
    if index >= len(row):
        return default

    value = row[
        index
    ]

    if value is None:
        return default

    return value


def get_component_value(
    components,
    label,
):
    return to_float(
        components.get(
            normalize_label(
                label
            ),
            0,
        )
    )


def build_result_row(
    *,
    year,
    month,
    month_name,
    period_type,
    start_date,
    end_date,
    source_row,
    source_label,
    source_values,
    components,
    updated_at,
):
    total_revenue = to_float(
        get_cell(
            source_values,
            1,
            0,
        )
    )

    check_revenue_net = (
        to_float(
            get_cell(
                source_values,
                2,
                0,
            )
        )
    )

    external_total = (
        to_float(
            get_cell(
                source_values,
                3,
                0,
            )
        )
    )

    external_orders = (
        to_int(
            get_cell(
                source_values,
                4,
                0,
            )
        )
    )

    external_share = (
        to_float(
            get_cell(
                source_values,
                5,
                0,
            )
        )
    )

    ktch = to_float(
        get_cell(
            source_values,
            6,
            0,
        )
    )

    checks = to_int(
        get_cell(
            source_values,
            7,
            0,
        )
    )

    average_check = (
        to_float(
            get_cell(
                source_values,
                8,
                0,
            )
        )
    )

    average_daily = (
        to_float(
            get_cell(
                source_values,
                9,
                0,
            )
        )
    )

    cash = get_component_value(
        components,
        "Продажи по чекам (НАЛ)",
    )

    card = get_component_value(
        components,
        "Продажи по чекам (БЕЗНАЛ)",
    )

    internal_cash = (
        get_component_value(
            components,
            (
                "Продажи по чекам "
                "(НАЛ) Инт.заказы МН"
            ),
        )
    )

    internal_card = (
        get_component_value(
            components,
            (
                "Продажи по чекам "
                "(БЕЗНАЛ) Инт.заказы МН"
            ),
        )
    )

    cash_returns = (
        get_component_value(
            components,
            "Возврат по чекам (нал)",
        )
    )

    card_returns = (
        get_component_value(
            components,
            "Возврат по чекам (экв.)",
        )
    )

    self_pickup = (
        get_component_value(
            components,
            (
                "Продажи по внешним "
                "заказам МН"
            ),
        )
    )

    yandex_food = (
        get_component_value(
            components,
            (
                "Продажи по внешним "
                "заказам Яндекс"
            ),
        )
    )

    kuper = get_component_value(
        components,
        (
            "Продажи по внешним "
            "заказам Купер"
        ),
    )

    no_receipt = (
        get_component_value(
            components,
            "Продажи без чека",
        )
    )

    now = datetime.now()

    end_dt = datetime.strptime(
        end_date,
        "%d.%m.%Y",
    )

    is_complete = (
        end_dt.date()
        < now.date()
    )

    return {
        "year":
            str(
                year
            ),

        "month":
            (
                str(
                    month
                )
                if month is not None
                else ""
            ),

        "month_name":
            month_name,

        "period_type":
            period_type,

        "start_date":
            start_date,

        "end_date":
            end_date,

        "is_complete":
            (
                "1"
                if is_complete
                else "0"
            ),

        "total_revenue":
            money(
                total_revenue
            ),

        "check_revenue_net":
            money(
                check_revenue_net
            ),

        "checks":
            str(
                checks
            ),

        "average_check":
            money(
                average_check
            ),

        "ktch":
            number_text(
                ktch
            ),

        "external_total":
            money(
                external_total
            ),

        "external_orders":
            str(
                external_orders
            ),

        "external_share_percent":
            number_text(
                external_share
            ),

        "average_daily_check_revenue":
            money(
                average_daily
            ),

        "cash":
            money(
                cash
            ),

        "card":
            money(
                card
            ),

        "internal_cash":
            money(
                internal_cash
            ),

        "internal_card":
            money(
                internal_card
            ),

        "cash_returns":
            money(
                cash_returns
            ),

        "card_returns":
            money(
                card_returns
            ),

        "returns":
            money(
                cash_returns
                + card_returns
            ),

        "self_pickup":
            money(
                self_pickup
            ),

        "yandex_food":
            money(
                yandex_food
            ),

        "kuper":
            money(
                kuper
            ),

        "no_receipt":
            money(
                no_receipt
            ),

        "source":
            "ПО ЧИСЛАМ",

        "source_row":
            str(
                source_row
            ),

        "source_label":
            source_label,

        "updated_at":
            updated_at,
    }


def parse_history(
    rows,
):
    result = []

    current_year = 2025
    current_components = {}

    updated_at = (
        datetime.now()
        .isoformat(
            timespec="seconds"
        )
    )

    for row_number, row in enumerate(
        rows,
        start=1,
    ):
        label = clean(
            get_cell(
                row,
                0,
                "",
            )
        )

        if not label:
            continue

        label_year = find_year(
            label
        )

        if label_year:
            current_year = (
                label_year
            )

        if not is_total_row(
            label
        ):
            normalized = (
                normalize_label(
                    label
                )
            )

            month_numbers = (
                find_month_numbers(
                    label
                )
            )

            if month_numbers:
                if (
                    not normalized.startswith(
                        "продажи"
                    )
                    and not normalized.startswith(
                        "возврат"
                    )
                ):
                    current_components = {}

            if (
                normalized.startswith(
                    "продажи"
                )
                or normalized.startswith(
                    "возврат"
                )
            ):
                current_components[
                    normalized
                ] = get_cell(
                    row,
                    1,
                    0,
                )

            continue

        year = (
            find_year(
                label
            )
            or current_year
        )

        current_year = year

        month_numbers = (
            find_month_numbers(
                label
            )
        )

        if not month_numbers:
            print(
                "Не удалось определить период:",
                label,
            )

            current_components = {}
            continue

        if len(
            month_numbers
        ) == 1:
            month = (
                month_numbers[
                    0
                ]
            )

            days_in_month = (
                monthrange(
                    year,
                    month,
                )[1]
            )

            start_date = (
                f"01.{month:02d}.{year:04d}"
            )

            end_date = (
                f"{days_in_month:02d}."
                f"{month:02d}."
                f"{year:04d}"
            )

            month_name = (
                list(
                    MONTHS.keys()
                )[
                    month - 1
                ].capitalize()
            )

            result.append(
                build_result_row(
                    year=year,
                    month=month,
                    month_name=month_name,
                    period_type="month",
                    start_date=start_date,
                    end_date=end_date,
                    source_row=row_number,
                    source_label=label,
                    source_values=row,
                    components=current_components,
                    updated_at=updated_at,
                )
            )

        else:
            first_month = min(
                month_numbers
            )

            last_month = max(
                month_numbers
            )

            expected = list(
                range(
                    first_month,
                    last_month + 1,
                )
            )

            if month_numbers != expected:
                print(
                    "Пропускаю несвязный объединённый период:",
                    label,
                )

                current_components = {}
                continue

            last_day = monthrange(
                year,
                last_month,
            )[1]

            start_date = (
                f"01.{first_month:02d}.{year:04d}"
            )

            end_date = (
                f"{last_day:02d}."
                f"{last_month:02d}."
                f"{year:04d}"
            )

            first_name = (
                list(
                    MONTHS.keys()
                )[
                    first_month - 1
                ]
            )

            last_name = (
                list(
                    MONTHS.keys()
                )[
                    last_month - 1
                ]
            )

            period_name = (
                f"{first_name.capitalize()}"
                f"–{last_name}"
            )

            print(
                "Сохраняю объединённый период:",
                label,
                "->",
                f"{start_date} — {end_date}",
            )

            result.append(
                build_result_row(
                    year=year,
                    month=None,
                    month_name=period_name,
                    period_type="combined",
                    start_date=start_date,
                    end_date=end_date,
                    source_row=row_number,
                    source_label=label,
                    source_values=row,
                    components=current_components,
                    updated_at=updated_at,
                )
            )

        current_components = {}

    result.sort(
        key=lambda item:
            datetime.strptime(
                item[
                    "start_date"
                ],
                "%d.%m.%Y",
            )
    )

    return result


def save_history(
    rows,
):
    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=FIELDNAMES,
        )

        writer.writeheader()

        writer.writerows(
            rows
        )


def print_summary(
    rows,
):
    print()
    print("=" * 70)
    print(
        "ИСТОРИЧЕСКИЕ ПЕРИОДЫ"
    )
    print("=" * 70)
    print()

    for row in rows:
        period_type = (
            row.get(
                "period_type"
            )
        )

        if period_type == "month":
            label = (
                f"{int(row['month']):02d}."
                f"{row['year']}"
            )

        else:
            label = (
                f"{row['start_date']} — "
                f"{row['end_date']}"
            )

        print(
            label
            + " | "
            + row.get(
                "period_type",
                "",
            )
            + " | "
            + f"{float(row['total_revenue']):,.2f} ₽"
            + " | чеки: "
            + row["checks"]
            + " | внешние: "
            + f"{float(row['external_total']):,.2f} ₽"
        )

    monthly_rows = [
        row
        for row in rows
        if (
            row.get(
                "period_type"
            )
            == "month"
        )
    ]

    combined_rows = [
        row
        for row in rows
        if (
            row.get(
                "period_type"
            )
            == "combined"
        )
    ]

    print()
    print(
        "Отдельных месяцев:",
        len(
            monthly_rows
        ),
    )

    print(
        "Объединённых периодов:",
        len(
            combined_rows
        ),
    )


def verify_known_values(
    rows,
):
    monthly_rows = [
        row
        for row in rows
        if (
            row.get(
                "period_type"
            )
            == "month"
        )
    ]

    by_period = {
        (
            int(
                row["year"]
            ),
            int(
                row["month"]
            ),
        ):
            row

        for row in monthly_rows
    }

    expected = {
        (
            2026,
            4,
        ): {
            "total_revenue":
                758889.50,

            "check_revenue_net":
                719502.50,

            "external_total":
                39387.00,

            "checks":
                1006,
        },

        (
            2026,
            5,
        ): {
            "total_revenue":
                842048.68,

            "check_revenue_net":
                764098.68,

            "external_total":
                77950.00,

            "checks":
                949,
        },

        (
            2026,
            7,
        ): {
            "total_revenue":
                772372.41,

            "check_revenue_net":
                674725.41,

            "external_total":
                94762.00,

            "checks":
                839,
        },
    }

    errors = []

    for period, values in (
        expected.items()
    ):
        row = by_period.get(
            period
        )

        if row is None:
            errors.append(
                (
                    f"Нет периода "
                    f"{period[1]:02d}."
                    f"{period[0]}"
                )
            )
            continue

        for field, expected_value in (
            values.items()
        ):
            if field == "checks":
                actual = int(
                    row[field]
                )

                if (
                    actual
                    != expected_value
                ):
                    errors.append(
                        (
                            f"{period}: "
                            f"{field} = "
                            f"{actual}, "
                            f"ожидалось "
                            f"{expected_value}"
                        )
                    )

            else:
                actual = float(
                    row[field]
                )

                if abs(
                    actual
                    - expected_value
                ) > 0.01:
                    errors.append(
                        (
                            f"{period}: "
                            f"{field} = "
                            f"{actual:.2f}, "
                            f"ожидалось "
                            f"{expected_value:.2f}"
                        )
                    )

    combined = [
        row
        for row in rows
        if (
            row.get(
                "period_type"
            )
            == "combined"
            and row.get(
                "year"
            )
            == "2025"
            and row.get(
                "start_date"
            )
            == "01.01.2025"
            and row.get(
                "end_date"
            )
            == "28.02.2025"
        )
    ]

    if not combined:
        errors.append(
            (
                "Не сохранён объединённый "
                "период январь–февраль 2025."
            )
        )

    print()
    print("=" * 70)
    print(
        "КОНТРОЛЬ ИЗВЕСТНЫХ ПЕРИОДОВ"
    )
    print("=" * 70)
    print()

    if errors:
        for error in errors:
            print(
                "ОШИБКА:",
                error,
            )

        raise RuntimeError(
            "Исторические данные "
            "не прошли контроль."
        )

    print(
        "Апрель 2026: совпал."
    )
    print(
        "Май 2026: совпал."
    )
    print(
        "Июль 2026: совпал."
    )
    print(
        "Январь–февраль 2025: "
        "сохранены единым периодом."
    )


def main():
    print()
    print("=" * 70)
    print(
        "СИНХРОНИЗАЦИЯ ИСТОРИИ ПРОДАЖ"
    )
    print("=" * 70)
    print()

    print(
        "Источник:"
    )
    print(
        "Google Sheets → ПО ЧИСЛАМ"
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

    print()
    print(
        "Получаю историческую таблицу..."
    )

    sheet_rows = (
        read_sheet_rows(
            service,
            spreadsheet_id,
        )
    )

    print(
        "Строк прочитано:",
        len(
            sheet_rows
        ),
    )

    history = parse_history(
        sheet_rows
    )

    verify_known_values(
        history
    )

    save_history(
        history
    )

    print_summary(
        history
    )

    print()
    print("=" * 70)
    print(
        "ГОТОВО"
    )
    print("=" * 70)
    print()

    print(
        "Файл:",
        OUTPUT_FILE,
    )

    print()
    print(
        "Важно:"
    )
    print(
        "январь–февраль 2025 сохранены "
        "единым фактическим периодом."
    )
    print(
        "Они НЕ превращаются в два "
        "выдуманных отдельных месяца."
    )


if __name__ == "__main__":
    main()