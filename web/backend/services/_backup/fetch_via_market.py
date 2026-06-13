"""
从市场页面抓取烟台价格数据
通过市场页面找到每个日期的烟台价格链接
"""
import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, '.')

from playwright.async_api import async_playwright
import sqlite3

DATA_DIR = Path('web/backend/services/data')
DB_FILE = DATA_DIR / 'yantai_rebar.db'
COOKIE_FILE = DATA_DIR / 'mysteel_cookies_new.json'
USERNAME = 'M6616592358'
PASSWORD = 'panhui199261'


def save_to_database(date: str, fetch_time: str, prices: list) -> int:
    """保存到数据库"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    inserted = 0
    for p in prices:
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO rebar_prices
                (date, fetch_time, material_name, spec, material_type, brand, price, region)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (date, fetch_time, p['material_name'], p['spec'],
                  p.get('material_type', ''), p.get('brand', ''),
                  p['price'], '山东烟台'))
            if cursor.rowcount > 0:
                inserted += 1
        except:
            pass
    conn.commit()
    conn.close()
    return inserted


def get_existing_dates() -> set:
    """获取已有日期"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT date FROM rebar_prices')
    dates = set(row[0] for row in cursor.fetchall())
    conn.close()
    return dates


def get_missing_dates(start_date: str, end_date: str) -> list:
    """获取缺失日期"""
    existing = get_existing_dates()
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    missing = []
    current = start
    while current <= end:
        if current.weekday() < 5:
            date_str = current.strftime('%Y-%m-%d')
            if date_str not in existing:
                missing.append(date_str)
        current += timedelta(days=1)
    return missing


async def fetch_via_market_page(page, date: str, period: str) -> tuple:
    """通过市场页面抓取指定日期的数据"""
    # 生成要搜索的日期字符串
    date_str = date.replace('-', '')
    yymmdd = date_str[2:]  # YYMMDD

    # 不同时间的URL
    hour = '10' if period == 'AM' else '16'

    print(f"  [{period}] 访问市场页面搜索...")

    try:
        # 访问山东/烟台市场页面
        await page.goto('https://jiancai.mysteel.com/market/pa228aa010101a0a01010205aaaa1.html',
                       wait_until='domcontentloaded', timeout=60000)
        await page.wait_for_timeout(5000)

        # 查找所有包含目标日期的链接
        links = await page.evaluate(f'''() => {{
            const targetDate = "{date_str}";
            const links = [];
            document.querySelectorAll('a[href]').forEach(a => {{
                const href = a.href;
                const text = a.textContent.trim();
                // 查找包含目标日期的链接
                if (href.includes("{yymmdd}") && href.includes('/m/') && text.includes('烟台')) {{
                    links.push({{text, href}});
                }}
            }});
            return links;
        }}''')

        if links:
            # 访问第一个匹配的链接
            link = links[0]
            print(f"  找到链接: {link['text']}")
            print(f"  URL: {link['href']}")

            await page.goto(link['href'], wait_until='domcontentloaded', timeout=60000)
            await page.wait_for_timeout(5000)

            # 截图
            screenshot_path = DATA_DIR / 'screenshots' / f"{date_str}_{period}.png"
            await page.screenshot(path=str(screenshot_path), full_page=True)

            # 提取数据
            data = await page.evaluate('''() => {{
                const tables = document.querySelectorAll('table');
                const results = [];
                tables.forEach((table) => {{
                    const rows = table.querySelectorAll('tr');
                    rows.forEach((row) => {{
                        const cells = row.querySelectorAll('td, th');
                        const rowData = [];
                        cells.forEach(c => rowData.push(c.textContent.trim()));
                        if (rowData.length >= 5) results.push(rowData);
                    }});
                }});
                return results;
            }}''')

            prices = []
            for row in data:
                material_name = str(row[0]).strip()
                spec = str(row[1]).strip()
                material_type = str(row[2]).strip() if len(row) > 2 else ''
                brand = str(row[3]).strip() if len(row) > 3 else ''
                price_str = str(row[4]).strip() if len(row) > 4 else ''

                valid_names = ['高线', '螺纹钢', '盘螺', '圆钢']
                if material_name in valid_names and spec.startswith('Φ') and price_str.isdigit():
                    try:
                        price = int(price_str)
                        if price > 0:
                            prices.append({
                                'material_name': material_name,
                                'spec': spec,
                                'material_type': material_type,
                                'brand': brand,
                                'price': price
                            })
                    except:
                        pass

            if prices:
                fetch_time = '09:00' if period == 'AM' else '15:00'
                inserted = save_to_database(date, fetch_time, prices)
                print(f"  提取 {len(prices)} 条，新增 {inserted} 条")
                return inserted, str(screenshot_path)

        print(f"  未找到{date}的链接")
        return 0, ""

    except Exception as e:
        print(f"  错误: {e}")
        return 0, ""


async def main():
    """主函数"""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--start', '-s', default='2024-01-01')
    parser.add_argument('--end', '-e', default='2024-06-28')
    parser.add_argument('--interval', '-i', type=int, default=5)
    args = parser.parse_args()

    missing = get_missing_dates(args.start, args.end)
    if not missing:
        print("没有缺失日期")
        return

    print(f"需要抓取 {len(missing)} 个工作日")
    print(f"日期范围: {missing[0]} 至 {missing[-1]}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 3000},
            locale='zh-CN'
        )
        page = await context.new_page()

        # 登录
        print("\n1. 登录...")
        await page.goto('https://passport.mysteel.com/', wait_until='networkidle', timeout=60000)
        await page.wait_for_timeout(3000)

        try:
            await page.click('.form-tab-account', timeout=5000)
        except:
            pass

        await page.evaluate(f'''() => {{
            const inputs = document.querySelectorAll('input');
            for (const inp of inputs) {{
                const ph = inp.placeholder || '';
                if (ph.includes('用户名')) inp.value = '{USERNAME}';
                if (ph.includes('密码') && inp.type === 'password') inp.value = '{PASSWORD}';
            }}
        }}''')
        await page.wait_for_timeout(500)

        try:
            checkbox = await page.query_selector('input[type="checkbox"]')
            if checkbox and not await checkbox.is_checked():
                checkbox.click()
        except:
            pass

        try:
            await page.click('.form-button-login', timeout=5000)
        except:
            pass

        print("等待登录...")
        await page.wait_for_timeout(10000)
        print(f"当前URL: {page.url}")

        # 保存Cookie
        cookies = await context.cookies()
        with open(COOKIE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cookies, f, ensure_ascii=False)

        print("\n2. 开始抓取...")
        total_inserted = 0

        for i, date in enumerate(missing[:10]):  # 先测试10天
            print(f"\n[{i+1}/{len(missing[:10])}] {date}")

            inserted_am, _ = await fetch_via_market_page(page, date, 'AM')
            await page.wait_for_timeout(args.interval * 1000)

            inserted_pm, _ = await fetch_via_market_page(page, date, 'PM')

            total_inserted += inserted_am + inserted_pm

            if i < len(missing[:10]) - 1:
                await page.wait_for_timeout(args.interval * 1000)

        await browser.close()

        print("\n" + "=" * 60)
        print(f"抓取完成！新增 {total_inserted} 条记录")
        print("=" * 60)


if __name__ == '__main__':
    asyncio.run(main())