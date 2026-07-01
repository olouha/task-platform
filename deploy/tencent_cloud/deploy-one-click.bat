@echo off
chcp 65001 >nul
echo ========================================
echo  腾讯云虚拟桌面 - 一键部署脚本
echo ========================================
echo.

:: 检查管理员权限
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [提示] 建议以管理员身份运行此脚本
    echo.
)

:: 1. 解压文件
echo [1/5] 解压文件...
powershell -Command "Expand-Archive -Path '%USERPROFILE%\Desktop\api_files.zip' -DestinationPath 'C:\task-platform-main\backend\api' -Force" 2>nul
powershell -Command "Expand-Archive -Path '%USERPROFILE%\Desktop\models_files.zip' -DestinationPath 'C:\task-platform-main\backend\models' -Force" 2>nul
powershell -Command "Expand-Archive -Path '%USERPROFILE%\Desktop\services_files.zip' -DestinationPath 'C:\task-platform-main\backend\services' -Force" 2>nul
echo [完成] 文件解压完成
echo.

:: 2. 验证文件
echo [2/5] 验证文件...
for /f %%i in ('powershell -Command "(Get-ChildItem C:\task-platform-main\backend\api\*.py ^|^ Measure-Object).Count"') do set API_COUNT=%%i
for /f %%i in ('powershell -Command "(Get-ChildItem C:\task-platform-main\backend\models\*.py ^|^ Measure-Object).Count"') do set MODELS_COUNT=%%i
for /f %%i in ('powershell -Command "(Get-ChildItem C:\task-platform-main\backend\services\*.py ^|^ Measure-Object).Count"') do set SERVICES_COUNT=%%i
echo api: %API_COUNT% 个文件
echo models: %MODELS_COUNT% 个文件
echo services: %SERVICES_COUNT% 个文件
echo.

:: 3. 停止旧进程
echo [3/5] 停止旧进程...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8080 ^| findstr LISTENING') do (
    taskkill /PID %%a /F >nul 2>&1
    echo 已停止 PID %%a
)
echo [完成] 旧进程已停止
echo.

:: 4. 启动后端
echo [4/5] 启动后端...
cd /d C:\task-platform-main\backend
start "Backend" cmd /k "python -m uvicorn main:app --host 0.0.0.0 --port 8080"
echo 后端启动中，请等待 3 秒...
timeout /t 3 /nobreak >nul
echo [完成] 后端已启动
echo.

:: 5. 启动前端
echo [5/5] 启动前端...
cd /d C:\task-platform-main\frontend
start "Frontend" cmd /k "npm run dev -- --host 0.0.0.0 --port 5173"
echo 前端启动中...
echo.

:: 完成
echo ========================================
echo  部署完成！
echo ========================================
echo.
echo  后端 API: http://localhost:8080
echo  前端页面: http://localhost:5173
echo  API文档:  http://localhost:8080/docs
echo.
pause