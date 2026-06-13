"""
测试Cookie是否有效
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

DATA_DIR = Path(__file__).parent.absolute() / 'data'
COOKIE_FILE = DATA_DIR / 'mysteel_cookies.json'


async def test_cookie():
    print("=" * 60)
    print("测试Cookie有效性")
    print("=" * 60)

    with open(COOKIE_FILE, 'r', encoding='utf-8') as f:
        cookies = json.load(f)

    print(f"\nCookie数量: {len(cookies)}")

    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=False)
    context = await browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        locale='zh-CN'
    )

    await context.add_cookies(cookies)
    print("已添加Cookie")

    page = await context.new_page()

    print("\n访问测试页面...")
    url = 'https://jiancai.mysteel.com/m/26051410/25B3355C6617BD3C.html'
    print(f"URL: {url}")

    try:
        response = await page.goto(url, wait_until='domcontentloaded', timeout=30000)
        print(f"HTTP状态: {response.status}")

        await asyncio.sleep(3)

        # 检查页面内容
        page_text = await page.evaluate('() => document.body.textContent')
        print(f"页面长度: {len(page_text)} 字符")

        if '烟台' in page_text:
            print("页面包含'烟台'")
        else:
            print("页面不包含'烟台'")

        # 检查是否需要登录
        if '登录' in page_text and len(page_text) < 1000:
            print("可能需要登录")

        # 截图
        await page.screenshot(path='test_page.png')
        print("已截图: test_page.png")

    except Exception as e:
        print(f"错误: {e}")

    print("\n按回车关闭...")
    input()

    await browser.close()
    await playwright.stop()


if __name__ == '__main__':
    asyncio.run(test_cookie())
