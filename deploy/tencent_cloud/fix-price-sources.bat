@echo off
chcp 65001 >nul
echo ========================================
echo   修复 price_sources.py Path 导入错误
echo ========================================
echo.

REM 确定服务器路径
set "BASE_DIR=C:\taskplatform"
if not exist "%BASE_DIR%" set "BASE_DIR=C:\web"

set "TARGET_FILE=%BASE_DIR%\web\backend\api\price_sources.py"

if not exist "%TARGET_FILE%" (
    echo [错误] 找不到文件: %TARGET_FILE%
    echo.
    echo 请确认:
    echo 1. 已通过远程桌面连接到服务器
    echo 2. 项目安装在 C:\taskplatform 或 C:\web
    pause
    exit /b 1
)

echo 目标文件: %TARGET_FILE%
echo.

REM 检查是否已修复
findstr /C:"from pathlib import Path" "%TARGET_FILE%" >nul
if not errorlevel 1 (
    echo ✓ Path 导入已存在，无需修复
    pause
    exit /b 0
)

echo [1/2] 添加 Path 导入...
powershell -NoProfile -Command "$content = Get-Content '%TARGET_FILE%' -Raw; if ($content -notmatch 'from pathlib import Path') { $content = $content -replace '(from fastapi import APIRouter)', 'from pathlib import Path`r`n`$1'; Set-Content '%TARGET_FILE%' -Value $content -NoNewline; Write-Host '  修复成功' } else { Write-Host '  已经包含导入' }"

if errorlevel 1 (
    echo [错误] 修复失败
    pause
    exit /b 1
)

echo.
echo [2/2] 验证修复...
findstr /C:"from pathlib import Path" "%TARGET_FILE%" >nul
if errorlevel 1 (
    echo [警告] 验证失败，请手动检查文件
) else (
    echo ✓ 验证通过
)

echo.
echo ========================================
echo   修复完成！
echo ========================================
echo.
echo 请重启后端服务:
echo   1. 停止: taskkill /F /IM python.exe
echo   2. 启动: cd /d %BASE_DIR%
echo            python -m uvicorn web.backend.main:app --host 0.0.0.0 --port 8000
echo.
pause
