import html
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request

import keyring

from agent_core import answer_question
from agent_tools import run_tool


SERVICE_NAME = "mokryi-nos-agent-telegram"
ACCOUNT_NAME = "bot_token"

TELEGRAM_MESSAGE_LIMIT = 3800

PROJECT_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

UPDATE_SCRIPT = os.path.join(
    PROJECT_DIR,
    "tools",
    "update_all.py",
)

LOGS_DIR = os.path.join(
    PROJECT_DIR,
    "logs",
)

TELEGRAM_UPDATE_LOG = os.path.join(
    LOGS_DIR,
    "telegram_update.log",
)

AUTHORIZED_UPDATE_CHAT_IDS = {
    1329087897,
}

UPDATE_COMMANDS = {
    "обнови данные",
    "обновить данные",
    "обнови все данные",
    "обновить все данные",
    "обнови базу",
    "обновить базу",
    "обнови аналитику",
    "обновить аналитику",
}

CAPABILITIES_COMMANDS = {
    "что умеет бот",
    "что ты умеешь",
    "возможности",
    "помощь",
}

CURRENT_SALES_COMMANDS = {
    "продажи сегодня",
    "продажи за сегодня",
}

LATEST_DAY_COMMANDS = {
    "последний закрытый день",
    "последний день",
}


def get_bot_token():
    token = keyring.get_password(
        SERVICE_NAME,
        ACCOUNT_NAME,
    )

    if not token:
        raise RuntimeError(
            "Telegram Bot Token не найден "
            "в защищённом хранилище Windows."
        )

    return token


TOKEN = get_bot_token()
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"


def get_main_keyboard():
    keyboard = {
        "keyboard": [
            [
                {
                    "text":
                        "🔄 Обновить данные",
                },
                {
                    "text":
                        "💰 Продажи сегодня",
                },
            ],
            [
                {
                    "text":
                        "📅 Последний закрытый день",
                },
                {
                    "text":
                        "📞 Кому позвонить",
                },
            ],
            [
                {
                    "text":
                        "📊 Сравнить периоды",
                },
                {
                    "text":
                        "📈 Финансы / ОПиУ",
                },
            ],
            [
                {
                    "text":
                        "ℹ️ Что умеет бот",
                },
            ],
        ],
        "resize_keyboard":
            True,
        "is_persistent":
            True,
        "input_field_placeholder":
            "Спроси что-нибудь о магазине",
    }

    return json.dumps(
        keyboard,
        ensure_ascii=False,
    )


def telegram_request(
    method,
    params=None,
    timeout=60,
):
    if params is None:
        params = {}

    url = f"{BASE_URL}/{method}"

    data = urllib.parse.urlencode(
        params
    ).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=data,
        method="POST",
    )

    with urllib.request.urlopen(
        request,
        timeout=timeout,
    ) as response:
        result = json.loads(
            response.read().decode("utf-8")
        )

    if not result.get("ok"):
        raise RuntimeError(
            f"Telegram API error: {result}"
        )

    return result["result"]


def send_chat_action(
    chat_id,
    action="typing",
):
    telegram_request(
        "sendChatAction",
        {
            "chat_id":
                chat_id,

            "action":
                action,
        },
    )


def split_message(
    text,
):
    text = str(
        text or ""
    ).strip()

    if not text:
        return [
            "Не получилось сформировать ответ."
        ]

    if len(text) <= TELEGRAM_MESSAGE_LIMIT:
        return [
            text
        ]

    parts = []
    remaining = text

    while remaining:
        if len(remaining) <= TELEGRAM_MESSAGE_LIMIT:
            parts.append(
                remaining
            )
            break

        cut = remaining.rfind(
            "\n",
            0,
            TELEGRAM_MESSAGE_LIMIT,
        )

        if cut < 1000:
            cut = remaining.rfind(
                " ",
                0,
                TELEGRAM_MESSAGE_LIMIT,
            )

        if cut < 1000:
            cut = TELEGRAM_MESSAGE_LIMIT

        part = remaining[
            :cut
        ].strip()

        if part:
            parts.append(
                part
            )

        remaining = remaining[
            cut:
        ].strip()

    return parts


def parse_markdown_table_row(
    line,
):
    return [
        cell.strip()
        for cell
        in line.strip()
        .strip("|")
        .split("|")
    ]


def is_markdown_table_line(
    line,
):
    stripped = line.strip()

    return (
        stripped.startswith("|")
        and stripped.endswith("|")
        and stripped.count("|") >= 3
    )


def is_markdown_separator_row(
    cells,
):
    if not cells:
        return False

    for cell in cells:
        compact = cell.replace(
            " ",
            "",
        )

        if not re.fullmatch(
            r":?-{3,}:?",
            compact,
        ):
            return False

    return True


def convert_markdown_tables(
    text,
):
    lines = str(
        text or ""
    ).splitlines()

    result = []

    index = 0

    while index < len(lines):
        line = lines[index]

        if (
            is_markdown_table_line(
                line
            )
            and index + 1
            < len(lines)
            and is_markdown_table_line(
                lines[index + 1]
            )
        ):
            block = []

            while (
                index < len(lines)
                and is_markdown_table_line(
                    lines[index]
                )
            ):
                block.append(
                    lines[index]
                )
                index += 1

            rows = [
                parse_markdown_table_row(
                    row
                )
                for row in block
            ]

            if (
                len(rows) >= 2
                and is_markdown_separator_row(
                    rows[1]
                )
            ):
                headers = rows[0]
                data_rows = rows[2:]

                for row in data_rows:
                    if not row:
                        continue

                    label = row[0]

                    values = []

                    max_index = min(
                        len(headers),
                        len(row),
                    )

                    for column_index in range(
                        1,
                        max_index,
                    ):
                        header = headers[
                            column_index
                        ]

                        value = row[
                            column_index
                        ]

                        if not value:
                            continue

                        if header:
                            values.append(
                                f"{header}: {value}"
                            )
                        else:
                            values.append(
                                value
                            )

                    if values:
                        result.append(
                            "• "
                            + label
                            + " — "
                            + "; ".join(
                                values
                            )
                        )
                    else:
                        result.append(
                            "• "
                            + label
                        )

                continue

            result.extend(
                block
            )
            continue

        result.append(
            line
        )

        index += 1

    return "\n".join(
        result
    )


def format_telegram_text(
    text,
):
    text = convert_markdown_tables(
        text
    )

    text = html.escape(
        str(
            text or ""
        ),
        quote=False,
    )

    text = re.sub(
        r"\*\*(.+?)\*\*",
        r"<b>\1</b>",
        text,
    )

    text = re.sub(
        r"__(.+?)__",
        r"<b>\1</b>",
        text,
    )

    text = re.sub(
        r"`([^`\n]+)`",
        r"<code>\1</code>",
        text,
    )

    formatted_lines = []

    for line in text.splitlines():
        heading_match = re.match(
            r"^\s*#{1,6}\s+(.+)$",
            line,
        )

        if heading_match:
            line = (
                "<b>"
                + heading_match.group(
                    1
                )
                + "</b>"
            )

        line = re.sub(
            r"^\s*[-*]\s+",
            "• ",
            line,
        )

        formatted_lines.append(
            line
        )

    return "\n".join(
        formatted_lines
    )


def send_message(
    chat_id,
    text,
):
    for part in split_message(
        text
    ):
        formatted = (
            format_telegram_text(
                part
            )
        )

        telegram_request(
            "sendMessage",
            {
                "chat_id":
                    chat_id,

                "text":
                    formatted,

                "parse_mode":
                    "HTML",

                "reply_markup":
                    get_main_keyboard(),
            },
        )


def format_money(
    value,
):
    try:
        number = float(
            value or 0
        )
    except (
        TypeError,
        ValueError,
    ):
        number = 0.0

    formatted = (
        f"{number:,.2f}"
        .replace(
            ",",
            " ",
        )
        .replace(
            ".",
            ",",
        )
    )

    return formatted


def normalize_command(
    text,
):
    normalized = str(
        text or ""
    ).lower()

    normalized = normalized.replace(
        "ё",
        "е",
    )

    normalized = re.sub(
        r"[^\w\s]+",
        " ",
        normalized,
        flags=re.UNICODE,
    )

    normalized = re.sub(
        r"\s+",
        " ",
        normalized,
    )

    return normalized.strip()


def is_update_command(
    text,
):
    return (
        normalize_command(
            text
        )
        in UPDATE_COMMANDS
    )


def is_capabilities_command(
    text,
):
    return (
        normalize_command(
            text
        )
        in CAPABILITIES_COMMANDS
    )


def is_current_sales_command(
    text,
):
    return (
        normalize_command(
            text
        )
        in CURRENT_SALES_COMMANDS
    )


def is_latest_day_command(
    text,
):
    return (
        normalize_command(
            text
        )
        in LATEST_DAY_COMMANDS
    )


def write_update_log_header():
    os.makedirs(
        LOGS_DIR,
        exist_ok=True,
    )

    with open(
        TELEGRAM_UPDATE_LOG,
        "a",
        encoding="utf-8",
    ) as log_file:
        log_file.write(
            "\n"
        )

        log_file.write(
            "=" * 70
            + "\n"
        )

        log_file.write(
            "TELEGRAM UPDATE\n"
        )

        log_file.write(
            time.strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            + "\n"
        )

        log_file.write(
            "=" * 70
            + "\n"
        )


def run_data_update():
    if not os.path.exists(
        UPDATE_SCRIPT
    ):
        return {
            "status":
                "error",

            "message":
                (
                    "Не найден файл "
                    "tools\\update_all.py."
                ),
        }

    write_update_log_header()

    environment = os.environ.copy()

    environment[
        "PYTHONUTF8"
    ] = "1"

    environment[
        "PYTHONIOENCODING"
    ] = "utf-8"

    try:
        with open(
            TELEGRAM_UPDATE_LOG,
            "a",
            encoding="utf-8",
        ) as log_file:
            result = subprocess.run(
                [
                    sys.executable,
                    UPDATE_SCRIPT,
                ],
                cwd=PROJECT_DIR,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                env=environment,
                check=False,
                timeout=3600,
            )

    except subprocess.TimeoutExpired:
        return {
            "status":
                "timeout",

            "message":
                (
                    "Обновление не завершилось "
                    "за установленный лимит времени "
                    "и было остановлено."
                ),
        }

    except Exception as error:
        return {
            "status":
                "error",

            "message":
                (
                    "Не удалось запустить обновление: "
                    f"{type(error).__name__}."
                ),
        }

    if result.returncode != 0:
        return {
            "status":
                "failed",

            "returncode":
                result.returncode,

            "message":
                (
                    "Обновление остановилось "
                    "с ошибкой. "
                    f"Код возврата: {result.returncode}."
                ),
        }

    try:
        latest = run_tool(
            "get_latest_sales_day",
            {},
            conversation_id=(
                "__telegram_update_check__"
            ),
        )

        latest_day = (
            latest
            .get(
                "day",
                {},
            )
            .get(
                "date"
            )
        )

    except Exception:
        latest_day = None

    try:
        current_sales = run_tool(
            "get_current_sales",
            {},
            conversation_id=(
                "__telegram_update_live__"
            ),
        )

    except Exception:
        current_sales = None

    return {
        "status":
            "ok",

        "latest_day":
            latest_day,

        "current_sales":
            current_sales,
    }


def build_current_sales_message(
    current_sales,
    title=True,
):
    if (
        not isinstance(
            current_sales,
            dict,
        )
        or current_sales.get(
            "status"
        )
        != "ok"
    ):
        return (
            "Не удалось прочитать "
            "текущие продажи."
        )

    current_date = current_sales.get(
        "date"
    )

    checks = int(
        current_sales.get(
            "checks"
        )
        or 0
    )

    sales_revenue = current_sales.get(
        "sales_revenue",
        0,
    )

    return_checks = int(
        current_sales.get(
            "return_checks"
        )
        or 0
    )

    returns = current_sales.get(
        "returns",
        0,
    )

    net_revenue = current_sales.get(
        "check_revenue_net",
        0,
    )

    average_check = current_sales.get(
        "average_check",
        0,
    )

    latest_check = current_sales.get(
        "latest_today_check_at"
    )

    lines = []

    if title:
        if current_date:
            lines.append(
                f"**Продажи сегодня — {current_date}**"
            )
        else:
            lines.append(
                "**Продажи сегодня**"
            )

        lines.append(
            ""
        )

    lines.append(
        f"• Чеков: **{checks}**"
    )

    lines.append(
        "• Выручка по чекам: "
        f"**{format_money(sales_revenue)} ₽**"
    )

    if return_checks > 0:
        lines.append(
            "• Возвратов: "
            f"**{return_checks}** "
            f"на {format_money(returns)} ₽"
        )

        lines.append(
            "• После возвратов: "
            f"**{format_money(net_revenue)} ₽**"
        )

    lines.append(
        "• Средний чек: "
        f"**{format_money(average_check)} ₽**"
    )

    if latest_check:
        lines.append(
            "• Последний чек: "
            f"**{latest_check}**"
        )

    lines.append(
        ""
    )

    lines.append(
        "Это текущий незакрытый день. "
        "Внешние заказы и продажи без чека "
        "в эту live-сумму пока не входят."
    )

    return "\n".join(
        lines
    )


def build_latest_day_message(
    result,
):
    if (
        not isinstance(
            result,
            dict,
        )
        or result.get(
            "status"
        )
        != "ok"
    ):
        return (
            "Не удалось определить "
            "последний закрытый день."
        )

    day = result.get(
        "day",
        {},
    )

    date = day.get(
        "date"
    )

    total_revenue = day.get(
        "total_revenue",
        0,
    )

    checks = int(
        day.get(
            "checks"
        )
        or 0
    )

    average_check = day.get(
        "average_check",
        0,
    )

    items = int(
        day.get(
            "items"
        )
        or 0
    )

    ktch = day.get(
        "ktch",
        0,
    )

    lines = [
        (
            "**Последний закрытый день"
            + (
                f" — {date}"
                if date
                else ""
            )
            + "**"
        ),
        "",
        (
            "• Общая выручка: "
            f"**{format_money(total_revenue)} ₽**"
        ),
        (
            f"• Чеков: **{checks}**"
        ),
        (
            "• Средний чек: "
            f"**{format_money(average_check)} ₽**"
        ),
        (
            f"• Товаров продано: **{items}**"
        ),
        (
            "• Товаров в чеке: "
            f"**{ktch}**"
        ),
        "",
        (
            "Если нужен разбор динамики, "
            "можно написать: "
            "«сравни этот день с предыдущим»."
        ),
    ]

    return "\n".join(
        lines
    )


def get_capabilities_message():
    return (
        "**Что умеет Мокрый нос AI**\n\n"

        "**Продажи**\n"
        "• Показывать продажи за сегодняшний "
        "незакрытый день.\n"
        "• Показывать последний закрытый день.\n"
        "• Сравнивать дни, месяцы и годы.\n"
        "• Сравнивать произвольные периоды.\n"
        "• Искать лучшие и худшие дни, "
        "месяцы и годы.\n"
        "• Анализировать выручку, чеки, "
        "средний чек, товары в чеке "
        "и внешние заказы.\n\n"

        "**Клиенты**\n"
        "• Искать клиента по имени.\n"
        "• Показывать историю и профиль клиента.\n"
        "• Показывать самых ценных клиентов.\n"
        "• Работать с RFM-сегментами.\n\n"

        "**Обзвон**\n"
        "• Выбирать, кому позвонить первым.\n"
        "• Предлагать следующего клиента.\n"
        "• Оценивать приоритет звонка.\n"
        "• Объяснять, почему клиент попал "
        "в приоритет.\n\n"

        "**Обновление**\n"
        "• Кнопка «Обновить данные» запускает "
        "полный рабочий pipeline магазина.\n\n"

        "**Финансы / ОПиУ**\n"
        "• Считать выручку, себестоимость, "
        "валовую прибыль и маржинальность.\n"
        "• Анализировать торговую наценку, "
        "роялти и коммерческие расходы.\n"
        "• Считать прибыль от продаж, EBITDA, "
        "прибыль до налогов и чистую прибыль.\n"
        "• Сравнивать финансовые периоды "
        "и искать лучшие и худшие месяцы.\n\n"

        "**Ограничения**\n"
        "• Финансовые данные ОПиУ имеют "
        "месячную детализацию. Расходы за часть "
        "месяца искусственно не распределяются.\n"
        "• Текущий незакрытый месяц в ОПиУ "
        "считается предварительным.\n"
        "• Live-продажи за сегодня пока состоят "
        "из чеков CRM и не включают внешние заказы "
        "и продажи без чека.\n\n"

        "Можно не пользоваться кнопками — "
        "просто пиши вопрос обычным языком."
    )


def handle_update_command(
    chat_id,
):
    if chat_id not in AUTHORIZED_UPDATE_CHAT_IDS:
        send_message(
            chat_id,
            (
                "Команда обновления данных "
                "доступна только владельцу бота."
            ),
        )
        return

    send_message(
        chat_id,
        (
            "**Обновляю данные…**\n\n"
            "Запускаю полный рабочий pipeline. "
            "Это может занять несколько минут."
        ),
    )

    print()
    print(
        "Запущено обновление данных "
        "из Telegram."
    )

    result = run_data_update()

    print()
    print(
        "Результат Telegram-обновления:"
    )
    print(
        result
    )

    if result.get(
        "status"
    ) == "ok":
        latest_day = result.get(
            "latest_day"
        )

        current_sales = result.get(
            "current_sales"
        )

        lines = [
            "**Данные успешно обновлены**",
        ]

        if latest_day:
            lines.append(
                ""
            )

            lines.append(
                "Последний закрытый день: "
                f"**{latest_day}**"
            )

        if (
            isinstance(
                current_sales,
                dict,
            )
            and current_sales.get(
                "status"
            )
            == "ok"
        ):
            lines.append(
                ""
            )

            lines.append(
                build_current_sales_message(
                    current_sales,
                    title=True,
                )
            )

        send_message(
            chat_id,
            "\n".join(
                lines
            ),
        )

        return

    send_message(
        chat_id,
        (
            "**Не удалось полностью обновить данные.**\n\n"
            f"{result.get('message', 'Неизвестная ошибка.')}\n\n"
            "Подробности сохранены в "
            "`logs\\telegram_update.log`."
        ),
    )


def handle_current_sales_command(
    chat_id,
):
    try:
        result = run_tool(
            "get_current_sales",
            {},
            conversation_id=(
                "__telegram_current_sales__"
            ),
        )

        send_message(
            chat_id,
            build_current_sales_message(
                result
            ),
        )

    except Exception as error:
        print()
        print(
            "Ошибка live-продаж:"
        )
        print(
            f"{type(error).__name__}: {error}"
        )

        send_message(
            chat_id,
            (
                "Не удалось получить "
                "текущие продажи."
            ),
        )


def handle_latest_day_command(
    chat_id,
):
    try:
        result = run_tool(
            "get_latest_sales_day",
            {},
            conversation_id=(
                "__telegram_latest_day__"
            ),
        )

        send_message(
            chat_id,
            build_latest_day_message(
                result
            ),
        )

    except Exception as error:
        print()
        print(
            "Ошибка последнего дня:"
        )
        print(
            f"{type(error).__name__}: {error}"
        )

        send_message(
            chat_id,
            (
                "Не удалось получить "
                "последний закрытый день."
            ),
        )


def handle_message(
    message,
):
    chat = message.get(
        "chat",
        {},
    )

    chat_id = chat.get(
        "id"
    )

    user = message.get(
        "from",
        {},
    )

    username = user.get(
        "username"
    )

    first_name = user.get(
        "first_name"
    )

    text = message.get(
        "text"
    )

    print()
    print("=" * 70)

    print(
        f"Chat ID: {chat_id}"
    )

    print(
        f"Имя: {first_name}"
    )

    if username:
        print(
            f"Username: @{username}"
        )
    else:
        print(
            "Username: нет"
        )

    print(
        f"Сообщение: {text}"
    )

    print("=" * 70)

    if not text:
        send_message(
            chat_id,
            (
                "Пока я умею работать "
                "только с текстовыми сообщениями."
            ),
        )
        return

    text = text.strip()

    if text.startswith(
        "/start"
    ):
        send_message(
            chat_id,
            (
                "**Мокрый нос AI**\n\n"
                "Я подключён к данным магазина. "
                "Можно выбрать действие кнопкой снизу "
                "или написать вопрос обычным языком."
            ),
        )
        return

    if (
        text.startswith(
            "/help"
        )
        or text.startswith(
            "/menu"
        )
    ):
        send_message(
            chat_id,
            get_capabilities_message(),
        )
        return

    if is_update_command(
        text
    ):
        handle_update_command(
            chat_id
        )
        return

    if is_capabilities_command(
        text
    ):
        send_message(
            chat_id,
            get_capabilities_message(),
        )
        return

    if text == "📊 Сравнить периоды":
        send_message(
            chat_id,
            (
                "**Сравнение периодов**\n\n"
                "Напиши два периода и, если нужно, "
                "укажи показатель. Например:\n\n"
                "• «сравни август с июлем»\n"
                "• «сравни 1–10 августа "
                "с 1–10 июля»\n"
                "• «сравни 2026 с 2025»\n"
                "• «сравни I и II квартал "
                "по финансам»\n"
                "• «сравни сегодня и вчера»\n\n"
                "Для продаж можно сравнивать выручку, "
                "чеки, средний чек, товары в чеке "
                "и другие доступные показатели. "
                "Для финансов используются данные ОПиУ."
            ),
        )
        return

    if text == "📈 Финансы / ОПиУ":
        send_message(
            chat_id,
            (
                "**Финансы / ОПиУ**\n\n"
                "Можно спросить, например:\n\n"
                "• «какая маржинальность "
                "за весь период?»\n"
                "• «какая чистая прибыль "
                "была в мае 2026?»\n"
                "• «какой месяц был "
                "самым маржинальным?»\n"
                "• «сравни I и II квартал "
                "по EBITDA»\n"
                "• «сколько мы потратили "
                "на роялти?»\n"
                "• «какие месяцы были "
                "худшими по чистой прибыли?»\n\n"
                "Финансовые расходы хранятся "
                "по месяцам, поэтому для части месяца "
                "я не придумываю дневное распределение. "
                "Текущий месяц может быть предварительным."
            ),
        )
        return

    if is_current_sales_command(
        text
    ):
        handle_current_sales_command(
            chat_id
        )
        return

    if is_latest_day_command(
        text
    ):
        handle_latest_day_command(
            chat_id
        )
        return

    conversation_id = (
        f"telegram:{chat_id}"
    )

    try:
        send_chat_action(
            chat_id
        )

        print()
        print(
            "Агент думает..."
        )

        answer = answer_question(
            text,
            conversation_id=conversation_id,
        )

        print()
        print(
            "Ответ агента:"
        )

        print(
            answer
        )

        send_message(
            chat_id,
            answer,
        )

    except Exception as error:
        print()
        print(
            "ОШИБКА АГЕНТА:"
        )

        print(
            f"{type(error).__name__}: {error}"
        )

        send_message(
            chat_id,
            (
                "Не получилось обработать вопрос. "
                "Ошибка записана в консоль бота."
            ),
        )


def main():
    print()
    print("=" * 70)

    print(
        "МОКРЫЙ НОС AI — TELEGRAM"
    )

    print("=" * 70)
    print()

    print(
        "Telegram-бот запущен."
    )

    print(
        "AI-агент подключён."
    )

    print(
        "Память разделена по Telegram-чатам."
    )

    print(
        "Команда обновления данных подключена."
    )

    print(
        "Меню Telegram подключено."
    )

    print(
        "HTML-оформление ответов подключено."
    )

    print(
        "Для остановки нажми Ctrl+C."
    )

    print()

    offset = None

    while True:
        try:
            params = {
                "timeout":
                    30,
            }

            if offset is not None:
                params[
                    "offset"
                ] = offset

            updates = telegram_request(
                "getUpdates",
                params,
                timeout=40,
            )

            for update in updates:
                offset = (
                    update[
                        "update_id"
                    ]
                    + 1
                )

                message = update.get(
                    "message"
                )

                if not message:
                    continue

                handle_message(
                    message
                )

        except KeyboardInterrupt:
            print()
            print(
                "Бот остановлен."
            )
            break

        except Exception as error:
            print()
            print(
                "Ошибка Telegram-цикла:"
            )

            print(
                f"{type(error).__name__}: {error}"
            )

            print(
                "Повтор через 5 секунд..."
            )

            time.sleep(
                5
            )


if __name__ == "__main__":
    main()