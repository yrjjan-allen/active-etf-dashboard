@echo off
cd /d "%~dp0"
echo ================================================== >> auto_run.log
echo [%DATE% %TIME%] Starting Auto ETF Crawler Task... >> auto_run.log
echo ================================================== >> auto_run.log

python etf_crawler.py >> auto_run.log 2>&1

echo [%DATE% %TIME%] Crawler finished. Syncing changes to GitHub... >> auto_run.log
git add data/ >> auto_run.log 2>&1
git commit -m "Auto update ETF holdings data: %DATE% %TIME%" >> auto_run.log 2>&1
git push origin main >> auto_run.log 2>&1

echo [%DATE% %TIME%] GitHub synchronization completed. >> auto_run.log
echo. >> auto_run.log
