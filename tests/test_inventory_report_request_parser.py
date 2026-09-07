import sys
import unittest
from pathlib import Path


TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS_DIR))

from inventory_report_request_parser import normalize_inventory_report_arguments


class InventoryReportRequestParserTests(unittest.TestCase):
    def normalize(self, question, model_arguments=None):
        return normalize_inventory_report_arguments(question, model_arguments)

    def test_a_named_month_removes_hallucinated_year(self):
        result = self.normalize(
            "Сделай отчёт движения товара за август",
            {"period_kind": "named_month", "year": 2025},
        )
        self.assertEqual(result, {"period_kind": "named_month", "month": 8})

    def test_b_named_month_keeps_explicit_year_from_question(self):
        result = self.normalize(
            "Сделай отчёт движения товара за август 2025",
            {"period_kind": "named_month", "year": 2025},
        )
        self.assertEqual(
            result,
            {"period_kind": "named_month", "month": 8, "year": 2025},
        )

    def test_c_day_range_restores_missing_model_fields(self):
        result = self.normalize(
            "Сформируй движение товара с 1 по 18 августа",
            {
                "period_kind": "day_range_in_month",
                "start_day": 1,
                "year": 2025,
            },
        )
        self.assertEqual(
            result,
            {
                "period_kind": "day_range_in_month",
                "start_day": 1,
                "end_day": 18,
                "month": 8,
            },
        )

    def test_d_day_range_keeps_explicit_year(self):
        result = self.normalize(
            "Сформируй движение товара с 1 по 18 августа 2025",
            {"period_kind": "day_range_in_month", "year": 2025},
        )
        self.assertEqual(
            result,
            {
                "period_kind": "day_range_in_month",
                "start_day": 1,
                "end_day": 18,
                "month": 8,
                "year": 2025,
            },
        )

    def test_e_previous_month_discards_all_model_dates(self):
        result = self.normalize(
            "Пришли Excel движения товара за прошлый месяц",
            {
                "period_kind": "named_month",
                "start_date": "2025-08-01",
                "end_date": "2025-08-31",
                "start_day": 1,
                "end_day": 31,
                "month": 8,
                "year": 2025,
            },
        )
        self.assertEqual(result, {"period_kind": "previous_month"})

    def test_f_current_month_discards_all_model_dates(self):
        result = self.normalize(
            "Сделай отчёт движения товара за этот месяц",
            {"period_kind": "named_month", "month": 8, "year": 2025},
        )
        self.assertEqual(result, {"period_kind": "current_month"})

    def test_g_explicit_iso_range_restores_end_date(self):
        result = self.normalize(
            "Сделай отчёт движения товара с 2026-08-01 по 2026-08-18",
            {
                "period_kind": "explicit_range",
                "start_date": "2026-08-01",
                "start_day": 1,
                "year": 2026,
            },
        )
        self.assertEqual(
            result,
            {
                "period_kind": "explicit_range",
                "start_date": "2026-08-01",
                "end_date": "2026-08-18",
            },
        )

    def test_h_incomplete_start_day_range_stays_incomplete(self):
        result = self.normalize(
            "Сделай отчёт движения товара с 1 августа",
            {"period_kind": "day_range_in_month", "year": 2025},
        )
        self.assertEqual(
            result,
            {"period_kind": "day_range_in_month", "start_day": 1, "month": 8},
        )

    def test_i_incomplete_end_day_range_stays_incomplete(self):
        result = self.normalize(
            "Сделай отчёт движения товара до 18 августа",
            {"period_kind": "day_range_in_month", "year": 2026},
        )
        self.assertEqual(
            result,
            {"period_kind": "day_range_in_month", "end_day": 18, "month": 8},
        )

    def test_j_explicit_brand_is_copied_exactly(self):
        result = self.normalize(
            "Сделай отчёт движения товара за август по бренду Royal Canin",
            {"period_kind": "named_month", "year": 2025},
        )
        self.assertEqual(
            result,
            {
                "period_kind": "named_month",
                "month": 8,
                "brand": "Royal Canin",
            },
        )

    def test_k_explicit_category_is_copied_exactly(self):
        result = self.normalize(
            "Сделай отчёт движения товара за август по категории Сухой корм",
            {"period_kind": "named_month", "year": 2025},
        )
        self.assertEqual(
            result,
            {
                "period_kind": "named_month",
                "month": 8,
                "category": "Сухой корм",
            },
        )

    def test_adversarial_model_fields_are_all_removed(self):
        result = self.normalize(
            "Отчёт за август",
            {
                "period_kind": "named_month",
                "month": 3,
                "year": 2024,
                "start_date": "2024-03-01",
                "end_date": "2024-03-31",
                "start_day": 1,
                "end_day": 31,
                "brand": "Fake Brand",
                "category": "Fake Category",
                "output_path": r"C:\secret.xlsx",
                "temp_root": r"C:\secret",
                "reference_date": "2025-01-01",
                "filesystem_path": r"C:\secret\report.xlsx",
            },
        )
        self.assertEqual(result, {"period_kind": "named_month", "month": 8})

    def test_all_required_russian_month_forms_are_supported(self):
        month_forms = {
            1: ("январь", "января", "январе"),
            2: ("февраль", "февраля", "феврале"),
            3: ("март", "марта", "марте"),
            4: ("апрель", "апреля", "апреле"),
            5: ("май", "мая", "мае"),
            6: ("июнь", "июня", "июне"),
            7: ("июль", "июля", "июле"),
            8: ("август", "августа", "августе"),
            9: ("сентябрь", "сентября", "сентябре"),
            10: ("октябрь", "октября", "октябре"),
            11: ("ноябрь", "ноября", "ноябре"),
            12: ("декабрь", "декабря", "декабре"),
        }
        for month, forms in month_forms.items():
            for form in forms:
                with self.subTest(month=month, form=form):
                    self.assertEqual(
                        self.normalize(f"Сделай отчёт за {form}"),
                        {"period_kind": "named_month", "month": month},
                    )

    def test_explicit_ddmmyyyy_range_is_converted_to_iso(self):
        result = self.normalize(
            "Сделай отчёт с 01.08.2026 по 18.08.2026",
            {"period_kind": "explicit_range"},
        )
        self.assertEqual(
            result,
            {
                "period_kind": "explicit_range",
                "start_date": "2026-08-01",
                "end_date": "2026-08-18",
            },
        )

    def test_supported_filter_markers_copy_only_user_text(self):
        cases = (
            ("по бренду Royal Canin", "brand", "Royal Canin"),
            ("бренд Royal Canin", "brand", "Royal Canin"),
            ("для бренда Royal Canin", "brand", "Royal Canin"),
            ("по категории Сухой корм", "category", "Сухой корм"),
            ("категория Сухой корм", "category", "Сухой корм"),
            ("для категории Сухой корм", "category", "Сухой корм"),
        )
        for suffix, field, value in cases:
            with self.subTest(suffix=suffix):
                result = self.normalize(f"Сделай отчёт за август {suffix}")
                self.assertEqual(result[field], value)

    def test_unrecognized_period_does_not_reuse_model_period(self):
        result = self.normalize(
            "Сделай какой-нибудь отчёт движения товара",
            {"period_kind": "previous_month", "year": 2025},
        )
        self.assertEqual(result, {"period_kind": "unrecognized"})


if __name__ == "__main__":
    unittest.main()
