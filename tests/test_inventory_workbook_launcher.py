import io
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import inventory_workbook_launcher as launcher
from inventory_workbook_updater import refresh_inventory_workbook


def refresh_result(
    *,
    status="ok",
    message="Отчёт успешно обновлён за 01.08.2026–18.08.2026.",
    replaced=True,
    verified=True,
):
    return SimpleNamespace(
        status=status,
        message=message,
        requested_start=date(2026, 8, 1),
        requested_end=date(2026, 8, 18),
        loaded_start=date(2026, 8, 1),
        loaded_end=date(2026, 8, 18),
        replaced=replaced,
        verified=verified,
    )


class InventoryWorkbookLauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_directory.name)
        self.workbook = self.root / "Папка с пробелами" / "Движение товара.xlsx"
        self.workbook.parent.mkdir()
        self.workbook.write_bytes(b"synthetic workbook sentinel")
        self.log_path = self.root / "logs" / "launcher.log"

    def tearDown(self):
        self.temp_directory.cleanup()

    def run_launcher_case(
        self,
        result=None,
        *,
        error=None,
        workbook=None,
        pause=False,
    ):
        calls = []
        prompts = []

        def fake_refresh(path):
            calls.append(path)
            if error is not None:
                raise error
            return result or refresh_result()

        stdout = io.StringIO()
        code = launcher.run_launcher(
            workbook or self.workbook,
            refresh=fake_refresh,
            stdout=stdout,
            input_func=lambda prompt: prompts.append(prompt) or "",
            pause=pause,
            environ={},
            app_root=self.root,
            log_path=self.log_path,
        )
        return code, stdout.getvalue(), calls, prompts

    def test_passes_cyrillic_workbook_path_with_spaces_unchanged(self):
        code, output, calls, _ = self.run_launcher_case()

        self.assertEqual(code, 0)
        self.assertEqual(calls, [self.workbook.absolute()])
        self.assertIn(launcher.PROGRESS_MESSAGE, output)
        self.assertIn("Отчёт успешно обновлён", output)

    def test_success_error_open_excel_and_missing_file_user_experience(self):
        scenarios = [
            (
                refresh_result(),
                0,
                "Отчёт успешно обновлён за 01.08.2026–18.08.2026.",
            ),
            (
                refresh_result(
                    status="error",
                    message="Не удалось сформировать отчёт движения товара.",
                    replaced=False,
                    verified=False,
                ),
                1,
                "Не удалось сформировать отчёт движения товара.",
            ),
            (
                refresh_result(
                    status="error",
                    message=(
                        "Закройте Excel с отчётом и запустите обновление ещё раз."
                    ),
                    replaced=False,
                    verified=False,
                ),
                1,
                "Закройте Excel с отчётом",
            ),
            (
                refresh_result(
                    status="error",
                    message="Файл отчёта не найден.",
                    replaced=False,
                    verified=False,
                ),
                1,
                "Файл отчёта не найден.",
            ),
        ]
        for result, expected_code, expected_text in scenarios:
            with self.subTest(expected_text=expected_text):
                code, output, _, _ = self.run_launcher_case(result)
                self.assertEqual(code, expected_code)
                self.assertIn(expected_text, output)
                self.assertNotIn("Traceback", output)

    def test_actual_updater_handles_missing_workbook_without_external_services(self):
        missing = self.root / "Нет такого отчёта.xlsx"
        stdout = io.StringIO()

        code = launcher.run_launcher(
            missing,
            refresh=refresh_inventory_workbook,
            stdout=stdout,
            pause=False,
            environ={},
            app_root=self.root,
            log_path=self.log_path,
        )

        self.assertEqual(code, 1)
        self.assertIn("Файл отчёта не найден.", stdout.getvalue())

    def test_unexpected_error_hides_traceback_and_secret(self):
        code, output, _, _ = self.run_launcher_case(
            error=RuntimeError("token=do-not-print")
        )

        self.assertEqual(code, 1)
        self.assertIn(launcher.UNEXPECTED_ERROR_MESSAGE, output)
        self.assertNotIn("token=do-not-print", output)
        self.assertNotIn("Traceback", output)
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn("error_type=RuntimeError", log_text)
        self.assertNotIn("token=do-not-print", log_text)

    def test_launcher_does_not_modify_workbook_itself(self):
        before = self.workbook.read_bytes()

        code, _, _, _ = self.run_launcher_case()

        self.assertEqual(code, 0)
        self.assertEqual(self.workbook.read_bytes(), before)

    def test_console_waits_for_enter_by_default(self):
        code, _, _, prompts = self.run_launcher_case(pause=True)

        self.assertEqual(code, 0)
        self.assertEqual(prompts, [launcher.PAUSE_MESSAGE])

    def test_main_no_pause_preserves_cli_workbook_argument(self):
        calls = []
        stdout = io.StringIO()

        code = launcher.main(
            ["--workbook", str(self.workbook), "--no-pause"],
            refresh=lambda path: calls.append(path) or refresh_result(),
            stdout=stdout,
            environ={},
            app_root=self.root,
            log_path=self.log_path,
        )

        self.assertEqual(code, 0)
        self.assertEqual(calls, [self.workbook.absolute()])

    def test_missing_playwright_path_gets_app_scoped_runtime(self):
        environment = {}

        configured = launcher.configure_app_scoped_playwright_runtime(
            self.root,
            environment,
        )

        self.assertEqual(
            configured,
            self.root / "runtime" / "playwright",
        )
        self.assertEqual(
            environment[launcher.PLAYWRIGHT_BROWSERS_ENV],
            str(self.root / "runtime" / "playwright"),
        )

    def test_explicit_playwright_path_is_preserved(self):
        explicit = self.root / "Внешние браузеры"
        environment = {launcher.PLAYWRIGHT_BROWSERS_ENV: str(explicit)}

        configured = launcher.configure_app_scoped_playwright_runtime(
            self.root,
            environment,
        )

        self.assertEqual(configured, explicit)
        self.assertEqual(
            environment[launcher.PLAYWRIGHT_BROWSERS_ENV],
            str(explicit),
        )

    def test_playwright_path_supports_spaces_cyrillic_and_no_hardcode(self):
        app_root = self.root / "Мокрый Нос Inventory App"
        environment = {}

        configured = launcher.configure_app_scoped_playwright_runtime(
            app_root,
            environment,
        )

        self.assertEqual(configured, app_root / "runtime" / "playwright")
        launcher_source = Path(launcher.__file__).read_text(encoding="utf-8")
        self.assertNotRegex(
            launcher_source,
            r"[A-Za-z]:\\Users\\",
        )
        self.assertNotIn("CODEX_ARTIFACT_NODE", launcher_source)

    def test_runtime_manifests_pin_only_required_top_level_dependencies(self):
        requirements = (
            REPO_ROOT
            / "deployment"
            / "inventory_updater"
            / "requirements.txt"
        ).read_text(encoding="utf-8").splitlines()
        packages = {
            line
            for line in requirements
            if line and not line.startswith("#")
        }

        self.assertEqual(
            packages,
            {
                "keyring==25.7.0",
                "openpyxl==3.1.5",
                "playwright==1.62.0",
                "tzdata==2026.2",
            },
        )
        self.assertFalse(
            (
                REPO_ROOT
                / "deployment"
                / "inventory_updater"
                / "package.json"
            ).exists()
        )


if __name__ == "__main__":
    unittest.main()
