@echo off
REM ====================================
REM TaskPlatform 完整服务启动器
REM 包含：后端 + 前端 + 调度器
REM ====================================

echo.
echo ====================================
echo TaskPlatform 完整服务启动
echo 时间: %date% %time%
echo ====================================
echo.

set PROJECT_DIR=e:\E\任务\task-platform
set BACKEND_DIR=%PROJECT_DIR%\web\backend
set FRONTEND_DIR=%PROJECT_DIR%\web\frontend

echo [1/4] 启动后端服务...
cd /d "%BACKEND_DIR%"
start "TaskPlatform-Backend" cmd /k "python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"
timeout /t 5 /nobreak >nul
echo 后端服务已启动 (http://localhost:8000)

echo [2/4] 启动前端服务...
cd /d "%FRONTEND_DIR%"
start "TaskPlatform-Frontend" cmd /k "npm run dev"
timeout /t 5 /nobreak >nul
echo 前端服务已启动

echo [3/4] 启动调度器（每天5点自动抓取）...
cd /d "%BACKEND_DIR%"
start "TaskPlatform-Scheduler" cmd /k "python services/scheduler.py"
timeout /t 3 /nobreak >nul
echo 调度器已启动

echo [4/4] 打开浏览器...
start http://localhost:3000

echo.
echo ====================================
echo 所有服务已启动完成！
echo ====================================
echo 后端 API: http://localhost:8000
echo 前端界面: http://localhost:3000
echo 调度器: 每天早上 5:00 自动抓取
echo API 文档: http://localhost:8000/docs
echo ====================================
echo.
echo 提示: 关闭此窗口不会停止服务
echo       请分别关闭各个服务窗口来停止服务
echo.
pause
