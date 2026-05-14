#!/bin/bash

# 安装依赖
pip install -r requirements.txt

# 安装 playwright 浏览器
playwright install chromium --with-deps

# 使用 python -m 方式运行 uvicorn（不依赖 PATH）
python -m uvicorn main:app --host 0.0.0.0 --port $PORT