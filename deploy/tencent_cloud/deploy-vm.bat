@echo off
chcp 65001 >nul
echo ========================================
echo   TaskPlatform 一键部署脚本
echo ========================================
echo.

REM 检查压缩包
if not exist "task-platform-deploy.tar.gz" (
    echo [错误] 找不到 task-platform-deploy.tar.gz
    echo 请确保压缩包在当前目录
    pause
    exit /b 1
)

echo [1/5] 解压文件...
tar -xzvf task-platform-deploy.tar.gz -C C:\
if errorlevel 1 (
    echo [错误] 解压失败
    pause
    exit /b 1
)
echo ✓ 解压完成

echo.
echo [2/5] 进入后端目录...
cd /d C:\web\backend

echo.
echo [3/5] 检查 Python...
python --version
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)

echo.
echo [4/5] 安装依赖...
pip install -r requirements.txt
if errorlevel 1 (
    echo [警告] 依赖安装可能有问题
)

echo.
echo [5/5] 配置环境变量...
if not exist .env (
    copy .env.example .env
    echo ✓ 已创建 .env 文件
    echo   请编辑 .env 填写实际配置
)

echo.
echo ========================================
echo   部署完成！
echo ========================================
echo.
echo 启动服务:
echo   cd C:\web\backend
echo   python -m uvicorn main:app --host 0.0.0.0 --port 8000
echo.
echo 访问地址: http://YOUR_IP:8000/docs
echo.
pause
