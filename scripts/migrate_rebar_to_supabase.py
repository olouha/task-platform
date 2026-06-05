"""
将 SQLite yantai_rebar.db 迁移到 Supabase
运行: python scripts/migrate_rebar_to_supabase.py
"""
import sys
sys.path.insert(0, 'web/backend')

import logging
from pathlib import Path
from services.supabase_service import SupabaseService

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_FILE = Path(__file__).parent.parent / 'web' / 'backend' / 'data' / 'yantai_rebar.db'


def migrate():
    import sqlite3
    logger.info(f"[migrate] 开始迁移 | DB={DB_FILE}")

    if not DB_FILE.exists():
        logger.error(f"[migrate] 数据库文件不存在: {DB_FILE}")
        return

    supabase = SupabaseService()
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 获取所有数据
    cursor.execute('SELECT date, fetch_time, material_name, spec, material_type, brand, price, region FROM rebar_prices ORDER BY date')
    rows = cursor.fetchall()
    conn.close()

    logger.info(f"[migrate] 读取到 {len(rows)} 条记录")

    # 批量插入
    BATCH = 100
    total_imported = 0
    total_errors = 0

    for i in range(0, len(rows), BATCH):
        batch = rows[i:i+BATCH]
        prices = [dict(row) for row in batch]
        result = supabase.insert_rebar_prices(prices)
        total_imported += result['imported']
        total_errors += len(result['errors'])
        logger.info(f"[migrate] 批次 {i//BATCH+1} | imported={result['imported']} | errors={len(result['errors'])}")

    logger.info(f"[migrate] 迁移完成 | 成功={total_imported} | 总数={len(rows)} | 失败={total_errors}")


if __name__ == '__main__':
    migrate()