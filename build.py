"""
打包脚本 - 将程序打包为单个可执行文件
跨平台支持: Windows / Linux / Mac
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path


def build_exe():
    """构建可执行文件"""
    print("=" * 50)
    print("TaskPlatform 打包工具")
    print("=" * 50)

    # 检查 PyInstaller
    try:
        import PyInstaller
    except ImportError:
        print("\n正在安装 PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    # 清理之前的构建
    print("\n清理之前的构建...")
    for folder in ['build', 'dist']:
        folder_path = Path(folder)
        if folder_path.exists():
            if sys.platform == 'win32':
                subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', folder], shell=True, check=False)
            else:
                shutil.rmtree(folder, ignore_errors=True)

    # 构建命令
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=TaskPlatform",
        "--onefile",  # 单文件
        "--windowed",  # 无控制台窗口
        "--add-data=config;config",  # 包含配置目录
        "main.py"
    ]

    print("\n开始打包...")
    print(f"命令: {' '.join(cmd)}")

    try:
        subprocess.run(cmd, check=True)
        print("\n" + "=" * 50)
        print("打包成功!")
        print("可执行文件位置: dist/TaskPlatform.exe")
        print("=" * 50)
    except subprocess.CalledProcessError as e:
        print(f"\n打包失败: {e}")
        sys.exit(1)


if __name__ == '__main__':
    build_exe()