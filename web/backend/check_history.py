"""检查是否有历史价格数据"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

DATA_DIR = Path(r'E:\E\任务\task-platform\web\backend\services\data')

async def check_history():
    """检查历史数据页面"""
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

        # 检查页面上的历史相关链接/按钮
        history_elements = await page.evaluate('''() => {
            const results = [];

            // 查找包含"历史"、"往期"、"前几天"等关键词的元素
            const keywords = ['历史', '往期', '前几天', '昨日', '05-13', '5月13'];
            const allElements = document.querySelectorAll('*');

            for (const el of allElements) {
                const text = el.textContent?.trim() || '';
                const className = el.className || '';
                const href = el.href || '';

                for (const keyword of keywords) {
                    if (keyword.length > 2 && keyword in text) {
                        results.push({
                            tag: el.tagName,
                            class: className,
                            text: text.slice(0, 100),
                            href: href
                        });
                        break;
                    }
                }
            }

            return results.slice(0, 20);
        }''')

        print("找到的历史相关元素:")
        for el in history_elements:
            print(f"  {el['tag']}.{el['class'][:30]}: {el['text'][:80]}")
            if el['href']:
                print(f"    链接: {el['href']}")

        # 检查页面 URL 中是否有日期参数
        current_url = page.url
        print(f"\n当前URL: {current_url}")

        # 截图
        screenshot = await page.screenshot(full_page=True)
        screenshot_path = DATA_DIR / 'check_history.png'
        with open(screenshot_path, 'wb') as f:
            f.write(screenshot)
        print(f"\n截图已保存: {screenshot_path}")

        await browser.close()

if __name__ == '__main__':
    asyncio.run(check_history())