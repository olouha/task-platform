#!/bin/bash
set -e

echo "=== Starting deployment ==="

# 检查 Python 版本
echo "Python version:"
python --version || python3 --version

echo "Step 1: Upgrading pip..."
python -m pip install --upgrade pip --quiet || python3 -m pip install --upgrade pip --quiet

echo "Step 2: Installing fastapi and uvicorn..."
python -m pip install fastapi "uvicorn[standard]" --quiet || python3 -m pip install fastapi "uvicorn[standard]" --quiet

echo "Step 3: Verifying installation..."
python -c "import uvicorn; print('uvicorn installed successfully!')" 2>/dev/null || python3 -c "import uvicorn; print('uvicorn installed successfully!')"

echo "Step 4: Starting server..."
python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} || python3 -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}