"""
从市场页面获取所有历史数据URL
账号: M6616592358 / panhui199261
"""
import asyncio
import json
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright

DATA_DIR = Path('services/data')
COOKIE_FILE = DATA_DIR / 'mysteel_cookies.json'
OUTPUT_FILE = DATA_DIR / 'real_urls.json'

USERNAME = 'M6616592358'
PASSWORD = 'panhui199261'

MARKET_URL = 'https://jiancai.mysteel.com/market/pa228aa010101a0a01010205aaaa1.html'


def log(msg):
    print(f'[{datetime.now().strftime("%H:%M:%S")}] {msg}')


async def login_and_get_urls():
    """登录并收集所有URL"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 3000},
            locale='zh-CN',
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = await context.new_page()

        # 1. 登录
        print('1. 登录...')
        await page.goto('https://passport.mysteel.com/', wait_until='networkidle', timeout=60000)
        await page.wait_for_timeout(3000)

        # 点击账号登录
        try:
            tab = await page.query_selector('text=账号登录')
            if tab:
                await tab.click()
                await page.wait_for_timeout(2000)
        except:
            pass

        # 填写表单
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

        # 点击登录
        try:
            btn = await page.query_selector('.form-button-login, button:has-text("登录")')
            if btn:
                await btn.click()
                # 等待登录完成
                for i in range(20):
                    await page.wait_for_timeout(1000)
                    if 'passport' not in page.url:
                        break
        except:
            pass

        cookies = await context.cookies()
        COOKIE_FILE.write_text(json.dumps(cookies, ensure_ascii=False), encoding='utf-8')
        log(f'登录成功，Cookie: {len(cookies)}条')

        # 2. 访问市场页面
        print('\n2. 访问市场页面...')
        await page.goto(MARKET_URL, wait_until='domcontentloaded', timeout=60000)
        await page.wait_for_timeout(8000)

        # 滚动加载
        for i in range(15):
            await page.evaluate('window.scrollBy(0, 500)')
            await page.wait_for_timeout(500)

        await page.screenshot(path=str(DATA_DIR / 'market_urls.png'))
        log('市场页面截图已保存')

        # 3. 收集所有URL
        print('\n3. 收集URL...')
        all_urls = []
        page_num = 1

        while page_num <= 500:
            log(f'  第{page_num}页...')

            await page.wait_for_timeout(2000)

            # 滚动加载
            for i in range(5):
                await page.evaluate('window.scrollBy(0, 300)')
                await page.wait_for_timeout(300)

            # 提取链接
            js_code = '''
                () => {
                    const results = [];
                    const links = document.querySelectorAll('a[href*="/m/"]');
                    links.forEach(link => {
                        const href = link.href;
                        if (href.includes('jiancai.mysteel.com/m/')) {
                            const match = href.match(/\\/m\\/(\\d{10})\\//);
                            if (match) {
                                const code = match[1];
                                const year = 2000 + parseInt(code.substring(0, 2));
                                const month = parseInt(code.substring(2, 4));
                                const day = parseInt(code.substring(4, 6));
                                const hour = parseInt(code.substring(6, 8));
                                const dateStr = year + '-' + (month < 10 ? '0' : '') + month + '-' + (day < 10 ? '0' : '') + day;
                                const period = hour >= 12 ? 'PM' : 'AM';
                                results.push({date: dateStr, period: period, url: href});
                            }
                        }
                    });
                    return results;
                }
            '''
            data = await page.evaluate(js_code)
            log(f'    找到 {len(data)} 个')

            if data:
                for item in data:
                    all_urls.append([item['date'], item['period'], item['url']])

            # 下一页
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

        # 去重
        seen = {}
        unique = []
        for item in all_urls:
            key = (item[0], item[1])
            if key not in seen:
                seen[key] = True
                unique.append(item)

        # 按日期排序
        unique.sort(key=lambda x: (x[0], x[1]), reverse=True)

        log(f'\n总计: {len(unique)} 条URL')

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
            log(f'\n范围: {unique[-1][0]} 至 {unique[0][0]}')

        await browser.close()


async def main():
    print('=' * 60)
    print('收集历史数据URL')
    print('=' * 60)
    await login_and_get_urls()


if __name__ == '__main__':
    asyncio.run(main())