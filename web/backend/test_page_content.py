"""
测试脚本 - 查看页面实际内容
"""
import asyncio
from playwright.async_api import async_playwright
import json

async def test_page():
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=False)
    context = await browser.new_context(viewport={'width': 1920, 'height': 3000})

    # 加载Cookie
    try:
        with open('services/data/mysteel_cookies.json', 'r', encoding='utf-8') as f:
            cookies = json.load(f)
        await context.add_cookies(cookies)
        print(f"加载了 {len(cookies)} 个Cookie")
    except:
        print("没有Cookie")

    page = await context.new_page()

    # 测试URL
    test_url = "https://jiancai.mysteel.com/m/26061010/B246DF5412BAD7A9.html"
    print(f"\n访问: {test_url}")

    await page.goto(test_url, wait_until='networkidle', timeout=30000)
    await asyncio.sleep(5)

    # 截图
    await page.screenshot(path="test_page.png", full_page=True)
    print("截图已保存: test_page.png")

    # 获取页面标题
    title = await page.title()
    print(f"页面标题: {title}")

    # 获取页面HTML（部分）
    body_html = await page.evaluate('''() => {
        return document.body.innerHTML.substring(0, 5000);
    }''')
    print(f"\n页面HTML前5000字符:\n{body_html}")

    # 尝试多种方式提取表格
    print("\n=== 尝试提取表格 ===")

    # 方式1: 所有table
    tables = await page.evaluate('''() => {
        const all = document.querySelectorAll('table');
        return {
            count: all.length,
            tables: Array.from(all).map((t, i) => ({
                index: i,
                rows: t.querySelectorAll('tr').length,
                className: t.className,
                id: t.id
            }))
        };
    }''')
    print(f"找到 {tables['count']} 个table标签")
    for t in tables['tables'][:5]:
        print(f"  表格{t['index']}: {t['rows']}行, class='{t['className']}', id='{t['id']}'")

    # 方式2: 尝试获取第一个表格的内容
    if tables['count'] > 0:
        table_data = await page.evaluate('''() => {
            const table = document.querySelector('table');
            if (!table) return null;
            const rows = table.querySelectorAll('tr');
            return Array.from(rows).slice(0, 10).map(row => {
                const cells = row.querySelectorAll('td, th');
                return Array.from(cells).map(c => c.textContent.trim());
            });
        }''')
        print("\n第一个表格前10行:")
        for row in table_data:
            print(f"  {row}")

    # 方式3: 查找所有包含价格的元素
    price_elements = await page.evaluate('''() => {
        const results = [];
        // 查找所有可能是价格的元素
        document.querySelectorAll('*').forEach(el => {
            const text = el.textContent.trim();
            // 价格通常是3-4位数字
            if (/^[0-9]{3,4}$/.test(text) && el.children.length === 0) {
                results.push(text);
            }
        });
        return results.slice(0, 20);
    }''')
    print(f"\n找到的可能价格元素: {price_elements}")

    # 方式4: 获取所有链接中的日期
    links = await page.evaluate('''() => {
        return Array.from(document.querySelectorAll('a')).map(a => ({
            href: a.href,
            text: a.textContent.trim()
        })).filter(l => l.href.includes('mysteel.com/m/') && l.text.length > 0 && l.text.length < 100);
    }''')
    print(f"\n页面中的价格链接 ({len(links)}个):")
    for link in links[:10]:
        print(f"  {link['text']}: {link['href']}")

    print("\n等待30秒...")
    await asyncio.sleep(30)

    await browser.close()

if __name__ == '__main__':
    asyncio.run(test_page())
