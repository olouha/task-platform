@echo off
chcp 65001 >nul
echo 正在重启服务...

cd /d C:\task-platform-main\backend

REM 停止现有进程
taskkill /F /IM python.exe 2>nul
timeout /t 2 >nul

REM 启动服务
echo 启动中...
start /B python -m uvicorn main:app --host 0.0.0.0 --port 8000

timeout /t 3 >nul

REM 检查是否启动成功
netstat | findstr ":8000" | findstr "LISTENING"
if %errorlevel% equ 0 (
    echo.
    echo === 服务已启动成功 ===
    echo 访问地址: http://140.143.125.234:8000
) else (
    echo.
    echo [警告] 服务可能未正常启动，请检查日志
)

pause