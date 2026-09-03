"""Deterministic period resolution for inventory movement reports."""

from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo


STORE_TIMEZONE = ZoneInfo("Europe/Moscow")

EXPLICIT_RANGE = "explicit_range"
NAMED_MONTH = "named_month"
PREVIOUS_MONTH = "previous_month"
CURRENT_MONTH = "current_month"

SUPPORTED_PERIOD_KINDS = {
    EXPLICIT_RANGE,
    NAMED_MONTH,
    PREVIOUS_MONTH,
    CURRENT_MONTH,
}

ISO_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


@dataclass(frozen=True)
class InventoryReportPeriod:
    status: str
    start_date: date | None
    end_date: date | None
    clarification: str | None
    period_kind: str
    error: str | None = None


def _ok(period_kind: str, start_date: date, end_date: date) -> InventoryReportPeriod:
    return InventoryReportPeriod(
        status="ok",
        start_date=start_date,
        end_date=end_date,
        clarification=None,
        period_kind=period_kind,
    )


def _needs_clarification(period_kind: str, message: str) -> InventoryReportPeriod:
    return InventoryReportPeriod(
        status="needs_clarification",
        start_date=None,
        end_date=None,
        clarification=message,
        period_kind=period_kind,
    )


def _error(period_kind: str, message: str) -> InventoryReportPeriod:
    return InventoryReportPeriod(
        status="error",
        start_date=None,
        end_date=None,
        clarification=None,
        period_kind=period_kind,
        error=message,
    )


def _store_today() -> date:
    return datetime.now(STORE_TIMEZONE).date()


def _parse_date(value: str | date | None, field_label: str) -> tuple[date | None, str | None]:
    if value is None:
        return None, None

    if isinstance(value, datetime):
        return None, f"{field_label} должна быть объектом date или строкой YYYY-MM-DD."

    if isinstance(value, date):
        return value, None

    if not isinstance(value, str):
        return None, f"{field_label} должна быть объектом date или строкой YYYY-MM-DD."

    text = value.strip()
    if not text:
        return None, None

    if ISO_DATE_RE.fullmatch(text) is None:
        return None, f"{field_label} должна быть в формате YYYY-MM-DD."

    try:
        return date.fromisoformat(text), None
    except ValueError:
        return None, f"{field_label} содержит несуществующую календарную дату."


def _resolve_reference_date(reference_date: date | None) -> tuple[date | None, str | None]:
    if reference_date is None:
        return _store_today(), None

    if isinstance(reference_date, datetime) or not isinstance(reference_date, date):
        return None, "reference_date должна быть объектом date."

    return reference_date, None


def _resolve_explicit_range(
    period_kind: str,
    start_date: str | date | None,
    end_date: str | date | None,
    reference_date: date,
) -> InventoryReportPeriod:
    parsed_start, start_error = _parse_date(start_date, "Дата начала периода")
    if start_error is not None:
        return _error(period_kind, start_error)

    parsed_end, end_error = _parse_date(end_date, "Дата окончания периода")
    if end_error is not None:
        return _error(period_kind, end_error)

    if parsed_start is None and parsed_end is None:
        return _needs_clarification(
            period_kind,
            "Укажите дату начала и дату окончания периода.",
        )

    if parsed_start is None:
        return _needs_clarification(period_kind, "Укажите дату начала периода.")

    if parsed_end is None:
        return _needs_clarification(period_kind, "Укажите дату окончания периода.")

    if parsed_start > parsed_end:
        return _error(
            period_kind,
            "Дата начала периода не может быть позже даты окончания.",
        )

    if parsed_end > reference_date:
        return _error(
            period_kind,
            "Дата окончания периода не может быть позже текущей даты магазина.",
        )

    return _ok(period_kind, parsed_start, parsed_end)


def _resolve_previous_month(period_kind: str, reference_date: date) -> InventoryReportPeriod:
    if reference_date.month == 1:
        year = reference_date.year - 1
        month = 12
    else:
        year = reference_date.year
        month = reference_date.month - 1

    if year < 1:
        return _error(period_kind, "Невозможно определить предыдущий календарный месяц.")

    start = date(year, month, 1)
    end = date(year, month, calendar.monthrange(year, month)[1])
    return _ok(period_kind, start, end)


def _resolve_current_month(period_kind: str, reference_date: date) -> InventoryReportPeriod:
    return _ok(
        period_kind,
        date(reference_date.year, reference_date.month, 1),
        reference_date,
    )


def _resolve_named_month(
    period_kind: str,
    month: int | None,
    year: int | None,
    reference_date: date,
) -> InventoryReportPeriod:
    if month is None:
        return _needs_clarification(period_kind, "Укажите месяц для отчёта.")

    if isinstance(month, bool) or not isinstance(month, int) or not 1 <= month <= 12:
        return _error(period_kind, "Месяц должен быть целым числом от 1 до 12.")

    if year is not None:
        if isinstance(year, bool) or not isinstance(year, int) or not 1 <= year <= 9999:
            return _error(period_kind, "Год должен быть целым числом от 1 до 9999.")
        resolved_year = year
    else:
        if month > reference_date.month:
            return _needs_clarification(
                period_kind,
                "Укажите год для выбранного месяца.",
            )
        resolved_year = reference_date.year

    requested_month = (resolved_year, month)
    reference_month = (reference_date.year, reference_date.month)

    if requested_month > reference_month:
        return _error(period_kind, "Выбранный месяц находится в будущем.")

    start = date(resolved_year, month, 1)
    if requested_month == reference_month:
        end = reference_date
    else:
        end = date(
            resolved_year,
            month,
            calendar.monthrange(resolved_year, month)[1],
        )

    return _ok(period_kind, start, end)


def resolve_inventory_report_period(
    period_kind: str,
    *,
    start_date: str | date | None = None,
    end_date: str | date | None = None,
    month: int | None = None,
    year: int | None = None,
    reference_date: date | None = None,
) -> InventoryReportPeriod:
    kind = period_kind if isinstance(period_kind, str) else ""
    if kind not in SUPPORTED_PERIOD_KINDS:
        return _error(kind, f"Неизвестный тип периода: {period_kind!r}.")

    reference, reference_error = _resolve_reference_date(reference_date)
    if reference_error is not None:
        return _error(kind, reference_error)

    assert reference is not None

    if kind == EXPLICIT_RANGE:
        return _resolve_explicit_range(kind, start_date, end_date, reference)

    if kind == PREVIOUS_MONTH:
        return _resolve_previous_month(kind, reference)

    if kind == CURRENT_MONTH:
        return _resolve_current_month(kind, reference)

    return _resolve_named_month(kind, month, year, reference)
