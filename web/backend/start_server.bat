@echo off
chcp 65001 > nul
title TaskPlatform 服务管理器

echo ========================================
echo   TaskPlatform 服务管理器
echo ========================================
echo.

cd /d "%~dp0"

:menu
cls
echo ========================================
echo   TaskPlatform 服务管理器
echo ========================================
echo.
echo   1. 启动服务
echo   2. 停止服务
echo   3. 重启服务
echo   4. 查看服务状态
echo   5. 访问网页
echo   0. 退出
echo.
set /p choice=请选择 (0-5):

if "%choice%"=="1" goto start
if "%choice%"=="2" goto stop
if "%choice%"=="3" goto restart
if "%choice%"=="4" goto status
if "%choice%"=="5" goto open
if "%choice%"=="0" goto end

:start
echo.
echo 正在启动服务...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    echo 服务已在运行 (PID: %%a)
    goto :menu
)
start python -m uvicorn main:app --host 0.0.0.0 --port 8000
timeout /t 3 > nul
echo 服务已启动！
echo.
echo 访问地址: http://localhost:8000
echo.
pause
goto menu

:stop
echo.
echo 正在停止服务...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /F /PID %%a > nul 2>&1
    echo 已停止 PID: %%a
)
echo 服务已停止。
echo.
pause
goto menu

:restart
echo.
echo 正在重启服务...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /F /PID %%a > nul 2>&1
)
timeout /t 2 > nul
start python -m uvicorn main:app --host 0.0.0.0 --port 8000
timeout /t 3 > nul
echo 服务已重启！
echo.
echo 访问地址: http://localhost:8000
echo.
pause
goto menu

:status
echo.
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    echo 服务状态: 运行中 (PID: %%a)
    goto :status_done
)
echo 服务状态: 已停止
:status_done
echo.
pause
goto menu

:open
start http://localhost:8000
goto menu

:end
echo.
echo 再见！
timeout /t 2 > nul
exit