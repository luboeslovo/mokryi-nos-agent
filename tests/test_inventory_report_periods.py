import sys
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch


TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import inventory_report_periods as periods


class InventoryReportPeriodTests(unittest.TestCase):
    reference_date = date(2026, 9, 3)

    def assert_ok(self, result, start_date, end_date):
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.start_date, start_date)
        self.assertEqual(result.end_date, end_date)
        self.assertIsNone(result.clarification)
        self.assertIsNone(result.error)

    def test_a_previous_month(self):
        result = periods.resolve_inventory_report_period(
            "previous_month",
            reference_date=self.reference_date,
        )
        self.assert_ok(result, date(2026, 8, 1), date(2026, 8, 31))

    def test_b_previous_month_across_year_boundary(self):
        result = periods.resolve_inventory_report_period(
            "previous_month",
            reference_date=date(2026, 1, 10),
        )
        self.assert_ok(result, date(2025, 12, 1), date(2025, 12, 31))

    def test_c_current_month(self):
        result = periods.resolve_inventory_report_period(
            "current_month",
            reference_date=self.reference_date,
        )
        self.assert_ok(result, date(2026, 9, 1), date(2026, 9, 3))

    def test_d_named_past_month_without_year(self):
        result = periods.resolve_inventory_report_period(
            "named_month",
            month=8,
            reference_date=self.reference_date,
        )
        self.assert_ok(result, date(2026, 8, 1), date(2026, 8, 31))

    def test_e_named_current_month_without_year(self):
        result = periods.resolve_inventory_report_period(
            "named_month",
            month=9,
            reference_date=self.reference_date,
        )
        self.assert_ok(result, date(2026, 9, 1), date(2026, 9, 3))

    def test_f_named_future_month_without_year_needs_clarification(self):
        result = periods.resolve_inventory_report_period(
            "named_month",
            month=12,
            reference_date=self.reference_date,
        )
        self.assertEqual(result.status, "needs_clarification")
        self.assertEqual(result.clarification, "Укажите год для выбранного месяца.")
        self.assertIsNone(result.start_date)
        self.assertIsNone(result.end_date)

    def test_g_named_past_month_with_year(self):
        result = periods.resolve_inventory_report_period(
            "named_month",
            month=7,
            year=2025,
            reference_date=self.reference_date,
        )
        self.assert_ok(result, date(2025, 7, 1), date(2025, 7, 31))

    def test_h_named_future_month_with_year_is_error(self):
        result = periods.resolve_inventory_report_period(
            "named_month",
            month=10,
            year=2026,
            reference_date=self.reference_date,
        )
        self.assertEqual(result.status, "error")
        self.assertEqual(result.error, "Выбранный месяц находится в будущем.")

    def test_i_explicit_range(self):
        result = periods.resolve_inventory_report_period(
            "explicit_range",
            start_date="2026-08-01",
            end_date="2026-08-18",
            reference_date=self.reference_date,
        )
        self.assert_ok(result, date(2026, 8, 1), date(2026, 8, 18))

    def test_j_explicit_range_without_end_needs_clarification(self):
        result = periods.resolve_inventory_report_period(
            "explicit_range",
            start_date="2026-08-01",
            reference_date=self.reference_date,
        )
        self.assertEqual(result.status, "needs_clarification")
        self.assertEqual(result.clarification, "Укажите дату окончания периода.")

    def test_k_explicit_range_without_start_needs_clarification(self):
        result = periods.resolve_inventory_report_period(
            "explicit_range",
            end_date="2026-08-18",
            reference_date=self.reference_date,
        )
        self.assertEqual(result.status, "needs_clarification")
        self.assertEqual(result.clarification, "Укажите дату начала периода.")

    def test_l_explicit_range_start_after_end_is_error(self):
        result = periods.resolve_inventory_report_period(
            "explicit_range",
            start_date="2026-08-19",
            end_date="2026-08-18",
            reference_date=self.reference_date,
        )
        self.assertEqual(result.status, "error")

    def test_m_explicit_range_with_future_end_is_error(self):
        result = periods.resolve_inventory_report_period(
            "explicit_range",
            start_date="2026-09-01",
            end_date="2026-09-04",
            reference_date=self.reference_date,
        )
        self.assertEqual(result.status, "error")

    def test_n_invalid_iso_date_is_error(self):
        result = periods.resolve_inventory_report_period(
            "explicit_range",
            start_date="01.08.2026",
            end_date="2026-08-18",
            reference_date=self.reference_date,
        )
        self.assertEqual(result.status, "error")

    def test_o_invalid_month_is_error(self):
        result = periods.resolve_inventory_report_period(
            "named_month",
            month=13,
            reference_date=self.reference_date,
        )
        self.assertEqual(result.status, "error")

    def test_p_unknown_period_kind_is_error(self):
        result = periods.resolve_inventory_report_period(
            "last_seven_days",
            reference_date=self.reference_date,
        )
        self.assertEqual(result.status, "error")

    def test_q_explicit_range_accepts_date_objects(self):
        result = periods.resolve_inventory_report_period(
            "explicit_range",
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 18),
            reference_date=self.reference_date,
        )
        self.assert_ok(result, date(2026, 8, 1), date(2026, 8, 18))

    def test_r_named_month_without_month_needs_clarification(self):
        result = periods.resolve_inventory_report_period(
            "named_month",
            reference_date=self.reference_date,
        )
        self.assertEqual(result.status, "needs_clarification")
        self.assertEqual(result.clarification, "Укажите месяц для отчёта.")

    def test_s_default_reference_uses_store_today(self):
        with patch.object(periods, "_store_today", return_value=self.reference_date):
            result = periods.resolve_inventory_report_period("current_month")
        self.assert_ok(result, date(2026, 9, 1), date(2026, 9, 3))

    def test_t_explicit_range_without_boundaries_needs_clarification(self):
        result = periods.resolve_inventory_report_period(
            "explicit_range",
            reference_date=self.reference_date,
        )
        self.assertEqual(result.status, "needs_clarification")
        self.assertEqual(
            result.clarification,
            "Укажите дату начала и дату окончания периода.",
        )

    def test_u_store_timezone_is_europe_moscow(self):
        self.assertEqual(periods.STORE_TIMEZONE.key, "Europe/Moscow")


if __name__ == "__main__":
    unittest.main()
