@echo off
chcp 65001 >nul
echo ========================================
echo   从 GitHub 拉取最新代码并部署
echo ========================================
echo.

:: 检查 Git 是否安装
where git >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未安装 Git，请先安装 Git
    echo 下载地址: https://git-scm.com/download/win
    pause
    exit /b 1
)

:: 1. 进入项目目录
echo [1/5] 进入项目目录...
cd /d C:\task-platform-main
if not exist ".git" (
    echo [错误] C:\task-platform-main 目录不是 Git 仓库
    echo 请先克隆仓库: git clone https://github.com/olouha/task-platform.git C:\task-platform-main
    pause
    exit /b 1
)
echo   当前目录: %CD%

:: 2. 拉取最新代码
echo [2/5] 拉取最新代码...
git fetch origin main
git checkout main
git pull origin main
if %errorlevel% neq 0 (
    echo [警告] 拉取代码失败，继续使用本地版本...
)

:: 3. 停止现有服务
echo [3/5] 停止现有服务...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8080 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
    echo   后端进程已停止
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5173 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
    echo   前端进程已停止
)

:: 4. 清除 Python 缓存
echo [4/5] 清除缓存...
cd C:\task-platform-main\backend
if exist "__pycache__" (
    rmdir /S /Q "__pycache__" 2>nul
)
for /d %%d in (__pycache__) do rmdir /S /Q "%%d" 2>nul

:: 5. 启动服务
echo [5/5] 启动服务...
:: 启动后端
start "Backend" cmd /c "cd /d C:\task-platform-main\backend && python -m uvicorn main:app --host 0.0.0.0 --port 8080"

:: 等待后端启动
timeout /t 3 /nobreak >nul

:: 启动前端
start "Frontend" cmd /c "cd /d C:\task-platform-main\frontend && npm run dev"

echo.
echo ========================================
echo   部署完成！
echo ========================================
echo.
echo   后端地址: http://localhost:8080
echo   前端地址: http://localhost:5173
echo.
echo   请刷新浏览器访问
echo.
pause
