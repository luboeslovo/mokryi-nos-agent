"""Safely refresh a permanent inventory workbook through the existing generator."""

from __future__ import annotations

import argparse
import contextlib
import io
import os
import stat
import sys
import tempfile
from dataclasses import dataclass, replace
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo

from inventory_movement_report import (
    InventoryMovementReportResult,
    generate_inventory_movement_report,
    reopen_and_verify_xlsx,
)
from inventory_workbook_contract import (
    InventoryWorkbookState,
    WorkbookContractError,
    read_inventory_workbook_state,
)


MOSCOW_TIME_ZONE = ZoneInfo("Europe/Moscow")
LOCKED_WORKBOOK_MESSAGE = (
    "Закройте Excel с отчётом и запустите обновление ещё раз."
)

InventoryReportGenerator = Callable[..., InventoryMovementReportResult]


@dataclass(frozen=True)
class InventoryWorkbookRefreshResult:
    status: str
    workbook_path: Path
    requested_start: date | None
    requested_end: date | None
    loaded_start: date | None
    loaded_end: date | None
    row_count: int | None
    intake_document_count: int | None
    verified: bool
    replaced: bool
    verification: dict[str, Any] | None
    message: str
    error: str | None


class _RefreshValidationError(RuntimeError):
    """A deterministic updater failure safe to show to a local user."""


class _WorkbookLockedError(_RefreshValidationError):
    """The permanent workbook cannot currently be opened for replacement."""


def _moscow_today() -> date:
    return datetime.now(MOSCOW_TIME_ZONE).date()


def _error_result(
    workbook_path: Path,
    message: str,
    *,
    state: InventoryWorkbookState | None = None,
) -> InventoryWorkbookRefreshResult:
    return InventoryWorkbookRefreshResult(
        status="error",
        workbook_path=workbook_path,
        requested_start=state.requested_start if state else None,
        requested_end=state.requested_end if state else None,
        loaded_start=state.loaded_start if state else None,
        loaded_end=state.loaded_end if state else None,
        row_count=None,
        intake_document_count=None,
        verified=False,
        replaced=False,
        verification=None,
        message=message,
        error=message,
    )


def _validate_permanent_workbook(path: Path) -> None:
    if path.suffix.lower() != ".xlsx":
        raise _RefreshValidationError(
            "Поддерживается только постоянная книга в формате .xlsx."
        )
    try:
        metadata = path.lstat()
    except FileNotFoundError as error:
        raise _RefreshValidationError("Файл отчёта не найден.") from error
    except PermissionError as error:
        raise _WorkbookLockedError(LOCKED_WORKBOOK_MESSAGE) from error
    except OSError as error:
        raise _RefreshValidationError(
            "Не удалось проверить файл отчёта."
        ) from error

    if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
        raise _RefreshValidationError(
            "Путь отчёта должен указывать на обычный XLSX-файл."
        )
    if metadata.st_size <= 0:
        raise _RefreshValidationError("Файл отчёта пуст.")


def _ensure_replace_access(path: Path) -> None:
    try:
        with path.open("r+b"):
            pass
    except PermissionError as error:
        raise _WorkbookLockedError(LOCKED_WORKBOOK_MESSAGE) from error
    except OSError as error:
        raise _RefreshValidationError(
            "Не удалось получить доступ к файлу отчёта."
        ) from error


def _create_owned_temp_xlsx(workbook_path: Path) -> Path:
    try:
        descriptor, raw_path = tempfile.mkstemp(
            prefix=f".{workbook_path.stem}.refresh_",
            suffix=".xlsx",
            dir=workbook_path.parent,
        )
    except PermissionError as error:
        raise _WorkbookLockedError(LOCKED_WORKBOOK_MESSAGE) from error
    except OSError as error:
        raise _RefreshValidationError(
            "Не удалось создать временный XLSX рядом с отчётом."
        ) from error
    os.close(descriptor)
    return Path(raw_path).resolve()


def _validate_generated_report(
    report: InventoryMovementReportResult,
    *,
    expected_path: Path,
    expected_start: date,
    expected_end: date,
) -> None:
    if report.verified is not True:
        raise _RefreshValidationError(
            "Генератор не подтвердил проверку нового XLSX."
        )
    if Path(report.output_path).resolve() != expected_path:
        raise _RefreshValidationError(
            "Генератор вернул неожиданный путь нового XLSX."
        )
    if report.start_date != expected_start or report.end_date != expected_end:
        raise _RefreshValidationError(
            "Генератор вернул период, отличный от выбранного."
        )
    if not isinstance(report.row_count, int) or report.row_count < 0:
        raise _RefreshValidationError(
            "Генератор вернул некорректное количество строк."
        )
    if (
        not isinstance(report.intake_document_count, int)
        or report.intake_document_count < 0
    ):
        raise _RefreshValidationError(
            "Генератор вернул некорректное количество документов прихода."
        )

    try:
        metadata = expected_path.lstat()
    except FileNotFoundError as error:
        raise _RefreshValidationError(
            "Генератор не создал новый XLSX."
        ) from error
    except PermissionError as error:
        raise _WorkbookLockedError(LOCKED_WORKBOOK_MESSAGE) from error
    except OSError as error:
        raise _RefreshValidationError(
            "Не удалось проверить созданный XLSX."
        ) from error

    if expected_path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
        raise _RefreshValidationError(
            "Генератор не создал обычный XLSX-файл."
        )
    if metadata.st_size <= 0:
        raise _RefreshValidationError("Генератор создал пустой XLSX.")


def _cleanup_owned_temp(temp_path: Path | None) -> str | None:
    if temp_path is None:
        return None
    try:
        temp_path.unlink(missing_ok=True)
    except OSError:
        return "Не удалось удалить временный файл обновления."
    return None


def refresh_inventory_workbook(
    workbook_path: Path,
    *,
    reference_date: date | None = None,
    generator: InventoryReportGenerator = generate_inventory_movement_report,
) -> InventoryWorkbookRefreshResult:
    """Refresh one explicit permanent XLSX and preserve it on every failure."""

    path = Path(workbook_path).absolute()
    state: InventoryWorkbookState | None = None
    validation_date = reference_date or _moscow_today()

    try:
        _validate_permanent_workbook(path)
        state = read_inventory_workbook_state(
            path,
            reference_date=validation_date,
        )
        _ensure_replace_access(path)
    except WorkbookContractError as error:
        if isinstance(error.__cause__, PermissionError):
            return _error_result(path, LOCKED_WORKBOOK_MESSAGE)
        return _error_result(
            path,
            f"Не удалось прочитать параметры отчёта: {error}",
        )
    except _RefreshValidationError as error:
        return _error_result(path, str(error), state=state)

    temp_path: Path | None = None
    result: InventoryWorkbookRefreshResult
    try:
        temp_path = _create_owned_temp_xlsx(path)
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(
            io.StringIO()
        ):
            report = generator(
                start=state.requested_start,
                end=state.requested_end,
                output_path=temp_path,
            )
        _validate_generated_report(
            report,
            expected_path=temp_path,
            expected_start=state.requested_start,
            expected_end=state.requested_end,
        )

        try:
            verification = reopen_and_verify_xlsx(
                temp_path,
                state.requested_start,
                state.requested_end,
                report.row_count,
            )
            generated_state = read_inventory_workbook_state(
                temp_path,
                reference_date=validation_date,
            )
        except Exception as error:
            raise _RefreshValidationError(
                "Новый XLSX не прошёл итоговую проверку."
            ) from error

        if (
            generated_state.requested_start != state.requested_start
            or generated_state.requested_end != state.requested_end
            or generated_state.loaded_start != report.start_date
            or generated_state.loaded_end != report.end_date
        ):
            raise _RefreshValidationError(
                "Периоды в новом XLSX не совпадают с выбранным периодом."
            )

        success_result = InventoryWorkbookRefreshResult(
            status="ok",
            workbook_path=path,
            requested_start=generated_state.requested_start,
            requested_end=generated_state.requested_end,
            loaded_start=generated_state.loaded_start,
            loaded_end=generated_state.loaded_end,
            row_count=report.row_count,
            intake_document_count=report.intake_document_count,
            verified=True,
            replaced=True,
            verification=verification,
            message=(
                "Отчёт успешно обновлён за "
                f"{generated_state.loaded_start.strftime('%d.%m.%Y')}–"
                f"{generated_state.loaded_end.strftime('%d.%m.%Y')}."
            ),
            error=None,
        )
        _ensure_replace_access(path)
        try:
            os.replace(temp_path, path)
        except PermissionError as error:
            raise _WorkbookLockedError(LOCKED_WORKBOOK_MESSAGE) from error
        except OSError as error:
            raise _RefreshValidationError(
                "Не удалось безопасно заменить файл отчёта."
            ) from error

        result = success_result
    except _RefreshValidationError as error:
        result = _error_result(path, str(error), state=state)
    except Exception:
        result = _error_result(
            path,
            "Не удалось обновить отчёт. Исходный файл сохранён.",
            state=state,
        )

    cleanup_error = _cleanup_owned_temp(temp_path)
    if cleanup_error is not None and result.replaced is False:
        message = f"{result.message} {cleanup_error}"
        result = replace(result, message=message, error=message)
    return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Безопасно обновить постоянный отчёт движения товара."
    )
    parser.add_argument(
        "--workbook",
        required=True,
        type=Path,
        help="Путь к постоянному XLSX-файлу отчёта.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    args = parse_args(argv)
    result = refresh_inventory_workbook(args.workbook)
    stream = sys.stdout if result.status == "ok" else sys.stderr
    print(result.message, file=stream)
    return 0 if result.status == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
