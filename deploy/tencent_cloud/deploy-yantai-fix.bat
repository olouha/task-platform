@echo off
REM 价格监控API修复部署脚本（简化版）
echo ==========================================
echo 价格监控API修复部署
echo ==========================================
echo.

REM 配置路径
set LOCAL_FILE=e:\E\任务\task-platform\web\backend\api\yantai_db.py
set SERVER_DIR=C:\taskplatform\web\backend\api
set SERVER_FILE=%SERVER_DIR%\yantai_db.py

REM 检查本地文件
if not exist "%LOCAL_FILE%" (
    echo [错误] 本地文件不存在: %LOCAL_FILE%
    pause
    exit /b 1
)

echo [1/4] 本地文件检查完成

REM 检查服务器目录
if not exist "%SERVER_DIR%" (
    echo [错误] 服务器目录不存在: %SERVER_DIR%
    echo 请确认服务器路径正确
    pause
    exit /b 1
)

echo [2/4] 服务器目录检查完成

REM 备份原文件
if exist "%SERVER_FILE%" (
    echo [3/4] 备份服务器文件...
    copy "%SERVER_FILE%" "%SERVER_FILE%.backup" /Y >nul
    echo       备份完成: %SERVER_FILE%.backup
) else (
    echo [3/4] 服务器文件不存在，跳过备份
)

REM 复制修复文件
echo [4/4] 复制修复文件...
copy "%LOCAL_FILE%" "%SERVER_FILE%" /Y
if %errorlevel% equ 0 (
    echo       复制完成！
    echo.
    echo ==========================================
    echo 部署成功！
    echo ==========================================
    echo.
    echo 请执行以下操作完成部署：
    echo 1. 重启后端服务:
    echo    cd C:\taskplatform
    echo    taskkill /F /IM python.exe
    echo    python -m uvicorn web.backend.main:app --host 0.0.0.0 --port 8000
    echo.
    echo 2. 或者运行重启脚本:
    echo    C:\taskplatform\deploy\tencent_cloud\restart.ps1
    echo.
    echo 3. 验证修复: 访问 http://140.143.125.234/
) else (
    echo       复制失败！
    echo 请检查权限和网络连接
)

echo.
pause
