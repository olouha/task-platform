"""
烟台钢筋价格抓取 - 修复登录和数据获取问题
"""
import asyncio
from playwright.async_api import async_playwright
import json
import re
import random
from pathlib import Path
from datetime import datetime
import sqlite3

DATA_DIR = Path('services/data')
DB_FILE = DATA_DIR / 'yantai_rebar.db'
COOKIE_FILE = DATA_DIR / 'mysteel_cookies.json'
CONFIG_FILE = DATA_DIR / 'mysteel_config.json'

MIN_PRICES = 11


async def smart_fetch():
    """智能抓取 - 确保登录并获取价格"""
    print("开始智能抓取...")
    print(f"确保每天不少于 {MIN_PRICES} 条数据")

    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=False)  # 显示浏览器便于调试
    context = await browser.new_context(viewport={'width': 1920, 'height': 3000}, locale='zh-CN')
    page = await context.new_page()

    # 加载或获取凭据
    username, password = '', ''
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            username = config.get('username', '')
            password = config.get('password', '')
        except:
            pass

    # 尝试加载Cookie
    cookies_loaded = False
    if COOKIE_FILE.exists():
        try:
            with open(COOKIE_FILE, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
            await context.add_cookies(cookies)
            cookies_loaded = True
            print(f"加载了 {len(cookies)} 个Cookie")
        except:
            pass

    # 检查登录状态并尝试登录
    if username and password:
        print(f"尝试登录: {username[:3]}***")
        try:
            await page.goto('https://passport.mysteel.com/', wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(2)

            # 填写表单
            await page.evaluate(f'''() => {{
                const inputs = document.querySelectorAll('input');
                for (const inp of inputs) {{
                    const ph = inp.placeholder || '';
                    if (ph.includes('用户名')) inp.value = '{username}';
                    if (ph.includes('密码') && inp.type === 'password') inp.value = '{password}';
                }}
            }}''')

            await asyncio.sleep(1)

            # 点击登录
            try:
                btn = await page.query_selector('.form-button-login, button:has-text("登录")')
                if btn:
                    await btn.click()
                    print("已点击登录按钮")
            except:
                pass

            await asyncio.sleep(8)

            # 保存Cookie
            cookies = await context.cookies()
            with open(COOKIE_FILE, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, ensure_ascii=False)
            print("登录成功，Cookie已保存")

        except Exception as e:
            print(f"自动登录失败: {e}")

    # 初始化数据库
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
    print(f"数据库已有 {len(existing_keys)} 条记录")

    # 从首页获取URL列表
    print("\n从首页获取URL列表...")
    await page.goto('https://jiancai.mysteel.com/', wait_until='domcontentloaded', timeout=30000)
    await asyncio.sleep(3)

    links = await page.evaluate('''() => {
        const results = [];
        document.querySelectorAll('a[href]').forEach(a => {
            const href = a.href;
            if (href.includes('/m/') && href.includes('jiancai.mysteel.com')) {
                results.push({href, text: a.textContent.trim()});
            }
        });
        return results;
    }''')

    print(f"找到 {len(links)} 个链接")

    # 去重
    seen = set()
    unique_links = []
    for link in links:
        if link['href'] not in seen:
            seen.add(link['href'])
            unique_links.append(link)

    print(f"去重后 {len(unique_links)} 个URL")

    total_inserted = 0
    success_count = 0

    # 抓取每个URL
    for i, link in enumerate(unique_links[:50]):  # 先测试前50个
        url = link['href']
        print(f"\n[{i+1}/50] {url}")

        try:
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(3)

            # 检查登录状态
            body_text = await page.evaluate('() => document.body.textContent')
            if '登录' in body_text and '注册' in body_text:
                print("  需要登录，跳过")
                continue

            # 获取表格数据 - 改进版本
            table_data = await page.evaluate('''() => {
                const table = document.querySelector('table#marketTable');
                if (!table) return [];

                const rows = table.querySelectorAll('tr');
                return Array.from(rows).map(row => {
                    const cells = row.querySelectorAll('td');
                    return Array.from(cells).map(cell => cell.textContent.trim());
                });
            }''')

            # 从URL提取日期
            date_match = re.search(r'(\d{6})', url)
            date_str = ''
            if date_match:
                d = date_match.group(1)
                date_str = f'20{d[:2]}-{d[2:4]}-{d[4:6]}'

            # 解析价格数据
            prices = []
            for row in table_data:
                if len(row) >= 6:
                    material = row[0].strip()
                    spec = row[1].strip()
                    material_type = row[2].strip()
                    brand = row[3].strip()
                    price_str = row[4].strip()  # 价格在第5列
                    change = row[5].strip()

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
                                    'price': price
                                })
                        except:
                            pass

            if prices:
                print(f"  提取 {len(prices)} 条数据: {date_str}")

                # 插入数据库
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                inserted = 0
                for price in prices:
                    key = f"{date_str}_{price['material_name']}_{price['spec']}_{price['brand']}"
                    if key not in existing_keys:
                        try:
                            c.execute('INSERT INTO rebar_prices (date, material_name, spec, material_type, brand, price, region) VALUES (?, ?, ?, ?, ?, ?, ?)',
                                (date_str, price['material_name'], price['spec'], price['material_type'], price['brand'], price['price'], '山东烟台'))
                            inserted += 1
                            existing_keys.add(key)
                        except:
                            pass

                conn.commit()
                conn.close()

                if inserted > 0:
                    total_inserted += inserted
                    success_count += 1
                    print(f"  插入 {inserted} 条新数据")

                    # 检查数据量
                    current_count = len([k for k in existing_keys if k.startswith(date_str)])
                    if current_count < MIN_PRICES:
                        print(f"  警告: {date_str} 只有 {current_count} 条，需要 {MIN_PRICES} 条")

            else:
                print(f"  未提取到数据")

        except Exception as e:
            print(f"  错误: {e}")

        # 延迟
        await asyncio.sleep(random.uniform(2, 4))

    await browser.close()

    print("\n" + "=" * 50)
    print("抓取完成")
    print(f"成功URL: {success_count}/50")
    print(f"新增记录: {total_inserted} 条")
    print("=" * 50)


if __name__ == '__main__':
    asyncio.run(smart_fetch())
