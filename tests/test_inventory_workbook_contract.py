import sys
import tempfile
import unittest
import zipfile
from datetime import date
from decimal import Decimal
from pathlib import Path


TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import inventory_movement_report as report
from inventory_workbook_contract import (
    PARAMETERS_SHEET_NAME,
    REPORT_HEADERS,
    REPORT_SHEET_NAME,
    REPORT_TABLE_NAME,
    WorkbookContractError,
    read_inventory_workbook_state,
    subtotal_formulas,
    table_end_row,
    total_row,
)
from tests.inventory_workbook_fixture import (
    default_rows,
    write_inventory_workbook_fixture,
)


class InventoryWorkbookContractTests(unittest.TestCase):
    def test_report_headers_have_required_order_without_supplier_sku(self):
        self.assertEqual(
            REPORT_HEADERS,
            (
                "№",
                "Категория",
                "Бренд",
                "Артикул ИТ",
                "Остаток на начало, количество",
                "Остаток на начало, сумма",
                "Приход, количество",
                "Приход, сумма",
                "Остаток на конец, количество",
                "Остаток на конец, сумма",
            ),
        )
        self.assertFalse(
            any("поставщик" in value.casefold() for value in REPORT_HEADERS)
        )

    def test_requested_and_loaded_periods_are_independent_excel_dates(self):
        with tempfile.TemporaryDirectory() as temp_root:
            path = Path(temp_root) / "report.xlsx"
            write_inventory_workbook_fixture(
                path,
                requested_start=date(2026, 8, 10),
                requested_end=date(2026, 8, 18),
                loaded_start=date(2026, 8, 1),
                loaded_end=date(2026, 8, 9),
            )
            state = read_inventory_workbook_state(
                path,
                reference_date=date(2026, 9, 8),
            )
            with zipfile.ZipFile(path) as archive:
                parameters_xml = archive.read(
                    "xl/worksheets/sheet1.xml"
                ).decode("utf-8")

        self.assertEqual(state.requested_start, date(2026, 8, 10))
        self.assertEqual(state.requested_end, date(2026, 8, 18))
        self.assertEqual(state.loaded_start, date(2026, 8, 1))
        self.assertEqual(state.loaded_end, date(2026, 8, 9))
        self.assertIn('<c r="B4" s="1"><v>', parameters_xml)
        self.assertIn('<c r="B5" s="1"><v>', parameters_xml)
        self.assertNotIn('<c r="B4" t="inlineStr">', parameters_xml)
        self.assertNotIn('<c r="B5" t="inlineStr">', parameters_xml)

    def test_builder_writes_requested_dates_as_date_objects(self):
        self.assertIn(
            "parameters.getRange(contract.requestedStartCell).values = "
            "[[localDate(data.requestedStart)]];",
            report.BUILDER_SOURCE,
        )
        self.assertIn(
            "parameters.getRange(contract.requestedEndCell).values = "
            "[[localDate(data.requestedEnd)]];",
            report.BUILDER_SOURCE,
        )

    def test_invalid_reversed_and_future_requested_dates_are_rejected(self):
        scenarios = [
            {
                "requested_start": "не дата",
                "requested_end": date(2026, 8, 18),
                "pattern": "настоящей датой Excel",
            },
            {
                "requested_start": date(2026, 8, 19),
                "requested_end": date(2026, 8, 18),
                "pattern": "не может быть позже",
            },
            {
                "requested_start": date(2026, 8, 1),
                "requested_end": date(2026, 9, 9),
                "pattern": "не может быть в будущем",
            },
        ]
        for scenario in scenarios:
            with self.subTest(pattern=scenario["pattern"]):
                with tempfile.TemporaryDirectory() as temp_root:
                    path = Path(temp_root) / "report.xlsx"
                    write_inventory_workbook_fixture(
                        path,
                        requested_start=scenario["requested_start"],
                        requested_end=scenario["requested_end"],
                    )
                    with self.assertRaisesRegex(
                        WorkbookContractError,
                        scenario["pattern"],
                    ):
                        read_inventory_workbook_state(
                            path,
                            reference_date=date(2026, 9, 8),
                        )

    def test_subtotal_ranges_cover_data_only_for_empty_one_and_many(self):
        expectations = {
            0: (9, 10, "=SUBTOTAL(109,E9:E9)"),
            1: (9, 10, "=SUBTOTAL(109,E9:E9)"),
            3: (11, 12, "=SUBTOTAL(109,E9:E11)"),
        }
        for row_count, expected in expectations.items():
            with self.subTest(row_count=row_count):
                formulas = subtotal_formulas(row_count)
                self.assertEqual(table_end_row(row_count), expected[0])
                self.assertEqual(total_row(row_count), expected[1])
                self.assertEqual(formulas["E"], expected[2])
                for formula in formulas.values():
                    self.assertNotIn(
                        f":E{total_row(row_count)})",
                        formula,
                    )

    def test_verification_accepts_native_table_and_totals_for_row_counts(self):
        for row_count in (0, 1, 3):
            with self.subTest(row_count=row_count):
                with tempfile.TemporaryDirectory() as temp_root:
                    path = Path(temp_root) / "report.xlsx"
                    write_inventory_workbook_fixture(
                        path,
                        rows=default_rows(row_count),
                    )
                    verification = report.reopen_and_verify_xlsx(
                        path,
                        date(2026, 8, 1),
                        date(2026, 8, 18),
                        row_count,
                    )

                self.assertEqual(
                    verification["sheets"],
                    [PARAMETERS_SHEET_NAME, REPORT_SHEET_NAME],
                )
                self.assertEqual(
                    verification["native_table"],
                    REPORT_TABLE_NAME,
                )
                self.assertEqual(verification["data_rows"], row_count)
                self.assertEqual(
                    verification["total_row"],
                    total_row(row_count),
                )

    def test_build_rows_preserves_exact_and_empty_brand(self):
        collected = self.synthetic_collected()
        rows = report.build_rows(collected, None, None)

        self.assertEqual([item["brand"] for item in rows], ["", "Exact Brand"])
        self.assertNotIn("Неизвестный бренд", [item["brand"] for item in rows])

    def test_python_controls_keep_existing_business_totals(self):
        collected = self.synthetic_collected()
        rows = report.build_rows(collected, None, None)
        controls = report.calculate_controls(collected, rows)

        self.assertEqual(controls.union_item_count, 2)
        self.assertEqual(controls.row_count, 2)
        self.assertEqual(controls.intake_document_count, 1)
        self.assertEqual(controls.intake_line_count, 2)
        self.assertEqual(controls.opening_amount, Decimal("300.00"))
        self.assertEqual(controls.intake_quantity, Decimal("3"))
        self.assertEqual(controls.intake_amount, Decimal("75.00"))
        self.assertEqual(controls.ending_amount, Decimal("375.00"))

    @staticmethod
    def synthetic_collected():
        opening = {
            101: report.BalanceValue(
                quantity=Decimal("1"),
                amount=Decimal("100.00"),
            ),
            102: report.BalanceValue(
                quantity=Decimal("2"),
                amount=Decimal("200.00"),
            ),
        }
        intake = report.IntakeAggregate(
            values={
                101: report.BalanceValue(
                    quantity=Decimal("1"),
                    amount=Decimal("25.00"),
                ),
                102: report.BalanceValue(
                    quantity=Decimal("2"),
                    amount=Decimal("50.00"),
                ),
            },
            line_count=2,
            document_count=1,
        )
        ending = {
            101: report.BalanceValue(
                quantity=Decimal("2"),
                amount=Decimal("125.00"),
            ),
            102: report.BalanceValue(
                quantity=Decimal("4"),
                amount=Decimal("250.00"),
            ),
        }
        metadata = {
            101: report.ProductMeta(
                nomenclature_id=1001,
                nmi_ids={101},
                parent_id=1,
                parent_name="Категория",
                brand="Exact Brand",
                suppliers=["Поставщик — SKU"],
                category="B / Категория",
            ),
            102: report.ProductMeta(
                nomenclature_id=1002,
                nmi_ids={102},
                parent_id=1,
                parent_name="Категория",
                brand="",
                suppliers=[],
                category="A / Категория",
            ),
        }
        return {
            "opening": opening,
            "ending": ending,
            "intake": intake,
            "metadata": metadata,
            "universe": {101, 102},
            "procurement": None,
        }


if __name__ == "__main__":
    unittest.main()
