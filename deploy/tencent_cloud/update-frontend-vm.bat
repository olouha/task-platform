@echo off
chcp 65001 >nul
echo ========================================
echo   虚拟桌面前端更新脚本
echo ========================================
echo.

echo [1/3] 更新前端 API 配置...
cd C:\web\frontend
echo VITE_API_URL=http://140.143.125.234:8000/api > .env
echo ✓ 配置已更新
echo.

echo [2/3] 停止当前前端服务...
echo 请手动关闭当前运行的前端服务（按 Ctrl+C）
echo 然后按任意键继续...
pause >nul
echo.

echo [3/3] 启动前端服务...
start cmd /k "npm run dev -- --host 0.0.0.0 --port 8081"

echo.
echo ========================================
echo   更新完成！
echo ========================================
echo.
echo 前端地址: http://140.143.125.234:8081/projects
echo 后端地址: http://140.143.125.234:8000/docs
echo.
pause
