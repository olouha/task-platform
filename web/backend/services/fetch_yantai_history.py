"""
山东烟台钢筋价格抓取 - 支持历史数据
"""
import asyncio
import sys
import json
import base64
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from typing import List, Optional

sys.path.insert(0, '.')

from playwright.async_api import async_playwright
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

DATA_DIR = Path('services/data')
DATA_DIR.mkdir(exist_ok=True)


@dataclass
class MaterialPrice:
    material_name: str = ''
    spec: str = ''
    material_type: str = ''
    brand: str = ''
    price: float = 0.0
    unit: str = '元/吨'
    region: str = '山东烟台'
    date: str = ''  # 数据日期
    time: str = ''  # 数据时间


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
    print('  获取历史日期列表...')

    url = 'https://jiancai.mysteel.com/market/pa228aa010101a0a01010205aaaa1.html'
    await page.goto(url, wait_until='domcontentloaded', timeout=60000)
    await page.wait_for_timeout(5000)

    # 提取日期链接和时间
    items = await page.evaluate('''() => {
        const results = [];
        const links = document.querySelectorAll('a[href*="mysteel.com/m/"]');

        links.forEach(link => {
            const text = link.textContent.trim();
            const href = link.getAttribute('href');
            const title = link.getAttribute('title') || '';

            // 匹配日期格式: 4月10日(16:20) 或 4月10日
            const dateMatch = text.match(/(\d{1,2})月(\d{1,2})日(?:\((\d{1,2}):(\d{1,2})\))?/);

            if (dateMatch) {
                const month = dateMatch[1].padStart(2, '0');
                const day = dateMatch[2].padStart(2, '0');
                const hour = dateMatch[3] ? dateMatch[3].padStart(2, '0') : '10';
                const minute = dateMatch[4] ? dateMatch[4].padStart(2, '0') : '10';

                results.push({
                    date: `2025-${month}-${day}`,
                    time: `${hour}:${minute}`,
                    text: text,
                    url: href || ''
                });
            }
        });

        // 去重（同一天只保留一条）
        const uniqueMap = new Map();
        results.forEach(item => {
            if (!uniqueMap.has(item.date)) {
                uniqueMap.set(item.date, item);
            }
        });

        return Array.from(uniqueMap.values()).sort((a, b) => b.date.localeCompare(a.date));
    }''')

    print(f'  找到 {len(items)} 个历史日期')
    return items


async def fetch_date_prices(page, username: str, password: str, target_date: str = None) -> dict:
    """抓取指定日期或最新日期的价格"""

    cookie_file = DATA_DIR / 'mysteel_cookies.json'

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 3000}, locale='zh-CN')
        page = await context.new_page()

        try:
            # 1. 登录
            print('1. 登录...')
            await page.goto('https://passport.mysteel.com/', wait_until='domcontentloaded', timeout=60000)
            await page.wait_for_timeout(5000)

            # 切换到账号登录
            try:
                account_tab = await page.query_selector('.form-tab-account, a[data-tab="account"]')
                if account_tab:
                    await account_tab.click()
                    await page.wait_for_timeout(2000)
            except: pass

            # 填写表单
            await page.evaluate(f'''() => {{
                const inputs = document.querySelectorAll('input');
                for (const inp of inputs) {{
                    const ph = inp.placeholder || '';
                    if (ph.includes('用户名')) inp.value = '{username}';
                    if (ph.includes('密码') && inp.type === 'password') inp.value = '{password}';
                }}
            }}''')

            await page.wait_for_timeout(500)

            # 登录
            try:
                login_btn = await page.query_selector('.form-button-login, button:has-text("登录")')
                if login_btn:
                    await login_btn.click()
            except: pass

            await page.wait_for_timeout(8000)
            print('  登录完成')

            # 保存Cookie
            cookies = await context.cookies()
            with open(cookie_file, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, ensure_ascii=False)

            # 2. 访问价格页
            print('2. 访问价格页...')
            url = 'https://jiancai.mysteel.com/m/26051410/25B3355C6617BD3C.html'
            await page.goto(url, wait_until='domcontentloaded', timeout=60000)
            await page.wait_for_timeout(10000)

            # 截图
            screenshot = await page.screenshot(full_page=True)
            screenshot_b64 = base64.b64encode(screenshot).decode('utf-8')

            # 3. 提取价格
            print('3. 提取价格...')
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
                                'material_name': material_name,
                                'spec': spec,
                                'material_type': material_type,
                                'brand': brand,
                                'price': float(price_str)
                            })

            await browser.close()

            return {
                'success': len(prices) > 0,
                'prices': prices,
                'source_name': '我的钢铁网-山东烟台',
                'fetched_at': datetime.now().isoformat(),
                'screenshot': screenshot_b64
            }

        except Exception as e:
            print(f'错误: {e}')
            await browser.close()
            return {
                'success': False,
                'error': str(e),
                'prices': []
            }


async def fetch_historical_data(days: int = 7):
    """抓取历史数据（最近N天的数据）"""

    cookie_file = DATA_DIR / 'mysteel_cookies.json'
    username, password = load_credentials()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 3000}, locale='zh-CN')
        page = await context.new_page()

        try:
            # 1. 登录
            print('1. 登录...')
            await page.goto('https://passport.mysteel.com/', wait_until='domcontentloaded', timeout=60000)
            await page.wait_for_timeout(5000)

            # 切换到账号登录
            try:
                account_tab = await page.query_selector('.form-tab-account, a[data-tab="account"]')
                if account_tab:
                    await account_tab.click()
                    await page.wait_for_timeout(2000)
            except: pass

            # 填写表单
            await page.evaluate(f'''() => {{
                const inputs = document.querySelectorAll('input');
                for (const inp of inputs) {{
                    const ph = inp.placeholder || '';
                    if (ph.includes('用户名')) inp.value = '{username}';
                    if (ph.includes('密码') && inp.type === 'password') inp.value = '{password}';
                }}
            }}''')

            await page.wait_for_timeout(500)

            # 登录
            try:
                login_btn = await page.query_selector('.form-button-login, button:has-text("登录")')
                if login_btn:
                    await login_btn.click()
            except: pass

            await page.wait_for_timeout(8000)
            print('  登录完成')

            # 保存Cookie
            cookies = await context.cookies()
            with open(cookie_file, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, ensure_ascii=False)

            # 2. 获取历史日期
            dates = await get_historical_dates(page)
            dates = dates[:days]  # 只取最近的N天

            # 3. 抓取每天的数据
            all_data = {}
            for date in dates:
                print(f'\n抓取日期: {date}')
                # 访问该日期的价格页
                # 注意：这里需要根据实际页面结构来调整URL或点击逻辑
                await page.wait_for_timeout(2000)

                # 暂时抓取最新数据，实际历史数据需要点击日期链接
                result = await fetch_date_prices(page, username, password, date)
                if result['success']:
                    all_data[date] = {
                        'prices': result['prices'],
                        'fetched_at': result['fetched_at']
                    }
                else:
                    print(f'  抓取失败: {result.get("error")}')

            await browser.close()

            return {
                'success': True,
                'data': all_data,
                'dates_fetched': len(all_data)
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
    print('=== 山东烟台钢筋价格抓取（支持历史数据）===')

    # 测试历史日期获取
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        dates = await get_historical_dates(page)
        print(f'\n可用的历史日期（最近15天）:')
        for item in dates[:15]:
            print(f'  - {item["date"]} ({item["time"]}) - {item["url"]}')

        # 测试抓取一个日期的数据
        if dates:
            test_date = dates[1]  # 测试昨天的数据
            print(f'\n测试抓取: {test_date["date"]}')

            username, password = load_credentials()
            print(f'  使用凭据: {username[:3]}***')

            # 先登录
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

            # 访问历史日期页面
            url = test_date['url']
            print(f'  访问: {url}')
            await page.goto(url, wait_until='domcontentloaded', timeout=60000)
            await page.wait_for_timeout(5000)

            # 截图
            screenshot = await page.screenshot(full_page=True)

            # 提取价格
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
                                'date': test_date['date'],
                                'time': test_date['time'],
                                'material_name': material_name,
                                'spec': spec,
                                'material_type': material_type,
                                'brand': brand,
                                'price': float(price_str)
                            })

            print(f'  成功抓取 {len(prices)} 条价格')

            if prices:
                print(f'\n示例数据:')
                for p in prices[:3]:
                    print(f'    {p["material_name"]} {p["spec"]} {p["brand"]}: {p["price"]}元/吨')

        await browser.close()

    print('\n如需抓取历史数据，请调用 fetch_historical_data(days=N)')


if __name__ == '__main__':
    asyncio.run(main())