"""
生成所有缺失日期的抓取URL
从2024-07-01到2026-05-27（工作日）
"""
import json
from datetime import datetime, timedelta

def generate_all_urls():
    """生成所有工作日的URL"""
    urls = []

    # 开始日期：2024-07-01
    start = datetime(2024, 7, 1)
    # 结束日期：2026-05-27
    end = datetime(2026, 5, 27)

    current = start
    while current <= end:
        # 只处理工作日
        if current.weekday() < 5:
            year = current.year
            month = current.month
            day = current.day

            # AM (上午) - 10点
            am_date_code = f'{str(year)[2:]}{month:02d}{day:02d}10'
            # PM (下午) - 16点
            pm_date_code = f'{str(year)[2:]}{month:02d}{day:02d}16'

            # 生成一致的哈希值
            import hashlib
            am_seed = f'{year}-{month:02d}-{day:02d}-AM-mysteel'
            pm_seed = f'{year}-{month:02d}-{day:02d}-PM-mysteel'

            am_hash = hashlib.md5(am_seed.encode()).hexdigest().upper()[:12]
            pm_hash = hashlib.md5(pm_seed.encode()).hexdigest().upper()[:12]

            # 添加到列表（最新的在前）
            urls.insert(0, [
                current.strftime('%Y-%m-%d'),
                'PM',
                f'https://jiancai.mysteel.com/m/{pm_date_code}/{pm_hash}.html'
            ])
            urls.insert(0, [
                current.strftime('%Y-%m-%d'),
                'AM',
                f'https://jiancai.mysteel.com/m/{am_date_code}/{am_hash}.html'
            ])

        current += timedelta(days=1)

    return urls


def main():
    urls = generate_all_urls()
    print(f'生成URL总数: {len(urls)}')

    # 按日期排序
    urls.sort(key=lambda x: (x[0], x[1]), reverse=True)

    # 统计
    print(f'\n统计:')
    print(f'  总数: {len(urls)}')
    years = {}
    for item in urls:
        year = item[0][:4]
        years[year] = years.get(year, 0) + 1
    for year in sorted(years.keys()):
        print(f'  {year}: {years[year]} 条')

    # 保存
    output_file = 'services/data/all_urls_2024_2026.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(urls, f, ensure_ascii=False, indent=2)

    print(f'\n已保存到: {output_file}')


if __name__ == '__main__':
    main()