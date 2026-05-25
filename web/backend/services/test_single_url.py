"""
测试单个URL访问
"""
import asyncio
from playwright.async_api import async_playwright
import json
from pathlib import Path

DATA_DIR = Path('services/data')
COOKIE_FILE = DATA_DIR / 'mysteel_cookies.json'
USERNAME = 'M6616592358'
PASSWORD = 'mysteel573005'

TEST_URLS = [
    'https://jiancai.mysteel.com/m/26051516/06AC8B0B0D2BB9BF.html',  # 2026-05-15 PM
    'https://jiancai.mysteel.com/m/26042910/B642D57F54B3CC2F.html',  # 2026-04-29 AM
]


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080}, locale='zh-CN')

        # 加载cookies
        if COOKIE_FILE.exists():
            try:
                cookies = json.loads(COOKIE_FILE.read_text(encoding='utf-8'))
                if cookies:
                    await context.add_cookies(cookies)
                    print('已加载Cookie')
            except:
                pass

        page = await context.new_page()

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

        await asyncio.sleep(10)
        print('登录完成\n')

        # 测试URL
        for url in TEST_URLS:
            print(f'访问: {url}')
            await page.goto(url, wait_until='domcontentloaded', timeout=60000)
            await asyncio.sleep(5)

            # 获取页面标题
            title = await page.title()
            print(f'页面标题: {title}')

            # 检查页面内容
            body_text = await page.evaluate('() => document.body.textContent')
            print(f'页面内容长度: {len(body_text)}')

            # 查找表格
            tables_count = await page.evaluate('() => document.querySelectorAll("table").length')
            print(f'表格数量: {tables_count}')

            # 保存截图
            screenshot_path = DATA_DIR / 'test_url.png'
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f'截图已保存: {screenshot_path}\n')

            await asyncio.sleep(3)

        await browser.close()


if __name__ == '__main__':
    asyncio.run(main())