"""
批量抓取烟台钢筋价格历史数据
"""
import asyncio
import sys
import json
import sqlite3
import re
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, '.')

from playwright.async_api import async_playwright

DATA_DIR = Path('services/data')
DB_FILE = DATA_DIR / 'yantai_rebar.db'
CONFIG_FILE = DATA_DIR / 'mysteel_config.json'


def load_credentials():
    """加载登录凭据"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get('username', 'M6616592358'), config.get('password', 'panhui199261')
        except:
            pass
    return 'M6616592358', 'panhui199261'


def get_existing_dates():
    """获取已存在的日期"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT DISTINCT date FROM rebar_prices')
    dates = set(row[0] for row in c.fetchall())
    conn.close()
    return dates


def get_missing_dates():
    """获取缺失的日期列表"""
    existing = get_existing_dates()
    start = datetime(2024, 1, 1)
    end = datetime(2026, 5, 30)
    missing = []
    current = start
    while current <= end:
        if current.weekday() < 5:
            date_str = current.strftime('%Y-%m-%d')
            if date_str not in existing:
                missing.append(date_str)
        current += timedelta(days=1)
    return missing


def save_prices(date, fetch_time, prices):
    """保存价格数据到数据库"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    inserted = 0
    for p in prices:
        try:
            c.execute('''
                INSERT OR IGNORE INTO rebar_prices
                (date, fetch_time, material_name, spec, material_type, brand, price, region)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (date, fetch_time, p['material_name'], p['spec'],
                  p.get('material_type', ''), p.get('brand', ''),
                  int(p['price']), '山东烟台'))
            if c.rowcount > 0:
                inserted += 1
        except:
            pass
    conn.commit()
    conn.close()
    return inserted


async def main():
    username, password = load_credentials()

    print('=' * 60)
    print('批量抓取烟台钢筋价格历史数据')
    missing = get_missing_dates()
    print(f'缺失日期数: {len(missing)}')
    print('=' * 60)

    if not missing:
        print('没有缺失日期!')
        return

    # 限制只抓取前50个缺失日期进行测试
    test_dates = missing[:50]
    print(f'测试抓取前 {len(test_dates)} 个日期...')

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={'width': 1920, 'height': 3000}, locale='zh-CN')
        page = await context.new_page()

        # 登录
        print('\n1. 登录...')
        await page.goto('https://passport.mysteel.com/', wait_until='networkidle', timeout=60000)
        await page.wait_for_timeout(3000)

        try:
            account_tab = await page.query_selector('.form-tab-account, a[data-tab="account"]')
            if account_tab:
                await account_tab.click()
                await page.wait_for_timeout(2000)
        except:
            pass

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
            checkbox = await page.query_selector('input[type="checkbox"]')
            if checkbox and not await checkbox.is_checked():
                await checkbox.click()
        except:
            pass

        try:
            login_btn = await page.query_selector('.form-button-login, button:has-text("登录")')
            if login_btn:
                await login_btn.click()
        except:
            pass

        await page.wait_for_timeout(8000)
        print('  登录完成')

        # 获取市场页面链接
        print('\n2. 获取市场页面链接...')
        url = 'https://jiancai.mysteel.com/market/pa228aa010101a0a01010205aaaa1.html'
        await page.goto(url, wait_until='domcontentloaded', timeout=60000)
        await page.wait_for_timeout(5000)

        # 获取所有链接
        all_links = await page.evaluate('''() => {
            const results = [];
            document.querySelectorAll('a[href*="jiancai.mysteel.com/m/"]').forEach(a => {
                results.push({ text: a.textContent.trim(), href: a.getAttribute('href') });
            });
            return results;
        }''')
        print(f'  找到 {len(all_links)} 个链接')

        # 按日期分组链接
        date_urls = {}
        for link in all_links:
            match = re.search(r'/(\d{2})(\d{2})(\d{2})/', link['href'])
            if match:
                yy, mm, dd = match.groups()
                date_str = f'20{yy}-{mm}-{dd}'
                if date_str not in date_urls:
                    date_urls[date_str] = []
                date_urls[date_str].append(link['href'])

        print(f'  解析出 {len(date_urls)} 个日期的URL')

        # 抓取测试日期
        print('\n3. 开始抓取...')
        total_inserted = 0
        success_count = 0

        for i, date in enumerate(test_dates):
            if date not in date_urls:
                print(f'[{i+1}/{len(test_dates)}] {date} - 未找到链接')
                continue

            print(f'[{i+1}/{len(test_dates)}] {date}', end='')

            # 抓取数据
            page_url = date_urls[date][0]
            await page.goto(page_url, wait_until='domcontentloaded', timeout=60000)
            await page.wait_for_timeout(5000)

            # 提取数据
            data = await page.evaluate('''() => {
                const tables = document.querySelectorAll('table');
                const results = [];
                tables.forEach((table) => {
                    const rows = table.querySelectorAll('tr');
                    rows.forEach((row) => {
                        const cells = row.querySelectorAll('td, th');
                        const rowData = [];
                        cells.forEach(c => rowData.push(c.textContent.trim()));
                        if (rowData.length >= 5) results.push(rowData);
                    });
                });
                return results;
            }''')

            prices = []
            for row in data:
                if len(row) >= 5:
                    material_name = str(row[0]).strip()
                    spec = str(row[1]).strip()
                    material_type = str(row[2]).strip() if len(row) > 2 else ''
                    brand = str(row[3]).strip() if len(row) > 3 else ''
                    price_str = str(row[4]).strip() if len(row) > 4 else ''

                    valid_names = ['高线', '螺纹钢', '盘螺', '圆钢']
                    if material_name in valid_names and spec.startswith('Φ') and price_str.isdigit():
                        try:
                            price = int(price_str)
                            if price > 0:
                                prices.append({
                                    'material_name': material_name,
                                    'spec': spec,
                                    'material_type': material_type,
                                    'brand': brand,
                                    'price': price
                                })
                        except:
                            pass

            if prices:
                inserted = save_prices(date, '09:00', prices)
                print(f' - {len(prices)}条, 新增{inserted}')
                total_inserted += inserted
                success_count += 1
            else:
                print(' - 无数据')

            await page.wait_for_timeout(3000)

        await browser.close()

        print('\n' + '=' * 60)
        print(f'抓取完成!')
        print(f'成功: {success_count}/{len(test_dates)} 天')
        print(f'新增记录: {total_inserted} 条')
        print('=' * 60)


if __name__ == '__main__':
    asyncio.run(main())
