"""
烟台钢筋价格抓取 - 手动登录（延长等待时间）
"""
import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright

DATA_DIR = Path('services/data')
DATA_DIR.mkdir(exist_ok=True)
COOKIE_FILE = DATA_DIR / 'mysteel_cookies.json'

TARGET_URL = "https://jiancai.mysteel.com/m/26060916/E3B5B7AB6E55FC6D.html"


async def main():
    print("=" * 60)
    print("烟台钢筋价格抓取 - 手动登录模式")
    print("=" * 60)
    print(f"\n目标页面: {TARGET_URL}")
    print("\n步骤:")
    print("1. 浏览器将打开登录页面")
    print("2. 请使用手机验证码登录")
    print("3. 登录成功后，等待脚本自动继续（最长90秒）")
    print("   或者登录成功后按 Ctrl+C 停止等待，脚本会立即继续")
    print("\n" + "=" * 60)

    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=False)
    context = await browser.new_context(viewport={'width': 1920, 'height': 1080}, locale='zh-CN')
    page = await context.new_page()

    # 先访问登录页面
    print("\n[1/3] 正在打开登录页面...")
    await page.goto('https://passport.mysteel.com/', wait_until='domcontentloaded')
    await asyncio.sleep(2)

    print("\n" + "=" * 40)
    print("请在浏览器中完成登录（使用手机验证码）")
    print("登录成功后，脚本将自动继续")
    print("=" * 40)

    # 等待90秒让用户登录，但允许按Ctrl+C跳过
    try:
        for i in range(90, 0, -10):
            print(f"  倒计时: {i} 秒... (登录成功后可按 Ctrl+C 继续)")
            await asyncio.sleep(10)
    except KeyboardInterrupt:
        print("\n[检测到中断] 继续执行...")

    # 保存Cookie
    print("\n[2/3] 正在保存Cookie...")
    cookies = await context.cookies()
    with open(COOKIE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cookies, f, ensure_ascii=False, indent=2)

    print(f"[OK] Cookie已保存: {len(cookies)} 条")
    print(f"     保存位置: {COOKIE_FILE}")

    # 现在访问目标页面测试
    print("\n[3/3] 正在访问目标页面...")
    await page.goto(TARGET_URL, wait_until='networkidle', timeout=60000)
    await asyncio.sleep(3)

    # 截图
    screenshot_path = DATA_DIR / 'yantia_test_page.png'
    await page.screenshot(path=str(screenshot_path), full_page=True)
    print(f"[OK] 截图已保存: {screenshot_path}")

    # 检查是否成功访问
    page_text = await page.evaluate('() => document.body.textContent')
    if '登录' in page_text and len(page_text) < 500:
        print("\n[警告] 页面可能仍然需要登录")
        print("请检查截图确认登录状态")
    else:
        print("\n[OK] 页面访问成功！")

    # 尝试提取数据
    print("\n正在提取价格数据...")

    # 首先检测表格结构
    table_analysis = await page.evaluate('''() => {
        const tables = document.querySelectorAll('table');
        const results = [];

        tables.forEach((table, idx) => {
            const rows = Array.from(table.querySelectorAll('tr'));
            const headers = rows.length > 0 ? Array.from(rows[0].querySelectorAll('td, th')).map(c => c.textContent.trim()) : [];

            results.push({
                index: idx,
                rowCount: rows.length,
                headers: headers,
                hasData: rows.length > 2
            });
        });

        return results;
    }''')

    print(f"\n找到 {len(table_analysis)} 个表格:")
    for t in table_analysis[:3]:  # 只显示前3个
        print(f"  表格{t['index']}: {t['rowCount']}行, 表头: {t['headers'][:5]}")

    # 尝试从所有表格提取数据
    prices = []
    for table_idx in range(len(table_analysis)):
        data = await page.evaluate(f'''(idx) => {{
            const tables = document.querySelectorAll('table');
            const table = tables[idx];
            if (!table) return [];

            const rows = table.querySelectorAll('tr');
            const results = [];

            rows.forEach((row) => {{
                const cells = row.querySelectorAll('td');
                if (cells.length >= 4) {{
                    const rowData = Array.from(cells).map(c => c.textContent.trim());
                    results.push(rowData);
                }}
            }});

            return results;
        }}''', table_idx)

        for row in data:
            if len(row) >= 4:
                # 检查是否是有效的价格数据
                valid_names = ['高线', '螺纹钢', '盘螺', '圆钢']
                for i, cell in enumerate(row):
                    if cell in valid_names and i + 1 < len(row):
                        spec = row[i + 1] if i + 1 < len(row) else ''
                        if spec.startswith('Φ'):
                            # 尝试查找价格
                            for j in range(i + 2, min(i + 5, len(row))):
                                price_str = row[j]
                                try:
                                    price = int(''.join(filter(str.isdigit, price_str)))
                                    if 3000 < price < 10000:
                                        brand = row[i + 2] if i + 2 < len(row) else ''
                                        prices.append({
                                            'material_name': cell,
                                            'spec': spec,
                                            'brand': brand,
                                            'price': price
                                        })
                                        print(f"  [OK] {cell} {spec} {brand}: {price} 元/吨")
                                        break
                                except:
                                    pass
                            break

    print(f"\n总计提取: {len(prices)} 条价格数据")

    # 从URL提取日期
    import re
    date_match = re.search(r'(\d{6})', TARGET_URL)
    if date_match:
        d = date_match.group(1)
        date_str = f'20{d[:2]}-{d[2:4]}-{d[4:6]}'
        print(f"日期: {date_str}")

    # 保存到数据库
    if prices:
        import sqlite3
        DB_FILE = DATA_DIR / 'yantai_rebar.db'

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

        print(f"\n[OK] 保存到数据库: {inserted} 条新记录")
    else:
        print("\n[警告] 未提取到数据，请检查登录状态")

    print("\n等待5秒查看结果...")
    await asyncio.sleep(5)

    await browser.close()
    await playwright.stop()

    print("\n" + "=" * 60)
    print("[完成] Cookie已保存，数据已提取")
    print("=" * 60)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n[中断] 用户取消操作")
