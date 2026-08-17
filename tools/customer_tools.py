import sqlite3
import json

from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
DB_FILE = PROJECT_DIR / "analytics.sqlite"

SHARED_CARD_CUSTOMER_ID = "806542"


def get_customer_profile(customer_id):
    db = sqlite3.connect(DB_FILE)
    db.row_factory = sqlite3.Row

    customer = db.execute(
        """
        SELECT
            customer_id,
            name,
            lastname,
            phone,
            email
        FROM customers
        WHERE customer_id = ?
        """,
        (customer_id,)
    ).fetchone()

    if customer is None:
        db.close()
        return {
            "error": "customer_not_found",
            "customer_id": customer_id,
        }

    stats = db.execute(
        """
        SELECT
            COUNT(*) AS purchases,
            SUM(amount_cents) AS total_cents,
            AVG(amount_cents) AS average_cents,
            MIN(datetime_iso) AS first_purchase,
            MAX(datetime_iso) AS last_purchase
        FROM checks
        WHERE
            customer_id = ?
            AND resolution_status = 'resolved'
            AND LOWER(type) NOT LIKE '%возврат%'
        """,
        (customer_id,)
    ).fetchone()

    products = db.execute(
        """
        SELECT
            i.product_name,
            COUNT(*) AS purchase_lines,
            SUM(i.quantity) AS quantity,
            SUM(i.amount_cents) AS total_cents
        FROM checks ch

        JOIN items i
            ON i.check_id = ch.check_id

        WHERE
            ch.customer_id = ?
            AND ch.resolution_status = 'resolved'
            AND LOWER(ch.type) NOT LIKE '%возврат%'

        GROUP BY
            i.product_name

        ORDER BY
            total_cents DESC

        LIMIT 10
        """,
        (customer_id,)
    ).fetchall()

    db.close()

    result = {
        "customer": {
            "customer_id": customer["customer_id"],
            "name": customer["name"],
            "lastname": customer["lastname"],
            "phone": customer["phone"],
            "email": customer["email"],
        },
        "statistics": {
            "purchases": stats["purchases"],
            "total_rubles": round(
                (stats["total_cents"] or 0) / 100,
                2
            ),
            "average_check_rubles": round(
                (stats["average_cents"] or 0) / 100,
                2
            ),
            "first_purchase": stats["first_purchase"],
            "last_purchase": stats["last_purchase"],
        },
        "top_products": []
    }

    for product in products:
        result["top_products"].append(
            {
                "product_name": product["product_name"],
                "purchase_lines": product["purchase_lines"],
                "quantity": product["quantity"],
                "total_rubles": round(
                    (product["total_cents"] or 0) / 100,
                    2
                ),
            }
        )

    return result


def get_top_customers(limit=10):
    limit = int(limit)

    if limit < 1:
        limit = 1

    if limit > 20:
        limit = 20

    db = sqlite3.connect(DB_FILE)
    db.row_factory = sqlite3.Row

    rows = db.execute(
        """
        SELECT
            ch.customer_id,
            c.name,
            c.lastname,
            COUNT(*) AS purchases,
            SUM(ch.amount_cents) AS total_cents,
            AVG(ch.amount_cents) AS average_cents,
            MIN(ch.datetime_iso) AS first_purchase,
            MAX(ch.datetime_iso) AS last_purchase
        FROM checks ch

        JOIN customers c
            ON c.customer_id = ch.customer_id

        WHERE
            ch.customer_id IS NOT NULL
            AND ch.customer_id != ''
            AND ch.resolution_status = 'resolved'
            AND LOWER(ch.type) NOT LIKE '%возврат%'

        GROUP BY
            ch.customer_id,
            c.name,
            c.lastname

        ORDER BY
            total_cents DESC

        LIMIT ?
        """,
        (limit,)
    ).fetchall()

    db.close()

    customers = []

    for position, row in enumerate(rows, start=1):
        customers.append(
            {
                "position": position,
                "customer_id": row["customer_id"],
                "name": row["name"],
                "lastname": row["lastname"],
                "purchases": row["purchases"],
                "total_rubles": round(
                    (row["total_cents"] or 0) / 100,
                    2
                ),
                "average_check_rubles": round(
                    (row["average_cents"] or 0) / 100,
                    2
                ),
                "first_purchase": row["first_purchase"],
                "last_purchase": row["last_purchase"],
            }
        )

    return {
        "ranking": "total_positive_purchases",
        "limit": limit,
        "customers": customers,
    }


def _normalize_text(value):
    if value is None:
        return ""

    return " ".join(
        str(value)
        .strip()
        .casefold()
        .split()
    )


def _close_token(first, second):
    """
    Считает слова близкими, если они отличаются максимум
    на одну букву: вставка, удаление или замена.

    Это позволяет понимать формы вроде:
    Потапов -> Потапова
    Кирилл -> Кирилла
    Сергей -> Сергея
    """

    if first == second:
        return True

    if len(first) < 4 or len(second) < 4:
        return False

    if abs(len(first) - len(second)) > 1:
        return False

    if len(first) == len(second):
        differences = sum(
            1
            for a, b in zip(first, second)
            if a != b
        )

        return differences <= 1

    if len(first) > len(second):
        first, second = second, first

    short_index = 0
    long_index = 0
    differences = 0

    while (
        short_index < len(first)
        and long_index < len(second)
    ):

        if first[short_index] == second[long_index]:
            short_index += 1
            long_index += 1
            continue

        differences += 1

        if differences > 1:
            return False

        long_index += 1

    return True


def _all_tokens_match(query_tokens, customer_tokens):

    used_indexes = set()

    for query_token in query_tokens:

        found = False

        for index, customer_token in enumerate(
            customer_tokens
        ):

            if index in used_indexes:
                continue

            if _close_token(
                query_token,
                customer_token
            ):
                used_indexes.add(index)
                found = True
                break

        if not found:
            return False

    return True


def find_customer_by_name(query, limit=10):
    query_normalized = _normalize_text(query)

    if not query_normalized:
        return {
            "status": "invalid_query",
            "query": query,
            "matches": []
        }

    limit = int(limit)

    if limit < 1:
        limit = 1

    if limit > 20:
        limit = 20

    db = sqlite3.connect(DB_FILE)
    db.row_factory = sqlite3.Row

    rows = db.execute(
        """
        SELECT
            customer_id,
            name,
            lastname
        FROM customers
        WHERE
            customer_id IS NOT NULL
            AND customer_id != ''
            AND customer_id != ?
        """,
        (SHARED_CARD_CUSTOMER_ID,)
    ).fetchall()

    db.close()

    query_tokens = query_normalized.split()

    matches = []

    for row in rows:
        name = row["name"] or ""
        lastname = row["lastname"] or ""

        name_normalized = _normalize_text(name)
        lastname_normalized = _normalize_text(lastname)

        full_name = _normalize_text(
            f"{name} {lastname}"
        )

        reverse_name = _normalize_text(
            f"{lastname} {name}"
        )

        customer_tokens = [
            token
            for token in [
                name_normalized,
                lastname_normalized
            ]
            if token
        ]

        score = None

        if query_normalized == full_name:
            score = 0

        elif query_normalized == reverse_name:
            score = 1

        elif all(
            token in customer_tokens
            for token in query_tokens
        ):
            score = 2

        elif _all_tokens_match(
            query_tokens,
            customer_tokens
        ):
            score = 3

        elif (
            query_normalized in full_name
            or query_normalized in reverse_name
        ):
            score = 4

        if score is None:
            continue

        matches.append(
            {
                "score": score,
                "customer_id": row["customer_id"],
                "name": name,
                "lastname": lastname,
            }
        )

    matches.sort(
        key=lambda item: (
            item["score"],
            _normalize_text(item["lastname"]),
            _normalize_text(item["name"]),
            str(item["customer_id"])
        )
    )

    if not matches:
        return {
            "status": "no_match",
            "query": query,
            "matches": []
        }

    best_score = matches[0]["score"]

    best_matches = [
        item
        for item in matches
        if item["score"] == best_score
    ]

    if len(best_matches) == 1:
        chosen = best_matches[0]

        profile = get_customer_profile(
            chosen["customer_id"]
        )

        return {
            "status": "unique_match",
            "query": query,
            "profile": {
                "customer": {
                    "customer_id": profile[
                        "customer"
                    ]["customer_id"],
                    "name": profile[
                        "customer"
                    ]["name"],
                    "lastname": profile[
                        "customer"
                    ]["lastname"],
                },
                "statistics": profile["statistics"],
                "top_products": profile[
                    "top_products"
                ],
            }
        }

    candidates = []

    for item in best_matches[:limit]:
        candidates.append(
            {
                "customer_id": item["customer_id"],
                "name": item["name"],
                "lastname": item["lastname"],
            }
        )

    return {
        "status": "multiple_matches",
        "query": query,
        "matches": candidates
    }


if __name__ == "__main__":
    print(
        json.dumps(
            find_customer_by_name(
                "Потапова Кирилл"
            ),
            ensure_ascii=False,
            indent=2
        )
    )