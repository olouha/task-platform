"""
根据URL直接抓取烟台价格数据
用法: python fetch_from_url.py <URL>
"""
import asyncio
import re
import sqlite3
import sys
import json
from pathlib import Path
from playwright.async_api import async_playwright

DATA_DIR = Path(__file__).parent / 'data'
COOKIE_FILE = DATA_DIR / 'mysteel_cookies.json'
DB_FILE = DATA_DIR / 'yantai_rebar.db'


def parse_date_from_url(url):
    match = re.search(r'/(\d{2})(\d{2})(\d{2})\d{2}/', url)
    if match:
        return f"20{match.group(1)}-{match.group(2)}-{match.group(3)}"
    return None


def parse_time_from_url(url):
    match = re.search(r'/(\d{8})/', url)
    if match:
        hour = match.group(1)[6:8]
        return f"{hour}:00:00"
    return "10:00:00"


def save_price(date_str, price_data, fetch_time):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute('''INSERT OR IGNORE INTO rebar_prices
            (date, material_name, spec, material_type, brand, price, region, fetch_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
            (date_str, price_data['name'], price_data['spec'], price_data['type'],
             price_data['brand'], price_data['price'], '山东烟台', fetch_time))
        conn.commit()
        return c.rowcount > 0
    except Exception as e:
        print(f"      保存错误: {e}")
        return False
    finally:
        conn.close()


async def fetch_url(url):
    print(f"=" * 60)
    print(f"抓取URL: {url}")
    print(f"=" * 60)

    # 解析日期
    date_str = parse_date_from_url(url)
    fetch_time = parse_time_from_url(url)

    if not date_str:
        print(f"[错误] 无法解析日期")
        return 0

    print(f"日期: {date_str}, 时间: {fetch_time}")

    # 加载Cookie
    with open(COOKIE_FILE, 'r', encoding='utf-8') as f:
        cookies = json.load(f)

    print(f"Cookie数量: {len(cookies)}")

    # 启动浏览器
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=False)
    context = await browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        locale='zh-CN'
    )
    await context.add_cookies(cookies)

    page = await context.new_page()

    try:
        # 访问页面
        print(f"访问页面...")
        response = await page.goto(url, wait_until='domcontentloaded', timeout=45000)
        print(f"HTTP状态: {response.status}")

        # 等待加载
        print(f"等待数据加载...")
        await asyncio.sleep(5)

        # 提取数据
        print(f"提取数据...")
        rows = await page.evaluate('''() => {
            const tables = document.querySelectorAll('table');
            let results = [];
            tables.forEach(t => {
                t.querySelectorAll('tr').forEach(row => {
                    let cells = Array.from(row.querySelectorAll('td')).map(c => c.textContent.trim());
                    if (cells.length >= 5) results.push(cells);
                });
            });
            return results;
        }''')

        print(f"找到 {len(rows)} 行数据")

        # 解析价格
        count = 0
        for row in rows:
            if len(row) >= 5:
                name = str(row[0]).strip()
                spec = str(row[1]).strip()

                if name in ['高线', '螺纹钢', '盘螺', '圆钢'] and spec.startswith('Φ'):
                    match = re.search(r'\d{4}', str(row[4]))
                    if match:
                        price = int(match.group())
                        if 3000 < price < 10000:
                            price_data = {
                                'name': name,
                                'spec': spec,
                                'type': row[2] if len(row) > 2 else '',
                                'brand': row[3] if len(row) > 3 else '',
                                'price': price
                            }
                            if save_price(date_str, price_data, fetch_time):
                                count += 1

        print(f"\n结果: 新增 {count} 条数据")

    except Exception as e:
        print(f"[错误] {e}")

    finally:
        await browser.close()
        await playwright.stop()

    return count


async def main():
    if len(sys.argv) < 2:
        print("用法: python fetch_from_url.py <URL>")
        print("示例: python fetch_from_url.py https://jiancai.mysteel.com/m/26051510/19B77109BDE6183C.html")
        return

    url = sys.argv[1]
    await fetch_url(url)

    # 显示数据库状态
    print(f"\n数据库状态:")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM rebar_prices')
    total = c.fetchone()[0]
    c.execute('SELECT COUNT(DISTINCT date) FROM rebar_prices')
    dates = c.fetchone()[0]
    conn.close()
    print(f"  总数据量: {total} 条")
    print(f"  覆盖日期: {dates} 天")


if __name__ == '__main__':
    asyncio.run(main())
