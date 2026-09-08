import calendar
import json
import re
from datetime import datetime

import keyring

from gigachat import GigaChat
from gigachat.models import (
    ChatCompletionRequest,
    ChatMessage,
)

from gigachat_tls import get_gigachat_ca_bundle_file

from agent_prompts import (
    FINAL_SYSTEM_PROMPT,
    build_main_system_prompt,
    build_tool_result_prompt,
)

from agent_tools import (
    REQUEST_TOOLS,
    TEXT_TOOLS,
    compact_result,
    run_tool,
)

from agent_response import (
    AgentResponse,
)

from inventory_report_request_parser import (
    INVENTORY_TOOL_NAME,
    normalize_inventory_report_arguments,
)

from agent_followups import (
    is_customer_list_call_followup,
    is_last_call_reason_followup,
    is_next_call_followup,
)

from sales_renderer import (
    render_sales_tool_result,
)

from call_renderer import (
    render_customer_call_assessment,
    render_last_call_reason,
    render_next_call_card,
)

from customer_list_renderer import (
    render_customer_list_call_assessment,
)

from customer_renderer import (
    render_customer_profile,
    render_customer_search_result,
)

from memory_tools import (
    get_last_call_suggestion,
    get_last_customer_list,
    get_recent_messages,
    get_state,
    record_call_suggestion,
    save_last_customer_list,
    save_message,
    set_state,
)


SERVICE_NAME = "mokryi-nos-agent-gigachat"
ACCOUNT_NAME = "authorization_key"

SCOPE = "GIGACHAT_API_PERS"
MODEL = "GigaChat-3-Ultra"

CONTEXT_MESSAGES = 10
MAX_CONTEXT_MESSAGE_LENGTH = 2500


DETERMINISTIC_SALES_TOOLS = {
    "compare_sales_months",
    "get_sales_period_summary",
    "compare_sales_periods",
    "get_sales_year_summary",
    "compare_sales_years",
    "rank_sales_periods",
}


MONTH_PATTERNS = [
    (
        re.compile(
            r"\bянвар(?:ь|я|е|ем)?\b",
            re.IGNORECASE,
        ),
        1,
    ),
    (
        re.compile(
            r"\bфеврал(?:ь|я|е|ем)?\b",
            re.IGNORECASE,
        ),
        2,
    ),
    (
        re.compile(
            r"\bмарт(?:а|е|ом)?\b",
            re.IGNORECASE,
        ),
        3,
    ),
    (
        re.compile(
            r"\bапрел(?:ь|я|е|ем)?\b",
            re.IGNORECASE,
        ),
        4,
    ),
    (
        re.compile(
            r"\b(?:май|мая|мае|маем)\b",
            re.IGNORECASE,
        ),
        5,
    ),
    (
        re.compile(
            r"\bиюн(?:ь|я|е|ем)?\b",
            re.IGNORECASE,
        ),
        6,
    ),
    (
        re.compile(
            r"\bиюл(?:ь|я|е|ем)?\b",
            re.IGNORECASE,
        ),
        7,
    ),
    (
        re.compile(
            r"\bавгуст(?:а|е|ом)?\b",
            re.IGNORECASE,
        ),
        8,
    ),
    (
        re.compile(
            r"\bсентябр(?:ь|я|е|ем)?\b",
            re.IGNORECASE,
        ),
        9,
    ),
    (
        re.compile(
            r"\bоктябр(?:ь|я|е|ем)?\b",
            re.IGNORECASE,
        ),
        10,
    ),
    (
        re.compile(
            r"\bноябр(?:ь|я|е|ем)?\b",
            re.IGNORECASE,
        ),
        11,
    ),
    (
        re.compile(
            r"\bдекабр(?:ь|я|е|ем)?\b",
            re.IGNORECASE,
        ),
        12,
    ),
]


def get_authorization_key():
    authorization_key = keyring.get_password(
        SERVICE_NAME,
        ACCOUNT_NAME,
    )

    if not authorization_key:
        raise RuntimeError(
            "Authorization key GigaChat не найден "
            "в защищённом хранилище Windows."
        )

    return authorization_key


client = GigaChat(
    credentials=get_authorization_key(),
    scope=SCOPE,
    model=MODEL,
    verify_ssl_certs=True,
    ca_bundle_file=get_gigachat_ca_bundle_file(),
    timeout=60,
)


def extract_function_call(message):
    function_call = getattr(
        message,
        "function_call",
        None,
    )

    if function_call is not None:
        return function_call

    content = getattr(
        message,
        "content",
        None,
    )

    if not content:
        return None

    if isinstance(
        content,
        str,
    ):
        return None

    try:
        for part in content:
            function_call = getattr(
                part,
                "function_call",
                None,
            )

            if function_call is not None:
                return function_call

    except TypeError:
        pass

    return None


def extract_text(response):
    messages = getattr(
        response,
        "messages",
        None,
    )

    if not messages:
        return ""

    content = getattr(
        messages[0],
        "content",
        None,
    )

    if isinstance(
        content,
        str,
    ):
        return content.strip()

    if not content:
        return ""

    parts = []

    try:
        for part in content:
            text = getattr(
                part,
                "text",
                None,
            )

            if text:
                parts.append(
                    text
                )

    except TypeError:
        return str(
            content
        ).strip()

    return "\n".join(
        parts
    ).strip()


def normalize_arguments(arguments):
    if arguments is None:
        return {}

    if isinstance(
        arguments,
        dict,
    ):
        return dict(
            arguments
        )

    if isinstance(
        arguments,
        str,
    ):
        try:
            result = json.loads(
                arguments
            )

            if isinstance(
                result,
                dict,
            ):
                return result

            return {}

        except json.JSONDecodeError:
            return {}

    try:
        return dict(
            arguments
        )

    except Exception:
        return {}


def trim_context_text(value):
    text = str(
        value or ""
    )

    if (
        len(text)
        <= MAX_CONTEXT_MESSAGE_LENGTH
    ):
        return text

    return (
        text[
            :MAX_CONTEXT_MESSAGE_LENGTH
        ]
        + "\n[предыдущее сообщение сокращено]"
    )


def build_history_messages(
    conversation_id,
):
    history = get_recent_messages(
        conversation_id,
        limit=CONTEXT_MESSAGES,
    )

    messages = []

    for item in history:
        role = item.get(
            "role"
        )

        if role not in {
            "user",
            "assistant",
        }:
            continue

        messages.append(
            ChatMessage(
                role=role,
                content=trim_context_text(
                    item.get(
                        "content"
                    )
                ),
            )
        )

    return messages


def get_latest_data_date():
    try:
        result = run_tool(
            "get_latest_sales_day",
            {},
            conversation_id="__system__",
        )

        if (
            result.get(
                "status"
            )
            == "ok"
        ):
            return (
                result
                .get(
                    "day",
                    {},
                )
                .get(
                    "date"
                )
            )

    except Exception:
        pass

    return None


def parse_latest_date(
    latest_data_date,
):
    if not latest_data_date:
        return None

    try:
        return datetime.strptime(
            str(
                latest_data_date
            ),
            "%d.%m.%Y",
        ).date()

    except Exception:
        return None


def detect_month_from_text(text):
    text = (
        str(
            text or ""
        )
        .lower()
        .replace(
            "ё",
            "е",
        )
    )

    for pattern, month in MONTH_PATTERNS:
        if pattern.search(
            text
        ):
            return month

    return None


def detect_year_from_text(
    text,
    default_year=None,
):
    matches = re.findall(
        r"\b(20\d{2})\b",
        str(
            text or ""
        ),
    )

    if matches:
        return int(
            matches[-1]
        )

    return default_year


def detect_requested_limit(
    question,
    current_limit=None,
):
    text = (
        str(
            question or ""
        )
        .lower()
        .replace(
            "ё",
            "е",
        )
    )

    top_match = re.search(
        r"\bтоп\s*[-–—]?\s*(\d+)\b",
        text,
    )

    if top_match:
        return max(
            1,
            min(
                int(
                    top_match.group(1)
                ),
                100,
            ),
        )

    count_match = re.search(
        (
            r"\b(\d+)\s+"
            r"(?:самых|лучших|худших|"
            r"сильных|слабых|дней|месяцев|лет)\b"
        ),
        text,
    )

    if count_match:
        return max(
            1,
            min(
                int(
                    count_match.group(1)
                ),
                100,
            ),
        )

    plural_markers = [
        "какие дни",
        "какие месяцы",
        "какие годы",
        "лучшие дни",
        "лучшие месяцы",
        "лучшие годы",
        "худшие дни",
        "худшие месяцы",
        "худшие годы",
        "несколько дней",
        "несколько месяцев",
        "несколько лет",
        "рейтинг",
        "топ ",
        "топ-",
    ]

    if any(
        marker in text
        for marker in plural_markers
    ):
        if current_limit is not None:
            return current_limit

        return 5

    singular_markers = [
        "какой день",
        "какой месяц",
        "какой год",
        "какая дата",
        "самый сильный",
        "самый слабый",
        "самый большой",
        "самый высокий",
        "самый низкий",
        "максимальный",
        "минимальный",
        "максимум",
        "минимум",
    ]

    if any(
        marker in text
        for marker in singular_markers
    ):
        return 1

    if current_limit is not None:
        return current_limit

    return 5


def normalize_rank_arguments(
    question,
    arguments,
    latest_data_date,
):
    result = dict(
        arguments
        or {}
    )

    granularity = (
        str(
            result.get(
                "granularity",
                "",
            )
        )
        .strip()
        .lower()
    )

    latest_date = (
        parse_latest_date(
            latest_data_date
        )
    )

    default_year = (
        latest_date.year
        if latest_date
        else None
    )

    requested_year = (
        detect_year_from_text(
            question,
            default_year=default_year,
        )
    )

    requested_month = (
        detect_month_from_text(
            question
        )
    )

    result[
        "limit"
    ] = detect_requested_limit(
        question,
        current_limit=result.get(
            "limit"
        ),
    )

    # ========================================================
    # РЕЙТИНГ ДНЕЙ
    #
    # Если пользователь назвал месяц, Python сам задаёт
    # границы этого месяца. Не полагаемся на то, что LLM
    # обязательно передаст date_from/date_to.
    # ========================================================

    if (
        granularity
        == "day"
        and requested_month is not None
        and requested_year is not None
    ):
        days_in_month = (
            calendar.monthrange(
                requested_year,
                requested_month,
            )[1]
        )

        start_date = datetime(
            requested_year,
            requested_month,
            1,
        ).date()

        end_date = datetime(
            requested_year,
            requested_month,
            days_in_month,
        ).date()

        if (
            latest_date is not None
            and requested_year
            == latest_date.year
            and requested_month
            == latest_date.month
            and latest_date
            < end_date
        ):
            end_date = (
                latest_date
            )

        result[
            "date_from"
        ] = start_date.strftime(
            "%d.%m.%Y"
        )

        result[
            "date_to"
        ] = end_date.strftime(
            "%d.%m.%Y"
        )

    # ========================================================
    # РЕЙТИНГ ДНЕЙ ЗА ГОД
    # ========================================================

    elif (
        granularity
        == "day"
        and requested_year is not None
        and re.search(
            r"\b20\d{2}\b",
            str(
                question
            ),
        )
    ):
        start_date = datetime(
            requested_year,
            1,
            1,
        ).date()

        end_date = datetime(
            requested_year,
            12,
            31,
        ).date()

        if (
            latest_date is not None
            and requested_year
            == latest_date.year
            and latest_date
            < end_date
        ):
            end_date = (
                latest_date
            )

        result[
            "date_from"
        ] = start_date.strftime(
            "%d.%m.%Y"
        )

        result[
            "date_to"
        ] = end_date.strftime(
            "%d.%m.%Y"
        )

    # ========================================================
    # РЕЙТИНГ МЕСЯЦЕВ ВНУТРИ КОНКРЕТНОГО ГОДА
    # ========================================================

    elif (
        granularity
        == "month"
        and requested_year is not None
        and re.search(
            r"\b20\d{2}\b",
            str(
                question
            ),
        )
    ):
        start_date = datetime(
            requested_year,
            1,
            1,
        ).date()

        end_date = datetime(
            requested_year,
            12,
            31,
        ).date()

        if (
            latest_date is not None
            and requested_year
            == latest_date.year
            and latest_date
            < end_date
        ):
            end_date = (
                latest_date
            )

        result[
            "date_from"
        ] = start_date.strftime(
            "%d.%m.%Y"
        )

        result[
            "date_to"
        ] = end_date.strftime(
            "%d.%m.%Y"
        )

    return result


def normalize_tool_arguments(
    tool_name,
    question,
    arguments,
    latest_data_date,
):
    result = dict(
        arguments
        or {}
    )

    if tool_name == INVENTORY_TOOL_NAME:
        return normalize_inventory_report_arguments(
            question,
            result,
        )

    if (
        tool_name
        == "rank_sales_periods"
    ):
        result = (
            normalize_rank_arguments(
                question,
                result,
                latest_data_date,
            )
        )

    return result


def record_call_result(
    conversation_id,
    result,
):
    if (
        result.get(
            "status"
        )
        != "ok"
    ):
        return

    candidate = result.get(
        "candidate",
        {},
    )

    customer_id = candidate.get(
        "customer_id"
    )

    if not customer_id:
        return

    record_call_suggestion(
        conversation_id=conversation_id,
        customer_id=customer_id,
        full_name=candidate.get(
            "full_name",
            "",
        ),
        mode=result.get(
            "mode",
            "retain",
        ),
    )

    set_state(
        conversation_id,
        "last_call_result_json",
        json.dumps(
            result,
            ensure_ascii=False,
            separators=(
                ",",
                ":",
            ),
        ),
    )


def get_last_call_result(
    conversation_id,
):
    raw = get_state(
        conversation_id,
        "last_call_result_json",
        default=None,
    )

    if not raw:
        return None

    try:
        return json.loads(
            raw
        )

    except Exception:
        return None


def record_top_customer_list(
    conversation_id,
    result,
):
    customers = result.get(
        "customers",
        [],
    )

    if not isinstance(
        customers,
        list,
    ):
        return

    if not customers:
        return

    visible_customers = customers[:5]

    save_last_customer_list(
        conversation_id,
        visible_customers,
        source_tool="get_top_customers",
    )

    print(
        "[memory] сохранён последний список клиентов: "
        f"{len(visible_customers)}"
    )


def handle_next_call_followup(
    conversation_id,
):
    last_call = get_last_call_suggestion(
        conversation_id
    )

    mode = (
        last_call.get(
            "mode",
            "retain",
        )
        if last_call
        else "retain"
    )

    print(
        "[memory] следующий звонок"
    )

    result = run_tool(
        "get_next_call_candidate",
        {
            "mode":
                mode,
        },
        conversation_id=conversation_id,
    )

    record_call_result(
        conversation_id,
        result,
    )

    return render_next_call_card(
        result
    )


def handle_last_call_reason(
    conversation_id,
):
    print(
        "[memory] объясняем выбор "
        "последнего клиента"
    )

    result = get_last_call_result(
        conversation_id
    )

    return render_last_call_reason(
        result
    )


def handle_customer_list_call_followup(
    conversation_id,
):
    payload = get_last_customer_list(
        conversation_id
    )

    if not payload:
        return render_customer_list_call_assessment(
            {
                "status":
                    "error",

                "error":
                    "no_customer_list",
            }
        )

    customers = payload.get(
        "customers",
        [],
    )

    if not customers:
        return render_customer_list_call_assessment(
            {
                "status":
                    "error",

                "error":
                    "empty_customer_list",
            }
        )

    print(
        "[memory] оцениваем звонки "
        "по последнему списку клиентов"
    )

    assessments = []

    for customer in customers:
        customer_id = customer.get(
            "customer_id"
        )

        if not customer_id:
            continue

        try:
            assessment = run_tool(
                "get_customer_call_assessment",
                {
                    "customer_id":
                        customer_id,
                },
                conversation_id=conversation_id,
            )

        except Exception as error:
            assessment = {
                "status":
                    "error",

                "customer_id":
                    str(customer_id),

                "error":
                    (
                        f"{type(error).__name__}: "
                        f"{error}"
                    ),
            }

        assessments.append(
            assessment
        )

    result = {
        "status":
            "ok",

        "source_tool":
            payload.get(
                "source_tool"
            ),

        "assessments":
            assessments,
    }

    return render_customer_list_call_assessment(
        result
    )


def save_and_return(
    conversation_id,
    response,
):
    if not isinstance(
        response,
        AgentResponse,
    ):
        response = AgentResponse(
            text=response,
        )

    save_message(
        conversation_id,
        "assistant",
        response.text,
    )

    return response


def _answer_request(
    question,
    conversation_id,
    tools,
):
    conversation_id = str(
        conversation_id
        or "console"
    )

    question = str(
        question
        or ""
    ).strip()

    if not question:
        return AgentResponse(
            text="Напиши вопрос о магазине.",
        )

    history_messages = (
        build_history_messages(
            conversation_id
        )
    )

    last_call = (
        get_last_call_suggestion(
            conversation_id
        )
    )

    save_message(
        conversation_id,
        "user",
        question,
    )

    # ========================================================
    # ДЕТЕРМИНИРОВАННЫЕ FOLLOW-UP ПО ПАМЯТИ
    # ========================================================

    if is_customer_list_call_followup(
        question,
        conversation_id,
    ):
        answer = (
            handle_customer_list_call_followup(
                conversation_id
            )
        )

        return save_and_return(
            conversation_id,
            answer,
        )

    if is_next_call_followup(
        question,
        conversation_id,
    ):
        answer = (
            handle_next_call_followup(
                conversation_id
            )
        )

        return save_and_return(
            conversation_id,
            answer,
        )

    if is_last_call_reason_followup(
        question,
        conversation_id,
    ):
        answer = (
            handle_last_call_reason(
                conversation_id
            )
        )

        return save_and_return(
            conversation_id,
            answer,
        )

    # ========================================================
    # GIGACHAT ВЫБИРАЕТ ИНСТРУМЕНТ
    # ========================================================

    latest_data_date = (
        get_latest_data_date()
    )

    system_prompt = (
        build_main_system_prompt(
            latest_data_date=latest_data_date,
            last_call=last_call,
        )
    )

    request_messages = [
        ChatMessage(
            role="system",
            content=system_prompt,
        )
    ]

    request_messages.extend(
        history_messages
    )

    request_messages.append(
        ChatMessage(
            role="user",
            content=question,
        )
    )

    request = ChatCompletionRequest(
        messages=request_messages,
        tools=tools,
    )

    first_response = (
        client.chat.create(
            request
        )
    )

    first_message = (
        first_response.messages[0]
    )

    function_call = (
        extract_function_call(
            first_message
        )
    )

    if function_call is None:
        answer = extract_text(
            first_response
        )

        if not answer:
            answer = (
                "Не получилось сформировать ответ."
            )

        return save_and_return(
            conversation_id,
            answer,
        )

    tool_name = (
        function_call.name
    )

    arguments = normalize_arguments(
        function_call.arguments
    )

    # ========================================================
    # ДЕТЕРМИНИРОВАННАЯ ПРОВЕРКА АРГУМЕНТОВ
    #
    # LLM выбирает инструмент, но Python страхует
    # важные фильтры. Например:
    #
    # "какой день августа..."
    #
    # Даже если GigaChat забыл date_from/date_to,
    # Python сам ограничит рейтинг августом.
    # ========================================================

    arguments = normalize_tool_arguments(
        tool_name,
        question,
        arguments,
        latest_data_date,
    )

    print(
        f"[tool] {tool_name}({arguments})"
    )

    # ========================================================
    # PYTHON СЧИТАЕТ ФАКТЫ
    # ========================================================

    try:
        tool_result = run_tool(
            tool_name,
            arguments,
            conversation_id=conversation_id,
        )

    except Exception as error:
        tool_result = {
            "error":
                "tool_execution_failed",

            "message":
                (
                    f"{type(error).__name__}: "
                    f"{error}"
                ),
        }

    if isinstance(
        tool_result,
        AgentResponse,
    ):
        return save_and_return(
            conversation_id,
            tool_result,
        )

    real_data = compact_result(
        tool_name,
        tool_result,
    )

    # ========================================================
    # ПАМЯТЬ СПИСКОВ / ЗВОНКОВ
    # ========================================================

    if (
        tool_name
        == "get_top_customers"
    ):
        record_top_customer_list(
            conversation_id,
            real_data,
        )

    if (
        tool_name
        == "get_next_call_candidate"
    ):
        record_call_result(
            conversation_id,
            real_data,
        )

        answer = (
            render_next_call_card(
                real_data
            )
        )

        return save_and_return(
            conversation_id,
            answer,
        )

    # ========================================================
    # ДЕТЕРМИНИРОВАННЫЙ РЕНДЕР ЗВОНКОВ
    # ========================================================

    if (
        tool_name
        == "get_customer_call_assessment"
    ):
        answer = (
            render_customer_call_assessment(
                real_data
            )
        )

        return save_and_return(
            conversation_id,
            answer,
        )

    # ========================================================
    # ДЕТЕРМИНИРОВАННЫЙ РЕНДЕР ПРОДАЖ
    # ========================================================

    if (
        tool_name
        in DETERMINISTIC_SALES_TOOLS
    ):
        answer = (
            render_sales_tool_result(
                tool_name,
                real_data,
            )
        )

        if not answer:
            answer = (
                "Не получилось корректно "
                "сформировать ответ по продажам."
            )

        return save_and_return(
            conversation_id,
            answer,
        )

    # ========================================================
    # ДЕТЕРМИНИРОВАННЫЙ РЕНДЕР КЛИЕНТОВ
    # ========================================================

    if (
        tool_name
        == "get_customer_profile"
    ):
        answer = (
            render_customer_profile(
                real_data
            )
        )

        return save_and_return(
            conversation_id,
            answer,
        )

    if (
        tool_name
        == "find_customer_by_name"
    ):
        answer = (
            render_customer_search_result(
                real_data
            )
        )

        return save_and_return(
            conversation_id,
            answer,
        )

    # ========================================================
    # ОСТАЛЬНЫЕ ИНСТРУМЕНТЫ:
    # GIGACHAT ФОРМУЛИРУЕТ ОТВЕТ ТОЛЬКО ИЗ REAL_DATA
    # ========================================================

    real_data_json = json.dumps(
        real_data,
        ensure_ascii=False,
        separators=(
            ",",
            ":",
        ),
    )

    final_messages = [
        ChatMessage(
            role="system",
            content=FINAL_SYSTEM_PROMPT,
        )
    ]

    final_messages.extend(
        history_messages
    )

    final_messages.append(
        ChatMessage(
            role="user",
            content=build_tool_result_prompt(
                question=question,
                tool_name=tool_name,
                real_data_json=real_data_json,
            ),
        )
    )

    final_request = (
        ChatCompletionRequest(
            messages=final_messages,
        )
    )

    final_response = (
        client.chat.create(
            final_request
        )
    )

    answer = extract_text(
        final_response
    )

    if not answer:
        answer = (
            "Не получилось сформировать ответ."
        )

    return save_and_return(
        conversation_id,
        answer,
    )


def answer_request(
    question,
    conversation_id="console",
) -> AgentResponse:
    return _answer_request(
        question,
        conversation_id,
        REQUEST_TOOLS,
    )


def answer_question(
    question,
    conversation_id="console",
) -> str:
    return _answer_request(
        question,
        conversation_id,
        TEXT_TOOLS,
    ).text


def run_demo_question(
    number,
    question,
):
    conversation_id = (
        f"__agent_core_sales_test_{number}__"
    )

    print()
    print("=" * 78)
    print(
        f"ТЕСТ {number}"
    )
    print("=" * 78)

    print()
    print(
        "Вопрос:",
        question,
    )

    print()
    print(
        "Агент думает..."
    )
    print()

    try:
        answer = answer_question(
            question,
            conversation_id=conversation_id,
        )

        print(
            answer
        )

    except Exception as error:
        print(
            "ОШИБКА:",
            type(error).__name__,
            error,
        )


def demo():
    print()
    print("=" * 78)
    print(
        "AGENT CORE — UNIVERSAL SALES TEST"
    )
    print("=" * 78)

    questions = [
        (
            "сравни апрель с маем"
        ),
        (
            "сколько выручки было "
            "за весь 2025 год?"
        ),
        (
            "какой месяц был самым сильным "
            "по выручке?"
        ),
        (
            "какой день августа был "
            "с самым большим средним чеком?"
        ),
        (
            "сравни период с 1 по 17 июля "
            "с периодом с 1 по 17 августа"
        ),
        (
            "какой месяц был "
            "самым прибыльным?"
        ),
    ]

    for number, question in enumerate(
        questions,
        start=1,
    ):
        run_demo_question(
            number,
            question,
        )


if __name__ == "__main__":
    demo()
