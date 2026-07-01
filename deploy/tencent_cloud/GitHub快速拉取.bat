@echo off
chcp 65001 >nul
echo ========================================
echo   GitHub 快速拉取更新
echo ========================================
echo.

cd /d C:\task-platform-main

echo 拉取最新代码...
git fetch origin main
git pull origin main

if %errorlevel% equ 0 (
    echo.
    echo [成功] 代码已更新！
    echo.
    echo 重启服务请运行: GitHub拉取部署.bat
) else (
    echo.
    echo [警告] 拉取失败，可能是合并冲突
    echo 请手动解决后重新运行
)

pause
