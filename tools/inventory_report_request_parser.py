"""Deterministic grounding of inventory report arguments from user text."""

from __future__ import annotations

import re


INVENTORY_TOOL_NAME = "generate_inventory_movement_report"
UNRECOGNIZED_PERIOD_KIND = "unrecognized"

MONTH_PATTERNS = (
    (1, re.compile(r"\bянвар(?:ь|я|е)\b")),
    (2, re.compile(r"\bфеврал(?:ь|я|е)\b")),
    (3, re.compile(r"\bмарт(?:а|е)?\b")),
    (4, re.compile(r"\bапрел(?:ь|я|е)\b")),
    (5, re.compile(r"\b(?:май|мая|мае)\b")),
    (6, re.compile(r"\bиюн(?:ь|я|е)\b")),
    (7, re.compile(r"\bиюл(?:ь|я|е)\b")),
    (8, re.compile(r"\bавгуст(?:а|е)?\b")),
    (9, re.compile(r"\bсентябр(?:ь|я|е)\b")),
    (10, re.compile(r"\bоктябр(?:ь|я|е)\b")),
    (11, re.compile(r"\bноябр(?:ь|я|е)\b")),
    (12, re.compile(r"\bдекабр(?:ь|я|е)\b")),
)

PREVIOUS_MONTH_RE = re.compile(r"\b(?:прошлый|предыдущий)\s+месяц\b")
CURRENT_MONTH_RE = re.compile(r"\b(?:этот|текущий)\s+месяц\b")

ISO_DATE_RE = re.compile(r"(?<!\d)(\d{4}-\d{2}-\d{2})(?!\d)")
DMY_DATE_RE = re.compile(r"(?<!\d)(\d{1,2})\.(\d{1,2})\.(\d{4})(?!\d)")

FULL_DAY_RANGE_RE = re.compile(
    r"\bс\s+(?P<start_day>\d{1,2})\s+по\s+(?P<end_day>\d{1,2})\b"
)
START_DAY_RE = re.compile(r"\bс\s+(?P<start_day>\d{1,2})\b")
END_DAY_RE = re.compile(r"\bдо\s+(?P<end_day>\d{1,2})\b")

BRAND_RE = re.compile(
    r"(?:\bпо\s+бренду|\bдля\s+бренда|\bбренд)\s+"
    r"(?P<value>.+?)\s*[.!?]*\s*$",
    re.IGNORECASE,
)
CATEGORY_RE = re.compile(
    r"(?:\bпо\s+категории|\bдля\s+категории|\bкатегория)\s+"
    r"(?P<value>.+?)\s*[.!?]*\s*$",
    re.IGNORECASE,
)


def _normalize_text(question: str) -> str:
    return str(question or "").lower().replace("ё", "е")


def _find_month(text: str) -> tuple[int | None, re.Match | None]:
    matches = []
    for month, pattern in MONTH_PATTERNS:
        for match in pattern.finditer(text):
            matches.append((match.start(), month, match))

    if not matches:
        return None, None

    distinct_months = {month for _, month, _ in matches}
    if len(distinct_months) != 1:
        return None, None

    _, month, match = min(matches, key=lambda item: item[0])
    return month, match


def _year_after_month(text: str, month_match: re.Match | None) -> int | None:
    if month_match is None:
        return None

    suffix = text[month_match.end():]
    match = re.match(r"\s+(\d{4})\b", suffix)
    if match is None:
        return None

    return int(match.group(1))


def _contains_period_language(value: str) -> bool:
    normalized = _normalize_text(value)
    if PREVIOUS_MONTH_RE.search(normalized) or CURRENT_MONTH_RE.search(normalized):
        return True
    if ISO_DATE_RE.search(normalized) or DMY_DATE_RE.search(normalized):
        return True
    return any(pattern.search(normalized) for _, pattern in MONTH_PATTERNS)


def _extract_filter(question: str, pattern: re.Pattern) -> str | None:
    match = pattern.search(str(question or ""))
    if match is None:
        return None

    value = match.group("value").strip()
    if not value or _contains_period_language(value):
        return None

    return value


def _explicit_range(text: str) -> dict | None:
    iso_dates = ISO_DATE_RE.findall(text)
    if len(iso_dates) >= 2:
        return {
            "period_kind": "explicit_range",
            "start_date": iso_dates[0],
            "end_date": iso_dates[1],
        }

    dmy_dates = DMY_DATE_RE.findall(text)
    if len(dmy_dates) >= 2:
        first_day, first_month, first_year = dmy_dates[0]
        second_day, second_month, second_year = dmy_dates[1]
        return {
            "period_kind": "explicit_range",
            "start_date": (
                f"{int(first_year):04d}-{int(first_month):02d}-{int(first_day):02d}"
            ),
            "end_date": (
                f"{int(second_year):04d}-{int(second_month):02d}-{int(second_day):02d}"
            ),
        }

    return None


def _period_arguments(text: str) -> dict:
    if PREVIOUS_MONTH_RE.search(text):
        return {"period_kind": "previous_month"}

    if CURRENT_MONTH_RE.search(text):
        return {"period_kind": "current_month"}

    explicit_range = _explicit_range(text)
    if explicit_range is not None:
        return explicit_range

    month, month_match = _find_month(text)
    if month is None:
        return {"period_kind": UNRECOGNIZED_PERIOD_KIND}

    explicit_year = _year_after_month(text, month_match)

    full_day_range = FULL_DAY_RANGE_RE.search(text)
    if full_day_range is not None:
        result = {
            "period_kind": "day_range_in_month",
            "start_day": int(full_day_range.group("start_day")),
            "end_day": int(full_day_range.group("end_day")),
            "month": month,
        }
        if explicit_year is not None:
            result["year"] = explicit_year
        return result

    start_day = START_DAY_RE.search(text)
    if start_day is not None:
        result = {
            "period_kind": "day_range_in_month",
            "start_day": int(start_day.group("start_day")),
            "month": month,
        }
        if explicit_year is not None:
            result["year"] = explicit_year
        return result

    end_day = END_DAY_RE.search(text)
    if end_day is not None:
        result = {
            "period_kind": "day_range_in_month",
            "end_day": int(end_day.group("end_day")),
            "month": month,
        }
        if explicit_year is not None:
            result["year"] = explicit_year
        return result

    result = {
        "period_kind": "named_month",
        "month": month,
    }
    if explicit_year is not None:
        result["year"] = explicit_year
    return result


def normalize_inventory_report_arguments(
    question: str,
    model_arguments: dict | None = None,
) -> dict:
    """Return inventory arguments proven by the original user question."""
    del model_arguments

    result = _period_arguments(_normalize_text(question))

    brand = _extract_filter(question, BRAND_RE)
    if brand is not None:
        result["brand"] = brand

    category = _extract_filter(question, CATEGORY_RE)
    if category is not None:
        result["category"] = category

    return result
