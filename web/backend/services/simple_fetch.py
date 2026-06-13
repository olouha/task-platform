"""
简化的批量抓取脚本
"""
import asyncio
import json
import re
import sqlite3
from pathlib import Path
from playwright.async_api import async_playwright

DATA_DIR = Path(__file__).parent / 'data'
COOKIE_FILE = DATA_DIR / 'mysteel_cookies.json'
DB_FILE = DATA_DIR / 'yantai_rebar.db'
LINKS_FILE = DATA_DIR / 'yantai_links.json'


def get_db_count():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM rebar_prices')
    total = c.fetchone()[0]
    c.execute('SELECT COUNT(DISTINCT date) FROM rebar_prices')
    dates = c.fetchone()[0]
    conn.close()
    return total, dates


def save_price(date_str, price_data):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute('''INSERT OR IGNORE INTO rebar_prices
            (date, material_name, spec, material_type, brand, price, region, fetch_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
            (date_str, price_data['name'], price_data['spec'], price_data['type'],
             price_data['brand'], price_data['price'], '山东烟台', price_data.get('time', '10:00:00')))
        return c.rowcount > 0
    except:
        return False
    finally:
        conn.close()


async def fetch_one(url, date):
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=False)

    with open(COOKIE_FILE, 'r') as f:
        cookies = json.load(f)

    context = await browser.new_context()
    await context.add_cookies(cookies)
    page = await context.new_page()

    print(f"访问: {url}")
    await page.goto(url, wait_until='domcontentloaded', timeout=30000)
    await asyncio.sleep(5)

    # 提取数据
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
                        if save_price(date, {'name': name, 'spec': spec, 'type': row[2], 'brand': row[3], 'price': price}):
                            count += 1

    await browser.close()
    await playwright.stop()
    return count


async def main():
    with open(LINKS_FILE, 'r', encoding='utf-8') as f:
        raw = json.load(f)

    links = []
    for l in raw:
        url = l.get('url') or l.get('href', '')
        m = re.search(r'/(\d{2})(\d{2})(\d{2})\d{2}/', url)
        if m:
            date = f"20{m.group(1)}-{m.group(2)}-{m.group(3)}"
            links.append((url, date))

    before = get_db_count()
    print(f"开始前: {before[0]}条, {before[1]}天")

    success = 0
    for i, (url, date) in enumerate(links[:20]):  # 先测试20个
        print(f"[{i+1}] {date}")
        n = await fetch_one(url, date)
        if n > 0:
            success += 1
            print(f"    新增{n}条")
        await asyncio.sleep(3)

    after = get_db_count()
    print(f"\n完成后: {after[0]}条, {after[1]}天")
    print(f"新增: {after[0]-before[0]}条, 成功{success}天")


if __name__ == '__main__':
    asyncio.run(main())
