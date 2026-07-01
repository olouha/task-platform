@echo off
chcp 65001 >nul
echo ========================================
echo   TaskPlatform 一键部署脚本 v2.0
echo ========================================
echo.

:: 检查管理员权限
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [警告] 建议以管理员身份运行此脚本
)

:: 1. 停止现有服务
echo [1/6] 停止现有服务...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8080 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5173 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
)
echo   服务已停止

:: 2. 解压后端文件
echo [2/6] 更新后端文件...
if exist "update_api.zip" (
    powershell -Command "Expand-Archive -Path 'update_api.zip' -DestinationPath 'C:\task-platform-main\backend\api' -Force"
    echo   api 目录已更新
)
if exist "update_models.zip" (
    powershell -Command "Expand-Archive -Path 'update_models.zip' -DestinationPath 'C:\task-platform-main\backend\models' -Force"
    echo   models 目录已更新
)
if exist "update_services.zip" (
    powershell -Command "Expand-Archive -Path 'update_services.zip' -DestinationPath 'C:\task-platform-main\backend\services' -Force"
    echo   services 目录已更新
)

:: 3. 更新前端配置
echo [3/6] 更新前端配置...
if exist "vite.config.ts" (
    copy /Y "vite.config.ts" "C:\task-platform-main\frontend\vite.config.ts" >nul
    echo   vite.config.ts 已更新
)
if exist ".env" (
    copy /Y ".env" "C:\task-platform-main\frontend\.env" >nul
    echo   .env 已更新
)

:: 4. 解压前端源码
echo [4/6] 更新前端源码...
if exist "update_frontend_src.zip" (
    powershell -Command "Expand-Archive -Path 'update_frontend_src.zip' -DestinationPath 'C:\task-platform-main\frontend\src' -Force"
    echo   前端源码已更新
)

:: 5. 安装前端依赖
echo [5/6] 检查前端依赖...
cd C:\task-platform-main\frontend
if not exist "node_modules" (
    echo   安装依赖中，请稍候...
    call npm install --silent
)

:: 6. 启动服务
echo [6/6] 启动服务...
:: 启动后端
start "Backend" cmd /c "cd C:\task-platform-main\backend && python -m uvicorn main:app --host 0.0.0.0 --port 8080"

:: 等待后端启动
timeout /t 3 /nobreak >nul

:: 启动前端
start "Frontend" cmd /c "cd C:\task-platform-main\frontend && npm run dev"

echo.
echo ========================================
echo   部署完成！
echo ========================================
echo.
echo   后端地址: http://localhost:8080
echo   前端地址: http://localhost:5173
echo.
echo   API文档: http://localhost:8080/docs
echo.
pause
