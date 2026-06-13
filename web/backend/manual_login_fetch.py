"""
烟台钢筋价格手动登录抓取脚本
1. 打开登录页面
2. 等待您手动登录
3. 自动抓取所有可用的烟台价格数据
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

MIN_PRICES = 11


async def manual_login_fetch():
    """手动登录 + 自动抓取"""
    print("=" * 60)
    print("烟台钢筋价格手动登录抓取")
    print("=" * 60)
    print("\n【步骤1】打开登录页面...")
    print("请在浏览器中手动输入账号密码完成登录")
    print("登录成功后程序会自动继续抓取\n")

    playwright = await async_playwright().start()
    # 使用非无头模式，让您看到浏览器
    browser = await playwright.chromium.launch(headless=False)
    context = await browser.new_context(viewport={'width': 1920, 'height': 3000}, locale='zh-CN')
    page = await context.new_page()

    # 打开登录页面
    await page.goto('https://passport.mysteel.com/', wait_until='domcontentloaded', timeout=60000)

    print("等待您登录...")
    print("(程序会每3秒检查一次登录状态，最多等待2分钟)")

    # 等待登录完成
    for i in range(40):  # 最多等待2分钟 (40 * 3秒)
        await asyncio.sleep(3)

        current_url = page.url
        # 检查是否已经离开登录页面
        if 'passport' not in current_url or 'login' not in current_url:
            print(f"\n[OK] 检测到登录成功！")
            break

        print(f"等待登录... ({i*3}/{120}秒)")
    else:
        print("\n[TIMEOUT] 登录超时，但继续尝试...")

    # 保存Cookie
    cookies = await context.cookies()
    try:
        with open(COOKIE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cookies, f, ensure_ascii=False)
        print(f"已保存 {len(cookies)} 个Cookie")
    except:
        pass

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

    # 从首页获取烟台价格URL列表
    print("\n【步骤2】获取烟台价格URL列表...")
    await page.goto('https://jiancai.mysteel.com/', wait_until='domcontentloaded', timeout=30000)
    await asyncio.sleep(3)

    # 查找烟台相关链接
    links = await page.evaluate('''() => {
        const results = [];
        document.querySelectorAll('a[href]').forEach(a => {
            const href = a.href;
            const text = a.textContent.trim();
            // 匹配烟台价格链接
            if (href.includes('/m/') && href.includes('jiancai.mysteel.com')) {
                results.push({href, text});
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

    # 抓取每个URL
    print(f"\n【步骤3】开始抓取数据（确保每天不少于 {MIN_PRICES} 条）...")
    print("=" * 60)

    total_inserted = 0
    success_count = 0
    incomplete_dates = []

    for i, link in enumerate(unique_links):
        url = link['href']
        print(f"\n[{i+1}/{len(unique_links)}] {url}")

        try:
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(2)

            # 检查登录状态
            body_text = await page.evaluate('() => document.body.textContent')
            if '登录' in body_text and '注册' in body_text and len(body_text) < 500:
                print("  [!] 需要登录，跳过")
                continue

            # 获取表格数据
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
                    price_str = row[4].strip()
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
                print(f"  [OK] 提取 {len(prices)} 条: {date_str}")

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
                    print(f"  [SAVE] 插入 {inserted} 条新数据")

                # 检查数据量
                current_count = len([k for k in existing_keys if k.startswith(date_str)])
                if current_count < MIN_PRICES:
                    print(f"  [WARN] {date_str} 只有 {current_count} 条，需要 {MIN_PRICES} 条")
                    incomplete_dates.append(date_str)
                else:
                    print(f"  [OK] {date_str} 数据完整: {current_count} 条")

            else:
                print(f"  [FAIL] 未提取到数据")

        except Exception as e:
            print(f"  [ERROR] 错误: {e}")

        # 延迟 - 模拟人类行为
        if i < len(unique_links) - 1:
            delay = random.uniform(2, 5)
            await asyncio.sleep(delay)

    await browser.close()

    print("\n" + "=" * 60)
    print("抓取完成统计")
    print("=" * 60)
    print(f"处理URL: {len(unique_links)} 个")
    print(f"成功URL: {success_count} 个")
    print(f"新增记录: {total_inserted} 条")

    if incomplete_dates:
        print(f"\n数据不足的日期: {len(incomplete_dates)} 天")
        for date in incomplete_dates[:10]:
            print(f"  - {date}")
        if len(incomplete_dates) > 10:
            print(f"  ... 还有 {len(incomplete_dates) - 10} 天")

    print(f"\n数据库: {DB_FILE}")
    print("=" * 60)


if __name__ == '__main__':
    asyncio.run(manual_login_fetch())
