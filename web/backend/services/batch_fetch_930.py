"""
从收集的930个链接批量抓取烟台历史数据
"""
import asyncio
import json
import sqlite3
import re
from pathlib import Path
from playwright.async_api import async_playwright

DATA_DIR = Path(__file__).parent.absolute() / 'data'
DATA_DIR.mkdir(exist_ok=True)

COOKIE_FILE = DATA_DIR / 'mysteel_cookies.json'
DB_FILE = DATA_DIR / 'yantai_rebar.db'
LINKS_FILE = DATA_DIR / 'collected_yantai_links.json'


def load_cookies():
    if COOKIE_FILE.exists():
        with open(COOKIE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS rebar_prices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        material_name TEXT,
        spec TEXT,
        material_type TEXT,
        brand TEXT,
        price INTEGER,
        region TEXT DEFAULT '山东烟台',
        fetch_time TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(date, material_name, spec, brand, price)
    )''')
    conn.commit()
    conn.close()


def get_existing_dates():
    if not DB_FILE.exists():
        return {}

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute('''
            SELECT date, COUNT(DISTINCT material_name || spec || brand || price) as count
            FROM rebar_prices
            GROUP BY date
            ORDER BY date DESC
        ''')
        return {row[0]: row[1] for row in c.fetchall()}
    except:
        return {}
    finally:
        conn.close()


def save_to_db(date_str, prices, fetch_time='10:00:00'):
    if not prices:
        return 0

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    inserted = 0
    for price in prices:
        try:
            c.execute('''
                INSERT OR IGNORE INTO rebar_prices
                (date, material_name, spec, material_type, brand, price, region, fetch_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                date_str,
                price.get('material_name', ''),
                price.get('spec', ''),
                price.get('material_type', ''),
                price.get('brand', ''),
                price.get('price', 0),
                '山东烟台',
                fetch_time
            ))
            if c.rowcount > 0:
                inserted += 1
        except:
            pass

    conn.commit()
    conn.close()
    return inserted


def parse_time_from_url(url):
    match = re.search(r'/(\d{8})/', url)
    if match:
        hour = match.group(1)[6:8]
        return f"{hour}:00:00"
    return "10:00:00"


async def extract_prices_from_page(page):
    try:
        await asyncio.sleep(1.5)

        data = await page.evaluate('''() => {
            const tables = document.querySelectorAll('table');
            const results = [];

            tables.forEach(table => {
                const rows = table.querySelectorAll('tr');
                rows.forEach(row => {
                    const cells = row.querySelectorAll('td');
                    if (cells.length >= 5) {
                        const rowData = Array.from(cells).map(c => c.textContent.trim());
                        results.push(rowData);
                    }
                });
            });

            return results;
        }''')

        prices = []
        for row in data:
            if len(row) >= 5:
                material_name = str(row[0]).strip()
                spec = str(row[1]).strip()
                material_type = str(row[2]).strip()
                brand = str(row[3]).strip()
                price_str = str(row[4]).strip()

                valid_names = ['高线', '螺纹钢', '盘螺', '圆钢']

                if material_name in valid_names and spec.startswith('Φ'):
                    price_match = re.search(r'\d{4}', price_str)
                    if price_match:
                        try:
                            price = int(price_match.group())
                            if 3000 < price < 10000:
                                prices.append({
                                    'material_name': material_name,
                                    'spec': spec,
                                    'material_type': material_type,
                                    'brand': brand,
                                    'price': price
                                })
                        except:
                            pass

        return prices

    except Exception as e:
        return []


async def batch_fetch():
    """批量抓取"""
    print("=" * 80)
    print("批量抓取烟台历史数据（930个链接）")
    print("=" * 80)

    # 读取链接
    if not LINKS_FILE.exists():
        print(f"[错误] 找不到链接文件: {LINKS_FILE}")
        return

    with open(LINKS_FILE, 'r', encoding='utf-8') as f:
        links = json.load(f)

    print(f"\n[读取]找到 {len(links)} 个链接")

    # 初始化数据库
    init_db()

    # 检查已有数据
    existing_dates = get_existing_dates()
    print(f"[扫描] 数据库已有 {len(existing_dates)} 个日期")

    # 确定需要抓取的链接
    links_to_fetch = []
    for link in links:
        date = link['date']
        count = existing_dates.get(date, 0)
        if count < 111:
            links_to_fetch.append(link)

    print(f"[目标] 需要抓取 {len(links_to_fetch)} 个日期")

    if not links_to_fetch:
        print("\n所有日期数据充足！")
        return

    # 启动浏览器
    cookies = load_cookies()

    print("\n[启动] 浏览器...")
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=True)
    context = await browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        locale='zh-CN'
    )

    if cookies:
        await context.add_cookies(cookies)
        print(f"  已加载 {len(cookies)} 条Cookie")

    page = await context.new_page()

    # 批量抓取
    print("\n[开始] 批量抓取...")
    print("=" * 80)

    success_count = 0
    fail_count = 0
    total_inserted = 0

    for i, link in enumerate(links_to_fetch, 1):
        url = link['url']
        date = link['date']
        fetch_time = parse_time_from_url(url)

        print(f"\n[{i}/{len(links_to_fetch)}] {date}")

        try:
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(1.5)

            prices = await extract_prices_from_page(page)

            if prices:
                inserted = save_to_db(date, prices, fetch_time)
                print(f"  OK 提取 {len(prices)} 条，新增 {inserted} 条")
                success_count += 1
                total_inserted += inserted
            else:
                print(f"  X 未提取到数据")
                fail_count += 1

        except Exception as e:
            print(f"  X 错误: {e}")
            fail_count += 1

        # 进度报告
        if i % 50 == 0:
            print(f"\n[进度] {i}/{len(links_to_fetch)} 完成")
            print(f"  成功: {success_count}, 失败: {fail_count}, 新增: {total_inserted}")

        # 避免请求过快
        if i < len(links_to_fetch):
            await asyncio.sleep(1)

    # 汇总
    print("\n" + "=" * 80)
    print("抓取完成!")
    print(f"  成功: {success_count}/{len(links_to_fetch)}")
    print(f"  失败: {fail_count}/{len(links_to_fetch)}")
    print(f"  总计: {total_inserted} 条新数据")
    print(f"  数据库: {DB_FILE}")
    print("=" * 80)

    # 显示最新统计
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM rebar_prices')
    total = c.fetchone()[0]
    c.execute('SELECT COUNT(DISTINCT date) FROM rebar_prices')
    date_count = c.fetchone()[0]
    conn.close()

    print(f"\n[最终统计]")
    print(f"  总数据量: {total} 条")
    print(f"  覆盖日期: {date_count} 天")

    await browser.close()
    await playwright.stop()


if __name__ == '__main__':
    try:
        asyncio.run(batch_fetch())
    except KeyboardInterrupt:
        print("\n\n[中断] 用户取消操作")