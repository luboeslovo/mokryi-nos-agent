import re

from memory_tools import (
    get_last_call_suggestion,
)


def normalize_text(value):
    text = (
        str(value or "")
        .strip()
        .lower()
        .replace("ё", "е")
    )

    text = re.sub(
        r"[?!.,:;«»\"'()]",
        " ",
        text,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def is_next_call_followup_text(
    question,
):
    text = normalize_text(
        question
    )

    exact_phrases = {
        "а кому еще",
        "кому еще",
        "еще",
        "дальше",
        "кто следующий",
        "следующий",
        "а дальше",
        "а кому дальше",
        "кому дальше",
        "кто дальше",
    }

    if text in exact_phrases:
        return True

    patterns = [
        "кому звонить после",
        "кому позвонить после",
        "кто после",
        "кого после",
        "следующий клиент",
        "следующий звонок",
        "кому дальше звонить",
        "кому дальше позвонить",
        "кому звонить дальше",
        "кому позвонить дальше",
    ]

    return any(
        pattern in text
        for pattern in patterns
    )


def is_last_call_reason_text(
    question,
):
    text = normalize_text(
        question
    )

    exact_phrases = {
        "почему",
        "а почему",

        "почему он",
        "почему она",
        "почему ему",
        "почему ей",
        "почему его",
        "почему ее",

        "почему именно он",
        "почему именно она",
        "почему именно ему",
        "почему именно ей",
        "почему именно его",
        "почему именно ее",

        "а почему он",
        "а почему она",
        "а почему ему",
        "а почему ей",
        "а почему его",
        "а почему ее",

        "а почему именно он",
        "а почему именно она",
        "а почему именно ему",
        "а почему именно ей",
        "а почему именно его",
        "а почему именно ее",
    }

    if text in exact_phrases:
        return True

    patterns = [
        "почему ты его выбрал",
        "почему ты ее выбрал",
        "почему выбрал его",
        "почему выбрал ее",

        "почему этот клиент",
        "почему эта клиентка",

        "почему именно этот",
        "почему именно эту",

        "чем он лучше",
        "чем она лучше",

        "почему ему звонить",
        "почему ей звонить",
        "почему звонить ему",
        "почему звонить ей",

        "почему ему позвонить",
        "почему ей позвонить",
        "почему позвонить ему",
        "почему позвонить ей",

        "почему он в приоритете",
        "почему она в приоритете",
        "почему именно он в приоритете",
        "почему именно она в приоритете",

        "почему выбрали его",
        "почему выбрали ее",
        "почему система выбрала его",
        "почему система выбрала ее",
    ]

    return any(
        pattern in text
        for pattern in patterns
    )


def has_last_call(
    conversation_id,
):
    return bool(
        get_last_call_suggestion(
            conversation_id
        )
    )


def is_next_call_followup(
    question,
    conversation_id,
):
    if not has_last_call(
        conversation_id
    ):
        return False

    return is_next_call_followup_text(
        question
    )


def is_last_call_reason_followup(
    question,
    conversation_id,
):
    if not has_last_call(
        conversation_id
    ):
        return False

    return is_last_call_reason_text(
        question
    )


def demo():
    next_call_tests = [
        "а кому дальше?",
        "кому ещё?",
        "кто следующий?",
        "кому звонить после неё?",
    ]

    reason_tests = [
        "почему именно она?",
        "а почему именно ей?",
        "почему ей?",
        "почему именно ему?",
        "почему ты её выбрал?",
        "почему этот клиент?",
    ]

    print()
    print("=" * 70)
    print("AGENT FOLLOWUPS — TEST")
    print("=" * 70)

    print()
    print("Следующий звонок:")

    for value in next_call_tests:
        print(
            f"{value!r} -> "
            f"{is_next_call_followup_text(value)}"
        )

    print()
    print("Почему этот клиент:")

    for value in reason_tests:
        print(
            f"{value!r} -> "
            f"{is_last_call_reason_text(value)}"
        )


if __name__ == "__main__":
    demo()