@echo off

cd /d C:\Users\1209v\mokryi-nos-agent

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

if not exist logs mkdir logs

echo. >> logs\daily_update.log
echo ============================================================ >> logs\daily_update.log
echo START %date% %time% >> logs\daily_update.log
echo ============================================================ >> logs\daily_update.log

py tools\update_all.py >> logs\daily_update.log 2>&1
set EXITCODE=%errorlevel%

echo. >> logs\daily_update.log
echo EXIT CODE: %EXITCODE% >> logs\daily_update.log
echo END %date% %time% >> logs\daily_update.log
echo ============================================================ >> logs\daily_update.log

exit /b %EXITCODE%