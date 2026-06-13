"""
智能批量抓取烟台历史数据
模拟人类行为：滚动、等待、随机间隔
"""
import asyncio
import json
import re
import random
from pathlib import Path
from playwright.async_api import async_playwright

DATA_DIR = Path(__file__).parent.absolute() / 'data'
DATA_DIR.mkdir(exist_ok=True)

COOKIE_FILE = DATA_DIR / 'mysteel_cookies.json'
DB_FILE = DATA_DIR / 'yantai_rebar.db'
LINKS_FILE = DATA_DIR / 'yantai_links_full.json'


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
    if not Path(DB_FILE).exists():
        return {}

    import sqlite3
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

    import sqlite3
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


def parse_date_from_url(url):
    match = re.search(r'/(\d{2})(\d{2})(\d{2})\d{2}/', url)
    if match:
        return f"20{match.group(1)}-{match.group(2)}-{match.group(3)}"
    return None


def parse_url_from_link(link):
    """兼容不同格式的链接"""
    if isinstance(link, str):
        return link
    elif isinstance(link, dict):
        return link.get('url') or link.get('href') or ''
    return ''


def parse_time_from_url(url):
    match = re.search(r'/(\d{8})/', url)
    if match:
        hour = match.group(1)[6:8]
        return f"{hour}:00:00"
    return "10:00:00"


async def human_like_scroll(page):
    """模拟人类滚动页面"""
    for _ in range(random.randint(2, 4)):
        scroll_amount = random.randint(200, 500)
        await page.evaluate(f'window.scrollBy(0, {scroll_amount})')
        await asyncio.sleep(random.uniform(0.5, 1.5))

    # 随机向上滚动一点
    await page.evaluate(f'window.scrollBy(0, -{random.randint(100, 200)})')
    await asyncio.sleep(random.uniform(0.3, 0.8))


async def extract_prices(page):
    """提取价格数据"""
    await asyncio.sleep(random.uniform(1, 2))

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


async def smart_fetch():
    """智能批量抓取"""
    print("=" * 80)
    print("智能批量抓取烟台历史数据")
    print("=" * 80)

    # 读取链接
    links_file = LINKS_FILE
    if not links_file.exists():
        #尝试另一个文件名
        alt_file = DATA_DIR / 'yantai_links.json'
        if alt_file.exists():
            links_file = alt_file
        else:
            print(f"[错误] 找不到链接文件")
            return

    with open(links_file, 'r', encoding='utf-8') as f:
        raw_links = json.load(f)

    # 转换为统一格式
    links = []
    for link in raw_links:
        url = parse_url_from_link(link)
        date = parse_date_from_url(url)
        if date:
            links.append({
                'url': url,
                'date': date,
                'text': link.get('text', '') if isinstance(link, dict) else ''
            })

    print(f"\n[读取]找到 {len(links)} 个有效链接")

    # 检查已有数据
    import sqlite3
    init_db()
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
    browser = await playwright.chromium.launch(headless=False)
    context = await browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        locale='zh-CN'
    )

    if cookies:
        await context.add_cookies(cookies)
        print(f"  已加载 {len(cookies)} 条Cookie")

    page = await context.new_page()

    # 批量抓取
    print("\n[开始] 智能批量抓取...")
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
            # 访问页面
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)

            # 模拟人类行为：随机滚动
            await human_like_scroll(page)

            # 提取价格
            prices = await extract_prices(page)

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

        # 随机等待（模拟人类阅读）
        wait_time = random.uniform(1.5, 3)
        await asyncio.sleep(wait_time)

        # 进度报告
        if i % 20 == 0:
            print(f"\n[进度] {i}/{len(links_to_fetch)} 完成")
            print(f"  成功: {success_count}, 失败: {fail_count}, 新增: {total_inserted}")

    # 汇总
    print("\n" + "=" * 80)
    print("抓取完成!")
    print(f"  成功: {success_count}/{len(links_to_fetch)}")
    print(f"  失败: {fail_count}/{len(links_to_fetch)}")
    print(f"  总计: {total_inserted} 条新数据")
    print("=" * 80)

    await browser.close()
    await playwright.stop()


if __name__ == '__main__':
    import sqlite3
    try:
        asyncio.run(smart_fetch())
    except KeyboardInterrupt:
        print("\n\n[中断] 用户取消操作")