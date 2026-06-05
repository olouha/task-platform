"""
将造价参考价硬编码数据迁移到 Supabase
运行: python scripts/migrate_cost_reference_to_supabase.py
"""
import sys
sys.path.insert(0, 'web/backend')

import logging
from services.supabase_service import SupabaseService
from models.cost_reference import STEEL_REBAR_PRICES, CONCRETE_PRICES, MORTAR_PRICES

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

PERIOD = '2024年第一季度'
SOURCE = '烟台工程建设标准造价管理'


def migrate():
    logger.info("[migrate] 开始迁移造价参考价数据")
    supabase = SupabaseService()

    steel_items = [{'category': '钢筋', 'period': PERIOD, 'source': SOURCE, **item} for item in STEEL_REBAR_PRICES]
    concrete_items = [{'category': '混凝土', 'period': PERIOD, 'source': SOURCE, **item} for item in CONCRETE_PRICES]
    mortar_items = [{'category': '砂浆', 'period': PERIOD, 'source': SOURCE, **item} for item in MORTAR_PRICES]

    all_items = steel_items + concrete_items + mortar_items
    logger.info(f"[migrate] 共 {len(all_items)} 条数据")

    result = supabase.insert_cost_reference_prices(all_items)
    logger.info(f"[migrate] 迁移完成 | 成功={result['imported']} | 总数={result['total']} | 失败={len(result['errors'])}")


if __name__ == '__main__':
    migrate()