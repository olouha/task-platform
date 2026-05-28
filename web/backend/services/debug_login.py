"""
调试登录流程 - 详细截图每一步
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
    print('调试登录流程')
    print('=' * 60)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 3000},
            locale='zh-CN'
        )
        page = await context.new_page()

        # 1. 访问登录页
        print('\n1. 访问登录页...')
        await page.goto('https://passport.mysteel.com/', wait_until='domcontentloaded', timeout=60000)
        await page.wait_for_timeout(3000)
        await page.screenshot(path=str(DATA_DIR / 'debug1_login_page.png'))
        print('  截图: debug1_login_page.png')

        # 2. 点击账号登录标签
        print('\n2. 点击账号登录标签...')
        tabs = await page.query_selector_all('.form-tab, .tab-item, [class*="tab"]')
        print(f'  找到 {len(tabs)} 个标签')
        for i, tab in enumerate(tabs):
            text = await tab.text_content()
            print(f'    {i}: {text[:50]}')

        tab = await page.query_selector('.form-tab-account, a[data-tab="account"]')
        if tab:
            await tab.click()
            await page.wait_for_timeout(2000)
            await page.screenshot(path=str(DATA_DIR / 'debug2_after_tab.png'))
            print('  点击后截图: debug2_after_tab.png')

        # 3. 查找输入框
        print('\n3. 查找输入框...')
        inputs = await page.query_selector_all('input')
        print(f'  找到 {len(inputs)} 个输入框')
        for i, inp in enumerate(inputs):
            ph = await inp.get_attribute('placeholder')
            typ = await inp.get_attribute('type')
            print(f'    {i}: type={typ}, placeholder={ph}')

        # 4. 填写表单
        print('\n4. 填写表单...')
        await page.evaluate(f'''
            () => {{
                const inputs = document.querySelectorAll('input');
                for (const inp of inputs) {{
                    const ph = (inp.placeholder || '').toLowerCase();
                    if (ph.includes('用户名') || ph.includes('账号') || ph.includes('手机')) {{
                        inp.value = '{USERNAME}';
                        console.log('填入用户名');
                    }}
                    if (ph.includes('密码') && inp.type === 'password') {{
                        inp.value = '{PASSWORD}';
                        console.log('填入密码');
                    }}
                }}
            }}
        ''')
        await page.wait_for_timeout(1000)
        await page.screenshot(path=str(DATA_DIR / 'debug3_after_fill.png'))
        print('  填写后截图: debug3_after_fill.png')

        # 5. 点击登录按钮
        print('\n5. 点击登录按钮...')
        buttons = await page.query_selector_all('button, input[type="submit"]')
        print(f'  找到 {len(buttons)} 个按钮')
        for i, btn in enumerate(buttons):
            text = await btn.text_content()
            typ = await btn.get_attribute('type')
            print(f'    {i}: text={text[:30]}, type={typ}')

        btn = await page.query_selector('button:has-text("登录"), input[type="submit"]')
        if btn:
            print('  点击登录按钮')
            await btn.click()
            await page.wait_for_timeout(10000)
            await page.screenshot(path=str(DATA_DIR / 'debug4_after_login.png'))
            print('  登录后截图: debug4_after_login.png')

        print(f'\n6. 当前URL: {page.url}')

        # 6. 保存Cookie
        cookies = await context.cookies()
        COOKIE_FILE.write_text(json.dumps(cookies, ensure_ascii=False), encoding='utf-8')
        print(f'Cookie保存: {len(cookies)} 条')

        # 7. 访问市场页面
        print('\n7. 访问市场页面...')
        await page.goto('https://jiancai.mysteel.com/market/pa228aa010101a0a01010205aaaa1.html',
                        wait_until='domcontentloaded', timeout=60000)
        await page.wait_for_timeout(5000)
        await page.screenshot(path=str(DATA_DIR / 'debug5_market.png'))
        print('  市场页面截图: debug5_market.png')

        body = await page.evaluate('() => document.body.textContent')
        if '登录' in body and 'passport' in page.url:
            print('  需要登录')
        elif '价格' in body:
            print('  有价格数据')
        else:
            print('  页面内容检查')

        await browser.close()


if __name__ == '__main__':
    asyncio.run(main())