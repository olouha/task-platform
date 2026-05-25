"""从首页获取烟台价格URL并抓取"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

DATA_DIR = Path(r'E:\E\任务\task-platform\web\backend\services\data')

async def get_yantai_url_and_fetch():
    """从首页获取烟台价格URL并抓取"""
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
            print(f"已加载 {len(cookies)} 个Cookie")

        # 1. 访问首页
        print("访问首页: https://jiancai.mysteel.com/")
        await page.goto('https://jiancai.mysteel.com/', wait_until='domcontentloaded', timeout=60000)
        await page.wait_for_timeout(5000)

        # 截图
        screenshot = await page.screenshot(full_page=True)
        screenshot_path = DATA_DIR / 'debug_home.png'
        with open(screenshot_path, 'wb') as f:
            f.write(screenshot)
        print(f"首页截图已保存")

        # 2. 获取所有链接
        links = await page.evaluate('''() => {
            const allLinks = [];
            document.querySelectorAll('a[href]').forEach(a => {
                const href = a.href;
                const text = a.textContent?.trim() || '';
                if (href.includes('jiancai.mysteel.com') && href.includes('/m/') && text.length > 0) {
                    allLinks.push({ text, href });
                }
            });
            return allLinks;
        }''')

        print(f"\n找到 {len(links)} 个/m/链接")

        # 查找烟台相关链接
        yantai_links = [l for l in links if '烟台' in l['text']]
        print(f"\n烟台链接:")
        for l in yantai_links[:10]:
            print(f"  {l['text']}: {l['href']}")

        # 查找山东市场链接
        shandong_links = [l for l in links if '山东' in l['text'] and 'market' in l['href']]
        print(f"\n山东市场链接:")
        for l in shandong_links[:5]:
            print(f"  {l['text']}: {l['href']}")

        # 如果有烟台链接，访问它
        if yantai_links:
            target_url = yantai_links[0]['href']
            print(f"\n访问烟台链接: {target_url}")
            await page.goto(target_url, wait_until='domcontentloaded', timeout=60000)
            await page.wait_for_timeout(10000)

            screenshot = await page.screenshot(full_page=True)
            screenshot_path = DATA_DIR / 'debug_yantai.png'
            with open(screenshot_path, 'wb') as f:
                f.write(screenshot)
            print(f"烟台页截图已保存")

            # 分析页面结构
            print("\n=== 页面结构分析 ===")
            data = await page.evaluate('''() => {
                const body = document.body.innerHTML;

                // 查找包含价格数据的表格或div
                const tables = document.querySelectorAll('table');
                const divs = document.querySelectorAll('[class*="table"], [class*="list"], [class*="price"], [class*="detail"]');

                return {
                    tableCount: tables.length,
                    divCount: divs.length,
                    bodyText: document.body.textContent?.slice(0, 500) || '',
                    allDivsWithPrice: Array.from(divs).slice(0, 10).map(d => ({
                        tag: d.tagName,
                        class: d.className || '',
                        text: d.textContent?.slice(0, 100) || ''
                    }))
                };
            }''')

            print(f"表格数量: {data['tableCount']}")
            print(f"包含table/list/price的div数量: {data['divCount']}")
            print(f"页面文本: {data['bodyText'][:200]}")

            for d in data['allDivsWithPrice']:
                print(f"  {d['tag']}.{d['class'][:40]}: {d['text'][:80]}")

        await browser.close()

if __name__ == '__main__':
    asyncio.run(get_yantai_url_and_fetch())