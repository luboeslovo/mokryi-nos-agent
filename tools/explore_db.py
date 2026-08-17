import sqlite3


DB_FILE = "analytics.sqlite"

TARGET_PRODUCT = (
    "Royal Canin British Shorthair Adult "
    "в соусе пауч д/кош 85 г"
)


db = sqlite3.connect(DB_FILE)


query = """
WITH purchase_checks AS (

    SELECT check_id

    FROM checks

    WHERE
        LOWER(type) NOT LIKE '%возврат%'
),

target_checks AS (

    SELECT DISTINCT
        i.check_id

    FROM items i

    JOIN purchase_checks pc
        ON pc.check_id = i.check_id

    WHERE
        i.product_name = ?
),

target_count AS (

    SELECT
        COUNT(*) AS n

    FROM target_checks
),

total_count AS (

    SELECT
        COUNT(*) AS n

    FROM purchase_checks
),

product_counts AS (

    SELECT
        i.product_name,
        COUNT(DISTINCT i.check_id) AS product_checks

    FROM items i

    JOIN purchase_checks pc
        ON pc.check_id = i.check_id

    GROUP BY
        i.product_name
),

pair_counts AS (

    SELECT
        i.product_name,
        COUNT(DISTINCT i.check_id) AS together

    FROM items i

    JOIN target_checks tc
        ON tc.check_id = i.check_id

    WHERE
        i.product_name <> ?

    GROUP BY
        i.product_name
)

SELECT
    pair_counts.product_name,

    pair_counts.together,

    ROUND(
        100.0
        * pair_counts.together
        / target_count.n,
        1
    ) AS confidence_percent,

    product_counts.product_checks,

    ROUND(
        (
            1.0
            * pair_counts.together
            / target_count.n
        )
        /
        (
            1.0
            * product_counts.product_checks
            / total_count.n
        ),
        2
    ) AS lift

FROM pair_counts

JOIN product_counts
    ON product_counts.product_name
       = pair_counts.product_name

CROSS JOIN target_count

CROSS JOIN total_count

WHERE
    pair_counts.together >= 3
    AND pair_counts.product_name
        NOT LIKE 'Пакет%'

ORDER BY
    lift DESC,
    pair_counts.together DESC

LIMIT 15
"""


rows = db.execute(
    query,
    (
        TARGET_PRODUCT,
        TARGET_PRODUCT,
    )
).fetchall()


print()
print("ТОВАР:")
print(TARGET_PRODUCT)
print()

print(
    "ТОВАРЫ, КОТОРЫЕ ПОКУПАЮТ "
    "ВМЕСТЕ ЧАЩЕ ОБЫЧНОГО"
)

print("=" * 110)


for row in rows:

    (
        product_name,
        together,
        confidence_percent,
        product_checks,
        lift,
    ) = row

    print(
        product_name,
        "| вместе:",
        together,
        "| в",
        confidence_percent,
        "% чеков с целевым товаром",
        "| вообще чеков:",
        product_checks,
        "| lift:",
        lift,
    )


db.close()