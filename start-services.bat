@echo off
REM ====================================
REM TaskPlatform 服务启动脚本
REM 每天早上 5:00 自动运行
REM ====================================

echo.
echo ====================================
echo TaskPlatform 服务启动
echo 时间: %date% %time%
echo ====================================
echo.

REM 设置工作目录
set PROJECT_DIR=e:\E\任务\task-platform
set BACKEND_DIR=%PROJECT_DIR%\web\backend
set FRONTEND_DIR=%PROJECT_DIR%\web\frontend

REM 检查 Python 是否安装
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] Python 未安装或不在 PATH 中
    pause
    exit /b 1
)

REM 检查 Node.js 是否安装
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] Node.js 未安装或不在 PATH 中
    pause
    exit /b 1
)

echo [1/4] 启动后端服务...
cd /d "%BACKEND_DIR%"
start "TaskPlatform-Backend" cmd /k "python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"
echo 后端服务已启动 (http://localhost:8000)

REM 等待后端启动
timeout /t 5 /nobreak >nul

echo [2/4] 启动前端服务...
cd /d "%FRONTEND_DIR%"
start "TaskPlatform-Frontend" cmd /k "npm run dev"
echo 前端服务已启动

REM 等待前端启动
timeout /t 5 /nobreak >nul

echo [3/4] 执行价格抓取任务...
cd /d "%BACKEND_DIR"
python -c "import asyncio; from services.price.scraper import YantaiScraper; asyncio.run(YantaiScraper().fetch())"

echo [4/4] 打开浏览器...
timeout /t 3 /nobreak >nul
start http://localhost:3000

echo.
echo ====================================
echo 所有服务已启动完成！
echo 后端: http://localhost:8000
echo 前端: http://localhost:3000
echo ====================================
echo.

REM 保持窗口打开10秒
timeout /t 10
