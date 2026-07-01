@echo off
chcp 65001 >nul
echo ========================================
echo   修复 main.py 导入问题
echo ========================================
echo.

set "MAIN_FILE=C:\task-platform-main\web\backend\main.py"

REM 备份
copy "%MAIN_FILE%" "%MAIN_FILE%.tmp" >nul

echo 正在创建修复后的 main.py...

powershell -NoProfile -Command ^
"$content = Get-Content '%MAIN_FILE%' -Raw; " ^
"$content = $content -replace 'from api import projects, materials, price_sources, price_history, adjustments, indicators, sync, yantai_prices, adjustment_rules, scheduler_api, fetch as fetch_api, cron_fetch, cost_reference, adjustment_project, history_fetch, price_history_db, file_parser, adjustment_prices, adjustment_prices_batch, building_schedule, building_adjustment, cost_history, yantai_db, data_manager, adjustment_template, indicator_report, fetch_history', 'from api import projects, materials, price_sources, price_history, adjustments, indicators, sync, yantai_prices, adjustment_rules, scheduler_api, fetch as fetch_api, cron_fetch, cost_reference, adjustment_project, history_fetch, price_history_db, file_parser, adjustment_prices, building_schedule, building_adjustment, cost_history, yantai_db, data_manager, adjustment_template, indicator_report, fetch_history'; " ^
"$content = $content -replace 'app\.include_router\(adjustment_prices_batch\.router, prefix=`"/api/adjustments/prices`", tags=\[`"璋冨樊浠锋牸鎵归樆鑾峰彇`"\]\)', ''; " ^
"Set-Content '%MAIN_FILE%' -Value $content -NoNewline"

if errorlevel 1 (
    echo [错误] 修复失败
    del "%MAIN_FILE%.tmp"
    pause
    exit /b 1
)

echo.
echo ========================================
echo   修复完成！
echo ========================================
echo.
echo 请重启服务:
echo   cd C:\task-platform-main\web\backend
echo   python -m uvicorn main:app --host 0.0.0.0 --port 8000
echo.

del "%MAIN_FILE%.tmp"
pause
