"""
探索烟台历史数据的URL模式
尝试从已知URL推断更早期的数据访问方式
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright
import re

DATA_DIR = Path('services/data')
COOKIE_FILE = DATA_DIR / 'mysteel_cookies.json'


def load_cookies():
    if COOKIE_FILE.exists():
        with open(COOKIE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


async def explore_url_patterns():
    """探索URL模式"""
    print("=" * 80)
    print("探索烟台历史数据URL模式")
    print("=" * 80)

    cookies = load_cookies()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            locale='zh-CN'
        )

        if cookies:
            await context.add_cookies(cookies)

        page = await context.new_page()

        # 已知的早期URL
        known_urls = [
            ('2026-04-24', 'https://jiancai.mysteel.com/m/26042410/E0D5A0D891C7BC12.html'),
            ('2026-04-20', 'https://jiancai.mysteel.com/m/26042010/'),  # 尝试构造
            ('2026-04-15', 'https://jiancai.mysteel.com/m/26041510/'),
            ('2026-04-10', 'https://jiancai.mysteel.com/m/26041010/'),
            ('2026-04-05', 'https://jiancai.mysteel.com/m/26040510/'),
        ]

        # 尝试访问更早的日期
        test_dates = []
        current_date = Path('2026-04-01')
        # 生成3月的日期
        for day in range(1, 32):
            test_dates.append(f'2026-03-{day:02d}')

        print(f"\n[测试] 尝试访问3月日期...")

        working_urls = []

        for date in test_dates[:10]:  # 先测试前10个
            yy = date[2:4]
            mm = date[5:7]
            dd = date[8:10]

            # 尝试构造URL
            test_url = f'https://jiancai.mysteel.com/m/{yy}{mm}{dd}10/'

            print(f"\n  测试: {date} -> {test_url}")

            try:
                await page.goto(test_url, wait_until='domcontentloaded', timeout=10000)
                await asyncio.sleep(1)

                current_url = page.url
                print(f"    跳转: {current_url}")

                # 如果URL不同，说明重定向了
                if current_url != test_url and 'mysteel.com/m/' in current_url:
                    working_urls.append((date, current_url))
                    print(f"    OK 找到有效URL!")

            except:
                print(f"    X 超时或错误")

        print(f"\n[结果] 找到 {len(working_urls)} 个有效URL")
        for date, url in working_urls:
            print(f"  {date}: {url}")

        # 保存结果
        with open('early_working_urls.json', 'w', encoding='utf-8') as f:
            json.dump(working_urls, f, ensure_ascii=False, indent=2)

        await browser.close()

    print("\n" + "=" * 80)
    print("探索完成")
    print("=" * 80)


if __name__ == '__main__':
    try:
        asyncio.run(explore_url_patterns())
    except KeyboardInterrupt:
        print("\n\n[中断]")
