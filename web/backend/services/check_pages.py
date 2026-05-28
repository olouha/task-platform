"""
检查登录和市场页面状态
"""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

DATA_DIR = Path('services/data')
COOKIE_FILE = DATA_DIR / 'mysteel_cookies.json'

USERNAME = 'M6616592358'
PASSWORD = 'panhui199261'

MARKET_URL = 'https://jiancai.mysteel.com/market/pa228aa010101a0a01010205aaaa1.html'


async def main():
    print('=' * 60)
    print('检查登录和市场页面')
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
        await page.goto('https://passport.mysteel.com/', wait_until='domcontentloaded', timeout=60000)
        await page.wait_for_timeout(3000)
        print(f'   URL: {page.url}')
        print(f'   标题: {await page.title()}')

        # 点击账号登录
        try:
            tab = await page.query_selector('.form-tab-account, a[data-tab="account"]')
            if tab:
                await tab.click()
                await page.wait_for_timeout(2000)
                print('   已点击账号登录')
        except Exception as e:
            print(f'   点击失败: {e}')

        # 填写表单
        await page.evaluate("""
            () => {
                const inputs = document.querySelectorAll('input');
                for (const inp of inputs) {
                    const ph = (inp.placeholder || '').toLowerCase();
                    if (ph.includes('用户名') || ph.includes('账号')) inp.value = 'M6616592358';
                    if (ph.includes('密码') && inp.type === 'password') inp.value = 'panhui199261';
                }
            }
        """)
        await page.wait_for_timeout(1000)

        # 点击登录
        try:
            btn = await page.query_selector('button:has-text("登录"), input[type="submit"]')
            if btn:
                await btn.click()
                print('   已点击登录按钮')
                await page.wait_for_timeout(8000)
        except Exception as e:
            print(f'   登录失败: {e}')

        print(f'   登录后URL: {page.url}')

        # 保存Cookie
        cookies = await context.cookies()
        COOKIE_FILE.write_text('[]', encoding='utf-8')
        import json
        COOKIE_FILE.write_text(json.dumps(cookies, ensure_ascii=False), encoding='utf-8')
        print(f'   Cookie: {len(cookies)}条')

        # 2. 访问市场页面
        print('\n2. 访问市场页面...')
        await page.goto(MARKET_URL, wait_until='domcontentloaded', timeout=60000)
        await page.wait_for_timeout(5000)
        print(f'   URL: {page.url}')
        print(f'   标题: {await page.title()}')

        # 截图
        await page.screenshot(path=str(DATA_DIR / 'market_page_check.png'))
        print('   截图已保存')

        # 检查页面内容
        body_text = await page.evaluate('() => document.body.textContent.substring(0, 2000)')
        print(f'\n   页面内容(前500字):')
        print(f'   {body_text[:500]}')

        # 3. 访问一个数据页面
        print('\n3. 访问数据页面...')
        test_url = 'https://jiancai.mysteel.com/m/26051410/25B3355C6617BD3C.html'
        await page.goto(test_url, wait_until='domcontentloaded', timeout=60000)
        await page.wait_for_timeout(5000)
        print(f'   URL: {page.url}')

        # 截图
        await page.screenshot(path=str(DATA_DIR / 'data_page_check.png'))
        print('   截图已保存')

        body_text = await page.evaluate('() => document.body.textContent.substring(0, 1000)')
        if '高线' in body_text or '螺纹钢' in body_text:
            print('   有价格数据')
        else:
            print(f'   内容: {body_text[:300]}')

        await browser.close()


if __name__ == '__main__':
    asyncio.run(main())