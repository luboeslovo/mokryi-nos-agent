"""Create the first permanent inventory workbook for a clean installation."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from inventory_workbook_contract import read_inventory_workbook_state
from inventory_workbook_writer import write_inventory_workbook


def create_initial_workbook(output: Path, today: date | None = None) -> None:
    current = today or date.today()
    start = current.replace(day=1)
    write_inventory_workbook(
        Path(output),
        start,
        current,
        [],
        "Без фильтра",
        ["Измените период на листе «Параметры» и запустите ярлык обновления."],
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    if args.validate_only:
        read_inventory_workbook_state(args.output)
    else:
        create_initial_workbook(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

