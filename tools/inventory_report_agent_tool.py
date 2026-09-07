"""Artifact-aware adapter for inventory movement report agent calls."""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

from agent_response import AgentResponse, DocumentArtifact


LOGGER = logging.getLogger(__name__)

GENERIC_ERROR_TEXT = "Не удалось сформировать отчёт движения товара."

SERVICE_ARGUMENT_NAMES = (
    "period_kind",
    "start_date",
    "end_date",
    "start_day",
    "end_day",
    "month",
    "year",
    "brand",
    "category",
)


def _error_response() -> AgentResponse:
    return AgentResponse(
        text=GENERIC_ERROR_TEXT,
        documents=(),
    )


def run_inventory_report_agent_tool(
    arguments: dict,
) -> AgentResponse:
    """Prepare an inventory report and convert it to an agent response."""
    try:
        from inventory_report_service import prepare_inventory_movement_report

        service_arguments = {
            name: arguments[name]
            for name in SERVICE_ARGUMENT_NAMES
            if name in arguments
        }
        artifact = prepare_inventory_movement_report(**service_arguments)

        if artifact.status == "needs_clarification":
            clarification = artifact.clarification
            if isinstance(clarification, str) and clarification.strip():
                return AgentResponse(
                    text=clarification,
                    documents=(),
                )
            return _error_response()

        if artifact.status != "ok":
            return _error_response()

        if not (
            artifact.verified is True
            and isinstance(artifact.path, Path)
            and isinstance(artifact.filename, str)
            and bool(artifact.filename.strip())
            and isinstance(artifact.mime_type, str)
            and bool(artifact.mime_type.strip())
            and isinstance(artifact.start_date, date)
            and isinstance(artifact.end_date, date)
        ):
            LOGGER.error("Inventory report service returned an invalid ok artifact")
            return _error_response()

        response_text = (
            "Отчёт движения товара за "
            f"{artifact.start_date.strftime('%d.%m.%Y')}–"
            f"{artifact.end_date.strftime('%d.%m.%Y')} сформирован."
        )

        return AgentResponse(
            text=response_text,
            documents=(
                DocumentArtifact(
                    path=artifact.path,
                    filename=artifact.filename,
                    mime_type=artifact.mime_type,
                    delete_after_send=artifact.delete_after_send,
                ),
            ),
        )

    except Exception:
        LOGGER.exception("Inventory report agent adapter failed")
        return _error_response()
