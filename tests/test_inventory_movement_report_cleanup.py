import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from datetime import date
from pathlib import Path
from unittest.mock import patch


TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import inventory_movement_report as report


WORKBOOK_XML = """<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets><sheet name="Отчет движения товара" sheetId="1" r:id="rId1"/></sheets>
</workbook>
"""

WORKBOOK_RELS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1"
   Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet"
   Target="worksheets/sheet1.xml"/>
</Relationships>
"""

SHEET_XML = """<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>
    <row r="1"><c r="A1" t="inlineStr"><is><t>Отчет движения товара</t></is></c></row>
    <row r="3">
      <c r="C3" t="inlineStr"><is><t>01.08.2026</t></is></c>
      <c r="E3" t="inlineStr"><is><t>18.08.2026</t></is></c>
    </row>
    <row r="8">
      <c r="A8" t="inlineStr"><is><t>№ п.п.</t></is></c>
      <c r="B8" t="inlineStr"><is><t>Категория ИТ</t></is></c>
      <c r="C8" t="inlineStr"><is><t>Артикул в ИТ</t></is></c>
      <c r="D8" t="inlineStr"><is><t>Артикул поставщика</t></is></c>
      <c r="E8" t="inlineStr"><is><t>Остаток на начало</t></is></c>
      <c r="G8" t="inlineStr"><is><t>Приход</t></is></c>
      <c r="I8" t="inlineStr"><is><t>Остаток на конец</t></is></c>
    </row>
    <row r="9">
      <c r="E9" t="inlineStr"><is><t>кв-во</t></is></c>
      <c r="F9" t="inlineStr"><is><t>сумма</t></is></c>
      <c r="G9" t="inlineStr"><is><t>кв-во</t></is></c>
      <c r="H9" t="inlineStr"><is><t>сумма</t></is></c>
      <c r="I9" t="inlineStr"><is><t>кв-во</t></is></c>
      <c r="J9" t="inlineStr"><is><t>сумма</t></is></c>
    </row>
  </sheetData>
  <mergeCells count="7">
    <mergeCell ref="A8:A9"/><mergeCell ref="B8:B9"/>
    <mergeCell ref="C8:C9"/><mergeCell ref="D8:D9"/>
    <mergeCell ref="E8:F8"/><mergeCell ref="G8:H8"/>
    <mergeCell ref="I8:J8"/>
  </mergeCells>
</worksheet>
"""


def write_synthetic_workbook(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("xl/workbook.xml", WORKBOOK_XML)
        archive.writestr("xl/_rels/workbook.xml.rels", WORKBOOK_RELS_XML)
        archive.writestr("xl/worksheets/sheet1.xml", SHEET_XML)


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
            write_synthetic_workbook(
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
