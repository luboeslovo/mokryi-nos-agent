import json
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch


TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import inventory_movement_report as report
from tests.inventory_workbook_fixture import (
    write_inventory_workbook_fixture,
)


class InventoryMovementReportCleanupTests(unittest.TestCase):
    def test_successful_verification_leaves_no_owned_sidecar(self):
        owned_temp_directory = None

        def fake_export(command, **kwargs):
            nonlocal owned_temp_directory
            payload = json.loads(
                Path(command[2]).read_text(
                    encoding="utf-8"
                )
            )
            exported_workbook = Path(
                payload["outputPath"]
            )
            owned_temp_directory = (
                exported_workbook.parent
            )
            write_inventory_workbook_fixture(
                exported_workbook
            )
            Path(
                str(exported_workbook)
                + ".inspect.ndjson"
            ).write_text(
                '{"kind":"synthetic"}\n',
                encoding="utf-8",
            )
            return subprocess.CompletedProcess(
                command,
                0,
                stdout="",
                stderr="",
            )

        with tempfile.TemporaryDirectory() as temp_root:
            output_path = (
                Path(temp_root)
                / "report.xlsx"
            )
            unrelated_sidecar = Path(
                str(output_path)
                + ".inspect.ndjson"
            )
            unrelated_sidecar.write_text(
                "foreign",
                encoding="utf-8",
            )

            with patch.object(
                report,
                "find_artifact_runtime",
                return_value=(
                    Path("node.exe"),
                    Path("node_modules"),
                ),
            ), patch.object(
                report,
                "create_runtime_junction",
            ), patch.object(
                report,
                "remove_runtime_junction",
            ), patch.object(
                report.subprocess,
                "run",
                side_effect=fake_export,
            ):
                report.write_workbook(
                    output_path,
                    date(2026, 8, 1),
                    date(2026, 8, 18),
                    [],
                    "Без фильтра",
                    [],
                )

            verification = (
                report.reopen_and_verify_xlsx(
                    output_path,
                    date(2026, 8, 1),
                    date(2026, 8, 18),
                    0,
                )
            )

            self.assertEqual(
                verification["data_rows"],
                0,
            )
            self.assertTrue(
                output_path.is_file()
            )
            self.assertEqual(
                unrelated_sidecar.read_text(
                    encoding="utf-8"
                ),
                "foreign",
            )
            self.assertIsNotNone(
                owned_temp_directory
            )
            self.assertFalse(
                owned_temp_directory.exists()
            )


if __name__ == "__main__":
    unittest.main()
