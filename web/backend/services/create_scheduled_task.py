"""
创建 Windows 任务计划程序任务
使用 schtasks 命令
"""

import subprocess
import sys
import os
from pathlib import Path
import tempfile

def create_scheduled_task():
    """创建定时任务"""
    task_name = "TaskPlatform-钢筋价格抓取"
    script_dir = Path(__file__).parent.absolute()

    python_exe = sys.executable

    print("=" * 50)
    print("创建定时任务")
    print("=" * 50)
    print(f"任务名称: {task_name}")
    print(f"执行时间: 每天 08:00")
    print(f"Python: {python_exe}")
    print(f"脚本目录: {script_dir}")
    print()

    # 创建 Python 脚本文件
    py_script_content = f'''
import asyncio
import sys
import json
from pathlib import Path

script_dir = Path(r"{script_dir}")
sys.path.insert(0, str(script_dir))

from yantai_rebar_scraper import YantaiRebarScraper, save_to_excel

def main():
    try:
        scraper = YantaiRebarScraper()
        result = asyncio.run(scraper.fetch_async(force=True))

        if result.success and result.prices:
            save_to_excel(result)
            print(f"成功: {{len(result.prices)}} 条数据")

            record = {{
                "last_fetch": result.fetched_at,
                "success": True,
                "prices_count": len(result.prices),
                "region": "山东烟台"
            }}

            log_dir = script_dir / "logs"
            log_dir.mkdir(exist_ok=True)
            log_file = log_dir / "yantai_last_fetch.json"

            with open(log_file, "w", encoding="utf-8") as f:
                json.dump(record, f, ensure_ascii=False, indent=2)
        else:
            print(f"失败: {{result.error_message}}")
    except Exception as e:
        print(f"错误: {{e}}")

if __name__ == "__main__":
    main()
'''

    # 保存 Python 脚本到临时文件
    temp_py = Path(tempfile.gettempdir()) / "taskplatform_fetch.py"
    with open(temp_py, 'w', encoding='utf-8') as f:
        f.write(py_script_content)

    print(f"临时脚本: {temp_py}")
    print()

    # 使用 schtasks 创建任务
    # 格式: schtasks /create /tn "名称" /tr "执行命令" /sc daily /st 08:00 /f

    cmd = [
        'schtasks',
        '/create',
        '/tn', task_name,
        '/tr', f'"{python_exe}" "{temp_py}"',
        '/sc', 'daily',
        '/st', '08:00',
        '/f'
    ]

    print(f"执行命令: {' '.join(cmd)}")
    print()

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            print("=" * 50)
            print("任务创建成功!")
            print("=" * 50)
            print()
            print("管理命令:")
            print(f'  查看状态: schtasks /query /tn "{task_name}"')
            print(f'  手动运行: schtasks /run /tn "{task_name}"')
            print(f'  删除任务: schtasks /delete /tn "{task_name}" /f')
            print()
        else:
            print(f"创建失败: {result.stderr}")
            print(f"输出: {result.stdout}")

    except Exception as e:
        print(f"执行失败: {e}")


if __name__ == '__main__':
    create_scheduled_task()