import sqlite3
from collections import Counter
from datetime import datetime


DB_FILE = "analytics.sqlite"
DATE_FORMAT = "%d.%m.%Y %H:%M"

TOP_N = 20


connection = sqlite3.connect(DB_FILE)
cursor = connection.cursor()


# ============================================================
# БЕРЁМ САМЫХ ЧАСТЫХ КЛИЕНТОВ
# ============================================================

cursor.execute(
    """
    SELECT
        customer_id,
        lastname,
        name,
        phone,
        frequency,
        monetary_kopecks,
        average_check_kopecks
    FROM customer_metrics
    ORDER BY frequency DESC
    LIMIT ?
    """,
    (TOP_N,)
)

top_customers = cursor.fetchall()


print()
print("=" * 90)
print("ПРОВЕРКА СВЕРХЧАСТЫХ КЛИЕНТОВ")
print("=" * 90)


for index, customer in enumerate(
    top_customers,
    start=1
):

    (
        customer_id,
        lastname,
        name,
        phone,
        frequency,
        monetary,
        average_check,
    ) = customer

    # --------------------------------------------------------
    # ВСЕ ПОКУПКИ ЭТОГО CUSTOMER_ID
    # --------------------------------------------------------

    cursor.execute(
        """
        SELECT
            date,
            number,
            amount_kopecks
        FROM checks
        WHERE customer_id = ?
          AND resolution_status = 'resolved'
          AND LOWER(check_type)
              NOT LIKE '%возврат%'
        ORDER BY date
        """,
        (customer_id,)
    )

    checks = cursor.fetchall()

    dates = []

    for (
        date_text,
        check_number,
        amount
    ) in checks:

        date = datetime.strptime(
            date_text,
            DATE_FORMAT
        )

        dates.append(date)

    # --------------------------------------------------------
    # ГРУППИРУЕМ ПО ДНЯМ
    # --------------------------------------------------------

    day_counter = Counter(
        date.date()
        for date in dates
    )

    unique_days = len(
        day_counter
    )

    max_checks_per_day = (
        max(day_counter.values())
        if day_counter
        else 0
    )

    days_with_2_plus = sum(
        1
        for count in day_counter.values()
        if count >= 2
    )

    days_with_3_plus = sum(
        1
        for count in day_counter.values()
        if count >= 3
    )

    days_with_5_plus = sum(
        1
        for count in day_counter.values()
        if count >= 5
    )

    checks_per_active_day = (
        len(checks) / unique_days
        if unique_days
        else 0
    )

    # --------------------------------------------------------
    # ТОП ДНЕЙ ПО КОЛИЧЕСТВУ ЧЕКОВ
    # --------------------------------------------------------

    busiest_days = sorted(
        day_counter.items(),
        key=lambda item: item[1],
        reverse=True
    )[:5]

    # --------------------------------------------------------
    # ВЫВОД
    # --------------------------------------------------------

    print()
    print("-" * 90)

    print(
        f"{index}. "
        f"{lastname} {name}"
    )

    print(
        f"   customer_id: {customer_id}"
    )

    print(
        f"   телефон: {phone}"
    )

    print(
        f"   покупок: {frequency}"
    )

    print(
        f"   M: {monetary / 100:.2f} ₽"
    )

    print(
        f"   средний чек: "
        f"{average_check / 100:.2f} ₽"
    )

    print(
        f"   уникальных дней с покупками: "
        f"{unique_days}"
    )

    print(
        f"   чеков на активный день: "
        f"{checks_per_active_day:.2f}"
    )

    print(
        f"   максимум чеков за один день: "
        f"{max_checks_per_day}"
    )

    print(
        f"   дней с 2+ чеками: "
        f"{days_with_2_plus}"
    )

    print(
        f"   дней с 3+ чеками: "
        f"{days_with_3_plus}"
    )

    print(
        f"   дней с 5+ чеками: "
        f"{days_with_5_plus}"
    )

    print(
        "   самые загруженные дни:"
    )

    for (
        day,
        count
    ) in busiest_days:

        print(
            f"      {day}: "
            f"{count} чеков"
        )

    # --------------------------------------------------------
    # ГРУБЫЙ ФЛАГ
    # --------------------------------------------------------

    suspicious = (
        max_checks_per_day >= 5
        or checks_per_active_day >= 2.0
    )

    if suspicious:

        print(
            "   >>> ПОДОЗРИТЕЛЬНО "
            "НА ОБЩУЮ/ТЕХНИЧЕСКУЮ КАРТУ"
        )


print()
print("=" * 90)
print("ГОТОВО")
print("=" * 90)


connection.close()