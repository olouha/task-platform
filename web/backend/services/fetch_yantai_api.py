"""
山东烟台钢筋价格抓取 - 支持历史数据 API
"""
import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional

sys.path.insert(0, '.')

from playwright.async_api import async_playwright
import openpyxl

DATA_DIR = Path('services/data')
DATA_DIR.mkdir(exist_ok=True)


def load_credentials():
    """从配置文件加载凭据"""
    config_file = DATA_DIR / 'mysteel_config.json'
    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get('username', 'M6616592358'), config.get('password', 'mysteel573005')
        except: pass
    return 'M6616592358', 'mysteel573005'


async def get_historical_dates(page) -> List[dict]:
    """获取历史日期列表"""
    url = 'https://jiancai.mysteel.com/market/pa228aa010101a0a01010205aaaa1.html'
    await page.goto(url, wait_until='domcontentloaded', timeout=60000)
    await page.wait_for_timeout(5000)

    items = await page.evaluate('''() => {
        const results = [];
        const links = document.querySelectorAll('a[href*="mysteel.com/m/"]');

        links.forEach(link => {
            const text = link.textContent.trim();
            const href = link.getAttribute('href');

            const dateMatch = text.match(/(\d{1,2})月(\d{1,2})日(?:\((\d{1,2}):(\d{1,2})\))?/);

            if (dateMatch) {
                const month = dateMatch[1].padStart(2, '0');
                const day = dateMatch[2].padStart(2, '0');
                const hour = dateMatch[3] ? dateMatch[3].padStart(2, '0') : '10';
                const minute = dateMatch[4] ? dateMatch[4].padStart(2, '0') : '10';

                results.push({
                    date: `2025-${month}-${day}`,
                    time: `${hour}:${minute}`,
                    url: href || ''
                });
            }
        });

        const uniqueMap = new Map();
        results.forEach(item => {
            if (!uniqueMap.has(item.date)) {
                uniqueMap.set(item.date, item);
            }
        });

        return Array.from(uniqueMap.values()).sort((a, b) => b.date.localeCompare(a.date));
    }''')

    return items


async def fetch_prices_for_date(page, date_info: dict) -> List[dict]:
    """抓取指定日期的价格数据"""
    url = date_info['url']
    await page.goto(url, wait_until='domcontentloaded', timeout=60000)
    await page.wait_for_timeout(5000)

    data = await page.evaluate('''() => {
        const tables = document.querySelectorAll('table');
        const results = [];
        tables.forEach((table, idx) => {
            const rows = table.querySelectorAll('tr');
            const tableData = [];
            rows.forEach((row) => {
                const cells = row.querySelectorAll('td, th');
                const rowData = [];
                cells.forEach(c => rowData.push(c.textContent.trim()));
                if (rowData.length > 0) tableData.push(rowData);
            });
            if (tableData.length > 0) results.push({idx, rows: tableData});
        });
        return results;
    }''')

    prices = []
    for t in data:
        for row in t['rows']:
            if row and len(row) >= 5:
                material_name = row[0].strip()
                spec = row[1].strip()
                material_type = row[2].strip()
                brand = row[3].strip()
                price_str = row[4].strip()

                valid_names = ['高线', '螺纹钢', '盘螺', '圆钢']
                if material_name in valid_names and spec.startswith('Φ') and price_str.isdigit():
                    prices.append({
                        'date': date_info['date'],
                        'time': date_info['time'],
                        'material_name': material_name,
                        'spec': spec,
                        'material_type': material_type,
                        'brand': brand,
                        'price': float(price_str),
                        'region': '山东烟台'
                    })

    return prices


async def fetch_historical_prices(days: int = 7) -> dict:
    """抓取历史价格数据（最近N天）"""
    username, password = load_credentials()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 3000}, locale='zh-CN')
        page = await context.new_page()

        try:
            # 登录
            print('1. 登录...')
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

            # 获取历史日期
            print('2. 获取历史日期列表...')
            dates = await get_historical_dates(page)
            dates = dates[:days]  # 只取最近的N天
            print(f'  找到 {len(dates)} 个历史日期')

            # 抓取每天的数据
            all_prices = {}
            for i, date_info in enumerate(dates, 1):
                print(f'  {i}/{len(dates)} 抓取 {date_info["date"]} ...')
                prices = await fetch_prices_for_date(page, date_info)
                all_prices[date_info['date']] = {
                    'prices': prices,
                    'time': date_info['time'],
                    'count': len(prices)
                }
                await page.wait_for_timeout(2000)

            await browser.close()

            return {
                'success': True,
                'data': all_prices,
                'dates_fetched': len(all_prices),
                'total_prices': sum(d['count'] for d in all_prices.values())
            }

        except Exception as e:
            print(f'错误: {e}')
            await browser.close()
            return {
                'success': False,
                'error': str(e),
                'data': {}
            }


async def main():
    result = await fetch_historical_prices(days=3)
    if result['success']:
        print(f'\n抓取完成: {result["dates_fetched"]}天, 共{result["total_prices"]}条数据')
        for date, info in result['data'].items():
            print(f'  {date}: {info["count"]}条')


if __name__ == '__main__':
    asyncio.run(main())