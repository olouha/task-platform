@echo off
chcp 65001 >nul
echo ========================================
echo   TaskPlatform 快速部署
echo ========================================
echo.

echo [步骤1] 检查目录...
if not exist "C:\task-platform-main" (
    echo [错误] 未找到 C:\task-platform-main
    pause
    exit
)
echo   目录存在

echo.
echo [步骤2] 停止服务...
taskkill /F /IM python.exe 2>nul
taskkill /F /IM node.exe 2>nul
echo   服务已停止

echo.
echo [步骤3] 更新后端文件...
if exist "update_api.zip" (
    powershell -Command "Expand-Archive -Path 'update_api.zip' -DestinationPath 'C:\task-platform-main\backend\api' -Force"
    echo   API 已更新
)

echo.
echo [步骤4] 更新前端...
if exist "vite.config.ts" (
    copy /Y "vite.config.ts" "C:\task-platform-main\frontend\vite.config.ts" >nul
    echo   配置已更新
)

echo.
echo [步骤5] 启动后端...
cd /d C:\task-platform-main\backend
start /B python -m uvicorn main:app --host 0.0.0.0 --port 8080

echo.
echo [步骤6] 启动前端...
cd /d C:\task-platform-main\frontend
start /B npm run dev

echo.
echo ========================================
echo   部署完成！
echo ========================================
echo.
echo 请访问: http://localhost:8080
echo.
pause
