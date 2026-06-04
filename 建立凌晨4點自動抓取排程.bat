@echo off
title Setup ETF 4AM Daily Crawler Task
cd /d "%~dp0"
echo ==================================================
echo       Setup ETF Daily Task Scheduler (4:00 AM)
echo ==================================================
echo.
echo Creating daily task in Windows Task Scheduler...
schtasks /create /tn "ETF_Holdings_Crawler" /tr "cmd.exe /c cd /d \"%cd%\" && call auto_update_and_push.bat" /sc daily /st 04:00 /f
echo.
if %errorlevel% equ 0 (
    echo [SUCCESS] Daily task created successfully!
    echo It will run automatically at 04:00 AM every day.
) else (
    echo [ERROR] Failed to create task.
    echo Please run this BAT file as Administrator (Right click -> Run as Administrator).
)
echo.
pause
