"""
测试访问具体日期的数据页面
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

DATA_DIR = Path('services/data')
COOKIE_FILE = DATA_DIR / 'mysteel_cookies.json'

USERNAME = 'M6616592358'
PASSWORD = 'panhui199261'


async def main():
    print('=' * 60)
    print('测试访问具体日期数据')
    print('=' * 60)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 3000},
            locale='zh-CN'
        )
        page = await context.new_page()

        # 1. 登录
        print('\n1. 登录...')
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
        print(f'Cookie: {len(cookies)}条')

        # 2. 测试访问几个具体日期
        test_urls = [
            ('2026-05-14 AM', 'https://jiancai.mysteel.com/m/26051410/25B3355C6617BD3C.html'),
            ('2026-05-15 AM', 'https://jiancai.mysteel.com/m/26051510/19B77109BDE6183C.html'),
            ('2026-05-13 PM', 'https://jiancai.mysteel.com/m/26051316/B7EAA4BE8AB3DA35.html'),
        ]

        for name, url in test_urls:
            print(f'\n2. 测试: {name}')
            await page.goto(url, wait_until='domcontentloaded', timeout=60000)
            await page.wait_for_timeout(8000)

            # 滚动
            for i in range(10):
                await page.evaluate('window.scrollBy(0, 500)')
                await page.wait_for_timeout(500)

            await page.screenshot(path=str(DATA_DIR / f'test_{name.replace(" ", "_")}.png'))

            # 检查内容
            body = await page.evaluate('() => document.body.textContent')
            if '高线' in body or '螺纹钢' in body:
                print(f'   有价格数据')

                # 提取数据
                prices = await page.evaluate('''
                    () => {
                        const results = [];
                        const tables = document.querySelectorAll('table');
                        tables.forEach(table => {
                            const rows = table.querySelectorAll('tr');
                            rows.forEach(row => {
                                const cells = row.querySelectorAll('td');
                                if (cells.length >= 5) {
                                    const material = cells[0]?.textContent?.trim() || '';
                                    const spec = cells[1]?.textContent?.trim() || '';
                                    const price = cells[4]?.textContent?.trim() || '';
                                    if (material && spec && price && price.match(/\\d{3,5}/)) {
                                        results.push({material, spec, price});
                                    }
                                }
                            });
                        });
                        return results;
                    }
                ''')
                print(f'   提取到 {len(prices)} 条数据')
                for i, pr in enumerate(prices[:3]):
                    print(f'     {i+1}: {pr.material} {pr.spec} {pr.price}')
            elif '暂无数据' in body:
                print(f'   暂无数据')
            else:
                print(f'   内容检查')

        await browser.close()


if __name__ == '__main__':
    asyncio.run(main())