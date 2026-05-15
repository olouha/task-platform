#!/bin/bash
set -e

echo "=== TaskPlatform Backend Start (Simple Version) ==="

# 升级 pip
echo "Step 1: Upgrading pip..."
pip install --upgrade pip --quiet

# 只安装必要的依赖
echo "Step 2: Installing minimal dependencies..."
pip install fastapi uvicorn[standard] openpyxl pydantic --quiet

# 检查配置文件
echo "Step 3: Checking configuration..."
if [ -f "services/data/mysteel_config.json" ]; then
    echo "✓ 配置文件存在"
    python -c "import json; config = json.load(open('services/data/mysteel_config.json', 'r')); print(f'用户: {config.get(\"username\")}')"
else
    echo "✗ 配置文件缺失，将使用默认凭据"

# 检查 Cookie 文件
echo "Step 4: Checking cookies..."
if [ -f "services/data/mysteel_cookies.json" ]; then
    echo "✓ Cookie 文件存在 ($(stat -f%m 'services/data/mysteel_cookies.json' bytes))"
else
    echo "✗ Cookie 文件不存在，需要先登录"

# 使用已保存的价格文件（如果有）
if [ -f "services/data/山东烟台钢筋价格.xlsx" ]; then
    echo "✓ 价格文件存在"
    # 复制今天的价格数据（如果需要的话）
    # cp "services/data/山东烟台钢筋价格.xlsx" "services/data/山东烟台钢筋价格_20260514.xlsx" 2>/dev/null
else
    echo "✗ 价格文件不存在"

# 启动服务
echo "Step 5: Starting FastAPI..."
cd /app

# 使用简单命令直接运行（避免 Playwright 安装问题）
# 先尝试 uvicorn
if command -v uvicorn >/dev/null 2>&1; then
    echo "Using uvicorn from PATH"
    exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
elif python -m uvicorn >/dev/null 2>&1; then
    echo "Using uvicorn via python -m"
    exec python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
else
    echo "✗ uvicorn not found, trying direct python..."
    exec python main:app --host 0.0.0.0 --port ${PORT:-8000}