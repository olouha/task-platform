#!/bin/bash
set -e

echo "=== Starting deployment ==="

echo "Step 1: Upgrading pip..."
pip install --upgrade pip --quiet

echo "Step 2: Installing fastapi and uvicorn..."
pip install fastapi "uvicorn[standard]" --quiet

echo "Step 3: Installing other dependencies..."
pip install playwright openpyxl pydantic --quiet

echo "Step 4: Installing playwright browsers..."
python -m playwright install chromium --with-deps 2>/dev/null || true

echo "Step 5: Checking uvicorn..."
which python
python -c "import uvicorn; print('uvicorn version:', uvicorn.__version__)"

echo "Step 6: Starting server..."
cd /app
python -m uvicorn main:app --host 0.0.0.0 --port $PORT