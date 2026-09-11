"""User-facing Windows launcher for the permanent inventory workbook updater."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import date
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Callable, Mapping, MutableMapping, TextIO


APP_DIRECTORY_NAME = "MokryiNosInventory"
LOG_RELATIVE_PATH = Path("logs") / "inventory_updater.log"
PLAYWRIGHT_BROWSERS_ENV = "PLAYWRIGHT_BROWSERS_PATH"
PROGRESS_MESSAGE = "Обновляю отчёт, это может занять несколько минут…"
UNEXPECTED_ERROR_MESSAGE = (
    "Не удалось запустить обновление отчёта. Обратитесь к специалисту."
)
PAUSE_MESSAGE = "Нажмите Enter, чтобы закрыть окно."

RefreshCallable = Callable[[Path], Any]


def _safe_log_value(value: object) -> str:
    text = "-" if value is None or value == "" else str(value)
    return " ".join(text.split())[:160]


def _date_log_value(value: object) -> str:
    return value.isoformat() if isinstance(value, date) else "-"


def default_log_path(
    environ: Mapping[str, str] | None = None,
) -> Path | None:
    environment = os.environ if environ is None else environ
    local_app_data = environment.get("LOCALAPPDATA")
    if not local_app_data:
        return None
    return (
        Path(local_app_data)
        / APP_DIRECTORY_NAME
        / LOG_RELATIVE_PATH
    )


def _write_log(log_path: Path | None, event: str, **fields: object) -> None:
    if log_path is None:
        return

    handler: RotatingFileHandler | None = None
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            log_path,
            maxBytes=1_000_000,
            backupCount=2,
            encoding="utf-8",
        )
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(message)s", "%Y-%m-%dT%H:%M:%S")
        )
        logger = logging.Logger("mokryi_nos_inventory_launcher")
        logger.addHandler(handler)
        details = " ".join(
            f"{key}={_safe_log_value(value)}"
            for key, value in fields.items()
        )
        logger.info("event=%s %s", event, details)
    except OSError:
        return
    finally:
        if handler is not None:
            handler.close()


def configure_app_scoped_playwright_runtime(
    app_root: Path,
    environ: MutableMapping[str, str] | None = None,
) -> Path:
    """Prefer app-local Playwright browsers without overriding an explicit path."""

    environment = os.environ if environ is None else environ
    browsers_path = Path(app_root) / "runtime" / "playwright"
    configured_path = environment.setdefault(
        PLAYWRIGHT_BROWSERS_ENV,
        str(browsers_path),
    )
    return Path(configured_path)


def _load_refresh_callable() -> RefreshCallable:
    from inventory_workbook_updater import refresh_inventory_workbook

    return refresh_inventory_workbook


def _pause(input_func: Callable[[str], str]) -> None:
    try:
        input_func(PAUSE_MESSAGE)
    except (EOFError, KeyboardInterrupt):
        pass


def run_launcher(
    workbook_path: Path,
    *,
    refresh: RefreshCallable | None = None,
    stdout: TextIO | None = None,
    input_func: Callable[[str], str] = input,
    pause: bool = True,
    environ: MutableMapping[str, str] | None = None,
    app_root: Path | None = None,
    log_path: Path | None = None,
) -> int:
    """Run one refresh and keep the console result visible for the user."""

    stream = sys.stdout if stdout is None else stdout
    environment = os.environ if environ is None else environ
    root = (
        Path(__file__).resolve().parents[1]
        if app_root is None
        else Path(app_root).resolve()
    )
    workbook = Path(workbook_path).absolute()
    actual_log_path = (
        default_log_path(environment)
        if log_path is None
        else Path(log_path)
    )

    print(PROGRESS_MESSAGE, file=stream, flush=True)
    _write_log(
        actual_log_path,
        "start",
        workbook=_safe_log_value(workbook.name),
    )

    try:
        configure_app_scoped_playwright_runtime(root, environment)
        refresh_callable = refresh or _load_refresh_callable()
        result = refresh_callable(workbook)
        status = getattr(result, "status", None)
        message = getattr(result, "message", None)
        if status not in {"ok", "error"} or not isinstance(message, str):
            raise RuntimeError("Updater returned an invalid result contract.")
    except Exception as error:
        print(UNEXPECTED_ERROR_MESSAGE, file=stream)
        _write_log(
            actual_log_path,
            "unexpected_error",
            error_type=type(error).__name__,
        )
        exit_code = 1
    else:
        print(message, file=stream)
        _write_log(
            actual_log_path,
            "success" if status == "ok" else "error",
            requested_start=_date_log_value(
                getattr(result, "requested_start", None)
            ),
            requested_end=_date_log_value(
                getattr(result, "requested_end", None)
            ),
            loaded_start=_date_log_value(
                getattr(result, "loaded_start", None)
            ),
            loaded_end=_date_log_value(
                getattr(result, "loaded_end", None)
            ),
            replaced=getattr(result, "replaced", False),
            verified=getattr(result, "verified", False),
        )
        exit_code = 0 if status == "ok" else 1

    if pause:
        _pause(input_func)
    return exit_code


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Обновить постоянный отчёт движения товара."
    )
    parser.add_argument(
        "--workbook",
        required=True,
        type=Path,
        help="Путь к постоянному XLSX-файлу отчёта.",
    )
    parser.add_argument(
        "--no-pause",
        action="store_true",
        help="Не ждать Enter после завершения.",
    )
    return parser.parse_args(argv)


def main(
    argv: list[str] | None = None,
    *,
    refresh: RefreshCallable | None = None,
    stdout: TextIO | None = None,
    input_func: Callable[[str], str] = input,
    environ: MutableMapping[str, str] | None = None,
    app_root: Path | None = None,
    log_path: Path | None = None,
) -> int:
    if stdout is None and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    args = parse_args(argv)
    return run_launcher(
        args.workbook,
        refresh=refresh,
        stdout=stdout,
        input_func=input_func,
        pause=not args.no_pause,
        environ=environ,
        app_root=app_root,
        log_path=log_path,
    )


if __name__ == "__main__":
    raise SystemExit(main())
