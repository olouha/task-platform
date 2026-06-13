"""
直接抓取指定URL的烟台钢筋价格
"""
import asyncio
from playwright.async_api import async_playwright
import json
import re
import sqlite3
from pathlib import Path
from datetime import datetime

DATA_DIR = Path('services/data')
DB_FILE = DATA_DIR / 'yantai_rebar.db'
COOKIE_FILE = DATA_DIR / 'mysteel_cookies.json'
CONFIG_FILE = DATA_DIR / 'mysteel_config.json'

TARGET_URL = "https://jiancai.mysteel.com/m/26060916/E3B5B7AB6E55FC6D.html"


async def fetch_single_url():
    """抓取单个URL的数据"""
    print(f"抓取目标: {TARGET_URL}")
    print("=" * 50)

    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=False)
    context = await browser.new_context(viewport={'width': 1920, 'height': 3000}, locale='zh-CN')
    page = await context.new_page()

    # 加载Cookie
    if COOKIE_FILE.exists():
        try:
            with open(COOKIE_FILE, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
            await context.add_cookies(cookies)
            print(f"加载了 {len(cookies)} 个Cookie")
        except:
            pass

    # 访问页面
    await page.goto(TARGET_URL, wait_until='domcontentloaded', timeout=30000)
    await asyncio.sleep(5)

    # 检查是否需要登录
    body_text = await page.evaluate('() => document.body.textContent')
    if '登录' in body_text and len(body_text) < 1000:
        print("\n需要登录！请在浏览器中完成登录...")
        print("登录后按回车继续...")
        input()

        # 重新加载Cookie
        cookies = await context.cookies()
        with open(COOKIE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cookies, f, ensure_ascii=False)

        await page.goto(TARGET_URL, wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(3)

    # 截图
    await page.screenshot(path="yantai_page.png", full_page=True)
    print("截图已保存: yantai_page.png")

    # 提取表格数据
    print("\n提取表格数据...")
    table_data = await page.evaluate('''() => {
        const table = document.querySelector('table#marketTable');
        if (!table) return [];

        const rows = table.querySelectorAll('tr');
        const results = [];

        rows.forEach((row, rowIndex) => {
            const cells = row.querySelectorAll('td');
            if (cells.length > 0) {
                const rowData = Array.from(cells).map(cell => ({
                    text: cell.textContent.trim(),
                    html: cell.innerHTML
                }));
                results.push({rowIndex, cells: rowData});
            }
        });

        return results;
    }''')

    print(f"表格行数: {len(table_data)}")

    # 从URL提取日期
    date_match = re.search(r'(\d{6})', TARGET_URL)
    date_str = ''
    if date_match:
        d = date_match.group(1)
        date_str = f'20{d[:2]}-{d[2:4]}-{d[4:6]}'

    print(f"日期: {date_str}")

    # 解析价格数据
    prices = []
    print("\n解析价格数据:")

    for row_data in table_data:
        if len(row_data['cells']) >= 5:
            cells = row_data['cells']
            material = cells[0]['text'].strip()
            spec = cells[1]['text'].strip()
            material_type = cells[2]['text'].strip() if len(cells) > 2 else ''
            brand = cells[3]['text'].strip() if len(cells) > 3 else ''
            price_str = cells[4]['text'].strip() if len(cells) > 4 else ''
            change = cells[5]['text'].strip() if len(cells) > 5 else ''

            valid_names = ['高线', '螺纹钢', '盘螺', '圆钢']
            if material in valid_names and spec.startswith('Φ'):
                try:
                    price = int(''.join(filter(str.isdigit, price_str)))
                    if price > 0:
                        prices.append({
                            'material_name': material,
                            'spec': spec,
                            'material_type': material_type,
                            'brand': brand,
                            'price': price,
                            'change': change
                        })
                        print(f"  {material} {spec} {brand}: {price}元/吨")
                except:
                    pass

    print(f"\n共提取 {len(prices)} 条数据")

    # 保存到数据库
    if prices:
        def init_db():
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS rebar_prices (
                id INTEGER PRIMARY KEY,
                date TEXT NOT NULL,
                material_name TEXT,
                spec TEXT,
                material_type TEXT,
                brand TEXT,
                price INTEGER,
                region TEXT DEFAULT '山东烟台',
                UNIQUE(date, material_name, spec, brand, price)
            )''')
            conn.commit()
            conn.close()

        init_db()

        # 获取已存在的键
        def get_existing_keys():
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute('SELECT date, material_name, spec, brand FROM rebar_prices')
            existing = {f"{r[0]}_{r[1]}_{r[2]}_{r[3]}" for r in c.fetchall()}
            conn.close()
            return existing

        existing_keys = get_existing_keys()

        # 插入数据
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        inserted = 0
        skipped = 0

        for price in prices:
            key = f"{date_str}_{price['material_name']}_{price['spec']}_{price['brand']}"
            if key not in existing_keys:
                try:
                    c.execute('INSERT INTO rebar_prices (date, material_name, spec, material_type, brand, price, region) VALUES (?, ?, ?, ?, ?, ?, ?)',
                        (date_str, price['material_name'], price['spec'], price['material_type'], price['brand'], price['price'], '山东烟台'))
                    inserted += 1
                    existing_keys.add(key)
                except Exception as e:
                    skipped += 1
            else:
                skipped += 1

        conn.commit()
        conn.close()

        print(f"\n数据库操作: 插入 {inserted} 条, 跳过 {skipped} 条")

    await browser.close()

    print("\n" + "=" * 50)
    print("抓取完成")
    print(f"日期: {date_str}")
    print(f"数据量: {len(prices)} 条")
    print(f"数据库: {DB_FILE}")
    print("=" * 50)

    # 显示数据汇总
    if prices:
        print("\n按品名汇总:")
        summary = {}
        for p in prices:
            name = p['material_name']
            if name not in summary:
                summary[name] = []
            summary[name].append(p['price'])

        for name, price_list in summary.items():
            print(f"  {name}: {len(price_list)}条, 价格范围: {min(price_list)}-{max(price_list)}")


if __name__ == '__main__':
    asyncio.run(fetch_single_url())
