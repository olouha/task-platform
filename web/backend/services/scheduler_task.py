"""
山东烟台钢筋价格定时抓取任务
每天自动执行，登录并抓取最新价格
"""

import asyncio
import logging
import sys
import os
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_scheduled_task():
    """执行定时抓取任务"""
    print("=" * 60)
    print(f"定时任务开始 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    try:
        from services.yantai_rebar_scraper import YantaiRebarScraper, save_to_excel, get_sheet_names

        scraper = YantaiRebarScraper(
            username="M6616592358",
            password="mysteel573005"
        )

        # 执行抓取（强制刷新）
        result = scraper.fetch(force=True)

        if result.success:
            print(f"\n抓取成功！共 {len(result.prices)} 条数据")

            # 保存到Excel
            if save_to_excel(result):
                print(f"已保存到Excel，Sheet: {get_sheet_names()}")

            # 打印统计
            summary = {}
            for p in result.prices:
                name = p.material_name
                if name not in summary:
                    summary[name] = {'count': 0, 'brands': set()}
                summary[name]['count'] += 1
                summary[name]['brands'].add(p.brand)

            print("\n品名统计:")
            for name, info in summary.items():
                print(f"  - {name}: {info['count']}条, 品牌: {', '.join(sorted(info['brands']))}")

            logger.info(f"定时任务完成 - 抓取 {len(result.prices)} 条数据")
            return True
        else:
            print(f"\n抓取失败: {result.error_message}")
            logger.error(f"定时任务失败: {result.error_message}")
            return False

    except Exception as e:
        print(f"\n任务异常: {e}")
        logger.error(f"定时任务异常: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    # 检查是否是强制执行
    force = '--force' in sys.argv

    if force:
        # 强制执行（忽略每日限制）
        run_scheduled_task()
    else:
        # 正常执行
        run_scheduled_task()