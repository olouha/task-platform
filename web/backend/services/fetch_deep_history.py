"""
烟台钢筋价格历史数据深度抓取 - 从2024年1月2日到现在
持续查找并抓取更早期的历史数据
"""
import asyncio
import json
import sqlite3
import sys
import re
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright

# 获取脚本所在目录
SCRIPT_DIR = Path(__file__).parent.absolute()
DATA_DIR = SCRIPT_DIR / 'data'
DATA_DIR.mkdir(exist_ok=True)

COOKIE_FILE = DATA_DIR / 'mysteel_cookies.json'
DB_FILE = DATA_DIR / 'yantai_rebar.db'
MARKET_PAGE = 'https://jiancai.mysteel.com/market/pa228aa010101a0a01010205aaaa1.html'

# 目标日期范围
TARGET_START_DATE = '2024-01-02'
TARGET_END_DATE = '2026-06-10'


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
        except Exception as e:
            pass

    conn.commit()
    conn.close()
    return inserted


def parse_date_from_url(url):
    """从URL中解析日期"""
    match = re.search(r'/(\d{2})(\d{2})(\d{2})\d{2}/', url)
    if match:
        year = '20' + match.group(1)
        month = match.group(2)
        day = match.group(3)
        return f"{year}-{month}-{day}"
    return None


def parse_time_from_url(url):
    """从URL中解析时间"""
    match = re.search(r'/(\d{8})/', url)
    if match:
        hour = match.group(1)[6:8]
        return f"{hour}:00:00"
    return "10:00:00"


async def extract_yantai_links_from_page(page):
    """从页面提取烟台历史链接"""
    try:
        await asyncio.sleep(2)

        links = await page.evaluate('''() => {
            const results = [];

            const allLinks = document.querySelectorAll('a[href]');
            allLinks.forEach(link => {
                const href = link.href;
                const text = link.textContent.trim();

                if (text.includes('烟台') && href.includes('/m/') && href.includes('jiancai.mysteel.com')) {
                    results.push({
                        url: href,
                        text: text
                    });
                }
            });

            return results;
        }''')

        # 解析日期
        parsed_links = []
        for link in links:
            url = link['url']
            date = parse_date_from_url(url)
            if date:
                parsed_links.append({
                    'url': url,
                    'date': date,
                    'text': link['text']
                })

        return parsed_links

    except Exception as e:
        print(f"      提取链接失败: {e}")
        return []


async def find_early_links(page, target_date):
    """翻页查找早期的链接"""
    all_links = []
    page_num = 1
    max_pages = 100  # 最多翻100页

    print(f"\n[翻页] 查找从 {target_date} 开始的历史数据...")

    while page_num <= max_pages:
        print(f"  第 {page_num} 页...")

        # 提取当前页面的链接
        links = await extract_yantai_links_from_page(page)
        page_links = []
        for link in links:
            date = link['date']
            if date >= target_date and link not in all_links:
                page_links.append(link)

        all_links.extend(page_links)
        print(f"    找到 {len(page_links)} 个新链接")

        # 检查是否找到目标日期
        dates = [link['date'] for link in all_links]
        if dates:
            earliest = min(dates)
            print(f"    当前最早日期: {earliest}")
            if earliest <= target_date:
                print(f"    已找到目标日期！")
                break

        # 查找"下一页"或"下一页"类型的链接
        try:
            # 查找分页链接
            next_links = await page.evaluate('''() => {
                const results = [];
                const allLinks = document.querySelectorAll('a[href]');

                allLinks.forEach(link => {
                    const text = link.textContent.trim();
                    const href = link.href;

                    if (text === '下一页' || text === '>' || text === '下页') {
                        results.push(href);
                    }
                });

                return results;
            }''')

            if next_links:
                next_url = next_links[0]
                print(f"    点击下一页: {next_url}")
                await page.goto(next_url, wait_until='domcontentloaded', timeout=30000)
                await asyncio.sleep(2)
                page_num += 1
            else:
                # 尝试查找数字分页
                page_links = await page.evaluate('''() => {
                    const results = [];
                    const allLinks = document.querySelectorAll('a[href]');

                    allLinks.forEach(link => {
                        const text = link.textContent.trim();
                        if (/^\\d+$/.test(text)) {
                            results.push({
                                url: link.href,
                                num: parseInt(text)
                            });
                        }
                    });

                    results.sort((a, b) => a.num - b.num);
                    return results;
                }''')

                # 找到当前页码，尝试访问下一页
                if page_links:
                    print(f"    找到数字分页，共 {len(page_links)} 页")
                    # 如果已经到了最后一页，停止
                    break
                else:
                    print(f"    未找到更多页面")
                    break

        except Exception as e:
            print(f"    翻页错误: {e}")
            break

    print(f"\n[完成] 共找到 {len(all_links)} 个历史链接")
    return all_links


async def extract_prices_from_page(page):
    """从页面提取价格数据"""
    try:
        await asyncio.sleep(2)

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

        # 解析价格数据
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
                    # 提取价格
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


async def fetch_deep_history():
    """深度抓取历史数据"""
    print("=" * 80)
    print("烟台钢筋价格历史数据深度抓取")
    print("=" * 80)
    print(f"\n目标日期范围: {TARGET_START_DATE} ~ {TARGET_END_DATE}")

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

    # 访问市场页面
    print(f"\n[访问] 烟台市场页面: {MARKET_PAGE}")
    await page.goto(MARKET_PAGE, wait_until='domcontentloaded', timeout=30000)
    await asyncio.sleep(3)

    # 翻页查找历史链接
    all_links = await find_early_links(page, TARGET_START_DATE)

    # 去重
    seen = set()
    unique_links = []
    for link in all_links:
        key = link['url']
        if key not in seen:
            seen.add(key)
            unique_links.append(link)

    all_links = unique_links
    print(f"\n[去重] {len(all_links)} 个唯一链接")

    # 按日期排序
    all_links.sort(key=lambda x: x['date'], reverse=True)

    # 检查已有数据
    init_db()
    existing_dates = get_existing_dates()

    print(f"\n[扫描] 数据库已有 {len(existing_dates)} 个日期")

    # 确定需要抓取的链接
    links_to_fetch = []
    for link in all_links:
        date = link['date']
        count = existing_dates.get(date, 0)
        if count < 111:
            links_to_fetch.append(link)

    print(f"\n[目标] 需要抓取 {len(links_to_fetch)} 个日期")

    if not links_to_fetch:
        print("\n所有日期数据充足！")
        await browser.close()
        await playwright.stop()
        return

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
        print(f"  URL: {url}")

        try:
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(2)

            # 提取价格
            prices = await extract_prices_from_page(page)

            if prices:
                # 保存到数据库
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

        # 避免请求过快
        if i < len(links_to_fetch):
            await asyncio.sleep(1.5)

    # 汇总
    print("\n" + "=" * 80)
    print("抓取完成!")
    print(f"  成功: {success_count}/{len(links_to_fetch)}")
    print(f"  失败: {fail_count}/{len(links_to_fetch)}")
    print(f"  总计: {total_inserted} 条新数据")
    print(f"  数据库: {DB_FILE}")
    print("=" * 80)

    await browser.close()
    await playwright.stop()


if __name__ == '__main__':
    try:
        asyncio.run(fetch_deep_history())
    except KeyboardInterrupt:
        print("\n\n[中断] 用户取消操作")
