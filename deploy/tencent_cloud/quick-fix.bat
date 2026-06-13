@echo off
REM ==========================================
REM 价格监控API快速修复 - 禁用Supabase
REM ==========================================

set CONFIG_FILE=C:\taskplatform\config\cloud.json
set BACKUP_FILE=C:\taskplatform\config\cloud.json.backup

echo ==========================================
echo 价格监控API快速修复
echo ==========================================
echo.

REM 检查服务器路径
if not exist "C:\taskplatform\" (
    echo [错误] 无法访问服务器路径: C:\taskplatform\
    echo.
    echo 请确认：
    echo 1. 你已登录服务器 (140.143.125.234)
    echo 2. 或者使用远程桌面连接到服务器
    pause
    exit /b 1
)

echo [1/5] 服务器路径检查完成

REM 备份配置文件
if exist "%CONFIG_FILE%" (
    echo [2/5] 备份配置文件...
    copy "%CONFIG_FILE%" "%BACKUP_FILE%" /Y >nul
    echo       备份完成: %BACKUP_FILE%
) else (
    echo [2/5] 配置文件不存在，创建新文件
)

REM 创建修复后的配置文件
echo [3/5] 创建修复配置...
(
echo {
echo   "mode": "sqlite",
echo   "supabase_url": "",
echo   "supabase_key": "",
echo   "version": "1.0.0"
echo }
) > "%CONFIG_FILE%"

echo       配置文件已更新

REM 停止后端服务
echo [4/5] 停止后端服务...
taskkill /F /IM python.exe >nul 2>&1
timeout /t 2 /nobreak >nul
echo       后端服务已停止

REM 启动后端服务
echo [5/5] 启动后端服务...
cd /d C:\taskplatform
start "TaskPlatform API" cmd /k "python -m uvicorn web.backend.main:app --host 0.0.0.0 --port 8000"

timeout /t 3 /nobreak >nul

echo.
echo ==========================================
echo 修复完成！
echo ==========================================
echo.
echo 验证步骤：
echo 1. 等待 5-10 秒让服务完全启动
echo 2. 访问: http://140.143.125.234/
echo 3. 应该能看到价格数据（10764条记录）
echo.
echo 如需恢复原配置:
echo   copy %BACKUP_FILE% %CONFIG_FILE%
echo.
pause
