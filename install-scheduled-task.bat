@echo off
REM ====================================
REM TaskPlatform Windows 任务计划程序安装脚本
REM 运行此脚本后，服务将在每天早上 5:00 自动启动
REM ====================================

echo.
echo ====================================
echo TaskPlatform 任务计划程序配置
echo ====================================
echo.

REM 检查管理员权限
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [提示] 需要管理员权限来创建任务计划
    echo 请右键点击此文件，选择"以管理员身份运行"
    echo.
    pause
    exit /b 1
)

set BATCH_FILE=%~dp0start-services.bat
set TASK_NAME=TaskPlatform_Daily_Start

echo [1/2] 删除旧任务计划（如果存在）...
schtasks /delete /tn "%TASK_NAME%" /f >nul 2>&1

echo [2/2] 创建新任务计划...
schtasks /create /tn "%TASK_NAME%" /tr "%BATCH_FILE%" /sc daily /st 05:00 /ru SYSTEM /rl highest /f

if %errorlevel% equ 0 (
    echo.
    echo ====================================
    echo 任务计划创建成功！
    echo ====================================
    echo.
    echo 任务名称: %TASK_NAME%
    echo 执行时间: 每天早上 05:00
    echo 执行脚本: %BATCH_FILE%
    echo.
    echo 管理命令:
    echo   查看任务: schtasks /query /tn "%TASK_NAME%"
    echo   删除任务: schtasks /delete /tn "%TASK_NAME%" /f
    echo   手动运行: schtasks /run /tn "%TASK_NAME%"
    echo.
) else (
    echo.
    echo [错误] 任务计划创建失败
    echo.
)

pause
