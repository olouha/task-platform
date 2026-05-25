"""
SQLite数据库服务 - 存储烟台钢筋价格历史数据
"""

import sqlite3
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

DB_PATH = Path(__file__).parent.parent / 'data' / 'yantai_prices.db'


def get_connection():
    """获取数据库连接"""
    os.makedirs(DB_PATH.parent, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """初始化数据库表"""
    conn = get_connection()
    cursor = conn.cursor()

    # 价格主表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS price_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            material_name TEXT NOT NULL,
            spec TEXT,
            brand TEXT,
            am_price REAL,
            pm_price REAL,
            price_change REAL,
            region TEXT DEFAULT '山东烟台',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(date, material_name, spec, brand)
        )
    ''')

    # 原始数据表（保存原始截图解析结果）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS raw_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            period TEXT NOT NULL,
            material_name TEXT,
            spec TEXT,
            brand TEXT,
            price REAL,
            raw_data TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 数据源表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS data_sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_type TEXT NOT NULL,
            source_url TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 创建索引
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_price_date ON price_records(date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_price_material ON price_records(material_name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_raw_date ON raw_prices(date)')

    conn.commit()
    conn.close()
    print(f'数据库初始化完成: {DB_PATH}')


def import_from_summary_excel(excel_path: str) -> int:
    """从汇总Excel导入数据"""
    import openpyxl

    conn = get_connection()
    cursor = conn.cursor()

    wb = openpyxl.load_workbook(excel_path, read_only=True)
    ws = wb.active

    count = 0
    skipped = 0

    for row in ws.iter_rows(min_row=4, values_only=True):
        if not row[0]:  # 日期为空
            continue

        date = str(row[0])
        material = row[1] or ''
        spec = row[2] or ''
        brand = row[3] or ''
        am_price = row[4] if row[4] else None
        pm_price = row[5] if row[5] else None
        price_change = row[6] if row[6] else None

        try:
            cursor.execute('''
                INSERT OR REPLACE INTO price_records
                (date, material_name, spec, brand, am_price, pm_price, price_change)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (date, material, spec, brand, am_price, pm_price, price_change))
            count += 1
        except Exception as e:
            skipped += 1
            print(f'导入失败: {date} {material} - {e}')

    conn.commit()
    conn.close()
    wb.close()

    print(f'导入完成: 成功 {count} 条, 跳过 {skipped} 条')
    return count


def get_all_prices(limit: int = None) -> List[Dict]:
    """获取所有价格数据"""
    conn = get_connection()
    cursor = conn.cursor()

    query = '''
        SELECT date, material_name, spec, brand, am_price, pm_price, price_change, region
        FROM price_records
        ORDER BY date DESC, material_name, spec
    '''
    if limit:
        query += f' LIMIT {limit}'

    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_prices_by_date(date: str) -> List[Dict]:
    """获取指定日期的价格"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT date, material_name, spec, brand, am_price, pm_price, price_change, region
        FROM price_records
        WHERE date = ?
        ORDER BY material_name, spec
    ''', (date,))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_prices_by_date_range(start_date: str, end_date: str) -> List[Dict]:
    """获取日期范围内的价格"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT date, material_name, spec, brand, am_price, pm_price, price_change, region
        FROM price_records
        WHERE date >= ? AND date <= ?
        ORDER BY date DESC, material_name, spec
    ''', (start_date, end_date))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_latest_price(material: str = None, spec: str = None) -> Optional[Dict]:
    """获取最新价格"""
    conn = get_connection()
    cursor = conn.cursor()

    if material and spec:
        cursor.execute('''
            SELECT date, material_name, spec, brand, am_price, pm_price
            FROM price_records
            WHERE material_name = ? AND spec = ?
            ORDER BY date DESC
            LIMIT 1
        ''', (material, spec))
    elif material:
        cursor.execute('''
            SELECT date, material_name, spec, brand, am_price, pm_price
            FROM price_records
            WHERE material_name = ?
            ORDER BY date DESC
            LIMIT 1
        ''', (material,))
    else:
        cursor.execute('''
            SELECT date, material_name, spec, brand, am_price, pm_price
            FROM price_records
            ORDER BY date DESC
            LIMIT 1
        ''')

    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


def get_statistics() -> Dict:
    """获取统计信息"""
    conn = get_connection()
    cursor = conn.cursor()

    # 总记录数
    cursor.execute('SELECT COUNT(*) FROM price_records')
    total_records = cursor.fetchone()[0]

    # 唯一日期数
    cursor.execute('SELECT COUNT(DISTINCT date) FROM price_records')
    total_dates = cursor.fetchone()[0]

    # 日期范围
    cursor.execute('SELECT MIN(date), MAX(date) FROM price_records')
    row = cursor.fetchone()
    min_date = row[0] if row else None
    max_date = row[1] if row else None

    # 材料种类
    cursor.execute('SELECT COUNT(DISTINCT material_name) FROM price_records')
    total_materials = cursor.fetchone()[0]

    conn.close()

    return {
        'total_records': total_records,
        'total_dates': total_dates,
        'date_range': f'{min_date} ~ {max_date}' if min_date else None,
        'total_materials': total_materials
    }


def add_price_record(date: str, material: str, spec: str, brand: str,
                     am_price: float = None, pm_price: float = None) -> bool:
    """添加价格记录"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO price_records
            (date, material_name, spec, brand, am_price, pm_price)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (date, material, spec, brand, am_price, pm_price))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f'添加记录失败: {e}')
        conn.close()
        return False


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print('用法: python sqlite_service.py <excel_path>')
        print('  初始化: python sqlite_service.py --init')
        print('  统计: python sqlite_service.py --stats')
        sys.exit(1)

    arg = sys.argv[1]

    if arg == '--init':
        init_database()
    elif arg == '--stats':
        stats = get_statistics()
        print(json.dumps(stats, ensure_ascii=False, indent=2))
    elif arg.endswith('.xlsx'):
        init_database()
        import_from_summary_excel(arg)
    else:
        print(f'未知参数: {arg}')