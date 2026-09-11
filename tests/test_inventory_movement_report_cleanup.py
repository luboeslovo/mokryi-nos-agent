import tempfile
import unittest
from datetime import date
from pathlib import Path


TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools"
import sys

sys.path.insert(0, str(TOOLS_DIR))

import inventory_movement_report as report
from tests.inventory_workbook_fixture import default_rows


class InventoryMovementReportCleanupTests(unittest.TestCase):
    def test_successful_openpyxl_export_leaves_no_sidecar_or_owned_temp(self):
        with tempfile.TemporaryDirectory() as temp_root:
            parent = Path(temp_root)
            output_path = parent / "report.xlsx"
            unrelated = parent / "do-not-touch.txt"
            unrelated.write_text("foreign", encoding="utf-8")

            report.write_workbook(
                output_path,
                date(2026, 8, 1),
                date(2026, 8, 18),
                default_rows(1),
                "Все товары",
                [],
            )

            verification = report.reopen_and_verify_xlsx(
                output_path,
                date(2026, 8, 1),
                date(2026, 8, 18),
                1,
            )

            self.assertEqual(verification["data_rows"], 1)
            self.assertTrue(output_path.is_file())
            self.assertEqual(unrelated.read_text(encoding="utf-8"), "foreign")
            self.assertEqual(list(parent.glob("*.inspect.ndjson")), [])
            self.assertEqual(list(parent.glob(".report.export_*.xlsx")), [])


if __name__ == "__main__":
    unittest.main()
