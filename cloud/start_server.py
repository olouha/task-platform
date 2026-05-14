# 云端服务启动脚本
# 双击运行或命令行: python start_server.py

import os
import sys

# 确保路径正确
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

# 启动Flask服务
sys.path.insert(0, script_dir)
from server.cloud_server import app

if __name__ == '__main__':
    print("\n" + "=" * 50)
    print("TaskPlatform 云端服务器")
    print("=" * 50)
    print("\n本地访问: http://localhost:5000")
    print("局域网访问: http://<本机IP>:5000")
    print("\n按 Ctrl+C 停止服务")
    print("=" * 50 + "\n")

    app.run(host='0.0.0.0', port=5000, debug=False)