import sys
import tempfile
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock, patch


TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import inventory_report_service as service
from inventory_movement_report import InventoryMovementReportResult, ReportError


class InventoryReportServiceTests(unittest.TestCase):
    reference_date = date(2026, 9, 3)

    @staticmethod
    def build_report_result(
        *,
        start,
        end,
        output_path,
        brand=None,
        category=None,
        verified=True,
    ):
        return InventoryMovementReportResult(
            output_path=Path(output_path).resolve(),
            start_date=start,
            end_date=end,
            brand=brand,
            category=category,
            row_count=1973,
            intake_document_count=33,
            intake_quantity=Decimal("2111"),
            intake_amount=Decimal("307230.94"),
            procurement_item_rows_amount=Decimal("307230.94"),
            procurement_server_total=Decimal("307230.939732"),
            verified=verified,
        )

    def successful_generator(
        self,
        *,
        start,
        end,
        output_path,
        brand=None,
        category=None,
    ):
        Path(output_path).write_bytes(b"dummy xlsx")
        return self.build_report_result(
            start=start,
            end=end,
            output_path=output_path,
            brand=brand,
            category=category,
        )

    def assert_success(self, artifact, start, end):
        self.assertEqual(artifact.status, "ok")
        self.assertEqual(artifact.start_date, start)
        self.assertEqual(artifact.end_date, end)
        self.assertTrue(artifact.verified)
        self.assertIsNotNone(artifact.path)
        self.assertTrue(artifact.path.is_file())

    def test_a_explicit_range_generates_under_temp_root(self):
        generator = Mock(side_effect=self.successful_generator)
        with tempfile.TemporaryDirectory() as temp_root, patch.object(
            service,
            "generate_inventory_movement_report",
            generator,
        ):
            artifact = service.prepare_inventory_movement_report(
                "explicit_range",
                start_date="2026-08-01",
                end_date="2026-08-18",
                reference_date=self.reference_date,
                temp_root=Path(temp_root),
            )

            self.assert_success(artifact, date(2026, 8, 1), date(2026, 8, 18))
            self.assertEqual(generator.call_count, 1)
            call = generator.call_args.kwargs
            self.assertEqual(call["start"], date(2026, 8, 1))
            self.assertEqual(call["end"], date(2026, 8, 18))
            self.assertIn(Path(temp_root).resolve(), artifact.path.parents)
            self.assertEqual(artifact.path.suffix, ".xlsx")

    def test_b_previous_month_dates_reach_generator(self):
        generator = Mock(side_effect=self.successful_generator)
        with tempfile.TemporaryDirectory() as temp_root, patch.object(
            service,
            "generate_inventory_movement_report",
            generator,
        ):
            service.prepare_inventory_movement_report(
                "previous_month",
                reference_date=self.reference_date,
                temp_root=Path(temp_root),
            )

        call = generator.call_args.kwargs
        self.assertEqual(call["start"], date(2026, 8, 1))
        self.assertEqual(call["end"], date(2026, 8, 31))

    def test_c_current_month_dates_reach_generator(self):
        generator = Mock(side_effect=self.successful_generator)
        with tempfile.TemporaryDirectory() as temp_root, patch.object(
            service,
            "generate_inventory_movement_report",
            generator,
        ):
            service.prepare_inventory_movement_report(
                "current_month",
                reference_date=self.reference_date,
                temp_root=Path(temp_root),
            )

        call = generator.call_args.kwargs
        self.assertEqual(call["start"], date(2026, 9, 1))
        self.assertEqual(call["end"], date(2026, 9, 3))

    def test_d_named_month_dates_reach_generator(self):
        generator = Mock(side_effect=self.successful_generator)
        with tempfile.TemporaryDirectory() as temp_root, patch.object(
            service,
            "generate_inventory_movement_report",
            generator,
        ):
            service.prepare_inventory_movement_report(
                "named_month",
                month=8,
                reference_date=self.reference_date,
                temp_root=Path(temp_root),
            )

        call = generator.call_args.kwargs
        self.assertEqual(call["start"], date(2026, 8, 1))
        self.assertEqual(call["end"], date(2026, 8, 31))

    def test_e_future_named_month_without_year_does_not_generate(self):
        generator = Mock()
        with tempfile.TemporaryDirectory() as temp_root, patch.object(
            service,
            "generate_inventory_movement_report",
            generator,
        ):
            artifact = service.prepare_inventory_movement_report(
                "named_month",
                month=12,
                reference_date=self.reference_date,
                temp_root=Path(temp_root),
            )
            self.assertEqual(list(Path(temp_root).iterdir()), [])

        self.assertEqual(artifact.status, "needs_clarification")
        self.assertEqual(artifact.clarification, "Укажите год для выбранного месяца.")
        self.assertIsNone(artifact.path)
        generator.assert_not_called()

    def test_f_incomplete_explicit_range_does_not_generate(self):
        generator = Mock()
        with tempfile.TemporaryDirectory() as temp_root, patch.object(
            service,
            "generate_inventory_movement_report",
            generator,
        ):
            artifact = service.prepare_inventory_movement_report(
                "explicit_range",
                start_date="2026-08-01",
                reference_date=self.reference_date,
                temp_root=Path(temp_root),
            )
            self.assertEqual(list(Path(temp_root).iterdir()), [])

        self.assertEqual(artifact.status, "needs_clarification")
        self.assertIsNone(artifact.path)
        generator.assert_not_called()

    def test_g_future_explicit_range_does_not_generate(self):
        generator = Mock()
        with tempfile.TemporaryDirectory() as temp_root, patch.object(
            service,
            "generate_inventory_movement_report",
            generator,
        ):
            artifact = service.prepare_inventory_movement_report(
                "explicit_range",
                start_date="2026-09-01",
                end_date="2026-09-04",
                reference_date=self.reference_date,
                temp_root=Path(temp_root),
            )
            self.assertEqual(list(Path(temp_root).iterdir()), [])

        self.assertEqual(artifact.status, "error")
        self.assertIsNone(artifact.path)
        generator.assert_not_called()

    def test_h_generator_error_cleans_temporary_directory(self):
        generator = Mock(side_effect=ReportError("CRM failure"))
        with tempfile.TemporaryDirectory() as temp_root, patch.object(
            service,
            "generate_inventory_movement_report",
            generator,
        ), patch.object(service.LOGGER, "exception") as log_exception:
            artifact = service.prepare_inventory_movement_report(
                "explicit_range",
                start_date="2026-08-01",
                end_date="2026-08-18",
                reference_date=self.reference_date,
                temp_root=Path(temp_root),
            )
            self.assertEqual(list(Path(temp_root).iterdir()), [])

        self.assertEqual(artifact.status, "error")
        self.assertFalse(artifact.verified)
        self.assertIsNone(artifact.path)
        self.assertEqual(artifact.error, "Не удалось сформировать отчёт движения товара.")
        log_exception.assert_called_once()

    def test_i_unverified_result_is_error_and_is_cleaned(self):
        def unverified_generator(**kwargs):
            Path(kwargs["output_path"]).write_bytes(b"dummy xlsx")
            return self.build_report_result(
                start=kwargs["start"],
                end=kwargs["end"],
                output_path=kwargs["output_path"],
                verified=False,
            )

        with tempfile.TemporaryDirectory() as temp_root, patch.object(
            service,
            "generate_inventory_movement_report",
            side_effect=unverified_generator,
        ), patch.object(service.LOGGER, "error"):
            artifact = service.prepare_inventory_movement_report(
                "previous_month",
                reference_date=self.reference_date,
                temp_root=Path(temp_root),
            )
            self.assertEqual(list(Path(temp_root).iterdir()), [])

        self.assertEqual(artifact.status, "error")
        self.assertFalse(artifact.verified)
        self.assertIsNone(artifact.path)

    def test_j_missing_physical_file_is_error(self):
        def missing_file_generator(**kwargs):
            return self.build_report_result(
                start=kwargs["start"],
                end=kwargs["end"],
                output_path=kwargs["output_path"],
            )

        with tempfile.TemporaryDirectory() as temp_root, patch.object(
            service,
            "generate_inventory_movement_report",
            side_effect=missing_file_generator,
        ), patch.object(service.LOGGER, "error"):
            artifact = service.prepare_inventory_movement_report(
                "previous_month",
                reference_date=self.reference_date,
                temp_root=Path(temp_root),
            )
            self.assertEqual(list(Path(temp_root).iterdir()), [])

        self.assertEqual(artifact.status, "error")
        self.assertIsNone(artifact.path)

    def test_k_empty_file_is_error(self):
        def empty_file_generator(**kwargs):
            Path(kwargs["output_path"]).touch()
            return self.build_report_result(
                start=kwargs["start"],
                end=kwargs["end"],
                output_path=kwargs["output_path"],
            )

        with tempfile.TemporaryDirectory() as temp_root, patch.object(
            service,
            "generate_inventory_movement_report",
            side_effect=empty_file_generator,
        ), patch.object(service.LOGGER, "error"):
            artifact = service.prepare_inventory_movement_report(
                "previous_month",
                reference_date=self.reference_date,
                temp_root=Path(temp_root),
            )
            self.assertEqual(list(Path(temp_root).iterdir()), [])

        self.assertEqual(artifact.status, "error")
        self.assertIsNone(artifact.path)

    def test_l_brand_and_category_are_forwarded_unchanged(self):
        generator = Mock(side_effect=self.successful_generator)
        with tempfile.TemporaryDirectory() as temp_root, patch.object(
            service,
            "generate_inventory_movement_report",
            generator,
        ):
            service.prepare_inventory_movement_report(
                "previous_month",
                brand="Raw Brand / 1",
                category="Raw Category / 2",
                reference_date=self.reference_date,
                temp_root=Path(temp_root),
            )

        call = generator.call_args.kwargs
        self.assertEqual(call["brand"], "Raw Brand / 1")
        self.assertEqual(call["category"], "Raw Category / 2")

    def test_m_each_call_gets_a_unique_output_path(self):
        generator = Mock(side_effect=self.successful_generator)
        with tempfile.TemporaryDirectory() as temp_root, patch.object(
            service,
            "generate_inventory_movement_report",
            generator,
        ):
            first = service.prepare_inventory_movement_report(
                "previous_month",
                reference_date=self.reference_date,
                temp_root=Path(temp_root),
            )
            second = service.prepare_inventory_movement_report(
                "previous_month",
                reference_date=self.reference_date,
                temp_root=Path(temp_root),
            )

        self.assertNotEqual(first.path, second.path)

    def test_n_successful_artifact_has_transport_metadata(self):
        generator = Mock(side_effect=self.successful_generator)
        with tempfile.TemporaryDirectory() as temp_root, patch.object(
            service,
            "generate_inventory_movement_report",
            generator,
        ):
            artifact = service.prepare_inventory_movement_report(
                "previous_month",
                reference_date=self.reference_date,
                temp_root=Path(temp_root),
            )

            self.assertEqual(artifact.mime_type, service.XLSX_MIME_TYPE)
            self.assertTrue(artifact.delete_after_send)
            self.assertEqual(artifact.filename, artifact.path.name)
            self.assertEqual(Path(artifact.filename).name, artifact.filename)
            self.assertNotIn(str(Path(temp_root)), artifact.filename)


if __name__ == "__main__":
    unittest.main()
