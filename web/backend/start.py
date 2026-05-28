#!/usr/bin/env python3
"""
TaskPlatform 启动脚本
Windows 虚拟桌面直接运行版本
"""

import os
import sys
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """主函数"""
    print("=" * 50)
    print("  TaskPlatform - 工程调差计算系统")
    print("=" * 50)
    print()

    # 获取项目根目录
    backend_dir = Path(__file__).parent
    project_root = backend_dir.parent

    print(f"项目目录: {project_root}")
    print(f"后端目录: {backend_dir}")
    print()

    # 检查环境变量文件
    env_file = backend_dir / ".env"
    if not env_file.exists():
        print("提示: 未找到 .env 文件，将使用默认值")
        print("可选环境变量:")
        print("  SUPABASE_URL   - Supabase 数据库地址")
        print("  SUPABASE_KEY   - Supabase API Key")
        print("  AI_API_URL     - AI 服务地址")
        print("  AI_API_KEY     - AI 服务密钥")
        print()

    # 切换到后端目录
    os.chdir(backend_dir)

    # 导入uvicorn
    try:
        import uvicorn
    except ImportError:
        print("错误: 未安装 uvicorn")
        print("请执行: pip install uvicorn[standard]")
        sys.exit(1)

    # 启动服务
    print("启动 FastAPI 服务...")
    print("API地址: http://localhost:8000")
    print("API文档: http://localhost:8000/docs")
    print()
    print("按 Ctrl+C 停止服务")
    print("-" * 50)

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )


if __name__ == "__main__":
    main()
