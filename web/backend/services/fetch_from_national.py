"""
烟台钢筋价格历史抓取 - 使用全国汇总页面
通过 /p/ 类型的URL获取全国汇总数据，从中提取烟台价格
"""
import asyncio
import json
import sqlite3
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

# 获取脚本所在目录
SCRIPT_DIR = Path(__file__).parent.absolute()
DATA_DIR = SCRIPT_DIR / 'data'
DATA_DIR.mkdir(exist_ok=True)

COOKIE_FILE = DATA_DIR / 'mysteel_cookies.json'
DB_FILE = DATA_DIR / 'yantai_rebar.db'


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


def save_to_db(date_str, prices):
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
                '09:00:00'
            ))
            if c.rowcount > 0:
                inserted += 1
        except Exception as e:
            print(f"      插入错误: {e}")

    conn.commit()
    conn.close()
    return inserted


async def extract_yantai_prices_from_national_page(page):
    """
    从全国汇总页面提取烟台价格数据
    """
    try:
        # 等待表格加载
        await asyncio.sleep(2)

        data = await page.evaluate('''() => {
            const results = [];

            // 查找所有表格
            const tables = document.querySelectorAll('table');

            tables.forEach(table => {
                const rows = table.querySelectorAll('tr');

                rows.forEach(row => {
                    const cells = row.querySelectorAll('td');
                    if (cells.length >= 3) {
                        const rowData = Array.from(cells).map(c => ({
                            text: c.textContent.trim(),
                            html: c.innerHTML
                        }));
                        results.push(rowData);
                    }
                });
            });

            return results;
        }''')

        # 解析数据，查找烟台
        prices = []
        for row in data:
            if len(row) >= 4:
                # 查找包含"烟台"的单元格
                yantai_index = -1
                for i, cell in enumerate(row):
                    if '烟台' in cell.get('text', '') or '山东' in cell.get('text', ''):
                        yantai_index = i
                        break

                if yantai_index >= 0:
                    # 提取价格数据
                    # 格式可能是：品名 | 规格 | 城市1价格 | 城市N价格
                    # 或者：城市 | 品名 | 规格 | 价格

                    # 尝试多种格式
                    row_text = [cell.get('text', '') for cell in row]

                    # 查找品名
                    material_name = ''
                    for name in ['高线', '螺纹钢', '盘螺', '圆钢']:
                        for cell in row_text:
                            if name in cell:
                                material_name = name
                                break
                        if material_name:
                            break

                    if material_name:
                        # 查找规格
                        spec = ''
                        for cell in row_text:
                            if cell.startswith('Φ'):
                                spec = cell.split()[0]  # 取第一部分
                                break

                        # 查找价格（烟台列的价格）
                        if yantai_index + 1 < len(row):
                            price_text = row[yantai_index + 1].get('text', '')
                            # 尝试提取数字
                            import re
                            price_match = re.search(r'\d{4}', price_text)
                            if price_match:
                                try:
                                    price = int(price_match.group())
                                    if 3000 < price < 10000:
                                        prices.append({
                                            'material_name': material_name,
                                            'spec': spec,
                                            'material_type': 'HRB400',
                                            'brand': '',
                                            'price': price
                                        })
                                except:
                                    pass

        return prices

    except Exception as e:
        print(f"      提取失败: {e}")
        return []


async def fetch_date_from_national_page(page, date_str):
    """
    通过全国汇总页面抓取指定日期的烟台价格
    URL格式: /p/YYMMDD09/HASH.html
    """
    # 构造URL
    date_parts = date_str.split('-')
    yy = date_parts[0][2:]  # 26
    mm = date_parts[1]       # 06
    dd = date_parts[2]       # 09

    # 使用固定的HASH模式（根据探索结果）
    # /p/26060901/格式
    date_code = f"{yy}{mm}{dd}09"

    # 尝试多个可能的HASH
    possible_hashes = [
        '864C3A3F5673C262',  # 螺纹钢汇总
        'F604D782F4BDF4E5',  # 线材汇总
        '5650DE9E6DE32BE1',  # 盘螺汇总
    ]

    print(f"\n[{date_str}] 开始抓取...")

    all_prices = []

    for hash_val in possible_hashes:
        try:
            url = f"https://jiancai.mysteel.com/p/{date_code}/{hash_val}.html"
            print(f"  尝试: {url}")

            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(2)

            # 检查页面是否有效
            page_text = await page.evaluate('() => document.body.textContent')
            if '登录' in page_text and len(page_text) < 500:
                print(f"    需要登录，跳过")
                continue

            if '404' in page_text or '页面不存在' in page_text:
                print(f"    页面不存在")
                continue

            # 提取烟台价格
            prices = await extract_yantai_prices_from_national_page(page)
            if prices:
                print(f"    OK 提取 {len(prices)} 条数据")
                all_prices.extend(prices)
            else:
                print(f"    X 未提取到数据")

            await asyncio.sleep(1)

        except Exception as e:
            print(f"    错误: {e}")
            continue

    # 去重
    seen = set()
    unique_prices = []
    for p in all_prices:
        key = (p['material_name'], p['spec'], p['price'])
        if key not in seen:
            seen.add(key)
            unique_prices.append(p)

    if unique_prices:
        # 保存到数据库
        inserted = save_to_db(date_str, unique_prices)
        print(f"  [成功] 去重后 {len(unique_prices)} 条，新增 {inserted} 条")
        return unique_prices
    else:
        print(f"  [失败] 未提取到数据")
        return []


async def smart_batch_fetch(start_date, end_date, min_count=111):
    """
    智能批量抓取 - 使用全国汇总页面
    """
    print("=" * 60)
    print("烟台钢筋价格批量抓取 - 全国汇总模式")
    print("=" * 60)
    print(f"\n日期范围: {start_date} ~ {end_date}")
    print(f"最小数据量: {min_count} 条/日期")

    # 初始化
    init_db()
    existing_dates = get_existing_dates()
    print(f"\n[扫描] 已有 {len(existing_dates)} 个日期的数据")

    # 确定需要抓取的日期
    dates_to_fetch = []
    current = datetime.strptime(start_date, '%Y-%m-%d').date()
    end = datetime.strptime(end_date, '%Y-%m-%d').date()

    while current <= end:
        date_str = current.strftime('%Y-%m-%d')
        count = existing_dates.get(date_str, 0)

        if count < min_count:
            dates_to_fetch.append(date_str)
            print(f"  - {date_str}: {count} 条 (需补充)")
        else:
            print(f"  OK {date_str}: {count} 条")

        current += timedelta(days=1)

    print(f"\n[目标] 需要抓取 {len(dates_to_fetch)} 个日期")

    if not dates_to_fetch:
        print("\nOK 所有日期数据充足！")
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
    print("=" * 60)

    success_count = 0
    fail_count = 0
    total_inserted = 0

    for i, date_str in enumerate(dates_to_fetch, 1):
        print(f"\n[{i}/{len(dates_to_fetch)}] {date_str}")

        prices = await fetch_date_from_national_page(page, date_str)

        if prices:
            success_count += 1
            total_inserted += len(prices)
        else:
            fail_count += 1

        # 避免请求过快
        if i < len(dates_to_fetch):
            await asyncio.sleep(2)

    # 汇总
    print("\n" + "=" * 60)
    print("抓取完成!")
    print(f"  成功: {success_count}/{len(dates_to_fetch)}")
    print(f"  失败: {fail_count}/{len(dates_to_fetch)}")
    print(f"  总计: {total_inserted} 条数据")
    print(f"  数据库: {DB_FILE}")
    print("=" * 60)

    await browser.close()
    await playwright.stop()


async def main():
    """抓取最近30天"""
    end = datetime.now().date()
    start = end - timedelta(days=30)

    await smart_batch_fetch(
        start_date=start.strftime('%Y-%m-%d'),
        end_date=end.strftime('%Y-%m-%d'),
        min_count=111
    )


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n[中断] 用户取消操作")
