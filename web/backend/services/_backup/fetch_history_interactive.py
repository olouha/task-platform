"""
烟台钢筋价格历史数据抓取 - 半自动模式
浏览器打开后手动操作一次，然后自动重复
"""
import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
import time

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


async def fetch_prices(page, date_str: str, existing: set):
    """从当前页面提取价格数据"""
    try:
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
                            prices.append({
                                'date': date_str,
                                'fetch_time': datetime.now().strftime('%H:%M:%S'),
                                'material_name': material_name,
                                'spec': spec,
                                'material_type': material_type,
                                'brand': brand,
                                'price': price
                            })
                    except:
                        pass

        if not prices:
            return 0

        # 保存到数据库
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()

        inserted = 0
        for p_data in prices:
            key = f"{p_data['date']}_{p_data['fetch_time']}_{p_data['material_name']}_{p_data['spec']}_{p_data['brand']}"
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

        return inserted

    except Exception as e:
        print(f'    [ERROR] {e}')
        return 0


async def interactive_fetch(start_date: str, end_date: str, interval_seconds: int = 20):
    """
    交互式抓取 - 打开浏览器让您手动操作

    1. 打开浏览器并登录
    2. 访问历史页面
    3. 选择一个日期范围并搜索
    4. 程序自动保存数据
    5. 重复步骤3-4直到完成
    """
    print('=' * 60)
    print('烟台钢筋价格历史数据抓取 - 交互模式')
    print('=' * 60)

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
        await page.wait_for_timeout(3000)

        print('\n' + '=' * 60)
        print('浏览器已打开，请在页面中执行以下操作：')
        print('1. 选择日期范围（开始日期和结束日期）')
        print('2. 点击搜索按钮')
        print('3. 等待数据加载')
        print('=' * 60)

        # 生成日期列表
        current = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        dates = []

        while current <= end:
            dates.append(current.strftime('%Y-%m-%d'))
            current += timedelta(days=1)

        print(f'\n目标日期: {start_date} 至 {end_date} (共 {len(dates)} 天)')
        print(f'间隔: {interval_seconds} 秒')

        # 循环检测并抓取
        total_inserted = 0
        last_count = 0
        no_change_count = 0

        print('\n开始监控数据变化...\n')

        for i in range(500):  # 最多循环500次（约2小时）
            # 检测表格数据变化
            current_count = await page.evaluate('''() => {
                let count = 0;
                const tables = document.querySelectorAll('table');
                tables.forEach(table => {
                    const tbody = table.querySelector('tbody');
                    if (tbody) {
                        const rows = tbody.querySelectorAll('tr');
                        rows.forEach(row => {
                            const cells = row.querySelectorAll('td');
                            if (cells.length >= 5) count++;
                        });
                    }
                });
                return count;
            }''')

            if current_count > last_count:
                print(f'[检查 {i+1}] 发现新数据 ({current_count} 行)，保存...')

                # 获取当前显示的日期
                date_from_page = await page.evaluate('''() => {
                    const startInput = document.querySelector('input.startTime');
                    return startInput ? startInput.value : '';
                }''')

                inserted = await fetch_prices(page, date_from_page or 'unknown', existing)

                if inserted > 0:
                    print(f'    [OK] 新增 {inserted} 条')
                    total_inserted += inserted
                    last_count = current_count
                    no_change_count = 0
                else:
                    print(f'    [SKIP] 无新增数据')
                    last_count = current_count
            else:
                if i % 10 == 0:  # 每10次打印一次状态
                    print(f'[检查 {i+1}] 等待新数据... (当前: {current_count} 行)')

            # 等待
            await page.wait_for_timeout(interval_seconds * 1000)

            # 如果多次没有变化，可能已完成
            no_change_count += 1
            if no_change_count >= 30 and current_count > 100:  # 30次检查无变化且有数据
                print(f'\n数据已稳定 (连续{no_change_count}次无变化)')
                break

        await browser.close()

        print('\n' + '=' * 60)
        print('抓取完成')
        print(f'  新增记录: {total_inserted} 条')
        print('=' * 60)


async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='烟台钢筋价格历史数据抓取 - 交互模式')
    parser.add_argument('--start', '-s', default='2024-01-01', help='开始日期 (YYYY-MM-DD)')
    parser.add_argument('--end', '-e', default=None, help='结束日期 (YYYY-MM-DD)')
    parser.add_argument('--interval', '-i', type=int, default=20, help='检查间隔秒数')

    args = parser.parse_args()

    end_date = args.end or datetime.now().strftime('%Y-%m-%d')

    await interactive_fetch(args.start, end_date, args.interval)


if __name__ == '__main__':
    asyncio.run(main())