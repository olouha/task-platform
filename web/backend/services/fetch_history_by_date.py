"""
烟台钢筋价格历史数据抓取
从 https://jiancai.mysteel.com/market/pa228aa010101a0a01010205aaaa1.html 抓取
支持日期选择和连续抓取
"""
import asyncio
import sys
import json
import time
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, '.')

from playwright.async_api import async_playwright
import openpyxl
import sqlite3

DATA_DIR = Path('services/data')
DB_FILE = DATA_DIR / 'yantai_rebar.db'
COOKIE_FILE = DATA_DIR / 'myst_cookies.json'
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


def get_existing_dates():
    """获取已抓取的日期"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT DISTINCT date, fetch_time FROM rebar_prices')
    existing = set(f"{row[0]}_{row[1]}" for row in c.fetchall())
    conn.close()
    return existing


async def select_date_and_fetch(page, target_date: str, period: str = None):
    """
    选择日期并抓取数据

    Args:
        page: Playwright page对象
        target_date: 目标日期 (YYYY-MM-DD)
        period: 时段 (AM/PM)，None表示不区分
    """
    try:
        # 点击日期选择器
        # 尝试多种方式打开日期选择器
        date_selectors = [
            'input[placeholder*="日期"]',
            'input[placeholder*="选择日期"]',
            '.date-input',
            '[class*="date-picker"] input',
            'input[placeholder*="请选择"]'
        ]

        date_input = None
        for selector in date_selectors:
            try:
                date_input = await page.query_selector(selector)
                if date_input:
                    break
            except:
                continue

        if not date_input:
            print(f'  [WARN] 未找到日期选择器')
            return None

        # 清空并输入日期
        await date_input.click()
        await page.wait_for_timeout(500)

        # 尝试清空并输入新日期
        await date_input.fill('')
        await page.wait_for_timeout(200)

        # 输入日期
        await date_input.type(target_date)
        await page.wait_for_timeout(500)

        # 按回车或点击确定
        await page.keyboard.press('Enter')
        await page.wait_for_timeout(2000)

        # 等待数据加载
        await page.wait_for_timeout(3000)

        # 截取页面
        timestamp = datetime.now().strftime('%H%M%S')
        screenshot_path = DATA_DIR / f'screenshot_{target_date.replace("-", "")}_{timestamp}.png'
        await page.screenshot(path=str(screenshot_path), full_page=True)

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
                        cells.forEach(cell => {
                            rowData.push(cell.textContent.trim());
                        });
                        if (rowData.length >= 5) {
                            results.push(rowData);
                        }
                    });
                }
            });
            return results;
        }''')

        if not data:
            print(f'  [WARN] 未找到数据表格')
            return None

        # 解析数据
        prices = []
        for row in data:
            if len(row) >= 6:
                # 格式: 品名 | 规格 | 材质 | 品牌 | 单价 | 单位 | ...
                material_name = row[0].strip()
                spec = row[1].strip()
                material_type = row[2].strip()
                brand = row[3].strip()
                price_str = row[4].strip()

                # 验证数据
                valid_names = ['高线', '螺纹钢', '盘螺', '圆钢']
                if material_name in valid_names and spec.startswith('Φ') and price_str:
                    try:
                        # 提取数字
                        price = int(''.join(filter(str.isdigit, price_str)))
                        if price > 0:
                            prices.append({
                                'date': target_date,
                                'fetch_time': datetime.now().strftime('%H:%M:%S'),
                                'material_name': material_name,
                                'spec': spec,
                                'material_type': material_type,
                                'brand': brand,
                                'price': price
                            })
                    except:
                        pass

        return prices if prices else None

    except Exception as e:
        print(f'  [ERROR] {e}')
        return None


async def click_and_select_date(page, date_str: str):
    """点击日期并选择"""
    try:
        # 查找日期输入框
        date_picker = await page.query_selector('.date-picker input, [placeholder*="日期"], input[readonly]')

        if not date_picker:
            # 尝试查找可点击的日期元素
            date_picker = await page.query_selector('.el-date-editor, .date-input')

        if date_picker:
            await date_picker.click()
            await page.wait_for_timeout(1000)

        # 在弹出的日历中输入日期
        # 查找输入框
        input_field = await page.query_selector('.el-date-editor input')
        if not input_field:
            input_field = await page.query_selector('[class*="date"] input')

        if input_field:
            # 清空并输入
            await input_field.click()
            await page.wait_for_timeout(300)
            await input_field.fill('')
            await input_field.type(date_str)
            await page.wait_for_timeout(500)
            await page.keyboard.press('Enter')
            await page.wait_for_timeout(2000)

            return True

        return False

    except Exception as e:
        print(f'  [ERROR] 选择日期失败: {e}')
        return False


async def fetch_by_date_range(start_date: str, end_date: str, interval_seconds: int = 10):
    """
    按日期范围抓取

    Args:
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)
        interval_seconds: 每次抓取间隔秒数
    """
    print(f'开始抓取: {start_date} 至 {end_date}')

    # 加载凭据
    with open(DATA_DIR / 'mysteel_config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
        username = config.get('username')
        password = config.get('password')

    init_database()
    existing = get_existing_dates()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 3000},
            locale='zh-CN',
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = await context.new_page()

        # 登录
        print('1. 登录中...')
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
        print(f'\n2. 访问历史页面...')
        await page.goto(HISTORY_URL, wait_until='networkidle', timeout=60000)
        await page.wait_for_timeout(5000)

        # 截图保存当前状态
        await page.screenshot(path=str(DATA_DIR / 'history_initial.png'), full_page=True)
        print('  初始页面已保存')

        # 生成日期列表
        current = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        dates = []

        while current <= end:
            dates.append(current.strftime('%Y-%m-%d'))
            current += timedelta(days=1)

        print(f'\n3. 开始抓取 {len(dates)} 个日期...')

        total_prices = 0
        success_dates = 0

        for i, date in enumerate(dates):
            print(f'\n[{i+1}/{len(dates)}] 抓取 {date}...')

            # 等待间隔
            if i > 0:
                print(f'  等待 {interval_seconds} 秒...')
                await page.wait_for_timeout(interval_seconds * 1000)

            # 选择日期
            success = await click_and_select_date(page, date)

            if success:
                # 等待数据加载
                await page.wait_for_timeout(3000)

                # 提取数据
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

                if data:
                    prices = []
                    for row in data:
                        if len(row) >= 6:
                            material_name = row[0].strip()
                            spec = row[1].strip()
                            material_type = row[2].strip()
                            brand = row[3].strip()
                            price_str = row[4].strip()

                            valid_names = ['高线', '螺纹钢', '盘螺', '圆钢']
                            if material_name in valid_names and spec.startswith('Φ') and price_str:
                                try:
                                    price = int(''.join(filter(str.isdigit, price_str)))
                                    if price > 0:
                                        prices.append({
                                            'date': date,
                                            'fetch_time': datetime.now().strftime('%H:%M:%S'),
                                            'material_name': material_name,
                                            'spec': spec,
                                            'material_type': material_type,
                                            'brand': brand,
                                            'price': price
                                        })
                                except:
                                    pass

                    if prices:
                        # 保存到数据库
                        conn = sqlite3.connect(DB_FILE)
                        c = conn.cursor()

                        inserted = 0
                        for p_data in prices:
                            key = f"{p_data['date']}_{p_data['fetch_time']}_{p_data['material_name']}_{p_data['spec']}"
                            if key not in existing:
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
                                    existing.add(key)
                                except:
                                    pass

                        conn.commit()
                        conn.close()

                        print(f'  [OK] 提取 {len(prices)} 条，新增 {inserted} 条')
                        total_prices += inserted
                        success_dates += 1

                        # 截图
                        await page.screenshot(
                            path=str(DATA_DIR / f'result_{date.replace("-", "")}.png'),
                            full_page=True
                        )
                    else:
                        print(f'  [FAIL] 未提取到有效数据')
                else:
                    print(f'  [FAIL] 未找到数据表格')
            else:
                print(f'  [FAIL] 选择日期失败')

        await browser.close()

        print('\n' + '=' * 60)
        print('抓取完成')
        print(f'  成功日期: {success_dates}/{len(dates)}')
        print(f'  新增记录: {total_prices} 条')
        print('=' * 60)


async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='烟台钢筋价格历史数据抓取')
    parser.add_argument('--start', '-s', default='2024-01-01', help='开始日期 (YYYY-MM-DD)')
    parser.add_argument('--end', '-e', default=None, help='结束日期 (YYYY-MM-DD)')
    parser.add_argument('--interval', '-i', type=int, default=10, help='抓取间隔秒数')

    args = parser.parse_args()

    end_date = args.end or datetime.now().strftime('%Y-%m-%d')

    await fetch_by_date_range(args.start, end_date, args.interval)


if __name__ == '__main__':
    asyncio.run(main())