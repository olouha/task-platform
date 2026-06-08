"""
烟台钢筋价格历史数据抓取 v2
从 https://jiancai.mysteel.com/market/pa228aa010101a0a01010205aaaa1.html 抓取
支持日期范围选择和连续抓取
"""
import asyncio
import sys
import json
import time
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, '.')

from playwright.async_api import async_playwright
import sqlite3

DATA_DIR = Path('services/data')
DB_FILE = DATA_DIR / 'yantai_rebar.db'
HISTORY_URL = 'https://jiancai.mysteel.com/market/pa228aa010101a0a01010205aaaa1.html'


def init_database():
    """初始化数据库"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS rebar_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            fetch_time TEXT,
            material_name TEXT,
            spec TEXT,
            material_type TEXT,
            brand TEXT,
            price INTEGER,
            region TEXT DEFAULT '山东烟台',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(date, fetch_time, material_name, spec, brand, price)
        )
    ''')

    c.execute('CREATE INDEX IF NOT EXISTS idx_date ON rebar_prices(date)')
    conn.commit()
    conn.close()


def get_existing_data():
    """获取已抓取的数据键"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT date, fetch_time, material_name, spec, brand FROM rebar_prices')
    existing = set(f"{r[0]}_{r[1]}_{r[2]}_{r[3]}_{r[4]}" for r in c.fetchall())
    conn.close()
    return existing


async def fetch_single_date(page, date_str: str, existing: set):
    """抓取单个日期的数据"""
    try:
        # 点击开始日期输入框
        start_input = await page.query_selector('input.startTime')
        if start_input:
            await start_input.click()
            await page.wait_for_timeout(500)
        else:
            print('  [ERROR] 未找到开始日期输入框')
            return 0

        # 清空并输入日期
        await start_input.fill('')
        await page.wait_for_timeout(200)
        await start_input.fill(date_str)
        await page.wait_for_timeout(500)

        # 输入结束日期（同一天）
        end_input = await page.query_selector('input.endTime')
        if end_input:
            await end_input.click()
            await page.wait_for_timeout(300)
            await end_input.fill('')
            await end_input.fill(date_str)
            await page.wait_for_timeout(500)

        # 点击搜索按钮
        search_btn = await page.query_selector('button:has-text("搜索")')
        if not search_btn:
            search_btn = await page.query_selector('.search-btn')
        if not search_btn:
            search_btn = await page.query_selector('button[class*="search"]')

        if search_btn:
            await search_btn.click()
            print(f'    已点击搜索')
        else:
            print(f'    [WARN] 未找到搜索按钮，尝试直接等待')

        # 等待数据加载
        await page.wait_for_timeout(3000)

        # 提取表格数据
        data = await page.evaluate('''() => {
            const results = [];
            const tables = document.querySelectorAll('table');
            tables.forEach(table => {
                const tbody = table.querySelector('tbody');
                if (tbody) {
                    const rows = tbody.querySelectorAll('tr');
                    rows.forEach(row => {
                        const cells = row.querySelectorAll('td');
                        const rowData = [];
                        cells.forEach(cell => rowData.push(cell.textContent.trim()));
                        if (rowData.length >= 5) results.push(rowData);
                    });
                }
            });
            return results;
        }''')

        if not data:
            print(f'    [WARN] 未找到数据表格')
            return 0

        # 解析数据
        prices = []
        for row in data:
            if len(row) >= 6:
                material_name = str(row[0]).strip()
                spec = str(row[1]).strip()
                material_type = str(row[2]).strip()
                brand = str(row[3]).strip()
                price_str = str(row[4]).strip()

                # 验证数据
                valid_names = ['高线', '螺纹钢', '盘螺', '圆钢']
                if material_name in valid_names and spec.startswith('Φ'):
                    try:
                        price = int(''.join(filter(str.isdigit, price_str)))
                        if price > 0:
                            key = f"{date_str}_{datetime.now().strftime('%H:%M:%S')}_{material_name}_{spec}_{brand}"
                            prices.append({
                                'date': date_str,
                                'fetch_time': datetime.now().strftime('%H:%M:%S'),
                                'material_name': material_name,
                                'spec': spec,
                                'material_type': material_type,
                                'brand': brand,
                                'price': price,
                                'key': key
                            })
                    except:
                        pass

        if not prices:
            print(f'    [WARN] 未提取到有效数据')
            return 0

        # 保存到数据库
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()

        inserted = 0
        for p_data in prices:
            if p_data['key'] not in existing:
                try:
                    c.execute('''
                        INSERT INTO rebar_prices
                        (date, fetch_time, material_name, spec, material_type, brand, price, region)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        p_data['date'], p_data['fetch_time'], p_data['material_name'],
                        p_data['spec'], p_data['material_type'], p_data['brand'],
                        p_data['price'], '山东烟台'
                    ))
                    inserted += 1
                    existing.add(p_data['key'])
                except:
                    pass

        conn.commit()
        conn.close()

        print(f'    [OK] 提取 {len(prices)} 条，新增 {inserted} 条')
        return inserted

    except Exception as e:
        print(f'    [ERROR] {e}')
        return 0


async def fetch_by_date_range(start_date: str, end_date: str, interval_seconds: int = 15):
    """按日期范围抓取"""
    print(f'开始抓取: {start_date} 至 {end_date}')
    print(f'抓取间隔: {interval_seconds} 秒')

    # 加载凭据
    with open(DATA_DIR / 'mysteel_config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
        username = config.get('username')
        password = config.get('password')

    init_database()
    existing = get_existing_data()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 3000},
            locale='zh-CN'
        )
        page = await context.new_page()

        # 登录
        print('\n1. 登录中...')
        await page.goto('https://passport.mysteel.com/', wait_until='domcontentloaded', timeout=60000)
        await page.wait_for_timeout(5000)

        try:
            account_tab = await page.query_selector('.form-tab-account, a[data-tab="account"]')
            if account_tab:
                await account_tab.click()
                await page.wait_for_timeout(2000)
        except: pass

        await page.evaluate(f'''() => {{
            const inputs = document.querySelectorAll('input');
            for (const inp of inputs) {{
                const ph = inp.placeholder || '';
                if (ph.includes('用户名')) inp.value = '{username}';
                if (ph.includes('密码') && inp.type === 'password') inp.value = '{password}';
            }}
        }}''')
        await page.wait_for_timeout(500)

        try:
            login_btn = await page.query_selector('.form-button-login, button:has-text("登录")')
            if login_btn:
                await login_btn.click()
        except: pass

        await page.wait_for_timeout(8000)
        print('  登录完成')

        # 访问历史页面
        print('\n2. 访问历史页面...')
        await page.goto(HISTORY_URL, wait_until='networkidle', timeout=60000)
        await page.wait_for_timeout(5000)

        # 保存初始截图
        await page.screenshot(path=str(DATA_DIR / 'history_start.png'), full_page=True)
        print('  初始页面已保存: history_start.png')

        # 生成日期列表
        current = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        dates = []

        while current <= end:
            dates.append(current.strftime('%Y-%m-%d'))
            current += timedelta(days=1)

        print(f'\n3. 开始逐日抓取...')

        total_inserted = 0
        success_count = 0

        for i, date in enumerate(dates):
            print(f'\n[{i+1}/{len(dates)}] {date}')

            inserted = await fetch_single_date(page, date, existing)

            if inserted > 0:
                success_count += 1
                total_inserted += inserted

            # 等待间隔
            if i < len(dates) - 1:
                print(f'  等待 {interval_seconds} 秒...')
                await page.wait_for_timeout(interval_seconds * 1000)

        await browser.close()

        print('\n' + '=' * 60)
        print('抓取完成')
        print(f'  成功日期: {success_count}/{len(dates)}')
        print(f'  新增记录: {total_inserted} 条')
        print('=' * 60)


async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='烟台钢筋价格历史数据抓取')
    parser.add_argument('--start', '-s', default='2024-01-01', help='开始日期 (YYYY-MM-DD)')
    parser.add_argument('--end', '-e', default=None, help='结束日期 (YYYY-MM-DD)')
    parser.add_argument('--interval', '-i', type=int, default=15, help='抓取间隔秒数')

    args = parser.parse_args()

    end_date = args.end or datetime.now().strftime('%Y-%m-%d')

    await fetch_by_date_range(args.start, end_date, args.interval)


if __name__ == '__main__':
    asyncio.run(main())