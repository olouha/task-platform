@echo off
REM 山东烟台钢筋价格自动抓取脚本
REM 自动设置 Windows 任务计划程序

echo ========================================
echo 山东烟台钢筋价格定时抓取设置
echo ========================================
echo.

REM 获取脚本所在目录
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

echo 当前目录: %CD%
echo.

REM 创建任务计划
echo 正在创建 Windows 任务计划...
schtasks /create /tn "TaskPlatform-钢筋价格抓取" /tr "powershell.exe -ExecutionPolicy Bypass -File \"%CD%\services\auto_fetch.ps1\"" /sc daily /st 08:00 /f

echo.
echo 任务创建完成！
echo.
echo ========================================
echo 任务详情:
echo   任务名称: TaskPlatform-钢筋价格抓取
echo   执行时间: 每天 早上 08:00
echo   执行脚本: services\auto_fetch.ps1
echo ========================================
echo.
echo 常用命令:
echo   查看任务: schtasks /query /tn "TaskPlatform-钢筋价格抓取"
echo   删除任务: schtasks /delete /tn "TaskPlatform-钢筋价格抓取" /f
echo   手动运行: schtasks /run /tn "TaskPlatform-钢筋价格抓取"
echo.
pause