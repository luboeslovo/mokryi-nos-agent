@echo off
chcp 65001 >nul
cd /d "%~dp0"
py -3.12 ".\tools\setup_inventory_updater.py"
if errorlevel 1 (
  echo.
  echo Installation failed. Check that Python 3.12 is installed.
  pause
  exit /b 1
)
echo.
echo Installation completed successfully.
pause

