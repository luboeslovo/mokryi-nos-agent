import csv
import os


PROJECT_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

RFM_FILE = os.path.join(
    PROJECT_DIR,
    "customer_rfm.csv",
)


RISK_SEGMENTS = [
    "Ценный под риском",
    "Нужно удержать",
    "Под риском",
    "Остывает",
]

LOST_SEGMENTS = [
    "Потерянный ценный",
    "Потерянный",
]


CONTACT_SELECTION_RULE = (
    "Сначала более приоритетный RFM-сегмент, "
    "внутри сегмента — более высокая сумма покупок, "
    "затем просрочка цикла и частота покупок."
)


def to_float(value):
    try:
        return float(
            value or 0
        )

    except Exception:
        return 0.0


def to_int(value):
    try:
        return int(
            float(
                value or 0
            )
        )

    except Exception:
        return 0


def load_rfm():
    if not os.path.exists(
        RFM_FILE
    ):
        raise FileNotFoundError(
            f"Не найден файл: {RFM_FILE}"
        )

    rows = []

    with open(
        RFM_FILE,
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        reader = csv.DictReader(
            file
        )

        for row in reader:
            rows.append(
                row
            )

    return rows


def compact_customer(row):
    return {
        "customer_id":
            row.get(
                "customer_id"
            ),

        "name":
            row.get(
                "name"
            ),

        "lastname":
            row.get(
                "lastname"
            ),

        "full_name":
            row.get(
                "check_name"
            ),

        "phone":
            row.get(
                "phone"
            ),

        "segment":
            row.get(
                "segment"
            ),

        "last_purchase":
            row.get(
                "last_purchase"
            ),

        "recency_days":
            to_int(
                row.get(
                    "recency_days"
                )
            ),

        "frequency":
            to_int(
                row.get(
                    "frequency"
                )
            ),

        "monetary":
            round(
                to_float(
                    row.get(
                        "monetary"
                    )
                ),
                2,
            ),

        "average_check":
            round(
                to_float(
                    row.get(
                        "average_check"
                    )
                ),
                2,
            ),

        "average_interval_days":
            round(
                to_float(
                    row.get(
                        "average_interval_days"
                    )
                ),
                2,
            ),

        "cycle_overdue_ratio":
            round(
                to_float(
                    row.get(
                        "cycle_overdue_ratio"
                    )
                ),
                2,
            ),

        "rfm_code":
            row.get(
                "rfm_code"
            ),
    }


def get_customer_rfm(
    customer_id,
):
    requested_id = str(
        customer_id or ""
    ).strip()

    if not requested_id:
        return {
            "status":
                "invalid_customer_id",

            "customer_id":
                requested_id,
        }

    for row in load_rfm():
        row_customer_id = str(
            row.get(
                "customer_id"
            )
            or ""
        ).strip()

        if (
            row_customer_id
            == requested_id
        ):
            return {
                "status":
                    "ok",

                "customer":
                    compact_customer(
                        row
                    ),
            }

    return {
        "status":
            "customer_not_found",

        "customer_id":
            requested_id,
    }


def get_rfm_summary():
    rows = load_rfm()

    counts = {}

    for row in rows:
        segment = str(
            row.get(
                "segment"
            )
            or "Без сегмента"
        ).strip()

        counts[
            segment
        ] = (
            counts.get(
                segment,
                0,
            )
            + 1
        )

    total = len(
        rows
    )

    segments = []

    for segment, count in sorted(
        counts.items(),
        key=lambda item:
            item[1],
        reverse=True,
    ):
        share_percent = (
            count
            / total
            * 100
            if total
            else 0
        )

        segments.append(
            {
                "segment":
                    segment,

                "count":
                    count,

                "share_percent":
                    round(
                        share_percent,
                        2,
                    ),
            }
        )

    risk_count = sum(
        counts.get(
            segment,
            0,
        )
        for segment
        in RISK_SEGMENTS
    )

    lost_count = sum(
        counts.get(
            segment,
            0,
        )
        for segment
        in LOST_SEGMENTS
    )

    return {
        "status":
            "ok",

        "total_customers":
            total,

        "segments":
            segments,

        "risk_customers":
            risk_count,

        "lost_customers":
            lost_count,
    }


def find_segment_name(
    requested_segment,
):
    requested = str(
        requested_segment
        or ""
    ).strip().lower()

    if not requested:
        return None

    available = {
        str(
            row.get(
                "segment"
            )
            or ""
        ).strip().lower():
            str(
                row.get(
                    "segment"
                )
                or ""
            ).strip()

        for row
        in load_rfm()
    }

    if requested in available:
        return available[
            requested
        ]

    for lower_name, original_name in (
        available.items()
    ):
        if (
            requested in lower_name
            or lower_name in requested
        ):
            return original_name

    return None


def get_rfm_segment(
    segment,
    limit=10,
    sort_by="monetary",
):
    limit = max(
        1,
        min(
            int(limit),
            100,
        ),
    )

    real_segment = find_segment_name(
        segment
    )

    if not real_segment:
        return {
            "status":
                "segment_not_found",

            "requested_segment":
                segment,

            "available_segments": [
                item[
                    "segment"
                ]
                for item
                in get_rfm_summary()[
                    "segments"
                ]
            ],
        }

    rows = [
        row
        for row
        in load_rfm()
        if str(
            row.get(
                "segment"
            )
            or ""
        ).strip()
        == real_segment
    ]

    sort_by = str(
        sort_by
        or "monetary"
    ).strip().lower()

    if sort_by == "recency":
        rows.sort(
            key=lambda row: (
                to_int(
                    row.get(
                        "recency_days"
                    )
                ),
                to_float(
                    row.get(
                        "monetary"
                    )
                ),
            ),
            reverse=True,
        )

    elif sort_by == "frequency":
        rows.sort(
            key=lambda row: (
                to_int(
                    row.get(
                        "frequency"
                    )
                ),
                to_float(
                    row.get(
                        "monetary"
                    )
                ),
            ),
            reverse=True,
        )

    elif sort_by == "overdue":
        rows.sort(
            key=lambda row: (
                to_float(
                    row.get(
                        "cycle_overdue_ratio"
                    )
                ),
                to_float(
                    row.get(
                        "monetary"
                    )
                ),
            ),
            reverse=True,
        )

    else:
        sort_by = "monetary"

        rows.sort(
            key=lambda row: (
                to_float(
                    row.get(
                        "monetary"
                    )
                ),
                to_int(
                    row.get(
                        "frequency"
                    )
                ),
            ),
            reverse=True,
        )

    return {
        "status":
            "ok",

        "segment":
            real_segment,

        "total_in_segment":
            len(
                rows
            ),

        "sort_by":
            sort_by,

        "customers": [
            compact_customer(
                row
            )
            for row
            in rows[
                :limit
            ]
        ],
    }


def normalize_contact_mode(
    mode,
):
    mode = str(
        mode
        or "retain"
    ).strip().lower()

    if mode in {
        "reactivate",
        "return",
        "lost",
        "вернуть",
        "потерянные",
        "потерянный",
        "возврат",
    }:
        return {
            "mode":
                "reactivate",

            "segments":
                LOST_SEGMENTS,

            "priority": {
                "Потерянный ценный":
                    0,

                "Потерянный":
                    1,
            },
        }

    return {
        "mode":
            "retain",

        "segments":
            RISK_SEGMENTS,

        "priority": {
            "Ценный под риском":
                0,

            "Нужно удержать":
                1,

            "Под риском":
                2,

            "Остывает":
                3,
        },
    }


def get_contact_candidate_rows(
    mode="retain",
):
    config = normalize_contact_mode(
        mode
    )

    selected_segments = (
        config[
            "segments"
        ]
    )

    priority = (
        config[
            "priority"
        ]
    )

    rows = [
        row
        for row
        in load_rfm()
        if str(
            row.get(
                "segment"
            )
            or ""
        ).strip()
        in selected_segments
    ]

    rows.sort(
        key=lambda row: (
            priority.get(
                str(
                    row.get(
                        "segment"
                    )
                    or ""
                ).strip(),
                999,
            ),

            -to_float(
                row.get(
                    "monetary"
                )
            ),

            -to_float(
                row.get(
                    "cycle_overdue_ratio"
                )
            ),

            -to_int(
                row.get(
                    "frequency"
                )
            ),
        )
    )

    return {
        "mode":
            config[
                "mode"
            ],

        "segments":
            selected_segments,

        "rows":
            rows,
    }


def get_contact_candidate_pool(
    mode="retain",
):
    """
    Внутренний полный пул кандидатов.

    ВАЖНО:
    здесь НЕТ ограничения в 100 клиентов.

    Эта функция нужна call_tools.py, чтобы сначала
    посчитать call score для ВСЕХ подходящих клиентов,
    а уже потом выбрать действительно лучшего.
    """

    payload = (
        get_contact_candidate_rows(
            mode
        )
    )

    rows = payload[
        "rows"
    ]

    return {
        "status":
            "ok",

        "mode":
            payload[
                "mode"
            ],

        "included_segments":
            payload[
                "segments"
            ],

        "selection_rule":
            CONTACT_SELECTION_RULE,

        "total_candidates":
            len(
                rows
            ),

        "customers": [
            compact_customer(
                row
            )
            for row
            in rows
        ],
    }


def get_contact_candidates(
    limit=10,
    mode="retain",
):
    """
    Публичный инструмент для агента.

    Здесь лимит до 100 сохраняем специально:
    пользователю не нужно возвращать сотни клиентов
    одним сообщением.

    Полный пул для внутреннего скоринга берётся через
    get_contact_candidate_pool().
    """

    limit = max(
        1,
        min(
            int(limit),
            100,
        ),
    )

    pool = (
        get_contact_candidate_pool(
            mode
        )
    )

    customers = pool.get(
        "customers",
        [],
    )

    return {
        "status":
            "ok",

        "mode":
            pool.get(
                "mode"
            ),

        "included_segments":
            pool.get(
                "included_segments",
                [],
            ),

        "selection_rule":
            pool.get(
                "selection_rule"
            ),

        "total_candidates":
            pool.get(
                "total_candidates",
                len(
                    customers
                ),
            ),

        "returned_candidates":
            min(
                limit,
                len(
                    customers
                ),
            ),

        "customers":
            customers[
                :limit
            ],
    }


def demo():
    print()
    print("=" * 70)
    print(
        "RFM TOOLS — TEST"
    )
    print("=" * 70)

    print()
    print(
        "RFM конкретного клиента:"
    )

    print(
        get_customer_rfm(
            "1000446"
        )
    )

    summary = (
        get_rfm_summary()
    )

    print()
    print(
        "RFM-сводка:"
    )

    print(
        summary
    )

    print()
    print("=" * 70)
    print(
        "ПОЛНЫЙ ПУЛ ДЛЯ УДЕРЖАНИЯ"
    )
    print("=" * 70)

    retain_pool = (
        get_contact_candidate_pool(
            mode="retain"
        )
    )

    print(
        "Всего кандидатов:",
        retain_pool.get(
            "total_candidates"
        ),
    )

    print(
        "RFM risk_customers:",
        summary.get(
            "risk_customers"
        ),
    )

    print(
        "Совпадает:",
        (
            retain_pool.get(
                "total_candidates"
            )
            == summary.get(
                "risk_customers"
            )
        ),
    )

    print()
    print("=" * 70)
    print(
        "ПУБЛИЧНЫЙ ЛИМИТ 500 — ДОЛЖЕН ВЕРНУТЬ НЕ БОЛЕЕ 100"
    )
    print("=" * 70)

    public_retain = (
        get_contact_candidates(
            limit=500,
            mode="retain",
        )
    )

    print(
        "Всего в полном пуле:",
        public_retain.get(
            "total_candidates"
        ),
    )

    print(
        "Вернулось пользователю:",
        len(
            public_retain.get(
                "customers",
                [],
            )
        ),
    )

    print()
    print("=" * 70)
    print(
        "ПОЛНЫЙ ПУЛ ПОТЕРЯННЫХ"
    )
    print("=" * 70)

    lost_pool = (
        get_contact_candidate_pool(
            mode="reactivate"
        )
    )

    print(
        "Всего кандидатов:",
        lost_pool.get(
            "total_candidates"
        ),
    )

    print(
        "RFM lost_customers:",
        summary.get(
            "lost_customers"
        ),
    )

    print(
        "Совпадает:",
        (
            lost_pool.get(
                "total_candidates"
            )
            == summary.get(
                "lost_customers"
            )
        ),
    )

    print()
    print("=" * 70)
    print(
        "ПЕРВЫЕ 5 ДЛЯ УДЕРЖАНИЯ"
    )
    print("=" * 70)

    for customer in (
        retain_pool.get(
            "customers",
            [],
        )[:5]
    ):
        print(
            customer
        )


if __name__ == "__main__":
    demo()