"""
从市场页面按月份提取真实URL
账号: M6616592358 / panhui199261
"""
import asyncio
import json
import re
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright

DATA_DIR = Path('services/data')
COOKIE_FILE = DATA_DIR / 'mysteel_cookies.json'
OUTPUT_FILE = DATA_DIR / 'real_urls_v2.json'

USERNAME = 'M6616592358'
PASSWORD = 'panhui199261'

MARKET_URL = 'https://jiancai.mysteel.com/market/pa228aa010101a0a01010205aaaa1.html'


def log(msg):
    print(f'[{datetime.now().strftime("%H:%M:%S")}] {msg}')


async def login(page, context):
    """登录"""
    log('登录中...')
    await page.goto('https://passport.mysteel.com/', wait_until='networkidle', timeout=60000)
    await page.wait_for_timeout(3000)

    try:
        tab = await page.query_selector('text=账号登录')
        if tab:
            await tab.click()
            await page.wait_for_timeout(2000)
    except:
        pass

    await page.evaluate(f'''
        () => {{
            const inputs = document.querySelectorAll('input');
            for (const inp of inputs) {{
                const ph = inp.placeholder || '';
                if (ph.includes('用户名') || ph.includes('手机')) inp.value = '{USERNAME}';
                if (ph.includes('密码') && inp.type === 'password') inp.value = '{PASSWORD}';
            }}
        }}
    ''')
    await page.wait_for_timeout(1000)

    try:
        btn = await page.query_selector('.form-button-login, button:has-text("登录")')
        if btn:
            await btn.click()
            for i in range(20):
                await page.wait_for_timeout(1000)
                if 'passport' not in page.url:
                    break
    except:
        pass

    cookies = await context.cookies()
    COOKIE_FILE.write_text(json.dumps(cookies, ensure_ascii=False), encoding='utf-8')
    log(f'登录成功，Cookie: {len(cookies)}条')


async def extract_urls_from_page(page):
    """从当前页面提取所有链接"""
    urls = []
    try:
        # 方法1: 直接查找链接
        links = await page.query_selector_all('a[href*="/m/"]')
        for link in links:
            href = await link.get_attribute('href')
            if href and 'jiancai.mysteel.com/m/' in href:
                # 提取日期
                match = re.search(r'/m/(\d{10})/', href)
                if match:
                    code = match.group(1)
                    year = 2000 + int(code[:2])
                    month = int(code[2:4])
                    day = int(code[4:6])
                    hour = int(code[6:8])
                    date_str = f'{year}-{month:02d}-{day:02d}'
                    period = 'PM' if hour >= 12 else 'AM'
                    urls.append([date_str, period, href])

        # 方法2: 查找列表项
        items = await page.query_selector_all('.list-item, [class*="item"], .price-item, tr')
        for item in items:
            try:
                link = await item.query_selector('a[href*="/m/"]')
                if link:
                    href = await link.get_attribute('href')
                    text = await item.text_content()
                    if href and 'jiancai.mysteel.com/m/' in href:
                        match = re.search(r'/m/(\d{10})/', href)
                        if match:
                            code = match.group(1)
                            year = 2000 + int(code[:2])
                            month = int(code[2:4])
                            day = int(code[4:6])
                            hour = int(code[6:8])
                            date_str = f'{year}-{month:02d}-{day:02d}'
                            period = 'PM' if hour >= 12 else 'AM'
                            if [date_str, period, href] not in urls:
                                urls.append([date_str, period, href])
            except:
                pass
    except Exception as e:
        log(f'提取失败: {e}')
    return urls


async def navigate_and_collect(page, start_year, start_month, end_year, end_month):
    """导航到特定月份并收集URL"""
    all_urls = []

    # 遍历所有月份
    year, month = start_year, start_month
    while (year < end_year) or (year == end_year and month <= end_month):
        log(f'\n处理: {year}-{month:02d}')

        # 访问市场页面
        await page.goto(MARKET_URL, wait_until='domcontentloaded', timeout=60000)
        await page.wait_for_timeout(5000)

        # 尝试选择月份筛选
        try:
            # 查找月份选择器
            month_selectors = [
                'input[placeholder*="月"]',
                'input[placeholder*="日期"]',
                '.month-picker input',
                '[class*="month"] input'
            ]

            for selector in month_selectors:
                month_input = await page.query_selector(selector)
                if month_input:
                    await month_input.click()
                    await page.wait_for_timeout(1000)

                    # 输入月份
                    month_value = f'{year}-{month:02d}'
                    await month_input.fill(month_value)
                    await month_input.press('Enter')
                    await page.wait_for_timeout(3000)
                    log(f'  已选择月份: {month_value}')
                    break
        except Exception as e:
            log(f'  月份选择失败: {e}')

        # 滚动加载
        for i in range(10):
            await page.evaluate('window.scrollBy(0, 500)')
            await page.wait_for_timeout(500)

        # 提取URL
        page_num = 1
        while True:
            log(f'  第{page_num}页...')

            urls = await extract_urls_from_page(page)
            log(f'    找到 {len(urls)} 个URL')
            all_urls.extend(urls)

            # 翻页
            try:
                next_btn = await page.query_selector('a:has-text("下一页")')
                if next_btn and await next_btn.is_visible():
                    await next_btn.click()
                    await page.wait_for_timeout(3000)
                    page_num += 1
                else:
                    break
            except:
                break

        # 下一个月
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1

        # 月份间停顿
        await asyncio.sleep(2)

    return all_urls


async def main():
    print('=' * 70)
    print('从市场页面提取所有历史数据URL')
    print('=' * 70)
    print()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 3000},
            locale='zh-CN'
        )
        page = await context.new_page()

        # 登录
        await login(page, context)

        # 收集URL (2024-07 到 2026-05)
        urls = await navigate_and_collect(page, 2024, 7, 2026, 5)

        # 去重
        seen = {}
        unique = []
        for item in urls:
            key = (item[0], item[1])
            if key not in seen:
                seen[key] = True
                unique.append(item)

        # 排序
        unique.sort(key=lambda x: (x[0], x[1]), reverse=True)

        log(f'\n总计收集: {len(unique)} 条URL')

        # 保存
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(unique, f, ensure_ascii=False, indent=2)

        log(f'已保存到: {OUTPUT_FILE}')

        # 统计
        if unique:
            years = {}
            for item in unique:
                year = item[0][:4]
                years[year] = years.get(year, 0) + 1
            log('\n按年份:')
            for year in sorted(years.keys()):
                log(f'  {year}: {years[year]}')

        await browser.close()


if __name__ == '__main__':
    asyncio.run(main())