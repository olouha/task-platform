"""
批量抓取烟台价格数据
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
    except:
        return False
    finally:
        conn.close()


async def fetch_url(url, date_str, fetch_time):
    """抓取单个URL"""
    # 加载Cookie
    with open(COOKIE_FILE, 'r', encoding='utf-8') as f:
        cookies = json.load(f)

    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=False)
    context = await browser.new_context()
    await context.add_cookies(cookies)
    page = await context.new_page()

    try:
        await page.goto(url, wait_until='domcontentloaded', timeout=45000)
        await asyncio.sleep(5)

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
                            if save_price(date_str, {'name': name, 'spec': spec, 'type': row[2] if len(row)>2 else '', 'brand': row[3] if len(row)>3 else '', 'price': price}, fetch_time):
                                count += 1

    finally:
        await browser.close()
        await playwright.stop()

    return count


async def main():
    # 读取链接文件
    links_file = Path(__file__).parent / 'links_2024-07-01_2024-07-31.json'

    if not links_file.exists():
        print(f"找不到文件: {links_file}")
        return

    with open(links_file, 'r', encoding='utf-8') as f:
        links = json.load(f)

    print(f"读取到 {len(links)} 个链接")

    # 按日期去重（每个日期取最后一个）
    seen = {}
    for link in links:
        date = link['date']
        seen[date] = link

    unique = list(seen.values())
    print(f"去重后 {len(unique)} 个日期")

    # 批量抓取
    success = 0
    total_new = 0

    for i, link in enumerate(unique):
        url = link['url']
        date = link['date']
        match = re.search(r'/(\d{8})/', url)
        fetch_time = f"{match.group(1)[6:8]}:00:00" if match else "10:00:00"

        print(f"[{i+1}/{len(unique)}] {date}...", end=' ', flush=True)

        try:
            count = await fetch_url(url, date, fetch_time)
            if count > 0:
                print(f"+{count}条")
                success += 1
                total_new += count
            else:
                print(f"已有数据")
        except Exception as e:
            print(f"错误: {e}")

        await asyncio.sleep(2)

    print(f"\n完成! 成功: {success}/{len(unique)}, 新增: {total_new}条")

    # 显示数据库状态
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM rebar_prices')
    total = c.fetchone()[0]
    c.execute('SELECT COUNT(DISTINCT date) FROM rebar_prices')
    dates = c.fetchone()[0]
    conn.close()
    print(f"数据库: {total}条, {dates}天")


if __name__ == '__main__':
    asyncio.run(main())
