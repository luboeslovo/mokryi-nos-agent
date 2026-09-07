import sys
import unittest
from datetime import date
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, patch


TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import inventory_report_agent_tool as adapter
from agent_response import AgentResponse, DocumentArtifact


class InventoryReportAgentToolTests(unittest.TestCase):
    private_path = Path(r"C:\secret\private\inventory.xlsx")

    @classmethod
    def artifact(cls, **overrides):
        values = {
            "status": "ok",
            "start_date": date(2026, 8, 1),
            "end_date": date(2026, 8, 18),
            "clarification": None,
            "error": None,
            "path": cls.private_path,
            "filename": "inventory.xlsx",
            "mime_type": (
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
            "delete_after_send": True,
            "verified": True,
        }
        values.update(overrides)
        return SimpleNamespace(**values)

    def run_with_service(self, service_mock, arguments=None):
        service_module = ModuleType("inventory_report_service")
        service_module.prepare_inventory_movement_report = service_mock
        with patch.dict(sys.modules, {"inventory_report_service": service_module}):
            return adapter.run_inventory_report_agent_tool(
                arguments or {"period_kind": "previous_month"}
            )

    def test_ok_returns_document_artifact_without_exposing_path(self):
        response = self.run_with_service(Mock(return_value=self.artifact()))

        self.assertIsInstance(response, AgentResponse)
        self.assertEqual(len(response.documents), 1)
        document = response.documents[0]
        self.assertIsInstance(document, DocumentArtifact)
        self.assertEqual(document.path, self.private_path)
        self.assertEqual(document.filename, "inventory.xlsx")
        self.assertEqual(
            document.mime_type,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.assertTrue(document.delete_after_send)
        self.assertIn("01.08.2026–18.08.2026", response.text)
        self.assertNotIn(str(self.private_path), response.text)
        self.assertNotIn("отправлен", response.text.lower())

    def test_needs_clarification_returns_exact_text_without_documents(self):
        clarification = "Укажите конечный день периода."
        response = self.run_with_service(
            Mock(
                return_value=self.artifact(
                    status="needs_clarification",
                    clarification=clarification,
                    path=None,
                    verified=False,
                )
            )
        )

        self.assertEqual(response, AgentResponse(text=clarification, documents=()))

    def test_error_returns_safe_generic_text_without_documents(self):
        unsafe_error = r"Failure in C:\secret\private\token.txt"
        response = self.run_with_service(
            Mock(
                return_value=self.artifact(
                    status="error",
                    error=unsafe_error,
                    path=None,
                    verified=False,
                )
            )
        )

        self.assertEqual(response.text, adapter.GENERIC_ERROR_TEXT)
        self.assertEqual(response.documents, ())
        self.assertNotIn(unsafe_error, response.text)

    def test_unexpected_exception_returns_safe_generic_response(self):
        error = RuntimeError(r"Failure in C:\secret\private\report.xlsx")
        with patch.object(adapter.LOGGER, "exception") as log_exception:
            response = self.run_with_service(Mock(side_effect=error))

        self.assertEqual(response.text, adapter.GENERIC_ERROR_TEXT)
        self.assertEqual(response.documents, ())
        self.assertNotIn(str(self.private_path), response.text)
        log_exception.assert_called_once()

    def test_unverified_ok_does_not_return_document(self):
        with patch.object(adapter.LOGGER, "error") as log_error:
            response = self.run_with_service(
                Mock(return_value=self.artifact(verified=False))
            )

        self.assertEqual(response.text, adapter.GENERIC_ERROR_TEXT)
        self.assertEqual(response.documents, ())
        log_error.assert_called_once()

    def test_ok_without_path_does_not_return_document(self):
        with patch.object(adapter.LOGGER, "error") as log_error:
            response = self.run_with_service(
                Mock(return_value=self.artifact(path=None))
            )

        self.assertEqual(response.text, adapter.GENERIC_ERROR_TEXT)
        self.assertEqual(response.documents, ())
        log_error.assert_called_once()

    def test_only_supported_arguments_are_forwarded_unchanged(self):
        service_mock = Mock(
            return_value=self.artifact(
                status="needs_clarification",
                clarification="Уточните период.",
                path=None,
                verified=False,
            )
        )
        arguments = {
            "period_kind": "day_range_in_month",
            "start_date": "raw-start",
            "end_date": "raw-end",
            "start_day": 1,
            "end_day": 18,
            "month": 8,
            "year": 2025,
            "brand": "Raw Brand / 1",
            "category": "Raw Category / 2",
            "output_path": r"C:\injected\report.xlsx",
            "temp_root": r"C:\injected",
            "reference_date": "2026-09-04",
            "unexpected": "ignored",
        }

        self.run_with_service(service_mock, arguments)

        service_mock.assert_called_once_with(
            period_kind="day_range_in_month",
            start_date="raw-start",
            end_date="raw-end",
            start_day=1,
            end_day=18,
            month=8,
            year=2025,
            brand="Raw Brand / 1",
            category="Raw Category / 2",
        )


if __name__ == "__main__":
    unittest.main()
