#!/bin/bash

# 升级 pip
pip install --upgrade pip

# 安装所有依赖（包括 uvicorn）
pip install fastapi uvicorn[standard] playwright openpyxl pydantic

# 安装 playwright 浏览器
python -m playwright install chromium

# 使用 python -m 方式运行
python -m uvicorn main:app --host 0.0.0.0 --port $PORT