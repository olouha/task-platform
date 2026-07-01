@echo off
chcp 65001 >nul
echo ========================================
echo   快速更新脚本（不停服热更新）
echo ========================================
echo.

:: 1. 解压后端文件
echo [1/4] 更新后端文件...
if exist "update_api.zip" (
    powershell -Command "Expand-Archive -Path 'update_api.zip' -DestinationPath 'C:\task-platform-main\backend\api' -Force"
    echo   api 已更新
)
if exist "update_models.zip" (
    powershell -Command "Expand-Archive -Path 'update_models.zip' -DestinationPath 'C:\task-platform-main\backend\models' -Force"
    echo   models 已更新
)
if exist "update_services.zip" (
    powershell -Command "Expand-Archive -Path 'update_services.zip' -DestinationPath 'C:\task-platform-main\backend\services' -Force"
    echo   services 已更新
)

:: 2. 更新前端配置
echo [2/4] 更新前端配置...
if exist "vite.config.ts" (
    copy /Y "vite.config.ts" "C:\task-platform-main\frontend\vite.config.ts" >nul
    echo   vite.config.ts 已更新
)
if exist ".env" (
    copy /Y ".env" "C:\task-platform-main\frontend\.env" >nul
    echo   .env 已更新
)

:: 3. 更新前端源码
echo [3/4] 更新前端源码...
if exist "update_frontend_src.zip" (
    powershell -Command "Expand-Archive -Path 'update_frontend_src.zip' -DestinationPath 'C:\task-platform-main\frontend\src' -Force"
    echo   前端源码已更新
)

:: 4. 重启服务
echo [4/4] 重启服务...
:: 找到并重启后端
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8080 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
    echo   后端进程已重启
)

:: 启动后端
start "Backend" cmd /c "cd C:\task-platform-main\backend && python -m uvicorn main:app --host 0.0.0.0 --port 8080"

timeout /t 3 /nobreak >nul

:: 找到并重启前端
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5173 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
    echo   前端进程已重启
)

:: 启动前端
start "Frontend" cmd /c "cd C:\task-platform-main\frontend && npm run dev"

echo.
echo ========================================
echo   更新完成！
echo ========================================
echo.
echo   请刷新浏览器访问: http://localhost:5173
echo.
pause
