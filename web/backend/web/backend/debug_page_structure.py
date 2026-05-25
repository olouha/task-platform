"""调试脚本 - 检查页面结构"""
import asyncio
import json
import base64
from pathlib import Path
from playwright.async_api import async_playwright

DATA_DIR = Path('data')
DATA_DIR.mkdir(exist_ok=True)

async def debug_page():
    """调试页面结构"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 3000}, locale='zh-CN')
        page = await context.new_page()

        # 加载cookie
        cookie_file = DATA_DIR / 'mysteel_cookies.json'
        if cookie_file.exists():
            with open(cookie_file, 'r') as f:
                cookies = json.load(f)
            await context.add_cookies(cookies)
            print(f"已加载 {len(cookies)} 个Cookie")

        url = 'https://jiancai.mysteel.com/m/26051510/25B3355C6617BD3C.html'
        print(f"访问: {url}")

        await page.goto(url, wait_until='domcontentloaded', timeout=60000)
        await page.wait_for_timeout(10000)

        # 截图
        screenshot = await page.screenshot(full_page=True)
        screenshot_path = DATA_DIR / 'debug_page.png'
        with open(screenshot_path, 'wb') as f:
            f.write(screenshot)
        print(f"截图已保存: {screenshot_path}")

        # 检查页面结构
        print("\n=== 页面结构分析 ===")

        # 查找所有表格
        table_count = await page.evaluate('''() => {
            return document.querySelectorAll('table').length;
        }''')
        print(f"标准 table 标签数量: {table_count}")

        # 查找所有class包含price的元素
        price_elements = await page.evaluate('''() => {
            const els = document.querySelectorAll('[class*="price"], [class*="list"], [class*="table"]');
            return Array.from(els).slice(0, 20).map(el => ({
                tag: el.tagName,
                class: el.className,
                text: el.textContent?.slice(0, 50) || ''
            }));
        }''')
        print(f"\n包含price/list/table的元素 (前20个):")
        for el in price_elements:
            print(f"  {el['tag']}.{el['class'][:30]}: {el['text'][:30]}")

        # 获取页面HTML的一部分
        html = await page.evaluate('''() => {
            const body = document.body.innerHTML;
            // 查找包含价格数据的部分
            const lines = body.split('\\n');
            const result = [];
            for (let i = 0; i < lines.length && result.length < 50; i++) {
                if (lines[i].includes('螺纹钢') || lines[i].includes('盘螺') || lines[i].includes('价格') || lines[i].includes('品名')) {
                    result.push(lines[i].trim());
                }
            }
            return result.slice(0, 30);
        }''')
        print(f"\n包含关键词的HTML行:")
        for line in html:
            print(f"  {line[:100]}")

        # 尝试直接找数据 - 查找所有文本包含数字的元素
        data_rows = await page.evaluate('''() => {
            // 查找所有可能是数据行的元素
            const allElements = document.querySelectorAll('*');
            const data = [];

            for (const el of allElements) {
                const text = el.textContent?.trim() || '';
                // 查找包含品名规格的行
                if (text.length > 10 && text.length < 200 &&
                    (text.includes('螺纹钢') || text.includes('盘螺') || text.includes('高线') || text.includes('圆钢')) &&
                    text.includes('Φ')) {
                    // 只添加直接的文本内容
                    data.push({
                        tag: el.tagName,
                        class: el.className,
                        text: text
                    });
                }
            }
            return data.slice(0, 10);
        }''')
        print(f"\n可能的数据行:")
        for row in data_rows:
            print(f"  {row['tag']}: {row['text'][:100]}")

        # 获取完整页面结构 - 查找data-testid等属性
        structure = await page.evaluate('''() => {
            const info = {
                url: window.location.href,
                title: document.title,
                bodyClass: document.body.className,
                mainElements: []
            };

            // 查找主要容器
            const mainContainers = document.querySelectorAll('main, [class*="main"], [class*="container"], [class*="content"]');
            for (const c of mainContainers) {
                info.mainElements.push({
                    tag: c.tagName,
                    class: c.className
                });
            }

            return info;
        }''')
        print(f"\n页面信息:")
        print(f"  URL: {structure['url']}")
        print(f"  Title: {structure['title']}")
        print(f"  Body class: {structure['bodyClass']}")
        print(f"  主要容器:")
        for c in structure['mainElements']:
            print(f"    {c['tag']}.{c['class'][:50]}")

        await browser.close()

if __name__ == '__main__':
    asyncio.run(debug_page())