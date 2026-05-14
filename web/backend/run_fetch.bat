@echo off
chcp 65001 > nul
cd /d "E:\E\任务\task-platform\web\backend"
echo ============================================
echo Yantai Rebar Price Scraper
echo ============================================
python -u services\scheduler_task.py --force
echo.
echo Done.