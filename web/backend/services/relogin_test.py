"""
重新登录并测试抓取
"""
import asyncio
import sys
import json
import base64
from pathlib import Path
from datetime import datetime

sys.path.insert(0, '.')

from playwright.async_api import async_playwright

DATA_DIR = Path('web/backend/services/data')
COOKIE_FILE = DATA_DIR / 'mysteel_cookies_new.json'
USERNAME = 'M6616592358'
PASSWORD = 'panhui199261'


async def login_and_test():
    """登录并测试"""
    print("=" * 60)
    print("重新登录并测试")
    print("=" * 60)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 3000},
            locale='zh-CN'
        )
        page = await context.new_page()

        # 访问登录页
        print("\n1. 访问登录页...")
        await page.goto('https://passport.mysteel.com/', wait_until='networkidle', timeout=60000)
        await page.wait_for_timeout(3000)
        await page.screenshot(path=str(DATA_DIR / 'login_new_1.png'))

        # 切换账号登录
        try:
            account_tab = await page.query_selector('.form-tab-account')
            if account_tab:
                await account_tab.click()
                print("已切换到账号登录")
                await page.wait_for_timeout(2000)
        except:
            pass

        # 填写表单
        await page.evaluate(f'''() => {{
            const inputs = document.querySelectorAll('input');
            for (const inp of inputs) {{
                const ph = inp.placeholder || '';
                if (ph.includes('用户名')) inp.value = '{USERNAME}';
                if (ph.includes('密码') && inp.type === 'password') inp.value = '{PASSWORD}';
            }}
        }}''')
        print("已填写用户名密码")
        await page.wait_for_timeout(500)

        # 勾选协议
        try:
            checkbox = await page.query_selector('input[type="checkbox"]')
            if checkbox and not await checkbox.is_checked():
                await checkbox.click()
        except:
            pass

        await page.wait_for_timeout(500)

        # 点击登录
        try:
            login_btn = await page.query_selector('.form-button-login')
            if login_btn:
                await login_btn.click()
            else:
                btns = await page.query_selector_all('button')
                for btn in btns:
                    text = await btn.text_content()
                    if text and '登录' in text:
                        await btn.click()
                        break
        except:
            pass

        print("点击登录，等待...")
        await page.wait_for_timeout(10000)
        await page.screenshot(path=str(DATA_DIR / 'login_new_2.png'))

        print(f"当前URL: {page.url}")

        # 保存Cookie
        cookies = await context.cookies()
        with open(COOKIE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cookies, f, ensure_ascii=False)
        print(f"Cookie已保存: {len(cookies)} 条")

        # 测试访问几个页面
        test_urls = [
            ("今日", "https://jiancai.mysteel.com/"),
            ("7月", "https://jiancai.mysteel.com/m/24070110/25B3355C6617BD3C.html"),
        ]

        for name, url in test_urls:
            print(f"\n测试 [{name}]: {url}")
            await page.goto(url, wait_until='domcontentloaded', timeout=60000)
            await page.wait_for_timeout(5000)

            text = await page.evaluate('() => document.body.innerText')
            print(f"页面文本长度: {len(text)}")

            # 截图
            screenshot_path = DATA_DIR / 'screenshots' / f'new_{name}.png'
            await page.screenshot(path=str(screenshot_path), full_page=True)

            if len(text) > 100:
                print(f"前200字符: {text[:200]}")
            else:
                print("页面内容为空，可能需要登录")

        await browser.close()


if __name__ == '__main__':
    asyncio.run(login_and_test())