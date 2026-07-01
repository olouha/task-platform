@echo off
chcp 65001 >nul
echo ========================================
echo   TaskPlatform 腾讯云部署脚本
echo ========================================
echo.

:: 获取脚本所在目录
set SCRIPT_DIR=%~dp0
set SCRIPT_DIR=%SCRIPT_DIR:~0,-1%

:: 检查目标目录
set TARGET_DIR=C:\task-platform-main
if not exist "%TARGET_DIR%" (
    set TARGET_DIR=%USERPROFILE%\task-platform
    echo [提示] 使用替代目录: %TARGET_DIR%
)

cd /d "%TARGET_DIR%"
echo [1/7] 目标目录: %CD%
echo.

:: 2. 尝试 GitHub 拉取
echo [2/7] 尝试从 GitHub 拉取最新代码...
git fetch origin main 2>nul
git pull origin main 2>nul
if %errorlevel% equ 0 (
    echo   [成功] GitHub 代码已更新
    set GITHUB_SUCCESS=1
) else (
    echo   [提示] GitHub 拉取失败，将使用本地文件更新
    set GITHUB_SUCCESS=0
)
echo.

:: 3. 停止服务
echo [3/7] 停止现有服务...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8080 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
    echo   后端已停止
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5173 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
    echo   前端已停止
)
echo.

:: 4. 如果 GitHub 失败，使用本地文件更新
if %GITHUB_SUCCESS%==0 (
    echo [4/7] 使用本地文件更新...

    :: api 目录
    if exist "%SCRIPT_DIR%\update_api.zip" (
        echo   更新 api 目录...
        powershell -Command "Expand-Archive -Path '%SCRIPT_DIR%\update_api.zip' -DestinationPath 'backend\api' -Force"
    )

    :: models 目录
    if exist "%SCRIPT_DIR%\update_models.zip" (
        echo   更新 models 目录...
        powershell -Command "Expand-Archive -Path '%SCRIPT_DIR%\update_models.zip' -DestinationPath 'backend\models' -Force"
    )

    :: services 目录
    if exist "%SCRIPT_DIR%\update_services.zip" (
        echo   更新 services 目录...
        powershell -Command "Expand-Archive -Path '%SCRIPT_DIR%\update_services.zip' -DestinationPath 'backend\services' -Force"
    )

    :: 前端配置
    if exist "%SCRIPT_DIR%\vite.config.ts" (
        copy /Y "%SCRIPT_DIR%\vite.config.ts" "frontend\vite.config.ts" >nul
        echo   vite.config.ts 已更新
    )

    :: 前端源码
    if exist "%SCRIPT_DIR%\update_frontend_src.zip" (
        echo   更新前端源码...
        powershell -Command "Expand-Archive -Path '%SCRIPT_DIR%\update_frontend_src.zip' -DestinationPath 'frontend\src' -Force"
    )
) else (
    echo [4/7] 跳过（GitHub 代码已更新）
)
echo.

:: 5. 清除 Python 缓存
echo [5/7] 清除 Python 缓存...
for /r "backend" /d %%d in (__pycache__) do (
    rmdir /S /Q "%%d" 2>nul
)
echo   缓存已清除
echo.

:: 6. 启动后端
echo [6/7] 启动后端服务...
cd /d "%TARGET_DIR%\backend"
start "Backend" cmd /k "python -m uvicorn main:app --host 0.0.0.0 --port 8080"
timeout /t 3 /nobreak >nul
echo.

:: 7. 启动前端
echo [7/7] 启动前端服务...
cd /d "%TARGET_DIR%\frontend"
start "Frontend" cmd /k "npm run dev"
echo.

echo ========================================
echo   部署完成！
echo ========================================
echo.
echo   访问地址:
echo   - 后端 API: http://localhost:8080
echo   - API 文档: http://localhost:8080/docs
echo   - 前端页面: http://localhost:8080
echo.
echo   按任意键退出...
pause >nul
