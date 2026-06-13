@echo off
chcp 65001 > nul
title TaskPlatform Windows 部署

echo ========================================
echo   TaskPlatform Windows 部署脚本
echo ========================================
echo.

REM 配置
set APP_DIR=C:\taskplatform
set ARCHIVE=%~dp0task-platform-deploy.tar.gz

REM 检查压缩包
if not exist "%ARCHIVE%" (
    echo 错误: 找不到 task-platform-deploy.tar.gz
    echo 请将压缩包放在当前目录: %~dp0
    pause
    exit /b 1
)

echo [1/6] 创建目录结构...
if not exist "%APP_DIR%" mkdir "%APP_DIR%"
if not exist "%APP_DIR%\backend" mkdir "%APP_DIR%\backend"
if not exist "%APP_DIR%\frontend" mkdir "%APP_DIR%\frontend"
if not exist "%APP_DIR%\logs" mkdir "%APP_DIR%\logs"

echo [2/6] 解压文件...
cd /d "%APP_DIR%"
tar -xzvf "%ARCHIVE%" -C "%APP_DIR%" --strip-components=1
if errorlevel 1 (
    echo 错误: 解压失败，请确保安装了 tar 工具
    pause
    exit /b 1
)

echo [3/6] 检查 Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)

echo [4/6] 安装 Python 依赖...
cd /d "%APP_DIR%\backend"
pip install -r requirements.txt
if errorlevel 1 (
    echo 警告: 依赖安装可能有问题，请检查
)

echo [5/6] 创建环境变量文件...
if not exist "%APP_DIR%\backend\.env" (
    (
        echo # 数据库配置
        echo SUPABASE_URL=https://your-project.supabase.co
        echo SUPABASE_KEY=your-anon-key
        echo.
        echo # AI服务配置
        echo AI_API_URL=https://api.openai.com/v1
        echo AI_API_KEY=sk-your-key
        echo.
        echo # 应用配置
        echo LOG_LEVEL=INFO
    ) > "%APP_DIR%\backend\.env"
    echo 已创建 .env 文件，请配置实际值
)

echo [6/6] 创建启动脚本...
(
    echo @echo off
    echo cd /d "%APP_DIR%\backend"
    echo python -m uvicorn main:app --host 0.0.0.0 --port 8000
) > "%APP_DIR%\start.bat"

echo.
echo ========================================
echo   部署完成！
echo ========================================
echo.
echo 应用目录: %APP_DIR%
echo 启动方式: 双击运行 %APP_DIR%\start.bat
echo 或者使用命令:
echo   cd %APP_DIR%\backend
echo   python -m uvicorn main:app --host 0.0.0.0 --port 8000
echo.
echo 访问地址: http://服务器IP:8000
echo API文档: http://服务器IP:8000/docs
echo.
pause
