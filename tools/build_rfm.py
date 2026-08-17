import csv
import os
import sqlite3
from collections import Counter
from decimal import Decimal


PROJECT_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

ANALYTICS_DB = os.path.join(
    PROJECT_DIR,
    "analytics.sqlite"
)

RFM_CSV = os.path.join(
    PROJECT_DIR,
    "customer_rfm.csv"
)


# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

def cents_to_rubles(cents):
    return (
        Decimal(cents)
        / Decimal("100")
    )


def format_money(cents):
    return (
        f"{cents_to_rubles(cents):,.2f}"
        .replace(",", " ")
        + " ₽"
    )


def percentile(values, probability):
    if not values:
        return 0

    ordered = sorted(values)

    if len(ordered) == 1:
        return ordered[0]

    position = (
        (len(ordered) - 1)
        * probability
    )

    lower_index = int(position)

    upper_index = min(
        lower_index + 1,
        len(ordered) - 1
    )

    fraction = (
        position
        - lower_index
    )

    return (
        ordered[lower_index]
        + (
            ordered[upper_index]
            - ordered[lower_index]
        )
        * fraction
    )


# ============================================================
# R
# ============================================================

def score_recency(recency_days):

    if recency_days <= 30:
        return 5

    if recency_days <= 60:
        return 4

    if recency_days <= 90:
        return 3

    if recency_days <= 150:
        return 2

    return 1


# ============================================================
# F
# ============================================================

def score_frequency(frequency):

    if frequency >= 11:
        return 5

    if frequency >= 6:
        return 4

    if frequency >= 3:
        return 3

    if frequency == 2:
        return 2

    return 1


# ============================================================
# M
# ============================================================

def score_monetary(
    monetary_cents,
    thresholds
):

    q20, q40, q60, q80 = thresholds

    if monetary_cents <= q20:
        return 1

    if monetary_cents <= q40:
        return 2

    if monetary_cents <= q60:
        return 3

    if monetary_cents <= q80:
        return 4

    return 5


# ============================================================
# СЕГМЕНТ
# ============================================================

def classify_segment(
    r_score,
    f_score,
    m_score,
    frequency,
    monetary_cents,
    vip_monetary_threshold
):

    # VIP:
    # активен последние 30 дней,
    # минимум 6 покупок,
    # входит в top 10% по деньгам.

    if (
        r_score == 5
        and frequency >= 6
        and monetary_cents
        >= vip_monetary_threshold
    ):
        return "VIP"

    if (
        r_score >= 4
        and f_score >= 3
        and m_score >= 3
    ):
        return "Лояльный"

    if (
        r_score >= 4
        and frequency == 1
    ):
        return "Новый"

    if r_score >= 4:
        return "Активный"

    if (
        r_score == 3
        and (
            f_score >= 4
            or m_score >= 4
        )
    ):
        return "Нужно удержать"

    if r_score == 3:
        return "Остывает"

    if (
        r_score == 2
        and (
            f_score >= 4
            or m_score >= 4
        )
    ):
        return "Ценный под риском"

    if r_score == 2:
        return "Под риском"

    if (
        r_score == 1
        and (
            f_score >= 4
            or m_score >= 4
        )
    ):
        return "Потерянный ценный"

    return "Потерянный"


# ============================================================
# CSV
# ============================================================

def export_rfm_csv(connection):

    cursor = connection.cursor()

    rows = cursor.execute(
        """
        SELECT
            m.customer_id,
            c.check_name,
            c.name,
            c.lastname,
            c.phone,
            m.first_purchase,
            m.last_purchase,
            m.recency_days,
            m.frequency,
            m.monetary_cents,
            m.average_check_cents,
            m.average_interval_days,
            r.r_score,
            r.f_score,
            r.m_score,
            r.rfm_code,
            r.rfm_total,
            r.segment,
            r.cycle_overdue_ratio
        FROM customer_metrics m

        JOIN customer_rfm r
            ON r.customer_id =
               m.customer_id

        LEFT JOIN customers c
            ON c.customer_id =
               m.customer_id

        ORDER BY
            CASE r.segment
                WHEN 'VIP' THEN 1
                WHEN 'Лояльный' THEN 2
                WHEN 'Нужно удержать' THEN 3
                WHEN 'Ценный под риском' THEN 4
                WHEN 'Потерянный ценный' THEN 5
                ELSE 6
            END,
            m.monetary_cents DESC
        """
    ).fetchall()

    headers = [
        "customer_id",
        "check_name",
        "name",
        "lastname",
        "phone",
        "first_purchase",
        "last_purchase",
        "recency_days",
        "frequency",
        "monetary",
        "average_check",
        "average_interval_days",
        "r_score",
        "f_score",
        "m_score",
        "rfm_code",
        "rfm_total",
        "segment",
        "cycle_overdue_ratio",
    ]

    with open(
        RFM_CSV,
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        writer = csv.writer(file)

        writer.writerow(headers)

        for row in rows:

            writer.writerow(
                [
                    row[0],
                    row[1],
                    row[2],
                    row[3],
                    row[4],
                    row[5],
                    row[6],
                    row[7],
                    row[8],
                    f"{cents_to_rubles(row[9]):.2f}",
                    f"{cents_to_rubles(row[10]):.2f}",
                    (
                        ""
                        if row[11] is None
                        else f"{row[11]:.2f}"
                    ),
                    row[12],
                    row[13],
                    row[14],
                    row[15],
                    row[16],
                    row[17],
                    (
                        ""
                        if row[18] is None
                        else f"{row[18]:.2f}"
                    ),
                ]
            )


# ============================================================
# ИТОГ
# ============================================================

def print_summary(
    customer_count,
    monetary_thresholds,
    vip_monetary_threshold,
    segment_counter
):

    print()
    print("=" * 70)
    print("RFM ПОСТРОЕН")

    print()
    print(
        f"Клиентов в RFM: "
        f"{customer_count}"
    )

    print()
    print(
        "R: "
        "R5=0-30, "
        "R4=31-60, "
        "R3=61-90, "
        "R2=91-150, "
        "R1=151+ дней"
    )

    print(
        "F: "
        "F1=1, "
        "F2=2, "
        "F3=3-5, "
        "F4=6-10, "
        "F5=11+ покупок"
    )

    print()
    print(
        "M — квинтили "
        "текущей клиентской базы:"
    )

    labels = [
        "20%",
        "40%",
        "60%",
        "80%",
    ]

    for label, value in zip(
        labels,
        monetary_thresholds
    ):

        print(
            f"{label}: "
            f"{format_money(int(value))}"
        )

    print()
    print(
        "VIP:"
    )

    print(
        "последняя покупка <= 30 дней"
    )

    print(
        "6+ покупок"
    )

    print(
        "top 10% по денежной ценности"
    )

    print(
        "Текущий денежный порог VIP: "
        f"{format_money(int(vip_monetary_threshold))}"
    )

    print()
    print("СЕГМЕНТЫ:")

    for segment, count in (
        segment_counter
        .most_common()
    ):

        print(
            f"{segment}: "
            f"{count}"
        )

    print()
    print("Создано:")

    print(
        "таблица customer_rfm "
        "в analytics.sqlite"
    )

    print(
        "customer_rfm.csv"
    )

    print("=" * 70)


# ============================================================
# BUILD
# ============================================================

def build_rfm():

    if not os.path.exists(
        ANALYTICS_DB
    ):

        raise FileNotFoundError(
            "Не найден analytics.sqlite. "
            "Сначала запусти "
            "tools\\build_analytics.py"
        )

    connection = sqlite3.connect(
        ANALYTICS_DB
    )

    connection.row_factory = sqlite3.Row

    cursor = connection.cursor()

    rows = cursor.execute(
        """
        SELECT
            m.customer_id,
            m.recency_days,
            m.frequency,
            m.monetary_cents,
            m.average_interval_days
        FROM customer_metrics m

        LEFT JOIN customer_flags f
            ON f.customer_id =
               m.customer_id

        WHERE
            COALESCE(
                f.flag,
                ''
            ) <> 'shared_card'
        """
    ).fetchall()

    if not rows:

        connection.close()

        raise RuntimeError(
            "В customer_metrics "
            "нет клиентов."
        )

    monetary_values = [
        row["monetary_cents"]
        for row in rows
    ]

    monetary_thresholds = (
        percentile(
            monetary_values,
            0.20
        ),
        percentile(
            monetary_values,
            0.40
        ),
        percentile(
            monetary_values,
            0.60
        ),
        percentile(
            monetary_values,
            0.80
        ),
    )

    # Отдельный более строгий
    # денежный порог для VIP.

    vip_monetary_threshold = (
        percentile(
            monetary_values,
            0.90
        )
    )

    cursor.execute(
        """
        DROP TABLE IF EXISTS
        customer_rfm
        """
    )

    cursor.execute(
        """
        CREATE TABLE customer_rfm (
            customer_id TEXT PRIMARY KEY,
            r_score INTEGER,
            f_score INTEGER,
            m_score INTEGER,
            rfm_code TEXT,
            rfm_total INTEGER,
            segment TEXT,
            cycle_overdue_ratio REAL
        )
        """
    )

    cursor.execute(
        """
        CREATE INDEX
        idx_customer_rfm_segment
        ON customer_rfm(segment)
        """
    )

    segment_counter = Counter()

    for row in rows:

        customer_id = (
            row["customer_id"]
        )

        recency_days = (
            row["recency_days"]
        )

        frequency = (
            row["frequency"]
        )

        monetary_cents = (
            row["monetary_cents"]
        )

        average_interval_days = (
            row["average_interval_days"]
        )

        r_score = score_recency(
            recency_days
        )

        f_score = score_frequency(
            frequency
        )

        m_score = score_monetary(
            monetary_cents,
            monetary_thresholds
        )

        rfm_code = (
            f"{r_score}"
            f"{f_score}"
            f"{m_score}"
        )

        rfm_total = (
            r_score
            + f_score
            + m_score
        )

        cycle_overdue_ratio = None

        if (
            average_interval_days
            is not None
            and average_interval_days > 0
        ):

            cycle_overdue_ratio = (
                recency_days
                / average_interval_days
            )

        segment = classify_segment(
            r_score,
            f_score,
            m_score,
            frequency,
            monetary_cents,
            vip_monetary_threshold
        )

        segment_counter[
            segment
        ] += 1

        cursor.execute(
            """
            INSERT INTO customer_rfm (
                customer_id,
                r_score,
                f_score,
                m_score,
                rfm_code,
                rfm_total,
                segment,
                cycle_overdue_ratio
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                customer_id,
                r_score,
                f_score,
                m_score,
                rfm_code,
                rfm_total,
                segment,
                cycle_overdue_ratio,
            )
        )

    connection.commit()

    export_rfm_csv(
        connection
    )

    print_summary(
        len(rows),
        monetary_thresholds,
        vip_monetary_threshold,
        segment_counter
    )

    connection.close()


if __name__ == "__main__":
    build_rfm()