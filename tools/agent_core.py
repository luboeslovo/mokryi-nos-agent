import json

import keyring

from gigachat import GigaChat
from gigachat.models import (
    ChatCompletionRequest,
    ChatMessage,
)

from agent_prompts import (
    FINAL_SYSTEM_PROMPT,
    build_main_system_prompt,
    build_tool_result_prompt,
)

from agent_tools import (
    TOOLS,
    compact_result,
    run_tool,
)

from agent_followups import (
    is_last_call_reason_followup,
    is_next_call_followup,
)

from sales_renderer import (
    render_month_comparison,
)

from call_renderer import (
    render_last_call_reason,
    render_next_call_card,
)

from memory_tools import (
    get_last_call_suggestion,
    get_recent_messages,
    get_state,
    record_call_suggestion,
    save_message,
    set_state,
)


SERVICE_NAME = "mokryi-nos-agent-gigachat"
ACCOUNT_NAME = "authorization_key"

SCOPE = "GIGACHAT_API_PERS"
MODEL = "GigaChat-3-Ultra"

CONTEXT_MESSAGES = 10
MAX_CONTEXT_MESSAGE_LENGTH = 2500


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
    verify_ssl_certs=False,
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
        return arguments

    if isinstance(
        arguments,
        str,
    ):
        try:
            return json.loads(
                arguments
            )

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


def answer_question(
    question,
    conversation_id="console",
):
    conversation_id = str(
        conversation_id or "console"
    )

    question = str(
        question or ""
    ).strip()

    if not question:
        return (
            "Напиши вопрос о магазине."
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

    if is_next_call_followup(
        question,
        conversation_id,
    ):
        answer = handle_next_call_followup(
            conversation_id
        )

        save_message(
            conversation_id,
            "assistant",
            answer,
        )

        return answer

    if is_last_call_reason_followup(
        question,
        conversation_id,
    ):
        answer = handle_last_call_reason(
            conversation_id
        )

        save_message(
            conversation_id,
            "assistant",
            answer,
        )

        return answer

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
        tools=TOOLS,
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

        save_message(
            conversation_id,
            "assistant",
            answer,
        )

        return answer

    tool_name = (
        function_call.name
    )

    arguments = normalize_arguments(
        function_call.arguments
    )

    print(
        f"[tool] {tool_name}({arguments})"
    )

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

    real_data = compact_result(
        tool_name,
        tool_result,
    )

    if (
        tool_name
        == "get_next_call_candidate"
    ):
        record_call_result(
            conversation_id,
            real_data,
        )

        answer = render_next_call_card(
            real_data
        )

        save_message(
            conversation_id,
            "assistant",
            answer,
        )

        return answer

    if (
        tool_name
        == "compare_sales_months"
    ):
        answer = render_month_comparison(
            real_data
        )

        save_message(
            conversation_id,
            "assistant",
            answer,
        )

        return answer

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

    save_message(
        conversation_id,
        "assistant",
        answer,
    )

    return answer


def demo():
    conversation_id = (
        "__agent_core_test__"
    )

    print()
    print("=" * 70)
    print(
        "AGENT CORE — TEST"
    )
    print("=" * 70)
    print()

    question = (
        "сравни август с июлем"
    )

    print(
        f"Вопрос: {question}"
    )

    print()
    print(
        "Агент думает..."
    )
    print()

    answer = answer_question(
        question,
        conversation_id=conversation_id,
    )

    print(
        answer
    )


if __name__ == "__main__":
    demo()