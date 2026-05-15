#!/bin/bash

set -e

echo "=== TaskPlatform Backend Start ==="
echo "当前目录: $(pwd)"
echo ""

# 检查 Python
echo "1. 检查 Python 环境..."
which python3 && echo "✓ Python3 找到: $(which python3)" || which python && echo "✓ Python 找到: $(which python)"
which python3 || echo "✓ Python 找到: $(which python)"

# 检查虚拟环境
echo ""
echo "2. 检查虚拟环境..."
python -c "import sys; print('Python:', sys.executable); print('Version:', sys.version)" 2>&1

# 尝试导入 main 模块
echo ""
echo "3. 检查 main 模块..."
python -c "
try:
    import main
    print('✓ main 模块可以导入')
    print('app 变量存在:', hasattr(main, 'app'))
except ImportError as e:
    print('✗ main 模块错误:', e)
except Exception as e:
    print('✗ 其他错误:', e)
" 2>&1

# 检查 uvicorn
echo ""
echo "4. 检查 uvicorn..."
if which uvicorn >/dev/null 2>&1; then
    echo "✓ uvicorn 可用: $(which uvicorn)"
else
    echo "✗ uvicorn 未安装"
    python -c "import uvicorn; print('✓ uvicorn 可以导入: ' + uvicorn.__version__)" 2>&1 || echo "✗ uvicorn 错误"

# 检查 FastAPI
echo ""
python -c "
try:
    import fastapi
    print('✓ FastAPI 版本:', fastapi.__version__)
except ImportError:
    print('✗ FastAPI 未安装')
" 2>&1

echo ""
echo "=== 环境检查完成 ==="
echo ""

# 安装依赖
echo "5. 安装依赖..."
pip install --upgrade pip --quiet 2>/dev/null || true
pip install fastapi uvicorn[standard] --quiet 2>/dev/null || true

# 安装 Playwright
echo "6. 安装 Playwright 浏览器..."
python -m playwright install chromium --with-deps 2>/dev/null || echo "Playwright 安装命令失败"

# 尝试直接启动（不使用 -m）
echo ""
echo "7. 尝试启动 uvicorn..."
cd /app

# 方法1: 直接调用 uvicorn
if command -v uvicorn 2>/dev/null; then
    echo "使用命令行 uvicorn..."
    uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} &
    UVICORN_PID=$!
    echo "uvicorn PID: $UVICORN_PID"
else
    echo "uvicorn 未安装，尝试 python -m..."
    python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} &
    UVICORN_PID=$!
    echo "uvicorn PID: $UVICORN_PID"

sleep 5

# 检查进程
echo ""
echo "8. 检查进程状态..."
if [ -n "$UVICORN_PID" ] && [ "$UVICORN_PID" != "!" ]; then
    if ps -p $UVICORN_PID > /dev/null 2>&1; then
        echo "✓ uvicorn 正在运行 (PID: $UVICORN_PID)"
        echo "等待 30 秒..."
        sleep 30
        if ps -p $UVICORN_PID > /dev/null 2>&1; then
            echo "✓ uvicorn 仍然在运行"
            echo "服务器已启动成功！"
        else
            echo "✗ uvicorn 进程已退出"
            echo "退出码: $?"
        fi
    else
    echo "✗ uvicorn 未启动"
fi

echo ""
echo "=== 启动脚本完成 ==="
