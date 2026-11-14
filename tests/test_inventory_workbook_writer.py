import sys
import tempfile
import unittest
import zipfile
from datetime import date, datetime
from pathlib import Path
from unittest.mock import patch

from openpyxl import load_workbook


TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import inventory_movement_report as report
import inventory_workbook_writer as writer
from inventory_workbook_contract import (
    AMOUNT_COLUMNS,
    DATE_NUMBER_FORMAT,
    DATETIME_NUMBER_FORMAT,
    LAST_SUCCESSFUL_UPDATE_CELL,
    LOADED_END_CELL,
    LOADED_START_CELL,
    NUMERIC_COLUMNS,
    PARAMETERS_SHEET_NAME,
    QUANTITY_COLUMNS,
    REPORT_FIRST_DATA_ROW,
    REPORT_HEADERS,
    REPORT_LOADED_END_CELL,
    REPORT_LOADED_START_CELL,
    REPORT_SHEET_NAME,
    REPORT_TABLE_NAME,
    REQUESTED_END_CELL,
    REQUESTED_START_CELL,
    TOTAL_COLUMNS,
    subtotal_formulas,
    table_end_row,
    total_row,
)
from tests.inventory_workbook_fixture import default_rows


START = date(2026, 8, 1)
END = date(2026, 8, 18)
GENERATED_AT = datetime(2026, 9, 10, 12, 30)


def date_part(value):
    return value.date() if isinstance(value, datetime) else value


class InventoryWorkbookWriterTests(unittest.TestCase):
    def test_openpyxl_writer_preserves_golden_semantics(self):
        for row_count in (0, 1, 3):
            with self.subTest(row_count=row_count):
                with tempfile.TemporaryDirectory() as temp_root:
                    parent = Path(temp_root)
                    output = parent / "Синтетический отчёт.xlsx"
                    rows = default_rows(row_count)
                    with patch.object(
                        report.subprocess,
                        "run",
                        side_effect=AssertionError("No process may be started"),
                    ):
                        writer.write_inventory_workbook(
                            output,
                            START,
                            END,
                            rows,
                            "Все товары",
                            ["Синтетическая проверка."],
                            generated_at=GENERATED_AT,
                        )

                    self.assertTrue(output.is_file())
                    self.assertGreater(output.stat().st_size, 0)
                    self.assertEqual(list(parent.glob("*.inspect.ndjson")), [])
                    self.assertEqual(
                        list(parent.glob(".Синтетический отчёт.export_*.xlsx")),
                        [],
                    )
                    with zipfile.ZipFile(output) as archive:
                        self.assertIsNone(archive.testzip())

                    verification = report.reopen_and_verify_xlsx(
                        output,
                        START,
                        END,
                        row_count,
                    )
                    self.assertEqual(verification["data_rows"], row_count)
                    self.assertEqual(
                        verification["auto_filter"],
                        f"A8:K{table_end_row(row_count)}",
                    )

                    workbook = load_workbook(output, data_only=False)
                    self.assertEqual(
                        workbook.sheetnames,
                        [PARAMETERS_SHEET_NAME, REPORT_SHEET_NAME],
                    )
                    parameters = workbook[PARAMETERS_SHEET_NAME]
                    report_sheet = workbook[REPORT_SHEET_NAME]

                    for ref, expected in (
                        (REQUESTED_START_CELL, START),
                        (REQUESTED_END_CELL, END),
                        (LOADED_START_CELL, START),
                        (LOADED_END_CELL, END),
                    ):
                        self.assertEqual(date_part(parameters[ref].value), expected)
                        self.assertTrue(parameters[ref].is_date)
                        self.assertEqual(
                            parameters[ref].number_format,
                            DATE_NUMBER_FORMAT,
                        )
                    self.assertEqual(
                        parameters[LAST_SUCCESSFUL_UPDATE_CELL].value,
                        GENERATED_AT,
                    )
                    self.assertEqual(
                        parameters[LAST_SUCCESSFUL_UPDATE_CELL].number_format,
                        DATETIME_NUMBER_FORMAT,
                    )
                    self.assertEqual(
                        date_part(report_sheet[REPORT_LOADED_START_CELL].value),
                        START,
                    )
                    self.assertEqual(
                        date_part(report_sheet[REPORT_LOADED_END_CELL].value),
                        END,
                    )
                    self.assertEqual(
                        report_sheet[REPORT_LOADED_START_CELL].number_format,
                        DATE_NUMBER_FORMAT,
                    )
                    self.assertEqual(
                        report_sheet[REPORT_LOADED_END_CELL].number_format,
                        DATE_NUMBER_FORMAT,
                    )

                    headers = tuple(
                        report_sheet.cell(8, index).value
                        for index in range(1, len(REPORT_HEADERS) + 1)
                    )
                    self.assertEqual(headers, REPORT_HEADERS)
                    self.assertFalse(
                        any("поставщик" in header.casefold() for header in headers)
                    )
                    table = report_sheet.tables[REPORT_TABLE_NAME]
                    expected_table_ref = f"A8:K{table_end_row(row_count)}"
                    self.assertEqual(table.ref, expected_table_ref)
                    self.assertEqual(table.autoFilter.ref, expected_table_ref)
                    self.assertEqual(
                        [column.name for column in table.tableColumns],
                        list(REPORT_HEADERS),
                    )
                    self.assertEqual(report_sheet.freeze_panes, "A9")
                    self.assertFalse(parameters.sheet_view.showGridLines)
                    self.assertFalse(report_sheet.sheet_view.showGridLines)
                    self.assertEqual(parameters["B4"].fill.fgColor.rgb[-6:], "FFF2CC")
                    self.assertEqual(
                        report_sheet["A8"].fill.fgColor.rgb[-6:],
                        "4472C4",
                    )
                    self.assertTrue(report_sheet["A8"].font.bold)
                    self.assertEqual(
                        report_sheet["A8"].font.color.rgb[-6:],
                        "FFFFFF",
                    )
                    self.assertTrue(report_sheet["E9"].alignment.wrap_text)
                    expected_widths = {
                        "A": 7,
                        "B": 34,
                        "C": 15,
                        "D": 20,
                        "E": 42,
                        "F": 17,
                        "G": 17,
                        "H": 17,
                        "I": 17,
                        "J": 17,
                        "K": 17,
                    }
                    self.assertEqual(
                        {
                            column: report_sheet.column_dimensions[column].width
                            for column in expected_widths
                        },
                        expected_widths,
                    )

                    formulas = subtotal_formulas(row_count)
                    totals_row = total_row(row_count)
                    self.assertEqual(report_sheet[f"A{totals_row}"].value, "ИТОГО")
                    for column in TOTAL_COLUMNS:
                        self.assertEqual(
                            report_sheet[f"{column}{totals_row}"].value,
                            formulas[column],
                        )
                        self.assertNotIn(
                            f"{column}{totals_row})",
                            formulas[column],
                        )

                    if row_count == 0:
                        self.assertIsNone(
                            report_sheet[f"A{REPORT_FIRST_DATA_ROW}"].value
                        )
                    else:
                        self.assertEqual(
                            report_sheet[f"D{REPORT_FIRST_DATA_ROW}"].value,
                            rows[0]["brand"],
                        )
                        self.assertEqual(
                            report_sheet[f"E{REPORT_FIRST_DATA_ROW}"].value,
                            rows[0]["nomenclature_name"],
                        )
                        for column in NUMERIC_COLUMNS:
                            cell = report_sheet[
                                f"{column}{REPORT_FIRST_DATA_ROW}"
                            ]
                            self.assertEqual(cell.data_type, "n")
                            self.assertIsInstance(cell.value, (int, float))
                        for column in QUANTITY_COLUMNS:
                            self.assertEqual(
                                report_sheet[
                                    f"{column}{REPORT_FIRST_DATA_ROW}"
                                ].number_format,
                                "#,##0.###",
                            )
                        for column in AMOUNT_COLUMNS:
                            self.assertEqual(
                                report_sheet[
                                    f"{column}{REPORT_FIRST_DATA_ROW}"
                                ].number_format,
                                "#,##0.00",
                            )
                    workbook.close()

    def test_failed_save_preserves_existing_output_and_cleans_owned_temp(self):
        with tempfile.TemporaryDirectory() as temp_root:
            parent = Path(temp_root)
            output = parent / "report.xlsx"
            output.write_bytes(b"existing workbook sentinel")

            with patch.object(
                writer.Workbook,
                "save",
                side_effect=OSError("synthetic save failure"),
            ):
                with self.assertRaisesRegex(OSError, "synthetic save failure"):
                    writer.write_inventory_workbook(
                        output,
                        START,
                        END,
                        default_rows(1),
                        "Все товары",
                        [],
                    )

            self.assertEqual(output.read_bytes(), b"existing workbook sentinel")
            self.assertEqual(list(parent.glob(".report.export_*.xlsx")), [])


if __name__ == "__main__":
    unittest.main()
