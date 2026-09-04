"""Prepare verified inventory movement report artifacts without transport logic."""

from __future__ import annotations

import logging
import shutil
import tempfile
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

from inventory_movement_report import (
    InventoryMovementReportResult,
    generate_inventory_movement_report,
)
from inventory_report_periods import (
    InventoryReportPeriod,
    resolve_inventory_report_period,
)


LOGGER = logging.getLogger(__name__)

XLSX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
TEMP_DIRECTORY_PREFIX = "mokryi_nos_inventory_"


@dataclass(frozen=True)
class InventoryReportArtifact:
    status: str
    start_date: date | None
    end_date: date | None
    clarification: str | None
    error: str | None
    path: Path | None
    filename: str | None
    mime_type: str | None
    delete_after_send: bool
    row_count: int | None
    intake_document_count: int | None
    intake_quantity: Decimal | None
    intake_amount: Decimal | None
    procurement_item_rows_amount: Decimal | None
    procurement_server_total: Decimal | None
    verified: bool


class ArtifactValidationError(RuntimeError):
    """A deterministic validation failure for a generated artifact."""


def _empty_artifact(
    *,
    status: str,
    start_date: date | None = None,
    end_date: date | None = None,
    clarification: str | None = None,
    error: str | None = None,
) -> InventoryReportArtifact:
    return InventoryReportArtifact(
        status=status,
        start_date=start_date,
        end_date=end_date,
        clarification=clarification,
        error=error,
        path=None,
        filename=None,
        mime_type=None,
        delete_after_send=False,
        row_count=None,
        intake_document_count=None,
        intake_quantity=None,
        intake_amount=None,
        procurement_item_rows_amount=None,
        procurement_server_total=None,
        verified=False,
    )


def _artifact_from_period_error(period: InventoryReportPeriod) -> InventoryReportArtifact:
    if period.status == "needs_clarification":
        return _empty_artifact(
            status="needs_clarification",
            start_date=period.start_date,
            end_date=period.end_date,
            clarification=period.clarification,
        )

    return _empty_artifact(
        status="error",
        start_date=period.start_date,
        end_date=period.end_date,
        error=period.error or "Не удалось определить период отчёта.",
    )


def _create_temp_directory(temp_root: Path | None) -> Path:
    if temp_root is None:
        return Path(tempfile.mkdtemp(prefix=TEMP_DIRECTORY_PREFIX)).resolve()

    root = Path(temp_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return Path(
        tempfile.mkdtemp(
            prefix=TEMP_DIRECTORY_PREFIX,
            dir=root,
        )
    ).resolve()


def _output_filename(start_date: date, end_date: date) -> str:
    return (
        "Отчет движения товара "
        f"{start_date.strftime('%d.%m.%Y')}-"
        f"{end_date.strftime('%d.%m.%Y')}.xlsx"
    )


def _validate_generated_report(
    report: InventoryMovementReportResult,
    expected_path: Path,
    expected_start: date,
    expected_end: date,
) -> None:
    if report.verified is not True:
        raise ArtifactValidationError("Генератор не подтвердил проверку XLSX.")

    actual_path = Path(report.output_path).resolve()
    if actual_path != expected_path:
        raise ArtifactValidationError("Генератор вернул неожиданный путь XLSX.")

    if report.start_date != expected_start or report.end_date != expected_end:
        raise ArtifactValidationError("Генератор вернул неожиданный период XLSX.")

    if expected_path.suffix.lower() != ".xlsx":
        raise ArtifactValidationError("Созданный файл не имеет расширение .xlsx.")

    if not expected_path.exists():
        raise ArtifactValidationError("Генератор не создал XLSX.")

    if not expected_path.is_file():
        raise ArtifactValidationError("Путь XLSX не является файлом.")

    if expected_path.stat().st_size <= 0:
        raise ArtifactValidationError("Генератор создал пустой XLSX.")


def _cleanup_failed_artifact(temp_directory: Path | None) -> None:
    if temp_directory is None:
        return

    try:
        shutil.rmtree(temp_directory)
    except OSError:
        LOGGER.exception(
            "Failed to clean inventory report temporary directory: %s",
            temp_directory,
        )


def prepare_inventory_movement_report(
    period_kind: str,
    *,
    start_date: str | date | None = None,
    end_date: str | date | None = None,
    start_day: int | None = None,
    end_day: int | None = None,
    month: int | None = None,
    year: int | None = None,
    brand: str | None = None,
    category: str | None = None,
    reference_date: date | None = None,
    temp_root: Path | None = None,
) -> InventoryReportArtifact:
    period = resolve_inventory_report_period(
        period_kind,
        start_date=start_date,
        end_date=end_date,
        start_day=start_day,
        end_day=end_day,
        month=month,
        year=year,
        reference_date=reference_date,
    )

    if period.status != "ok":
        return _artifact_from_period_error(period)

    resolved_start = period.start_date
    resolved_end = period.end_date
    if resolved_start is None or resolved_end is None:
        return _empty_artifact(
            status="error",
            error="Resolver не вернул полные границы периода.",
        )

    temp_directory: Path | None = None
    try:
        temp_directory = _create_temp_directory(temp_root)
        output_path = (
            temp_directory
            / _output_filename(resolved_start, resolved_end)
        ).resolve()

        report = generate_inventory_movement_report(
            start=resolved_start,
            end=resolved_end,
            output_path=output_path,
            brand=brand,
            category=category,
        )

        _validate_generated_report(
            report,
            output_path,
            resolved_start,
            resolved_end,
        )

        return InventoryReportArtifact(
            status="ok",
            start_date=resolved_start,
            end_date=resolved_end,
            clarification=None,
            error=None,
            path=output_path,
            filename=output_path.name,
            mime_type=XLSX_MIME_TYPE,
            delete_after_send=True,
            row_count=report.row_count,
            intake_document_count=report.intake_document_count,
            intake_quantity=report.intake_quantity,
            intake_amount=report.intake_amount,
            procurement_item_rows_amount=report.procurement_item_rows_amount,
            procurement_server_total=report.procurement_server_total,
            verified=True,
        )

    except ArtifactValidationError as error:
        LOGGER.error("Inventory report artifact validation failed: %s", error)
        _cleanup_failed_artifact(temp_directory)
        return _empty_artifact(
            status="error",
            start_date=resolved_start,
            end_date=resolved_end,
            error=str(error),
        )

    except Exception:
        LOGGER.exception("Inventory movement report generation failed")
        _cleanup_failed_artifact(temp_directory)
        return _empty_artifact(
            status="error",
            start_date=resolved_start,
            end_date=resolved_end,
            error="Не удалось сформировать отчёт движения товара.",
        )
