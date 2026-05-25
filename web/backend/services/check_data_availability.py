"""
快速检查哪些链接有数据
"""
import asyncio
from playwright.async_api import async_playwright
import json
import re
from datetime import datetime, timedelta
from pathlib import Path

DATA_DIR = Path('services/data')
COOKIE_FILE = DATA_DIR / 'mysteel_cookies.json'
LINKS_FILE = DATA_DIR / 'yantai_links.json'
EXCEL_FILE = DATA_DIR / '山东烟台钢筋价格.xlsx'

USERNAME = 'M6616592358'
PASSWORD = 'mysteel573005'


def parse_date_from_url(href):
    match = re.search(r'/m/(\d{8})/', href)
    if match:
        full = match.group(1)
        year = 2000 + int(full[0:2])
        month = int(full[2:4])
        day = int(full[4:6])
        hour = int(full[6:8])
        return f'{year}-{month:02d}-{day:02d}', 'AM' if hour < 12 else 'PM'
    return None, None


async def get_existing_sheets():
    existing_sheets = set()
    if EXCEL_FILE.exists():
        try:
            import openpyxl
            wb = openpyxl.load_workbook(EXCEL_FILE)
            existing_sheets = set(wb.sheetnames)
            wb.close()
        except Exception:
            pass
    return existing_sheets


async def has_data(page, url):
    """检查链接是否有数据"""
    try:
        await page.goto(url, wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(1)

        data = await page.evaluate('''() => {
            const tables = document.querySelectorAll('table');
            const results = [];
            tables.forEach(table => {
                const rows = table.querySelectorAll('tr');
                rows.forEach(row => {
                    const cells = row.querySelectorAll('td');
                    if (cells.length >= 5) {
                        const material_name = cells[0]?.textContent?.trim();
                        const spec = cells[1]?.textContent?.trim();
                        const price = cells[4]?.textContent?.trim();

                        if (['高线', '螺纹钢', '盘螺', '圆钢'].includes(material_name) &&
                            spec && spec.startsWith('Φ') && price && /^\d+$/.test(price)) {
                            results.push(true);
                        }
                    }
                });
            });
            return results.length > 0;
        }''')

        return data
    except:
        return False


async def main():
    print('=' * 60)
    print('快速检查哪些链接有数据')
    print('=' * 60)

    # 加载链接
    with open(LINKS_FILE, 'r', encoding='utf-8') as f:
        all_links = json.load(f)

    print(f'总链接数: {len(all_links)}')

    # 获取已存在的sheet
    existing_sheets = await get_existing_sheets()
    print(f'已有sheet: {len(existing_sheets)}个')

    # 过滤已抓取的
    links_to_check = []
    for link in all_links:
        href = link['href']
        date_str, period = parse_date_from_url(href)
        if date_str:
            has_existing = any(s.startswith(f'{date_str}_{period}') for s in existing_sheets)
            if not has_existing:
                links_to_check.append((date_str, period, href))

    print(f'需要检查: {len(links_to_check)}个链接\n')

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080}, locale='zh-CN')
        page = await context.new_page()

        # 加载cookies
        if COOKIE_FILE.exists():
            try:
                cookies = json.loads(COOKIE_FILE.read_text(encoding='utf-8'))
                if cookies:
                    await page.context.add_cookies(cookies)
                    print('已加载Cookie')
            except:
                pass

        # 登录
        print('登录中...')
        await page.goto('https://passport.mysteel.com/', wait_until='domcontentloaded', timeout=60000)
        await asyncio.sleep(3)

        await page.evaluate(f'''() => {{
            const inputs = document.querySelectorAll('input');
            for (const inp of inputs) {{
                const ph = inp.placeholder || '';
                if (ph.includes('用户名')) inp.value = '{USERNAME}';
                if (ph.includes('密码') && inp.type === 'password') inp.value = '{PASSWORD}';
            }}
        }}''')

        await asyncio.sleep(1)

        try:
            checkbox = await page.query_selector('input[type="checkbox"]')
            if checkbox and not await checkbox.is_checked():
                await checkbox.click()
        except:
            pass

        await asyncio.sleep(1)

        try:
            login_btn = await page.query_selector('.form-button-login')
            if login_btn:
                await login_btn.click()
        except:
            pass

        await asyncio.sleep(8)
        print('登录完成\n')

        # 检查链接
        has_data_links = []
        no_data_links = []

        for i, (date_str, period, url) in enumerate(links_to_check[:100]):  # 先检查前100个
            print(f'[{i+1}/100] {date_str} {period}...', end='', flush=True)

            if await has_data(page, url):
                has_data_links.append((date_str, period, url))
                print(' 有数据 ✓')
            else:
                no_data_links.append((date_str, period, url))
                print(' 无数据')

            if (i + 1) % 10 == 0:
                print(f'  有数据: {len(has_data_links)}, 无数据: {len(no_data_links)}')
                await asyncio.sleep(2)

        await browser.close()

    print()
    print('=' * 60)
    print('检查完成')
    print('=' * 60)
    print(f'有数据: {len(has_data_links)}个')
    print(f'无数据: {len(no_data_links)}个')

    # 保存有数据的链接
    with open(DATA_DIR / 'has_data_links.json', 'w', encoding='utf-8') as f:
        json.dump(has_data_links, f, ensure_ascii=False, indent=2)
    print(f'有数据的链接已保存到 has_data_links.json')


if __name__ == '__main__':
    asyncio.run(main())