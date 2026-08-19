import json
import os
import sqlite3
from datetime import datetime


PROJECT_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

DB_PATH = os.path.join(
    PROJECT_DIR,
    "agent_memory.sqlite",
)

MAX_MESSAGES_PER_CONVERSATION = 100


def now_iso():
    return datetime.now().isoformat(
        timespec="seconds"
    )


def today_iso():
    return datetime.now().date().isoformat()


def connect():
    connection = sqlite3.connect(
        DB_PATH
    )

    connection.row_factory = sqlite3.Row

    return connection


def init_db():
    with connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_messages_conversation
            ON messages (
                conversation_id,
                id
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS conversation_state (
                conversation_id TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (
                    conversation_id,
                    key
                )
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS call_suggestions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                customer_id TEXT NOT NULL,
                full_name TEXT,
                mode TEXT,
                suggested_at TEXT NOT NULL
            )
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_call_suggestions_conversation
            ON call_suggestions (
                conversation_id,
                suggested_at
            )
            """
        )

        connection.commit()


def prune_messages(
    conversation_id,
):
    with connect() as connection:
        connection.execute(
            """
            DELETE FROM messages
            WHERE conversation_id = ?
              AND id NOT IN (
                  SELECT id
                  FROM messages
                  WHERE conversation_id = ?
                  ORDER BY id DESC
                  LIMIT ?
              )
            """,
            (
                str(conversation_id),
                str(conversation_id),
                MAX_MESSAGES_PER_CONVERSATION,
            ),
        )

        connection.commit()


def save_message(
    conversation_id,
    role,
    content,
):
    conversation_id = str(
        conversation_id
    ).strip()

    role = str(
        role
    ).strip().lower()

    content = str(
        content or ""
    ).strip()

    if not conversation_id:
        raise ValueError(
            "conversation_id пустой"
        )

    if role not in {
        "user",
        "assistant",
    }:
        raise ValueError(
            "role должен быть user или assistant"
        )

    if not content:
        return

    with connect() as connection:
        connection.execute(
            """
            INSERT INTO messages (
                conversation_id,
                role,
                content,
                created_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                conversation_id,
                role,
                content,
                now_iso(),
            ),
        )

        connection.commit()

    prune_messages(
        conversation_id
    )


def get_recent_messages(
    conversation_id,
    limit=12,
):
    limit = max(
        1,
        min(
            int(limit),
            50,
        ),
    )

    with connect() as connection:
        rows = connection.execute(
            """
            SELECT
                role,
                content,
                created_at
            FROM messages
            WHERE conversation_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (
                str(conversation_id),
                limit,
            ),
        ).fetchall()

    rows = list(
        reversed(rows)
    )

    return [
        {
            "role":
                row["role"],

            "content":
                row["content"],

            "created_at":
                row["created_at"],
        }
        for row in rows
    ]


def set_state(
    conversation_id,
    key,
    value,
):
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO conversation_state (
                conversation_id,
                key,
                value,
                updated_at
            )
            VALUES (?, ?, ?, ?)
            ON CONFLICT (
                conversation_id,
                key
            )
            DO UPDATE SET
                value = excluded.value,
                updated_at = excluded.updated_at
            """,
            (
                str(conversation_id),
                str(key),
                None
                if value is None
                else str(value),
                now_iso(),
            ),
        )

        connection.commit()


def get_state(
    conversation_id,
    key,
    default=None,
):
    with connect() as connection:
        row = connection.execute(
            """
            SELECT value
            FROM conversation_state
            WHERE conversation_id = ?
              AND key = ?
            """,
            (
                str(conversation_id),
                str(key),
            ),
        ).fetchone()

    if row is None:
        return default

    return row["value"]


def save_last_customer_list(
    conversation_id,
    customers,
    source_tool=None,
):
    clean_customers = []

    for customer in customers or []:
        customer_id = customer.get(
            "customer_id"
        )

        if not customer_id:
            continue

        name = str(
            customer.get(
                "name",
                "",
            )
            or ""
        ).strip()

        lastname = str(
            customer.get(
                "lastname",
                "",
            )
            or ""
        ).strip()

        full_name = str(
            customer.get(
                "full_name",
                "",
            )
            or ""
        ).strip()

        if not full_name:
            full_name = " ".join(
                part
                for part in [
                    name,
                    lastname,
                ]
                if part
            ).strip()

        clean_customers.append(
            {
                "customer_id":
                    str(customer_id),

                "name":
                    name,

                "lastname":
                    lastname,

                "full_name":
                    full_name,

                "position":
                    customer.get(
                        "position"
                    ),
            }
        )

    payload = {
        "source_tool":
            str(source_tool or ""),

        "customers":
            clean_customers,
    }

    set_state(
        conversation_id,
        "last_customer_list_json",
        json.dumps(
            payload,
            ensure_ascii=False,
            separators=(
                ",",
                ":",
            ),
        ),
    )

    return payload


def get_last_customer_list(
    conversation_id,
):
    raw = get_state(
        conversation_id,
        "last_customer_list_json",
        default=None,
    )

    if not raw:
        return None

    try:
        payload = json.loads(
            raw
        )

    except Exception:
        return None

    if not isinstance(
        payload,
        dict,
    ):
        return None

    customers = payload.get(
        "customers"
    )

    if not isinstance(
        customers,
        list,
    ):
        return None

    return payload


def record_call_suggestion(
    conversation_id,
    customer_id,
    full_name=None,
    mode="retain",
):
    timestamp = now_iso()

    with connect() as connection:
        connection.execute(
            """
            INSERT INTO call_suggestions (
                conversation_id,
                customer_id,
                full_name,
                mode,
                suggested_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                str(conversation_id),
                str(customer_id),
                str(full_name or ""),
                str(mode or "retain"),
                timestamp,
            ),
        )

        connection.commit()

    set_state(
        conversation_id,
        "last_call_customer_id",
        customer_id,
    )

    set_state(
        conversation_id,
        "last_call_customer_name",
        full_name or "",
    )

    set_state(
        conversation_id,
        "last_call_mode",
        mode or "retain",
    )


def get_last_call_suggestion(
    conversation_id,
):
    with connect() as connection:
        row = connection.execute(
            """
            SELECT
                customer_id,
                full_name,
                mode,
                suggested_at
            FROM call_suggestions
            WHERE conversation_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (
                str(conversation_id),
            ),
        ).fetchone()

    if row is None:
        return None

    return {
        "customer_id":
            row["customer_id"],

        "full_name":
            row["full_name"],

        "mode":
            row["mode"],

        "suggested_at":
            row["suggested_at"],
    }


def get_today_suggested_customer_ids(
    conversation_id,
    mode=None,
):
    today = today_iso()

    query = """
        SELECT DISTINCT customer_id
        FROM call_suggestions
        WHERE conversation_id = ?
          AND substr(suggested_at, 1, 10) = ?
    """

    params = [
        str(conversation_id),
        today,
    ]

    if mode:
        query += """
          AND mode = ?
        """

        params.append(
            str(mode)
        )

    with connect() as connection:
        rows = connection.execute(
            query,
            params,
        ).fetchall()

    return [
        str(
            row["customer_id"]
        )
        for row in rows
    ]


def clear_conversation(
    conversation_id,
):
    conversation_id = str(
        conversation_id
    )

    with connect() as connection:
        connection.execute(
            """
            DELETE FROM messages
            WHERE conversation_id = ?
            """,
            (
                conversation_id,
            ),
        )

        connection.execute(
            """
            DELETE FROM conversation_state
            WHERE conversation_id = ?
            """,
            (
                conversation_id,
            ),
        )

        connection.execute(
            """
            DELETE FROM call_suggestions
            WHERE conversation_id = ?
            """,
            (
                conversation_id,
            ),
        )

        connection.commit()


def demo():
    test_id = "__memory_test__"

    clear_conversation(
        test_id
    )

    save_message(
        test_id,
        "user",
        "Кому мне сейчас позвонить?",
    )

    save_message(
        test_id,
        "assistant",
        "Позвони Павлу Васильеву.",
    )

    record_call_suggestion(
        test_id,
        customer_id="844016",
        full_name="Васильев Павел",
        mode="retain",
    )

    save_last_customer_list(
        test_id,
        [
            {
                "position":
                    1,

                "customer_id":
                    "111",

                "name":
                    "Сергей",

                "lastname":
                    "Зверев",
            },
            {
                "position":
                    2,

                "customer_id":
                    "222",

                "name":
                    "Никита",

                "lastname":
                    "Янцев",
            },
        ],
        source_tool="get_top_customers",
    )

    print()
    print("=" * 70)
    print(
        "MEMORY TOOLS — TEST"
    )
    print("=" * 70)

    print()
    print(
        "Последние сообщения:"
    )

    print(
        get_recent_messages(
            test_id
        )
    )

    print()
    print(
        "Последний предложенный клиент:"
    )

    print(
        get_last_call_suggestion(
            test_id
        )
    )

    print()
    print(
        "Уже предложенные сегодня:"
    )

    print(
        get_today_suggested_customer_ids(
            test_id
        )
    )

    print()
    print(
        "Последний список клиентов:"
    )

    print(
        get_last_customer_list(
            test_id
        )
    )

    clear_conversation(
        test_id
    )

    print()
    print(
        "Тестовая память очищена."
    )

    print()
    print(
        f"Рабочая база памяти: {DB_PATH}"
    )


init_db()


if __name__ == "__main__":
    demo()