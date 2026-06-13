"""
检查烟台钢筋价格数据完整性
1. 检查日期缺失
2. 检查已有日期的数据量（是否满足111条）
"""
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

DATA_DIR = Path('services/data')
DB_FILE = DATA_DIR / 'yantai_rebar.db'


def check_data_integrity():
    print("=" * 60)
    print("烟台钢筋价格数据完整性检查")
    print("=" * 60)

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # 1. 获取所有日期及数据量
    print("\n[1/3] 检查已有日期及数据量...")
    c.execute('''
        SELECT date, COUNT(DISTINCT material_name || spec || brand || price) as count
        FROM rebar_prices
        GROUP BY date
        ORDER BY date DESC
    ''')

    date_counts = {}
    for row in c.fetchall():
        date_counts[row[0]] = row[1]

    print(f"\n已有 {len(date_counts)} 个日期的数据:")
    for date, count in sorted(date_counts.items(), reverse=True):
        status = "[OK]" if count >= 111 else "[不足]"
        print(f"  {date}: {count:3d} 条 {status}")

    # 2. 计算日期范围（最近30天）
    print("\n[2/3] 检查日期缺失...")
    today = datetime.now().date()
    start_date = today - timedelta(days=30)

    all_dates = []
    current = start_date
    while current <= today:
        all_dates.append(current.strftime('%Y-%m-%d'))
        current += timedelta(days=1)

    missing_dates = [d for d in all_dates if d not in date_counts]

    print(f"\n最近30天日期范围: {start_date} ~ {today}")
    print(f"缺失日期数量: {len(missing_dates)}")

    if missing_dates:
        print(f"\n缺失日期列表:")
        for d in missing_dates[:10]:
            print(f"  - {d}")
        if len(missing_dates) > 10:
            print(f"  ... 还有 {len(missing_dates) - 10} 个日期")

    # 3. 检查已有日期的数据质量
    print("\n[3/3] 数据质量检查...")

    # 统计各日期的材料类型分布
    c.execute('''
        SELECT date, material_name, COUNT(*) as count
        FROM rebar_prices
        GROUP BY date, material_name
        ORDER BY date DESC, material_name
    ''')

    material_by_date = defaultdict(lambda: defaultdict(int))
    for date, material, count in c.fetchall():
        material_by_date[date][material] = count

    print("\n各日期的材料类型分布:")
    for date in sorted(material_by_date.keys(), reverse=True)[:10]:
        materials = material_by_date[date]
        total = sum(materials.values())
        status = "[OK]" if total >= 111 else "[不足]"
        print(f"\n  {date} (总计: {total} {status}):")
        for material, count in materials.items():
            print(f"    - {material}: {count} 条")

    # 4. 检查品牌覆盖
    print("\n[4/4] 品牌覆盖检查...")
    c.execute('''
        SELECT DISTINCT brand
        FROM rebar_prices
        WHERE brand IS NOT NULL AND brand != ''
        ORDER BY brand
    ''')

    brands = [row[0] for row in c.fetchall()]
    print(f"共有 {len(brands)} 个品牌:")
    for brand in brands[:10]:
        print(f"  - {brand}")
    if len(brands) > 10:
        print(f"  ... 还有 {len(brands) - 10} 个品牌")

    # 5. 总结
    print("\n" + "=" * 60)
    print("总结")
    print("=" * 60)
    print(f"已有日期: {len(date_counts)} 个")
    print(f"缺失日期: {len(missing_dates)} 个")
    print(f"数据充足日期: {sum(1 for c in date_counts.values() if c >= 111)} 个")
    print(f"数据不足日期: {sum(1 for c in date_counts.values() if c < 111)} 个")

    conn.close()

    return {
        'date_counts': date_counts,
        'missing_dates': missing_dates,
        'material_by_date': dict(material_by_date),
        'brands': brands
    }


if __name__ == '__main__':
    result = check_data_integrity()
