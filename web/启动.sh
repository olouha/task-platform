#!/bin/bash
chcp 65001 >nul 2>&1
echo "===================================="
echo "  TaskPlatform Web 启动器 (Linux/Mac)"
echo "===================================="
echo ""

# 检查依赖
command -v node >/dev/null 2>&1 || { echo "[错误] 未安装 Node.js"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "[错误] 未安装 Python"; exit 1; }

echo "[1/4] 检查依赖..."

# 创建 Python 虚拟环境
if [ ! -d "backend/venv" ]; then
    echo "[后端] 创建虚拟环境..."
    python3 -m venv backend/venv
fi

echo "[后端] 安装依赖..."
source backend/venv/bin/activate
pip install -r backend/requirements.txt -q

echo "[前端] 安装依赖..."
cd frontend && npm install -q && cd ..

echo ""
echo "===================================="
echo "  启动服务"
echo "===================================="
echo ""

# 启动后端
echo "[后端] 启动 FastAPI (端口 8000)..."
cd backend && source ../backend/venv/bin/activate && uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!

# 等待后端启动
sleep 3

# 启动前端
echo "[前端] 启动 React (端口 3000)..."
cd frontend && npm run dev &
FRONTEND_PID=$!

echo ""
echo "===================================="
echo "  服务已启动"
echo "===================================="
echo ""
echo "  后端 API: http://localhost:8000"
echo "  前端界面: http://localhost:3000"
echo ""
echo "  按 Ctrl+C 停止所有服务"

# 等待信号
wait