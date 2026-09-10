import contextlib
import io
import sys
import tempfile
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch


TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import inventory_workbook_updater as updater
from inventory_movement_report import (
    InventoryMovementReportResult,
    reopen_and_verify_xlsx,
)
from inventory_workbook_contract import read_inventory_workbook_state
from tests.inventory_workbook_fixture import (
    default_rows,
    write_inventory_workbook_fixture,
)


REFERENCE_DATE = date(2026, 9, 8)
REQUESTED_START = date(2026, 8, 1)
REQUESTED_END = date(2026, 8, 18)


def report_result(
    output_path: Path,
    *,
    start: date = REQUESTED_START,
    end: date = REQUESTED_END,
    verified: bool = True,
    row_count: int = 1,
) -> InventoryMovementReportResult:
    return InventoryMovementReportResult(
        output_path=Path(output_path),
        start_date=start,
        end_date=end,
        brand=None,
        category=None,
        row_count=row_count,
        intake_document_count=2,
        intake_quantity=Decimal("3"),
        intake_amount=Decimal("150.00"),
        procurement_item_rows_amount=Decimal("150.00"),
        procurement_server_total=Decimal("150.00"),
        verified=verified,
    )


class InventoryWorkbookUpdaterTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.parent = Path(self.temp_directory.name)
        self.workbook = self.parent / "Движение товара.xlsx"

    def tearDown(self):
        self.temp_directory.cleanup()

    def write_old_workbook(
        self,
        *,
        requested_start=REQUESTED_START,
        requested_end=REQUESTED_END,
        loaded_start=date(2026, 7, 1),
        loaded_end=date(2026, 7, 31),
    ) -> bytes:
        write_inventory_workbook_fixture(
            self.workbook,
            requested_start=requested_start,
            requested_end=requested_end,
            loaded_start=loaded_start,
            loaded_end=loaded_end,
            rows=default_rows(1),
        )
        return self.workbook.read_bytes()

    @staticmethod
    def successful_generator(calls: list[tuple[date, date, Path]]):
        def generate(*, start, end, output_path):
            output = Path(output_path)
            calls.append((start, end, output))
            write_inventory_workbook_fixture(
                output,
                requested_start=start,
                requested_end=end,
                loaded_start=start,
                loaded_end=end,
                rows=default_rows(1),
            )
            return report_result(output, start=start, end=end)

        return generate

    def refresh(self, generator):
        return updater.refresh_inventory_workbook(
            self.workbook,
            reference_date=REFERENCE_DATE,
            generator=generator,
        )

    def assert_preserved(self, before: bytes, result):
        self.assertEqual(result.status, "error")
        self.assertFalse(result.replaced)
        self.assertFalse(result.verified)
        self.assertEqual(self.workbook.read_bytes(), before)
        self.assertEqual(self.owned_temp_files(), [])

    def owned_temp_files(self):
        return list(self.parent.glob(".Движение товара.refresh_*.xlsx"))

    def test_success_uses_requested_dates_and_atomically_replaces_workbook(self):
        before = self.write_old_workbook()
        calls = []

        result = self.refresh(self.successful_generator(calls))
        state = read_inventory_workbook_state(
            self.workbook,
            reference_date=REFERENCE_DATE,
        )

        self.assertEqual(result.status, "ok")
        self.assertTrue(result.replaced)
        self.assertTrue(result.verified)
        self.assertEqual(result.requested_start, REQUESTED_START)
        self.assertEqual(result.requested_end, REQUESTED_END)
        self.assertEqual(result.loaded_start, REQUESTED_START)
        self.assertEqual(result.loaded_end, REQUESTED_END)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][:2], (REQUESTED_START, REQUESTED_END))
        self.assertEqual(calls[0][2].parent, self.workbook.parent)
        self.assertNotEqual(self.workbook.read_bytes(), before)
        self.assertEqual(state.loaded_start, REQUESTED_START)
        self.assertEqual(state.loaded_end, REQUESTED_END)
        self.assertEqual(self.owned_temp_files(), [])

    def test_invalid_requested_date_does_not_call_generator(self):
        before = self.write_old_workbook(requested_start="не дата")
        calls = []

        result = self.refresh(self.successful_generator(calls))

        self.assertEqual(calls, [])
        self.assert_preserved(before, result)

    def test_missing_requested_date_does_not_call_generator(self):
        before = self.write_old_workbook(requested_end=None)
        calls = []

        result = self.refresh(self.successful_generator(calls))

        self.assertEqual(calls, [])
        self.assert_preserved(before, result)

    def test_reversed_dates_do_not_call_generator(self):
        before = self.write_old_workbook(
            requested_start=date(2026, 8, 19),
            requested_end=date(2026, 8, 18),
        )
        calls = []

        result = self.refresh(self.successful_generator(calls))

        self.assertEqual(calls, [])
        self.assert_preserved(before, result)

    def test_future_end_date_does_not_call_generator(self):
        before = self.write_old_workbook(
            requested_end=date(2026, 9, 9),
        )
        calls = []

        result = self.refresh(self.successful_generator(calls))

        self.assertEqual(calls, [])
        self.assert_preserved(before, result)

    def test_generator_exception_preserves_bytes_and_cleans_owned_temp(self):
        before = self.write_old_workbook()

        def generate(*, start, end, output_path):
            Path(output_path).write_bytes(b"partial")
            raise RuntimeError("secret CRM payload")

        result = self.refresh(generate)

        self.assertNotIn("secret CRM payload", result.message)
        self.assert_preserved(before, result)

    def test_unverified_result_preserves_old_workbook(self):
        before = self.write_old_workbook()

        def generate(*, start, end, output_path):
            write_inventory_workbook_fixture(
                output_path,
                requested_start=start,
                requested_end=end,
                loaded_start=start,
                loaded_end=end,
                rows=default_rows(1),
            )
            return report_result(output_path, verified=False)

        self.assert_preserved(before, self.refresh(generate))

    def test_wrong_result_path_preserves_old_and_does_not_delete_other_file(self):
        before = self.write_old_workbook()
        unrelated = self.parent / "unrelated.xlsx"
        unrelated.write_bytes(b"foreign")

        def generate(*, start, end, output_path):
            write_inventory_workbook_fixture(
                output_path,
                requested_start=start,
                requested_end=end,
                loaded_start=start,
                loaded_end=end,
                rows=default_rows(1),
            )
            return report_result(unrelated)

        result = self.refresh(generate)

        self.assertEqual(unrelated.read_bytes(), b"foreign")
        self.assert_preserved(before, result)

    def test_missing_generated_file_preserves_old_workbook(self):
        before = self.write_old_workbook()

        def generate(*, start, end, output_path):
            Path(output_path).unlink()
            return report_result(output_path)

        self.assert_preserved(before, self.refresh(generate))

    def test_empty_generated_file_preserves_old_workbook(self):
        before = self.write_old_workbook()

        def generate(*, start, end, output_path):
            return report_result(output_path)

        self.assert_preserved(before, self.refresh(generate))

    def test_invalid_generated_xlsx_preserves_old_workbook(self):
        before = self.write_old_workbook()

        def generate(*, start, end, output_path):
            Path(output_path).write_bytes(b"not an xlsx")
            return report_result(output_path)

        self.assert_preserved(before, self.refresh(generate))

    def test_replace_permission_error_reports_excel_message_without_fallback(self):
        before = self.write_old_workbook()
        calls = []

        with patch.object(
            updater.os,
            "replace",
            side_effect=PermissionError("locked"),
        ) as replace_mock:
            result = self.refresh(self.successful_generator(calls))

        self.assertIn("Закройте Excel", result.message)
        replace_mock.assert_called_once()
        self.assert_preserved(before, result)

    def test_unrelated_sibling_file_is_unchanged_on_success(self):
        self.write_old_workbook()
        unrelated = self.parent / "notes.txt"
        unrelated.write_bytes(b"do not touch")
        calls = []

        result = self.refresh(self.successful_generator(calls))

        self.assertEqual(result.status, "ok")
        self.assertEqual(unrelated.read_bytes(), b"do not touch")
        self.assertEqual(self.owned_temp_files(), [])

    def test_same_requested_and_loaded_dates_still_refreshes(self):
        self.write_old_workbook(
            loaded_start=REQUESTED_START,
            loaded_end=REQUESTED_END,
        )
        calls = []

        result = self.refresh(self.successful_generator(calls))

        self.assertEqual(result.status, "ok")
        self.assertEqual(len(calls), 1)

    def test_generator_console_output_is_not_exposed(self):
        self.write_old_workbook()

        def generate(*, start, end, output_path):
            print(f"internal temp: {output_path}")
            print("secret diagnostic", file=sys.stderr)
            write_inventory_workbook_fixture(
                output_path,
                requested_start=start,
                requested_end=end,
                loaded_start=start,
                loaded_end=end,
                rows=default_rows(1),
            )
            return report_result(output_path)

        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = self.refresh(generate)

        self.assertEqual(result.status, "ok")
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "")

    def test_synthetic_integration_reopens_replaced_workbook_contract(self):
        self.write_old_workbook()
        calls = []

        result = self.refresh(self.successful_generator(calls))
        verification = reopen_and_verify_xlsx(
            self.workbook,
            REQUESTED_START,
            REQUESTED_END,
            1,
        )

        self.assertEqual(result.status, "ok")
        self.assertEqual(verification["data_rows"], 1)
        self.assertEqual(verification["auto_filter"], "A8:K9")

    def test_cli_success_and_error_exit_codes_use_safe_messages(self):
        success = updater.InventoryWorkbookRefreshResult(
            status="ok",
            workbook_path=self.workbook,
            requested_start=REQUESTED_START,
            requested_end=REQUESTED_END,
            loaded_start=REQUESTED_START,
            loaded_end=REQUESTED_END,
            row_count=1,
            intake_document_count=2,
            verified=True,
            replaced=True,
            verification={},
            message="Успешно.",
            error=None,
        )
        failure = updater._error_result(self.workbook, "Безопасная ошибка.")

        with patch.object(
            updater,
            "refresh_inventory_workbook",
            side_effect=[success, failure],
        ), patch.object(updater.sys, "stdout", io.StringIO()) as stdout, patch.object(
            updater.sys,
            "stderr",
            io.StringIO(),
        ) as stderr:
            self.assertEqual(
                updater.main(["--workbook", str(self.workbook)]),
                0,
            )
            self.assertIn("Успешно.", stdout.getvalue())
            self.assertEqual(
                updater.main(["--workbook", str(self.workbook)]),
                1,
            )
            self.assertIn("Безопасная ошибка.", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
