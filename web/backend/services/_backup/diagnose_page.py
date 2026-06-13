"""
诊断脚本 - 检查历史页面内容
"""
import asyncio
import sys
import json
from pathlib import Path

sys.path.insert(0, '.')

from playwright.async_api import async_playwright

DATA_DIR = Path('web/backend/services/data')
COOKIE_FILE = DATA_DIR / 'mysteel_cookies_test.json'


async def diagnose_page():
    """诊断页面内容"""
    print("=" * 60)
    print("诊断页面内容")
    print("=" * 60)

    with open(COOKIE_FILE, 'r', encoding='utf-8') as f:
        cookies = json.load(f)

    test_urls = [
        ("2024-01-02 AM", "https://jiancai.mysteel.com/m/24010210/25B3355C6617BD3C.html"),
        ("2024-07-01 AM", "https://jiancai.mysteel.com/m/24070110/25B3355C6617BD3C.html"),
        ("2025-01-02 AM", "https://jiancai.mysteel.com/m/25010210/25B3355C6617BD3C.html"),
    ]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 3000},
            locale='zh-CN'
        )
        page = await context.new_page()
        await context.add_cookies(cookies)

        for name, url in test_urls:
            print(f"\n[{name}]")
            print(f"URL: {url}")

            try:
                await page.goto(url, wait_until='domcontentloaded', timeout=60000)
                await page.wait_for_timeout(8000)

                # 获取页面文本
                text = await page.evaluate('() => document.body.innerText')
                print(f"页面文本长度: {len(text)} 字符")
                print(f"前500字符: {text[:500]}...")

                # 检查表格数量
                table_count = await page.evaluate('() => document.querySelectorAll("table").length')
                print(f"表格数量: {table_count}")

                # 检查是否有价格数据
                has_numbers = await page.evaluate('''() => {
                    const text = document.body.innerText;
                    const numbers = text.match(/\d{3,4}/g);
                    return numbers ? numbers.slice(0, 10) : [];
                }''')
                print(f"数字价格示例: {has_numbers}")

                # 截图
                screenshot_path = DATA_DIR / 'screenshots' / f'diag_{name.replace(" ", "_").replace("-", "")}.png'
                await page.screenshot(path=str(screenshot_path), full_page=True)
                print(f"截图: {screenshot_path}")

            except Exception as e:
                print(f"错误: {e}")

        await browser.close()


if __name__ == '__main__':
    asyncio.run(diagnose_page())