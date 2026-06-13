"""
烟台钢筋价格智能抓取 - 自动检测页面结构
"""
import asyncio
from playwright.async_api import async_playwright
import json
import re
import sqlite3
from pathlib import Path

DATA_DIR = Path('services/data')
DB_FILE = DATA_DIR / 'yantai_rebar.db'
COOKIE_FILE = DATA_DIR / 'mysteel_cookies.json'

TARGET_URL = "https://jiancai.mysteel.com/m/26060916/E3B5B7AB6E55FC6D.html"


async def fetch_with_auto_detect():
    """自动检测页面结构并抓取数据"""
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
    await page.goto(TARGET_URL, wait_until='networkidle', timeout=30000)
    await asyncio.sleep(5)

    # 检查登录状态
    body_text = await page.evaluate('() => document.body.textContent')
    if '登录' in body_text and len(body_text) < 1000:
        print("\n需要登录！请在浏览器中完成登录后按回车...")
        input()

    # 保存Cookie
    cookies = await context.cookies()
    with open(COOKIE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cookies, f, ensure_ascii=False)

    # 刷新页面
    await page.reload(wait_until='networkidle')
    await asyncio.sleep(3)

    # 截图
    await page.screenshot(path="yantai_debug.png", full_page=True)
    print("截图已保存: yantai_debug.png")

    # 检测页面中的表格
    print("\n检测页面结构...")

    table_info = await page.evaluate('''() => {
        const tables = document.querySelectorAll('table');
        const results = [];

        tables.forEach((table, index) => {
            const rows = table.querySelectorAll('tr');
            const cellCount = rows.length > 0 ? rows[0].querySelectorAll('td, th').length : 0;

            results.push({
                index: index,
                id: table.id || '',
                className: table.className || '',
                rowCount: rows.length,
                cellCount: cellCount,
                hasData: rows.length > 2
            });
        });

        return results;
    }''')

    print(f"找到 {len(table_info)} 个表格:")
    for info in table_info:
        print(f"  表格{info['index']}: id='{info['id']}', class='{info['className']}', {info['rowCount']}行")

    # 尝试从每个表格提取数据
    prices = []
    date_str = ''

    # 从URL提取日期
    date_match = re.search(r'(\d{6})', TARGET_URL)
    if date_match:
        d = date_match.group(1)
        date_str = f'20{d[:2]}-{d[2:4]}-{d[4:6]}'

    print(f"\n日期: {date_str}")

    # 尝试不同的提取方式
    print("\n尝试提取数据...")

    # 方式1: 从marketTable提取
    if any(t['id'] == 'marketTable' for t in table_info):
        print("使用marketTable...")
        data = await page.evaluate('''() => {
            const table = document.querySelector('table#marketTable');
            if (!table) return [];

            const rows = table.querySelectorAll('tr');
            return Array.from(rows).map(row => {
                const cells = row.querySelectorAll('td');
                return Array.from(cells).map(cell => cell.textContent.trim());
            });
        }''')

        for row in data:
            if len(row) >= 5:
                material = row[0].strip()
                spec = row[1].strip()
                brand = row[3].strip() if len(row) > 3 else ''
                price_str = row[4].strip() if len(row) > 4 else ''

                valid_names = ['高线', '螺纹钢', '盘螺', '圆钢']
                if material in valid_names and spec.startswith('Φ'):
                    try:
                        price = int(''.join(filter(str.isdigit, price_str)))
                        if price > 0:
                            prices.append({
                                'material_name': material,
                                'spec': spec,
                                'brand': brand,
                                'price': price
                            })
                            print(f"  {material} {spec} {brand}: {price}")
                    except:
                        pass

    # 方式2: 从所有表格提取
    if not prices:
        print("尝试从所有表格提取...")
        for table_idx in range(len(table_info)):
            data = await page.evaluate(f'''() => {{
                const tables = document.querySelectorAll('table');
                const table = tables[{table_idx}];
                if (!table) return [];

                const rows = table.querySelectorAll('tr');
                return Array.from(rows).map(row => {{
                    const cells = row.querySelectorAll('td');
                    return Array.from(cells).map(cell => cell.textContent.trim());
                }});
            }}''')

            for row in data:
                if len(row) >= 4:
                    # 尝试不同的列顺序
                    for offset in range(len(row) - 3):
                        material = row[offset].strip()
                        if material in ['高线', '螺纹钢', '盘螺', '圆钢']:
                            spec = row[offset + 1].strip() if offset + 1 < len(row) else ''
                            brand = row[offset + 2].strip() if offset + 2 < len(row) else ''
                            price_str = row[offset + 3].strip() if offset + 3 < len(row) else ''

                            if spec.startswith('Φ'):
                                try:
                                    price = int(''.join(filter(str.isdigit, price_str)))
                                    if price > 0:
                                        prices.append({
                                            'material_name': material,
                                            'spec': spec,
                                            'brand': brand,
                                            'price': price
                                        })
                                        print(f"  {material} {spec} {brand}: {price}")
                                except:
                                    pass

    # 方式3: 使用更宽松的选择器
    if not prices:
        print("使用宽松模式...")
        all_text = await page.evaluate('''() => {
            return document.body.textContent;
        }''')

        # 从文本中提取价格模式
        lines = all_text.split('\n')
        for line in lines:
            if 'Φ' in line and any(n in line for n in ['高线', '螺纹钢', '盘螺', '圆钢']):
                parts = line.split()
                # 尝试解析
                for i, part in enumerate(parts):
                    if part.startswith('Φ') and i > 0:
                        material = parts[i - 1]
                        spec = part
                        # 查找价格
                        for j in range(i + 1, len(parts)):
                            try:
                                price = int(''.join(filter(str.isdigit, parts[j])))
                                if 3000 < price < 10000:  # 合理价格范围
                                    prices.append({
                                        'material_name': material,
                                        'spec': spec,
                                        'brand': '',
                                        'price': price
                                    })
                                    print(f"  {material} {spec}: {price}")
                                    break
                            except:
                                pass
                        break

    print(f"\n总共提取 {len(prices)} 条数据")

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
                brand TEXT,
                price INTEGER,
                region TEXT DEFAULT '山东烟台',
                UNIQUE(date, material_name, spec, brand, price)
            )''')
            conn.commit()
            conn.close()

        init_db()

        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        inserted = 0

        for price in prices:
            try:
                c.execute('INSERT OR IGNORE INTO rebar_prices (date, material_name, spec, brand, price, region) VALUES (?, ?, ?, ?, ?, ?)',
                    (date_str, price['material_name'], price['spec'], price['brand'], price['price'], '山东烟台'))
                if c.rowcount > 0:
                    inserted += 1
            except Exception as e:
                print(f"插入错误: {e}")

        conn.commit()
        conn.close()

        print(f"保存到数据库: {inserted} 条新记录")

    # 等待30秒让用户查看
    print("\n等待30秒...")
    await asyncio.sleep(30)

    await browser.close()

    print("\n" + "=" * 50)
    print("抓取完成")
    print(f"日期: {date_str}")
    print(f"数据量: {len(prices)} 条")
    print("=" * 50)


if __name__ == '__main__':
    asyncio.run(fetch_with_auto_detect())
