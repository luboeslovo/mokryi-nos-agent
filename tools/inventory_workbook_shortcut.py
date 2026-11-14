"""Create the Windows desktop shortcut for the inventory updater."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


SHORTCUT_NAME = "Обновить движение товара.lnk"


def shortcut_arguments(launcher: Path, workbook: Path) -> str:
    return subprocess.list2cmdline(
        [str(Path(launcher).resolve()), "--workbook", str(Path(workbook).resolve())]
    )


def create_shortcut(
    shortcut_path: Path,
    *,
    target: Path,
    launcher: Path,
    workbook: Path,
    working_directory: Path,
) -> None:
    """Create or replace one .lnk without third-party Python packages."""

    shortcut = Path(shortcut_path).resolve()
    shortcut.parent.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    environment.update(
        {
            "MN_SHORTCUT": str(shortcut),
            "MN_TARGET": str(Path(target).resolve()),
            "MN_ARGUMENTS": shortcut_arguments(launcher, workbook),
            "MN_WORKDIR": str(Path(working_directory).resolve()),
        }
    )
    command = (
        "$s=(New-Object -ComObject WScript.Shell).CreateShortcut($env:MN_SHORTCUT);"
        "$s.TargetPath=$env:MN_TARGET;"
        "$s.Arguments=$env:MN_ARGUMENTS;"
        "$s.WorkingDirectory=$env:MN_WORKDIR;"
        "$s.Description='Обновить таблицу движения товара';"
        "$s.Save()"
    )
    subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            command,
        ],
        check=True,
        env=environment,
    )

