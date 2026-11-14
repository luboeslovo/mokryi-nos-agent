import os
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import create_inventory_workbook as creator
import inventory_workbook_shortcut as shortcut
import setup_inventory_updater as setup
from inventory_workbook_contract import read_inventory_workbook_state


class InventoryUpdaterSetupTests(unittest.TestCase):
    def test_bundle_contains_every_declared_production_file(self):
        for name in setup.PRODUCTION_TOOLS:
            self.assertTrue((TOOLS_DIR / name).is_file(), name)
        self.assertTrue((REPO_ROOT / setup.REQUIREMENTS).is_file())

    def test_initial_workbook_uses_current_month_and_valid_contract(self):
        with tempfile.TemporaryDirectory() as temp_root:
            path = Path(temp_root) / "Движение товара.xlsx"
            creator.create_initial_workbook(path, date(2026, 11, 14))
            state = read_inventory_workbook_state(
                path, reference_date=date(2026, 11, 14)
            )
            self.assertEqual(state.requested_start, date(2026, 11, 1))
            self.assertEqual(state.requested_end, date(2026, 11, 14))

    def test_shortcut_arguments_preserve_spaces_and_cyrillic(self):
        arguments = shortcut.shortcut_arguments(
            Path(r"C:\App Root\tools\inventory_workbook_launcher.py"),
            Path(r"C:\Users\Мама\Documents\Мокрый нос\Движение товара.xlsx"),
        )
        self.assertIn("--workbook", arguments)
        self.assertIn("Движение товара.xlsx", arguments)
        self.assertIn('"', arguments)

    def test_non_interactive_crm_requires_explicit_skip(self):
        args = setup.parse_args(["--non-interactive"])
        self.assertTrue(args.non_interactive)
        self.assertFalse(args.skip_crm_auth)

    def test_config_write_is_atomic_json(self):
        with tempfile.TemporaryDirectory() as temp_root:
            path = Path(temp_root) / "config.json"
            setup._write_json_atomic(path, {"workbook_path": "C:/Тест.xlsx"})
            self.assertIn("Тест.xlsx", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

