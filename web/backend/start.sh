#!/bin/bash
set -e

echo "=== TaskPlatform Backend ==="

# 检查配置
if [ -f "services/data/mysteel_config.json" ]; then
    echo "✓ 配置文件存在"
    python -c "import json; config = json.load(open('services/data/mysteel_config.json', 'r')); print(f'用户名: {config.get(\\\"username\\\", \\\"\\\")}')"
else
    echo "✗ 配置文件不存在"

# 安装依赖
echo "安装 Python 依赖..."
pip install fastapi uvicorn[standard] openpyxl pydantic --quiet

# 安装 Playwright 浏览器
echo "安装 Playwright..."
python -m playwright install chromium --with-deps --quiet

# 检查安装
if command -v uvicorn >/dev/null 2>&1; then
    echo "✓ uvicorn 安装成功"
else
    echo "✗ uvicorn 未安装"

if python -c "import playwright" >/dev/null 2>&1; then
    echo "✓ Playwright 安装成功"
else
    echo "✗ Playwright 未安装"

# 启动服务
echo "启动服务..."
exec python -m uvicorn main:app --host 0.0.0.0 --port 8000
