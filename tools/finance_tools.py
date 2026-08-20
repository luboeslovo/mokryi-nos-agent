import os
import re
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


PROJECT_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
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

SHEET_NAME = "ОПиУ"
SHEET_RANGE = "'ОПиУ'!A3:AE53"

STORE_TIMEZONE = ZoneInfo(
    "Europe/Moscow"
)

CACHE_TTL_SECONDS = 60

_CACHE_ROWS = None
_CACHE_TIME = 0.0


MONTH_NAMES = {
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


MONEY_ROW_SPECS = {
    "revenue": {
        "label": "Выручка",
    },
    "cogs": {
        "label": "Себестоимость",
    },
    "gross_profit": {
        "label": "Валовая прибыль",
    },

    "commercial_expenses": {
        "label": "Коммерческие расходы",
    },

    "rent": {
        "code": "11000",
    },
    "rent_fixed": {
        "code": "11100",
    },
    "rent_variable": {
        "code": "11200",
    },
    "internet": {
        "code": "11300",
    },

    "bank_services": {
        "code": "12000",
    },
    "rko": {
        "code": "12100",
    },
    "acquiring": {
        "code": "12200",
    },

    "delivery_commission": {
        "code": "15000",
    },
    "yandex_commission": {
        "code": "15100",
    },
    "kuper_commission": {
        "code": "15200",
    },

    "royalty": {
        "code": "13000",
    },

    "salary": {
        "code": "14000",
    },

    "advertising": {
        "code": "16000",
    },
    "promoter": {
        "code": "16100",
    },
    "advertising_materials": {
        "code": "16200",
    },
    "job_ads": {
        "code": "16300",
    },

    "other_expenses": {
        "code": "17000",
    },
    "household_expenses": {
        "code": "17100",
    },
    "software_expenses": {
        "code": "17200",
    },
    "equipment": {
        "code": "17300",
    },

    "inventory_total": {
        "code": "18000",
    },
    "inventory": {
        "code": "18100",
    },
    "consumables_writeoff": {
        "code": "18200",
    },
    "expired": {
        "code": "18300",
    },
    "expired_supplier_compensated": {
        "code": "18301",
    },
    "samples": {
        "code": "18305",
    },
    "defect": {
        "code": "18400",
    },

    "profit_from_sales": {
        "label": "Прибыль от продаж",
    },

    "management_expenses": {
        "label": "Управленческие расходы",
    },

    "ebitda": {
        "label": "Операционная прибыль (EBITDA)",
    },

    "financial_activity": {
        "label": "Финансовая деятельность",
    },

    "deposit_interest": {
        "label": "% по вкладу",
    },

    "other_income": {
        "label": "Прочие доходы",
    },

    "supplier_bonus": {
        "label": "Бонус Поставщика",
    },

    "sber_bonus_reimbursement": {
        "label": "Возмещение СБ Бонусы Спасибо",
    },

    "pretax_profit": {
        "label": "Прибыль до налогообложения",
    },

    "taxes": {
        "code": "19000",
    },
    "payroll_taxes": {
        "code": "19100",
    },
    "trade_fee": {
        "code": "19200",
    },
    "ip_insurance": {
        "code": "19300",
    },
    "usn": {
        "code": "19400",
    },

    "net_profit": {
        "label": "Чистая прибыль",
    },
}


NON_ADDITIVE_LABELS = {
    "Рентабельность валовой прибыли",
    "Торговая наценка",
}


METRIC_ALIASES = {
    "выручка":
        "revenue",

    "себестоимость":
        "cogs",

    "валовая прибыль":
        "gross_profit",

    "маржинальность":
        "gross_margin_pct",

    "валовая маржинальность":
        "gross_margin_pct",

    "валовая маржа":
        "gross_margin_pct",

    "рентабельность валовой прибыли":
        "gross_margin_pct",

    "торговая наценка":
        "markup_factor",

    "наценка":
        "markup_pct",

    "процент наценки":
        "markup_pct",

    "коммерческие расходы":
        "commercial_expenses",

    "прибыль от продаж":
        "profit_from_sales",

    "рентабельность продаж":
        "sales_margin_pct",

    "маржа прибыли от продаж":
        "sales_margin_pct",

    "ebitda":
        "ebitda",

    "операционная прибыль":
        "ebitda",

    "ebitda margin":
        "ebitda_margin_pct",

    "рентабельность ebitda":
        "ebitda_margin_pct",

    "операционная рентабельность":
        "ebitda_margin_pct",

    "прибыль до налогообложения":
        "pretax_profit",

    "рентабельность до налогообложения":
        "pretax_margin_pct",

    "чистая прибыль":
        "net_profit",

    "чистая рентабельность":
        "net_margin_pct",

    "рентабельность чистой прибыли":
        "net_margin_pct",

    "роялти":
        "royalty",

    "доля роялти":
        "royalty_share_pct",

    "аренда":
        "rent",

    "доля аренды":
        "rent_share_pct",

    "зарплата":
        "salary",

    "доля зарплаты":
        "salary_share_pct",

    "эквайринг":
        "acquiring",

    "доля эквайринга":
        "acquiring_share_pct",

    "комиссия доставок":
        "delivery_commission",

    "комиссии доставок":
        "delivery_commission",

    "доля комиссии доставок":
        "delivery_commission_share_pct",

    "реклама":
        "advertising",

    "налоги":
        "taxes",
}


PERCENT_METRICS = {
    "gross_margin_pct",
    "markup_pct",
    "cogs_share_pct",
    "commercial_expenses_share_pct",
    "sales_margin_pct",
    "ebitda_margin_pct",
    "pretax_margin_pct",
    "net_margin_pct",
    "royalty_share_pct",
    "rent_share_pct",
    "salary_share_pct",
    "acquiring_share_pct",
    "delivery_commission_share_pct",
}


def normalize_text(
    value,
):
    return re.sub(
        r"\s+",
        " ",
        str(
            value or ""
        ).strip(),
    )


def normalize_code(
    value,
):
    if value is None:
        return ""

    if isinstance(
        value,
        float,
    ):
        if value.is_integer():
            return str(
                int(
                    value
                )
            )

    text = normalize_text(
        value
    )

    if text.endswith(
        ".0"
    ):
        text = text[
            :-2
        ]

    return text


def to_number(
    value,
):
    if value is None:
        return 0.0

    if isinstance(
        value,
        bool,
    ):
        return float(
            value
        )

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

    text = normalize_text(
        value
    )

    if not text:
        return 0.0

    if text in {
        "-",
        "—",
    }:
        return 0.0

    negative = False

    if (
        text.startswith(
            "("
        )
        and text.endswith(
            ")"
        )
    ):
        negative = True

        text = text[
            1:-1
        ]

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
        number = float(
            text
        )

    except ValueError:
        return 0.0

    if negative:
        number = -abs(
            number
        )

    return number


def round_money(
    value,
):
    return round(
        float(
            value or 0
        ),
        2,
    )


def round_percent(
    value,
):
    if value is None:
        return None

    return round(
        float(
            value
        ),
        2,
    )


def safe_percent(
    numerator,
    denominator,
):
    denominator = float(
        denominator or 0
    )

    if denominator == 0:
        return None

    return (
        float(
            numerator or 0
        )
        / denominator
        * 100
    )


def parse_month_header(
    value,
):
    text = normalize_text(
        value
    ).lower()

    match = re.fullmatch(
        (
            r"(январь|февраль|март|апрель|май|июнь|"
            r"июль|август|сентябрь|октябрь|ноябрь|декабрь)"
            r"\s+(\d{4})"
        ),
        text,
    )

    if not match:
        return None

    month_name = match.group(
        1
    )

    year = int(
        match.group(
            2
        )
    )

    return (
        year,
        MONTH_NAMES[
            month_name
        ],
    )


def parse_month_argument(
    value,
):
    if value is None:
        return None

    if isinstance(
        value,
        (
            tuple,
            list,
        ),
    ):
        if len(value) == 2:
            return (
                int(
                    value[0]
                ),
                int(
                    value[1]
                ),
            )

    text = normalize_text(
        value
    ).lower()

    match = re.fullmatch(
        r"(\d{4})-(\d{1,2})",
        text,
    )

    if match:
        return (
            int(
                match.group(
                    1
                )
            ),
            int(
                match.group(
                    2
                )
            ),
        )

    match = re.fullmatch(
        r"(\d{1,2})\.(\d{4})",
        text,
    )

    if match:
        return (
            int(
                match.group(
                    2
                )
            ),
            int(
                match.group(
                    1
                )
            ),
        )

    parsed_header = parse_month_header(
        text
    )

    if parsed_header:
        return parsed_header

    raise ValueError(
        (
            "Не удалось распознать месяц: "
            f"{value}. "
            "Используй формат YYYY-MM, MM.YYYY "
            "или «Август 2026»."
        )
    )


def month_key(
    year,
    month,
):
    return (
        int(
            year
        )
        * 100
        + int(
            month
        )
    )


def month_display(
    year,
    month,
):
    return (
        f"{int(month):02d}."
        f"{int(year):04d}"
    )


def load_opiu_rows(
    force_refresh=False,
):
    global _CACHE_ROWS
    global _CACHE_TIME

    now_monotonic = time.monotonic()

    if (
        not force_refresh
        and _CACHE_ROWS is not None
        and (
            now_monotonic
            - _CACHE_TIME
        )
        < CACHE_TTL_SECONDS
    ):
        return _CACHE_ROWS

    if not os.path.exists(
        TOKEN_FILE
    ):
        raise RuntimeError(
            "Не найден token.json"
        )

    if not os.path.exists(
        SPREADSHEET_ID_FILE
    ):
        raise RuntimeError(
            "Не найден rfm_spreadsheet_id.txt"
        )

    with open(
        SPREADSHEET_ID_FILE,
        "r",
        encoding="utf-8",
    ) as file:
        spreadsheet_id = (
            file.read().strip()
        )

    if not spreadsheet_id:
        raise RuntimeError(
            "rfm_spreadsheet_id.txt пуст"
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
        cache_discovery=False,
    )

    result = (
        service
        .spreadsheets()
        .values()
        .get(
            spreadsheetId=spreadsheet_id,
            range=SHEET_RANGE,
            valueRenderOption=(
                "UNFORMATTED_VALUE"
            ),
        )
        .execute()
    )

    rows = result.get(
        "values",
        [],
    )

    if not rows:
        raise RuntimeError(
            "Лист ОПиУ пуст или недоступен"
        )

    _CACHE_ROWS = rows
    _CACHE_TIME = now_monotonic

    return rows


def get_cell(
    row,
    index,
):
    if index >= len(
        row
    ):
        return None

    return row[
        index
    ]


def find_row_value(
    data_rows,
    spec,
    column_index,
):
    target_code = spec.get(
        "code"
    )

    target_label = spec.get(
        "label"
    )

    for row in data_rows:
        code = normalize_code(
            get_cell(
                row,
                0,
            )
        )

        label = normalize_text(
            get_cell(
                row,
                1,
            )
        )

        if (
            target_code
            and code == target_code
        ):
            return to_number(
                get_cell(
                    row,
                    column_index,
                )
            )

        if (
            target_label
            and label == target_label
        ):
            return to_number(
                get_cell(
                    row,
                    column_index,
                )
            )

    return 0.0


def build_line_items(
    data_rows,
    column_index,
):
    result = []

    for row in data_rows:
        code = normalize_code(
            get_cell(
                row,
                0,
            )
        )

        label = normalize_text(
            get_cell(
                row,
                1,
            )
        )

        if not label:
            continue

        if label in NON_ADDITIVE_LABELS:
            continue

        amount = to_number(
            get_cell(
                row,
                column_index,
            )
        )

        result.append(
            {
                "code":
                    code or None,

                "label":
                    label,

                "amount":
                    round_money(
                        amount
                    ),
            }
        )

    return result


def load_financial_months(
    force_refresh=False,
):
    rows = load_opiu_rows(
        force_refresh=force_refresh
    )

    header = rows[
        0
    ]

    data_rows = rows[
        1:
    ]

    current = datetime.now(
        STORE_TIMEZONE
    )

    months = []

    for column_index, header_value in enumerate(
        header
    ):
        parsed = parse_month_header(
            header_value
        )

        if not parsed:
            continue

        year, month = parsed

        metrics = {}

        for (
            metric_name,
            spec,
        ) in MONEY_ROW_SPECS.items():
            metrics[
                metric_name
            ] = round_money(
                find_row_value(
                    data_rows,
                    spec,
                    column_index,
                )
            )

        has_data = any(
            abs(
                metrics.get(
                    metric,
                    0
                )
            )
            > 0.000001
            for metric in (
                "revenue",
                "cogs",
                "gross_profit",
                "commercial_expenses",
                "ebitda",
                "net_profit",
            )
        )

        if not has_data:
            continue

        is_partial = (
            year
            == current.year
            and month
            == current.month
        )

        is_future = (
            month_key(
                year,
                month,
            )
            > month_key(
                current.year,
                current.month,
            )
        )

        if is_future:
            continue

        months.append(
            {
                "year":
                    year,

                "month":
                    month,

                "month_key":
                    f"{year:04d}-{month:02d}",

                "display":
                    month_display(
                        year,
                        month,
                    ),

                "is_partial":
                    is_partial,

                "metrics":
                    metrics,

                "line_items":
                    build_line_items(
                        data_rows,
                        column_index,
                    ),
            }
        )

    months.sort(
        key=lambda item: (
            item[
                "year"
            ],
            item[
                "month"
            ],
        )
    )

    return months


def derive_metrics(
    totals,
):
    revenue = totals.get(
        "revenue",
        0,
    )

    cogs = totals.get(
        "cogs",
        0,
    )

    gross_profit = totals.get(
        "gross_profit",
        0,
    )

    commercial_expenses = totals.get(
        "commercial_expenses",
        0,
    )

    profit_from_sales = totals.get(
        "profit_from_sales",
        0,
    )

    ebitda = totals.get(
        "ebitda",
        0,
    )

    pretax_profit = totals.get(
        "pretax_profit",
        0,
    )

    net_profit = totals.get(
        "net_profit",
        0,
    )

    royalty = totals.get(
        "royalty",
        0,
    )

    rent = totals.get(
        "rent",
        0,
    )

    salary = totals.get(
        "salary",
        0,
    )

    acquiring = totals.get(
        "acquiring",
        0,
    )

    delivery_commission = totals.get(
        "delivery_commission",
        0,
    )

    if cogs:
        markup_factor = (
            revenue
            / cogs
        )

        markup_pct = (
            (
                revenue
                - cogs
            )
            / cogs
            * 100
        )

    else:
        markup_factor = None
        markup_pct = None

    return {
        "gross_margin_pct":
            round_percent(
                safe_percent(
                    gross_profit,
                    revenue,
                )
            ),

        "markup_factor":
            (
                round(
                    markup_factor,
                    4,
                )
                if markup_factor
                is not None
                else None
            ),

        "markup_pct":
            round_percent(
                markup_pct
            ),

        "cogs_share_pct":
            round_percent(
                safe_percent(
                    cogs,
                    revenue,
                )
            ),

        "commercial_expenses_share_pct":
            round_percent(
                safe_percent(
                    commercial_expenses,
                    revenue,
                )
            ),

        "sales_margin_pct":
            round_percent(
                safe_percent(
                    profit_from_sales,
                    revenue,
                )
            ),

        "ebitda_margin_pct":
            round_percent(
                safe_percent(
                    ebitda,
                    revenue,
                )
            ),

        "pretax_margin_pct":
            round_percent(
                safe_percent(
                    pretax_profit,
                    revenue,
                )
            ),

        "net_margin_pct":
            round_percent(
                safe_percent(
                    net_profit,
                    revenue,
                )
            ),

        "royalty_share_pct":
            round_percent(
                safe_percent(
                    royalty,
                    revenue,
                )
            ),

        "rent_share_pct":
            round_percent(
                safe_percent(
                    rent,
                    revenue,
                )
            ),

        "salary_share_pct":
            round_percent(
                safe_percent(
                    salary,
                    revenue,
                )
            ),

        "acquiring_share_pct":
            round_percent(
                safe_percent(
                    acquiring,
                    revenue,
                )
            ),

        "delivery_commission_share_pct":
            round_percent(
                safe_percent(
                    delivery_commission,
                    revenue,
                )
            ),
    }


def aggregate_line_items(
    months,
):
    totals = {}

    for month in months:
        for item in month.get(
            "line_items",
            [],
        ):
            code = item.get(
                "code"
            )

            label = item.get(
                "label"
            )

            if code:
                key = (
                    f"{code}|{label}"
                )
            else:
                key = (
                    f"label|{label}"
                )

            if key not in totals:
                totals[
                    key
                ] = {
                    "code":
                        code,

                    "label":
                        label,

                    "amount":
                        0.0,
                }

            totals[
                key
            ][
                "amount"
            ] += float(
                item.get(
                    "amount",
                    0,
                )
                or 0
            )

    result = []

    for item in totals.values():
        result.append(
            {
                "code":
                    item[
                        "code"
                    ],

                "label":
                    item[
                        "label"
                    ],

                "amount":
                    round_money(
                        item[
                            "amount"
                        ]
                    ),
            }
        )

    return result


def get_finance_period(
    start_month=None,
    end_month=None,
    include_partial=False,
    force_refresh=False,
):
    months = load_financial_months(
        force_refresh=force_refresh
    )

    if not months:
        return {
            "status":
                "no_data",
        }

    start = parse_month_argument(
        start_month
    )

    end = parse_month_argument(
        end_month
    )

    if start is None:
        start = (
            months[0][
                "year"
            ],
            months[0][
                "month"
            ],
        )

    if end is None:
        end = (
            months[-1][
                "year"
            ],
            months[-1][
                "month"
            ],
        )

    if (
        month_key(
            start[0],
            start[1],
        )
        > month_key(
            end[0],
            end[1],
        )
    ):
        return {
            "status":
                "invalid_period",

            "message":
                (
                    "Начало периода позже конца."
                ),
        }

    selected = []

    excluded_partial = []

    for month in months:
        key = month_key(
            month[
                "year"
            ],
            month[
                "month"
            ],
        )

        if key < month_key(
            start[0],
            start[1],
        ):
            continue

        if key > month_key(
            end[0],
            end[1],
        ):
            continue

        if (
            month[
                "is_partial"
            ]
            and not include_partial
        ):
            excluded_partial.append(
                month[
                    "month_key"
                ]
            )
            continue

        selected.append(
            month
        )

    if not selected:
        return {
            "status":
                "no_data",

            "requested_start":
                f"{start[0]:04d}-{start[1]:02d}",

            "requested_end":
                f"{end[0]:04d}-{end[1]:02d}",

            "excluded_partial_months":
                excluded_partial,
        }

    totals = {
        metric:
            0.0
        for metric
        in MONEY_ROW_SPECS
    }

    for month in selected:
        for metric in totals:
            totals[
                metric
            ] += float(
                month[
                    "metrics"
                ].get(
                    metric,
                    0,
                )
                or 0
            )

    totals = {
        metric:
            round_money(
                value
            )
        for (
            metric,
            value,
        )
        in totals.items()
    }

    derived = derive_metrics(
        totals
    )

    metrics = {
        **totals,
        **derived,
    }

    contains_partial = any(
        month[
            "is_partial"
        ]
        for month in selected
    )

    warnings = []

    if contains_partial:
        warnings.append(
            (
                "Период включает текущий незакрытый месяц. "
                "Расходы, EBITDA, прибыль и рентабельность "
                "могут быть неполными до закрытия месяца."
            )
        )

    return {
        "status":
            "ok",

        "source":
            "Google Sheets / ОПиУ",

        "requested_period": {
            "start":
                f"{start[0]:04d}-{start[1]:02d}",

            "end":
                f"{end[0]:04d}-{end[1]:02d}",
        },

        "actual_period": {
            "start":
                selected[0][
                    "month_key"
                ],

            "end":
                selected[-1][
                    "month_key"
                ],
        },

        "months_count":
            len(
                selected
            ),

        "months": [
            {
                "month":
                    month[
                        "month_key"
                    ],

                "is_partial":
                    month[
                        "is_partial"
                    ],
            }
            for month
            in selected
        ],

        "contains_partial_month":
            contains_partial,

        "excluded_partial_months":
            excluded_partial,

        "metrics":
            metrics,

        "line_items":
            aggregate_line_items(
                selected
            ),

        "warnings":
            warnings,

        "calculation_notes": {
            "gross_margin_pct":
                (
                    "Σ валовая прибыль / "
                    "Σ выручка × 100"
                ),

            "sales_margin_pct":
                (
                    "Σ прибыль от продаж / "
                    "Σ выручка × 100"
                ),

            "ebitda_margin_pct":
                (
                    "Σ EBITDA / "
                    "Σ выручка × 100"
                ),

            "pretax_margin_pct":
                (
                    "Σ прибыль до налогообложения / "
                    "Σ выручка × 100"
                ),

            "net_margin_pct":
                (
                    "Σ чистая прибыль / "
                    "Σ выручка × 100"
                ),

            "markup_factor":
                (
                    "Σ выручка / "
                    "Σ себестоимость"
                ),

            "markup_pct":
                (
                    "(Σ выручка - Σ себестоимость) / "
                    "Σ себестоимость × 100"
                ),
        },
    }


def percent_change(
    later,
    earlier,
):
    later = float(
        later or 0
    )

    earlier = float(
        earlier or 0
    )

    if earlier == 0:
        return None

    return round(
        (
            later
            - earlier
        )
        / abs(
            earlier
        )
        * 100,
        2,
    )


def compare_finance_periods(
    start_a,
    end_a,
    start_b,
    end_b,
    include_partial=False,
):
    period_a = get_finance_period(
        start_month=start_a,
        end_month=end_a,
        include_partial=include_partial,
    )

    period_b = get_finance_period(
        start_month=start_b,
        end_month=end_b,
        include_partial=include_partial,
    )

    if (
        period_a.get(
            "status"
        )
        != "ok"
        or period_b.get(
            "status"
        )
        != "ok"
    ):
        return {
            "status":
                "period_error",

            "period_a":
                period_a,

            "period_b":
                period_b,
        }

    metrics_a = period_a[
        "metrics"
    ]

    metrics_b = period_b[
        "metrics"
    ]

    comparison = {}

    all_metrics = sorted(
        set(
            metrics_a
        )
        | set(
            metrics_b
        )
    )

    for metric in all_metrics:
        value_a = metrics_a.get(
            metric
        )

        value_b = metrics_b.get(
            metric
        )

        if (
            value_a is None
            or value_b is None
        ):
            continue

        if metric in PERCENT_METRICS:
            comparison[
                metric
            ] = {
                "period_a":
                    value_a,

                "period_b":
                    value_b,

                "delta_percentage_points":
                    round(
                        value_b
                        - value_a,
                        2,
                    ),
            }

        elif metric == "markup_factor":
            comparison[
                metric
            ] = {
                "period_a":
                    value_a,

                "period_b":
                    value_b,

                "delta":
                    round(
                        value_b
                        - value_a,
                        4,
                    ),
            }

        else:
            comparison[
                metric
            ] = {
                "period_a":
                    value_a,

                "period_b":
                    value_b,

                "delta":
                    round_money(
                        value_b
                        - value_a
                    ),

                "change_pct":
                    percent_change(
                        value_b,
                        value_a,
                    ),
            }

    return {
        "status":
            "ok",

        "source":
            "Google Sheets / ОПиУ",

        "period_a":
            period_a,

        "period_b":
            period_b,

        "comparison":
            comparison,
    }


def normalize_metric_name(
    metric,
):
    text = normalize_text(
        metric
    ).lower()

    text = text.replace(
        "ё",
        "е",
    )

    return text


def get_finance_metric(
    metric,
    start_month=None,
    end_month=None,
    include_partial=False,
):
    normalized = normalize_metric_name(
        metric
    )

    if normalized in {
        "рентабельность",
        "средняя рентабельность",
    }:
        return {
            "status":
                "ambiguous_metric",

            "metric":
                metric,

            "message":
                (
                    "У рентабельности есть несколько "
                    "корректных определений."
                ),

            "available_metrics": {
                "gross_margin_pct":
                    "валовая маржинальность",

                "sales_margin_pct":
                    "рентабельность продаж",

                "ebitda_margin_pct":
                    "EBITDA-рентабельность",

                "pretax_margin_pct":
                    "рентабельность до налогов",

                "net_margin_pct":
                    "чистая рентабельность",
            },
        }

    metric_key = METRIC_ALIASES.get(
        normalized,
        metric,
    )

    period = get_finance_period(
        start_month=start_month,
        end_month=end_month,
        include_partial=include_partial,
    )

    if period.get(
        "status"
    ) != "ok":
        return period

    metrics = period[
        "metrics"
    ]

    if metric_key in metrics:
        return {
            "status":
                "ok",

            "source":
                period[
                    "source"
                ],

            "metric":
                metric_key,

            "value":
                metrics[
                    metric_key
                ],

            "period":
                period[
                    "actual_period"
                ],

            "months_count":
                period[
                    "months_count"
                ],

            "contains_partial_month":
                period[
                    "contains_partial_month"
                ],

            "warnings":
                period[
                    "warnings"
                ],
        }

    normalized_label = normalize_text(
        metric
    ).lower()

    matches = []

    for item in period.get(
        "line_items",
        [],
    ):
        label = normalize_text(
            item.get(
                "label"
            )
        ).lower()

        if (
            normalized_label
            == label
            or normalized_label
            in label
        ):
            matches.append(
                item
            )

    if len(matches) == 1:
        return {
            "status":
                "ok",

            "source":
                period[
                    "source"
                ],

            "metric":
                matches[0][
                    "label"
                ],

            "code":
                matches[0][
                    "code"
                ],

            "value":
                matches[0][
                    "amount"
                ],

            "period":
                period[
                    "actual_period"
                ],

            "months_count":
                period[
                    "months_count"
                ],

            "contains_partial_month":
                period[
                    "contains_partial_month"
                ],

            "warnings":
                period[
                    "warnings"
                ],
        }

    if len(matches) > 1:
        return {
            "status":
                "multiple_matches",

            "query":
                metric,

            "matches":
                matches,
        }

    return {
        "status":
            "unknown_metric",

        "metric":
            metric,

        "available_derived_metrics":
            sorted(
                metrics.keys()
            ),
    }


def get_finance_overall(
    include_partial=False,
):
    return get_finance_period(
        start_month=None,
        end_month=None,
        include_partial=include_partial,
    )


def print_money(
    label,
    value,
):
    print(
        f"{label}: "
        f"{float(value or 0):,.2f}"
    )


def main():
    print()
    print("=" * 70)
    print("FINANCE TOOLS — TEST")
    print("=" * 70)
    print()

    result = get_finance_overall(
        include_partial=False
    )

    print(
        "status:",
        result.get(
            "status"
        ),
    )

    if result.get(
        "status"
    ) != "ok":
        print(
            result
        )
        return

    print(
        "source:",
        result[
            "source"
        ],
    )

    print(
        "period:",
        result[
            "actual_period"
        ],
    )

    print(
        "months_count:",
        result[
            "months_count"
        ],
    )

    print()

    metrics = result[
        "metrics"
    ]

    print_money(
        "Выручка",
        metrics[
            "revenue"
        ],
    )

    print_money(
        "Себестоимость",
        metrics[
            "cogs"
        ],
    )

    print_money(
        "Валовая прибыль",
        metrics[
            "gross_profit"
        ],
    )

    print(
        "Валовая маржинальность:",
        metrics[
            "gross_margin_pct"
        ],
        "%",
    )

    print(
        "Торговая наценка, коэффициент:",
        metrics[
            "markup_factor"
        ],
    )

    print(
        "Наценка:",
        metrics[
            "markup_pct"
        ],
        "%",
    )

    print_money(
        "Роялти",
        metrics[
            "royalty"
        ],
    )

    print(
        "Доля роялти:",
        metrics[
            "royalty_share_pct"
        ],
        "%",
    )

    print_money(
        "Прибыль от продаж",
        metrics[
            "profit_from_sales"
        ],
    )

    print(
        "Рентабельность продаж:",
        metrics[
            "sales_margin_pct"
        ],
        "%",
    )

    print_money(
        "EBITDA",
        metrics[
            "ebitda"
        ],
    )

    print(
        "EBITDA-рентабельность:",
        metrics[
            "ebitda_margin_pct"
        ],
        "%",
    )

    print_money(
        "Чистая прибыль",
        metrics[
            "net_profit"
        ],
    )

    print(
        "Чистая рентабельность:",
        metrics[
            "net_margin_pct"
        ],
        "%",
    )

    print()

    print(
        "Исключённые незакрытые месяцы:",
        result[
            "excluded_partial_months"
        ],
    )

    print()
    print("=" * 70)


if __name__ == "__main__":
    main()