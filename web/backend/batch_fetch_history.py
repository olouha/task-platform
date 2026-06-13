"""
批量抓取烟台钢筋历史价格数据 - 简化版

基于已验证的抓取逻辑，批量处理历史日期
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
DB_FILE = DATA_DIR / 'yantai_rebar.db'

# 基础URL模板（需要根据实际情况调整）
# 烟台地区价格页面URL格式: https://jiancai.mysteel.com/m/YYMMDDXX/Hash.html
BASE_URL_TEMPLATE = "https://jiancai.mysteel.com/m/{date_code}/E3B5B7AB6E55FC6D.html"


def load_cookies():
    """加载Cookie"""
    if COOKIE_FILE.exists():
        with open(COOKIE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def get_existing_dates():
    """获取已有数据的日期及数量"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        SELECT date, COUNT(DISTINCT material_name || spec || brand || price) as count
        FROM rebar_prices
        GROUP BY date
        ORDER BY date DESC
    ''')
    result = {row[0]: row[1] for row in c.fetchall()}
    conn.close()
    return result


def date_to_url_code(date_str):
    """
    将日期转换为URL代码
    例如: 2026-06-09 → 26060916
    """
    parts = date_str.split('-')
    year_short = parts[0][2:]  # 26
    month = parts[1]           # 06
    day = parts[2]             # 09
    # 最后两位数字可能需要根据实际情况调整
    return f"{year_short}{month}{day}16"


def save_to_db(date_str, prices):
    """保存数据到数据库"""
    if not prices:
        return 0

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # 确保表存在
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

    inserted = 0
    for price in prices:
        try:
            c.execute('INSERT OR IGNORE INTO rebar_prices (date, material_name, spec, brand, price, region) VALUES (?, ?, ?, ?, ?, ?)',
                (date_str, price['material_name'], price['spec'], price['brand'], price['price'], '山东烟台'))
            if c.rowcount > 0:
                inserted += 1
        except Exception as e:
            print(f"      插入错误: {e}")

    conn.commit()
    conn.close()
    return inserted


async def fetch_single_date(page, date_str):
    """抓取单个日期的数据"""
    date_code = date_to_url_code(date_str)
    url = BASE_URL_TEMPLATE.format(date_code=date_code)

    print(f"\n[{date_str}] 正在抓取...")
    print(f"  URL: {url}")

    try:
        await page.goto(url, wait_until='networkidle', timeout=30000)
        await asyncio.sleep(2)

        # 检查页面状态
        page_text = await page.evaluate('() => document.body.textContent')
        if '登录' in page_text and len(page_text) < 500:
            print(f"  [需要登录]")
            return []

        # 提取数据
        data = await page.evaluate('''() => {
            const tables = document.querySelectorAll('table');
            const results = [];

            tables.forEach((table, idx) => {
                const rows = table.querySelectorAll('tr');
                rows.forEach((row) => {
                    const cells = row.querySelectorAll('td');
                    if (cells.length >= 4) {
                        const rowData = Array.from(cells).map(c => c.textContent.trim());
                        if (rowData.length >= 4) {
                            results.push(rowData);
                        }
                    }
                });
            });

            return results;
        }''')

        # 解析价格数据
        prices = []
        for row in data:
            if len(row) >= 4:
                valid_names = ['高线', '螺纹钢', '盘螺', '圆钢']
                for i, cell in enumerate(row):
                    if cell in valid_names and i + 1 < len(row):
                        spec = row[i + 1] if i + 1 < len(row) else ''
                        if spec.startswith('Φ'):
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
                                        break
                                except:
                                    pass
                            break

        print(f"  [OK] 提取 {len(prices)} 条数据")

        # 保存到数据库
        inserted = save_to_db(date_str, prices)
        print(f"  [保存] 新增 {inserted} 条记录")

        return prices

    except Exception as e:
        print(f"  [错误] {e}")
        return []


async def batch_fetch(start_date, end_date, min_count=111):
    """
    批量抓取历史数据

    Args:
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)
        min_count: 最小数据量要求
    """
    print("=" * 60)
    print("批量抓取烟台钢筋历史价格")
    print("=" * 60)
    print(f"\n日期范围: {start_date} ~ {end_date}")
    print(f"最小数据量: {min_count} 条")

    # 获取现有数据
    print("\n[扫描] 现有数据...")
    existing_dates = get_existing_dates()
    print(f"  已有 {len(existing_dates)} 个日期")

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
            print(f"  [OK] {date_str}: {count} 条")

        current += timedelta(days=1)

    print(f"\n[目标] 需要抓取/补充 {len(dates_to_fetch)} 个日期")

    if not dates_to_fetch:
        print("\n所有日期数据充足！")
        return

    # 加载Cookie
    cookies = load_cookies()
    if not cookies:
        print("\n[错误] 未找到Cookie!")
        print("请先运行: python manual_login_save_cookie.py")
        return

    print(f"\n[Cookie] 使用 {len(cookies)} 条")

    # 启动浏览器
    print("\n[启动] 浏览器...")
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=True)
    context = await browser.new_context(viewport={'width': 1920, 'height': 1080}, locale='zh-CN')
    await context.add_cookies(cookies)
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

        prices = await fetch_single_date(page, date_str)

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
    print("=" * 60)

    await browser.close()
    await playwright.stop()


# 使用示例
async def main():
    # 抓取最近10天的数据
    end = datetime.now().date()
    start = end - timedelta(days=10)

    await batch_fetch(
        start_date=start.strftime('%Y-%m-%d'),
        end_date=end.strftime('%Y-%m-%d'),
        min_count=111
    )


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n[中断] 用户取消操作")
