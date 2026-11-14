"""Install the inventory workbook updater into a stable per-user location."""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from inventory_workbook_shortcut import SHORTCUT_NAME, create_shortcut


APP_NAME = "MokryiNosInventory"
SOURCE_ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS = Path("deployment/inventory_updater/requirements.txt")
PRODUCTION_TOOLS = (
    "auto_login_crm.py",
    "create_inventory_workbook.py",
    "inventory_movement_report.py",
    "inventory_workbook_contract.py",
    "inventory_workbook_launcher.py",
    "inventory_workbook_shortcut.py",
    "inventory_workbook_updater.py",
    "inventory_workbook_writer.py",
    "setup_crm_credentials.py",
)


class SetupError(RuntimeError):
    pass


def _known_folder(folder_id: int, fallback: Path) -> Path:
    if os.name != "nt":
        return fallback
    buffer = ctypes.create_unicode_buffer(260)
    result = ctypes.windll.shell32.SHGetFolderPathW(
        None, folder_id, None, 0, buffer
    )
    if result != 0 or not buffer.value:
        return fallback
    return Path(buffer.value)


def default_app_root() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        raise SetupError("Не найдена папка LOCALAPPDATA.")
    return Path(local_app_data) / APP_NAME


def default_workbook() -> Path:
    documents = _known_folder(5, Path.home() / "Documents")
    return documents / "Мокрый нос" / "Движение товара.xlsx"


def default_shortcut_dir() -> Path:
    return _known_folder(16, Path.home() / "Desktop")


def venv_python(app_root: Path) -> Path:
    return Path(app_root) / ".venv" / "Scripts" / "python.exe"


def _run(command: list[str], *, env: dict[str, str] | None = None) -> None:
    subprocess.run(command, check=True, env=env)


def _copy_bundle(app_root: Path) -> None:
    tools_dir = app_root / "tools"
    deployment_dir = app_root / REQUIREMENTS.parent
    tools_dir.mkdir(parents=True, exist_ok=True)
    deployment_dir.mkdir(parents=True, exist_ok=True)
    for name in PRODUCTION_TOOLS:
        source = SOURCE_ROOT / "tools" / name
        if not source.is_file():
            raise SetupError(f"В установочном комплекте отсутствует tools/{name}.")
        shutil.copy2(source, tools_dir / name)
    shutil.copy2(SOURCE_ROOT / REQUIREMENTS, app_root / REQUIREMENTS)


def _write_json_atomic(path: Path, payload: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, raw_path = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(raw_path, path)
    finally:
        Path(raw_path).unlink(missing_ok=True)


def _ensure_python() -> None:
    if os.name != "nt":
        raise SetupError("Установщик предназначен для Windows.")
    if sys.version_info[:2] != (3, 12):
        raise SetupError("Нужен обычный Python 3.12.")


def install(args: argparse.Namespace) -> Path:
    _ensure_python()
    app_root = Path(args.app_root or default_app_root()).resolve()
    workbook = Path(args.workbook or default_workbook()).resolve()
    shortcut_dir = Path(args.shortcut_dir or default_shortcut_dir()).resolve()
    browser_root = app_root / "runtime" / "playwright"
    python = venv_python(app_root)

    print("[1/8] Проверяю Python 3.12…")
    print("[2/8] Подготавливаю файлы приложения…")
    _copy_bundle(app_root)

    print("[3/8] Создаю окружение…")
    if not python.is_file():
        _run([sys.executable, "-m", "venv", str(app_root / ".venv")])
    _run([str(python), "-m", "pip", "install", "--disable-pip-version-check", "-r", str(app_root / REQUIREMENTS)])
    _run([str(python), "-m", "pip", "check"])

    print("[4/8] Устанавливаю Chromium…")
    environment = os.environ.copy()
    environment["PLAYWRIGHT_BROWSERS_PATH"] = str(browser_root)
    _run([str(python), "-m", "playwright", "install", "chromium"], env=environment)

    print("[5/8] Проверяю Excel-файл…")
    workbook.parent.mkdir(parents=True, exist_ok=True)
    workbook_tool = app_root / "tools" / "create_inventory_workbook.py"
    if workbook.exists():
        _run([str(python), str(workbook_tool), "--output", str(workbook), "--validate-only"])
    else:
        _run([str(python), str(workbook_tool), "--output", str(workbook)])

    print("[6/8] Настраиваю CRM…")
    auth_file = app_root / "auth.json"
    if not args.skip_crm_auth:
        if args.non_interactive:
            raise SetupError("Для настройки CRM нужен интерактивный режим или --skip-crm-auth.")
        if args.refresh_crm_auth or not auth_file.exists():
            _run([str(python), str(app_root / "tools" / "setup_crm_credentials.py")], env=environment)
            _run([str(python), str(app_root / "tools" / "auto_login_crm.py")], env=environment)

    print("[7/8] Сохраняю настройку Excel…")
    _write_json_atomic(app_root / "config.json", {"workbook_path": str(workbook)})

    print("[8/8] Создаю ярлык…")
    shortcut = shortcut_dir / SHORTCUT_NAME
    create_shortcut(
        shortcut,
        target=python,
        launcher=app_root / "tools" / "inventory_workbook_launcher.py",
        workbook=workbook,
        working_directory=app_root,
    )
    print("Установка завершена. Ярлык обновления готов.")
    return shortcut


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Установить обновлятор таблицы движения товара."
    )
    parser.add_argument("--workbook", type=Path)
    parser.add_argument("--app-root", type=Path)
    parser.add_argument("--shortcut-dir", type=Path)
    parser.add_argument("--skip-crm-auth", action="store_true")
    parser.add_argument("--refresh-crm-auth", action="store_true")
    parser.add_argument("--non-interactive", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        install(parse_args(argv))
    except (SetupError, OSError, subprocess.CalledProcessError) as error:
        print(f"Установка не завершена: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

