"""
分析用户提供的市场页面
查找烟台历史价格数据入口
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

DATA_DIR = Path('services/data')
COOKIE_FILE = DATA_DIR / 'mysteel_cookies.json'


def load_cookies():
    if COOKIE_FILE.exists():
        with open(COOKIE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


async def analyze_market_page():
    """分析市场页面"""
    print("=" * 60)
    print("分析市场页面")
    print("=" * 60)

    cookies = load_cookies()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            locale='zh-CN'
        )

        if cookies:
            await context.add_cookies(cookies)

        page = await context.new_page()

        # 用户提供的URL
        url = 'https://jiancai.mysteel.com/market/pa228aa010101a0a01010205aaaa1.html'
        print(f"\n[访问] {url}")

        await page.goto(url, wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(3)

        # 截图
        await page.screenshot(path='market_page.png', full_page=True)
        print(f"[截图] market_page.png")

        # 分析页面内容
        print("\n[分析] 页面内容...")

        analysis = await page.evaluate('''() => {
            const results = {
                pageTitle: document.title,
                allLinks: [],
                yantaiLinks: [],
                dateLinks: [],
                tables: []
            };

            // 查找所有链接
            const allLinks = document.querySelectorAll('a[href]');
            allLinks.forEach(link => {
                const href = link.href;
                const text = link.textContent.trim();

                // 查找烟台相关链接
                if (text.includes('烟台') || href.includes('yantai')) {
                    results.yantaiLinks.push({ url: href, text: text });
                }

                // 查找包含日期的链接
                if (text.match(/\\d{4}-\\d{2}-\\d{2}|\\d{1,2}月\\d{1,2}日/)) {
                    results.dateLinks.push({ url: href, text: text });
                }

                results.allLinks.push({ url: href, text: text.substring(0, 50) });
            });

            // 分析表格
            const tables = document.querySelectorAll('table');
            tables.forEach((table, idx) => {
                const rows = table.querySelectorAll('tr');
                const tableData = [];

                rows.forEach((row, rowIdx) => {
                    const cells = row.querySelectorAll('td, th');
                    const rowData = [];
                    cells.forEach(cell => {
                        rowData.push(cell.textContent.trim());
                    });
                    if (rowData.length > 0) {
                        tableData.push({ rowIdx: rowIdx, cells: rowData });
                    }
                });

                if (tableData.length > 0 && tableData.length < 200) {
                    results.tables.push({
                        tableIdx: idx,
                        rowCount: tableData.length,
                        sampleRows: tableData.slice(0, 10)
                    });
                }
            });

            return results;
        }''')

        print(f"\n页面标题: {analysis['pageTitle']}")
        print(f"总链接数: {len(analysis['allLinks'])}")

        print(f"\n[烟台相关链接] {len(analysis['yantaiLinks'])} 个:")
        for link in analysis['yantaiLinks'][:15]:
            print(f"  - {link['text']}: {link['url']}")

        print(f"\n[日期相关链接] {len(analysis['dateLinks'])} 个:")
        for link in analysis['dateLinks'][:15]:
            print(f"  - {link['text']}: {link['url']}")

        print(f"\n[表格] {len(analysis['tables'])} 个:")
        for table in analysis['tables']:
            print(f"\n  表格 {table['tableIdx']} ({table['rowCount']} 行):")
            for row in table['sampleRows'][:5]:
                print(f"    行{row['rowIdx']}: {row['cells'][:6]}")

        # 保存分析结果
        with open('market_page_analysis.json', 'w', encoding='utf-8') as f:
            json.dump(analysis, f, ensure_ascii=False, indent=2)
        print(f"\n[保存] market_page_analysis.json")

        await browser.close()

    print("\n" + "=" * 60)
    print("分析完成")
    print("=" * 60)


if __name__ == '__main__':
    try:
        asyncio.run(analyze_market_page())
    except KeyboardInterrupt:
        print("\n\n[中断]")
