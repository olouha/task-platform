@echo off
REM 设置定时任务
REM 山东烟台钢筋价格自动抓取

cd /d "%~dp0"
echo ========================================
echo 设置定时抓取任务
echo ========================================
echo.

set TASK_NAME=TaskPlatform-钢筋价格抓取
set SCRIPT_PATH=%CD%\services\run_fetch.bat

echo 任务名称: %TASK_NAME%
echo 执行脚本: %SCRIPT_PATH%
echo.

REM 删除旧任务
schtasks /delete /tn "%TASK_NAME%" /f 2>nul

REM 创建新任务 - 每天早上8点
echo 正在创建任务...
schtasks /create /tn "%TASK_NAME%" /tr "\"%SCRIPT_PATH%\"" /sc daily /st 08:00 /f

echo.
echo 任务创建完成!
echo.
echo 常用命令:
echo   查看任务: schtasks /query /tn "%TASK_NAME%"
echo   手动运行: schtasks /run /tn "%TASK_NAME%"
echo   删除任务: schtasks /delete /tn "%TASK_NAME%" /f
echo.
pause