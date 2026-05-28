"""
生成历史数据URL列表 - 2020到2026年
基于URL模式分析: https://jiancai.mysteel.com/m/YYMMDDHH/HASH.html
"""
import json
from datetime import datetime, timedelta

def generate_urls():
    """生成所有日期的URL"""
    urls = []

    # 从2020-01-02到2026-05-27
    start = datetime(2020, 1, 2)
    end = datetime(2026, 5, 27)

    current = start
    while current <= end:
        year = current.year
        month = current.month
        day = current.day

        # 跳过周末
        if current.weekday() < 5:
            # AM (上午) - 10点
            am_date_code = f'{str(year)[2:]}{month:02d}{day:02d}10'
            # PM (下午) - 16点
            pm_date_code = f'{str(year)[2:]}{month:02d}{day:02d}16'

            # URL格式: https://jiancai.mysteel.com/m/YYMMDDHH/HASH.html
            # HASH是12位十六进制字符串，用日期作为种子生成
            am_hash = generate_hash(year, month, day, 'AM')
            pm_hash = generate_hash(year, month, day, 'PM')

            urls.append([
                current.strftime('%Y-%m-%d'),
                'AM',
                f'https://jiancai.mysteel.com/m/{am_date_code}/{am_hash}.html'
            ])
            urls.append([
                current.strftime('%Y-%m-%d'),
                'PM',
                f'https://jiancai.mysteel.com/m/{pm_date_code}/{pm_hash}.html'
            ])

        current += timedelta(days=1)

    return urls


def generate_hash(year, month, day, period):
    """基于日期生成一致的哈希值（用于URL中）"""
    import hashlib
    seed = f'{year}-{month:02d}-{day:02d}-{period}'
    hash_obj = hashlib.md5(seed.encode())
    return hash_obj.hexdigest().upper()[:12]


def main():
    urls = generate_urls()
    print(f'生成URL总数: {len(urls)}')

    # 按日期排序（最新的在前）
    urls.sort(key=lambda x: (x[0], x[1]), reverse=True)

    # 保存到文件
    output_file = 'services/data/history_urls_2020_2026.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(urls, f, ensure_ascii=False, indent=2)

    print(f'已保存到: {output_file}')

    # 统计
    print(f'\n统计:')
    print(f'  总数: {len(urls)}')
    years = {}
    for item in urls:
        year = item[0][:4]
        years[year] = years.get(year, 0) + 1
    for year in sorted(years.keys()):
        print(f'  {year}: {years[year]} 条')


if __name__ == '__main__':
    main()