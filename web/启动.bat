@echo off
chcp 65001 >nul
echo ====================================
echo   TaskPlatform Web 启动器
echo ====================================
echo.

:: 检查 Node.js
where npm >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未安装 Node.js
    echo 请从 https://nodejs.org 下载安装
    pause
    exit /b 1
)

:: 检查 Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未安装 Python
    echo 请从 https://python.org 下载安装
    pause
    exit /b 1
)

echo [1/4] 检查依赖...
echo.

:: 安装后端依赖
if not exist "backend\venv" (
    echo [后端] 创建虚拟环境...
    python -m venv backend\venv
)

echo [后端] 安装 Python 依赖...
call backend\venv\Scripts\activate.bat
pip install -r backend\requirements.txt >nul 2>&1

:: 安装前端依赖
echo [前端] 安装 Node 依赖...
cd frontend
if not exist "node_modules" (
    call npm install
)
cd ..

echo.
echo ====================================
echo   启动服务
echo ====================================
echo.

:: 启动后端
start "TaskPlatform Backend (8000)" cmd /k "cd backend && ..\backend\venv\Scripts\activate.bat && uvicorn main:app --reload --port 8000"

:: 等待后端启动
timeout /t 3 /nobreak >nul

:: 启动前端
start "TaskPlatform Frontend (3000)" cmd /k "cd frontend && npm run dev"

echo.
echo ====================================
echo   服务已启动
echo ====================================
echo.
echo   后端 API: http://localhost:8000
echo   前端界面: http://localhost:3000
echo.
echo   按任意键打开浏览器...
pause >nul

start http://localhost:3000