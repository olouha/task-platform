"""查找往期按钮并点击"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

DATA_DIR = Path(r'E:\E\任务\task-platform\web\backend\services\data')

async def find_and_click_wangqi():
    """查找往期按钮"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={'width': 1920, 'height': 3000}, locale='zh-CN')
        page = await context.new_page()

        # 加载 Cookie
        cookie_file = DATA_DIR / 'mysteel_cookies.json'
        if cookie_file.exists():
            with open(cookie_file, 'r') as f:
                cookies = json.load(f)
            await context.add_cookies(cookies)

        # 访问烟台价格页
        url = 'https://jiancai.mysteel.com/m/26051516/06AC8B0B0D2BB9BF.html'
        await page.goto(url, wait_until='domcontentloaded', timeout=60000)
        await page.wait_for_timeout(5000)

        # 获取所有包含"往期"的元素
        elements = await page.evaluate('''() => {
            const results = [];
            const allElements = document.querySelectorAll('*');

            for (const el of allElements) {
                const text = el.textContent?.trim() || '';
                if (text.includes('往期')) {
                    results.push({
                        tag: el.tagName,
                        class: el.className || '',
                        text: text.slice(0, 50),
                        id: el.id || ''
                    });
                }
            }

            return results;
        }''')

        print("包含'往期'的元素:")
        for el in elements:
            print(f"  {el['tag']}.{el['class'][:30]}: {el['text']}")
            if el['id']:
                print(f"    ID: {el['id']}")

        # 尝试通过 XPath 点击
        if elements:
            await page.wait_for_timeout(2000)
            await page.click('xpath=//*[contains(text(), "往期")]')
            await page.wait_for_timeout(3000)

            # 截图
            screenshot = await page.screenshot(full_page=True)
            screenshot_path = DATA_DIR / 'after_wangqi.png'
            with open(screenshot_path, 'wb') as f:
                f.write(screenshot)
            print(f"\n点击后截图已保存")

            # 检查新页面
            new_tables = await page.evaluate('''() => {
                const tables = document.querySelectorAll('table');
                return {
                    count: tables.length,
                    text: document.body.textContent?.slice(0, 500) || ''
                };
            }''')
            print(f"新页面表格数: {new_tables['count']}")
            print(f"页面文本: {new_tables['text'][:200]}")

        await browser.close()

if __name__ == '__main__':
    asyncio.run(find_and_click_wangqi())