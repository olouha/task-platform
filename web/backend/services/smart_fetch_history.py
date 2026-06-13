"""
烟台钢筋价格历史抓取 - 智能版
从页面的历史链接导航获取正确的URL
"""
import asyncio
import json
import sqlite3
import sys
from pathlib import Path
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

DATA_DIR = Path('services/data')
COOKIE_FILE = DATA_DIR / 'mysteel_cookies.json'
DB_FILE = DATA_DIR / 'yantai_rebar.db')


def load_cookies():
    """加载Cookie"""
    if COOKIE_FILE.exists():
        with open(COOKIE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def get_existing_dates():
    """获取已有数据的日期及数量"""
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


def init_db():
    """初始化数据库"""
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


def save_to_db(date_str, prices, period='AM'):
    """保存数据到数据库"""
    if not prices:
        return 0

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    inserted = 0
    fetch_time = f"{period}:10:00" if period == 'AM' else f"{period}:04:00"

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
            print(f"      插入错误: {e}")

    conn.commit()
    conn.close()
    return inserted


async def extract_historical_links(page, target_date):
    """
    从当前页面提取历史日期链接
    网站通常有日期选择器或历史数据导航
    """
    try:
        # 尝试查找日期选择器
        date_links = await page.evaluate('''() => {
            const links = [];

            // 查找所有可能包含日期的链接
            const allLinks = document.querySelectorAll('a[href*="mysteel.com/m/"]');

            allLinks.forEach(link => {
                const href = link.href;
                const text = link.textContent.trim();

                // 匹配URL格式: /YYMMDDHH/Hash.html
                const match = href.match(/\/(\d{8})\/([A-F0-9]+)\.html/);
                if (match) {
                    links.push({
                        url: href,
                        code: match[1],  // YYMMDDHH
                        text: text
                    });
                }
            });

            return links;
        }''')

        return date_links
    except Exception as e:
        print(f"    [链接提取失败] {e}")
        return []


async def fetch_with_date_navigation(page, date_str, period='AM'):
    """
    通过日期导航抓取指定日期的数据

    策略：
    1. 先访问已知的有效价格页面
    2. 从页面中查找历史日期链接或日期选择器
    3. 导航到目标日期
    4. 提取数据
    """

    # 基础价格页面（当前有效页面）
    base_url = 'https://jiancai.mysteel.com/m/26051410/25B3355C6617BD3C.html'

    print(f"\n[{date_str} {period}] 开始抓取...")

    try:
        # 1. 访问基础页面
        print(f"  [1/3] 访问基础页面...")
        await page.goto(base_url, wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(2)

        # 2. 查找历史链接
        print(f"  [2/3] 查找历史日期链接...")
        historical_links = await extract_historical_links(page, date_str)

        if historical_links:
            print(f"    找到 {len(historical_links)} 个历史链接")

            # 尝试匹配目标日期
            target_code = date_str.replace('-', '')  # YYYYMMDD
            target_code_short = target_code[2:]      # YYMMDD

            # 查找匹配的链接
            matched_url = None
            for link in historical_links:
                code = link['code']
                # 检查是否匹配目标日期 (前6位是YYMMDD)
                if code[:6] == target_code_short:
                    # 根据时间段选择小时 (AM=10, PM=16)
                    expected_hour = '10' if period == 'AM' else '16'
                    if code[6] == expected_hour or len(code) == 6:
                        matched_url = link['url']
                        break

            if matched_url:
                print(f"    找到匹配URL: {matched_url}")
                await page.goto(matched_url, wait_until='domcontentloaded', timeout=30000)
                await asyncio.sleep(2)
            else:
                print(f"    [未找到] 目标日期 {date_str} 的链接")
                # 尝试构造URL (使用已知的hash格式)
                constructed_url = f"https://jiancai.mysteel.com/m/{target_code_short}10/25B3355C6617BD3C.html"
                print(f"    尝试构造URL: {constructed_url}")
                await page.goto(constructed_url, wait_until='domcontentloaded', timeout=30000)
                await asyncio.sleep(2)
        else:
            print(f"    [未找到] 历史链接，尝试构造URL")
            # 构造URL
            target_code_short = date_str.replace('-', '')[2:]
            hour = '10' if period == 'AM' else '16'
            constructed_url = f"https://jiancai.mysteel.com/m/{target_code_short}{hour}/25B3355C6617BD3C.html"
            print(f"    尝试: {constructed_url}")
            await page.goto(constructed_url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(2)

        # 3. 提取数据
        print(f"  [3/3] 提取价格数据...")
        prices = await extract_prices_from_page(page)

        if prices:
            # 保存到数据库
            inserted = save_to_db(date_str, prices, period)
            print(f"    [成功] 提取 {len(prices)} 条，新增 {inserted} 条")
            return prices
        else:
            print(f"    [失败] 未提取到数据")
            return []

    except Exception as e:
        print(f"    [错误] {e}")
        return []


async def extract_prices_from_page(page):
    """从页面提取价格数据"""
    try:
        data = await page.evaluate('''() => {
            const tables = document.querySelectorAll('table');
            const results = [];

            tables.forEach((table) => {
                const rows = table.querySelectorAll('tr');
                rows.forEach((row) => {
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

                if material_name in valid_names and spec.startswith('Φ') and price_str.isdigit():
                    try:
                        price = int(price_str)
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
        print(f"      [提取失败] {e}")
        return []


async def smart_batch_fetch(start_date, end_date, min_count=111):
    """
    智能批量抓取 - 从页面历史链接导航
    """
    print("=" * 60)
    print("烟台钢筋价格智能批量抓取")
    print("=" * 60)
    print(f"\n日期范围: {start_date} ~ {end_date}")
    print(f"最小数据量: {min_count} 条/日期")

    # 初始化数据库
    init_db()

    # 获取现有数据
    print("\n[扫描] 现有数据...")
    existing_dates = get_existing_dates()
    print(f"  已有 {len(existing_dates)} 个日期的数据")

    # 确定需要抓取的日期
    print("\n[计划] 确定抓取目标...")
    dates_to_fetch = []

    current = datetime.strptime(start_date, '%Y-%m-%d').date()
    end = datetime.strptime(end_date, '%Y-%m-%d').date()

    while current <= end:
        date_str = current.strftime('%Y-%m-%d')
        count = existing_dates.get(date_str, 0)

        if count < min_count:
            dates_to_fetch.append({
                'date': date_str,
                'current': count,
                'needed': min_count - count
            })
            print(f"  - {date_str}: {count} 条 (需补充)")
        else:
            print(f"  ✓ {date_str}: {count} 条 (充足)")

        current += timedelta(days=1)

    print(f"\n[目标] 需要抓取/补充 {len(dates_to_fetch)} 个日期")

    if not dates_to_fetch:
        print("\n✓ 所有日期数据充足！")
        return

    # 加载Cookie
    cookies = load_cookies()
    if not cookies:
        print("\n[警告] 未找到Cookie，将尝试直接访问")

    # 启动浏览器
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

    for i, item in enumerate(dates_to_fetch, 1):
        date_str = item['date']
        print(f"\n[{i}/{len(dates_to_fetch)}] {date_str}")

        # 尝试抓取上午数据
        prices_am = await fetch_with_date_navigation(page, date_str, 'AM')
        await asyncio.sleep(2)

        # 尝试抓取下午数据
        prices_pm = await fetch_with_date_navigation(page, date_str, 'PM')
        await asyncio.sleep(2)

        all_prices = prices_am + prices_pm
        if all_prices:
            success_count += 1
            total_inserted += len(all_prices)
            print(f"  ✓ 成功: AM={len(prices_am)}, PM={len(prices_pm)}")
        else:
            fail_count += 1
            print(f"  ✗ 失败")

        # 避免请求过快
        if i < len(dates_to_fetch):
            await asyncio.sleep(3)

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
    """主函数 - 抓取最近30天"""
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
