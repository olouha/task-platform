"""
调试脚本：分析页面表格结构
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

DATA_DIR = Path('services/data')
COOKIE_FILE = DATA_DIR / 'mysteel_cookies.json'

TARGET_URL = "https://jiancai.mysteel.com/m/26060916/E3B5B7AB6E55FC6D.html"


async def analyze_page():
    print("=" * 60)
    print("页面结构分析工具")
    print("=" * 60)

    # 加载Cookie
    cookies = []
    if COOKIE_FILE.exists():
        with open(COOKIE_FILE, 'r', encoding='utf-8') as f:
            cookies = json.load(f)
        print(f"\n加载了 {len(cookies)} 条Cookie")

    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=False)
    context = await browser.new_context(viewport={'width': 1920, 'height': 1080}, locale='zh-CN')

    if cookies:
        await context.add_cookies(cookies)

    page = await context.new_page()

    print("\n正在访问目标页面...")
    await page.goto(TARGET_URL, wait_until='networkidle', timeout=60000)
    await asyncio.sleep(3)

    # 分析所有表格
    print("\n" + "=" * 60)
    print("分析表格结构...")
    print("=" * 60)

    tables_info = await page.evaluate('''() => {
        const tables = document.querySelectorAll('table');
        const results = [];

        tables.forEach((table, idx) => {
            const rows = Array.from(table.querySelectorAll('tr'));
            const firstRow = rows[0];

            // 获取表头信息
            let headers = [];
            if (firstRow) {
                const headerCells = firstRow.querySelectorAll('th, td');
                headers = Array.from(headerCells).map(cell => ({
                    text: cell.textContent.trim(),
                    colspan: parseInt(cell.getAttribute('colspan') || '1'),
                    rowspan: parseInt(cell.getAttribute('rowspan') || '1')
                }));
            }

            // 获取前3行数据
            const sampleRows = rows.slice(0, 5).map(row => {
                const cells = row.querySelectorAll('td, th');
                return Array.from(cells).map(cell => cell.textContent.trim());
            });

            results.push({
                index: idx,
                id: table.id || '',
                className: table.className || '',
                rowCount: rows.length,
                headers: headers,
                sampleRows: sampleRows
            });
        });

        return results;
    }''')

    for i, table in enumerate(tables_info):
        print(f"\n表格 {i}:")
        print(f"  ID: '{table['id']}'")
        print(f"  Class: '{table['className']}'")
        print(f"  行数: {table['rowCount']}")

        print(f"  表头:")
        for h in table['headers']:
            print(f"    - '{h['text']}' (colspan={h['colspan']}, rowspan={h['rowspan']})")

        print(f"  前5行样本:")
        for r_idx, row in enumerate(table['sampleRows']):
            print(f"    行{r_idx}: {row[:8]}")  # 只显示前8列

    # 保存详细分析到文件
    output_file = DATA_DIR / 'page_analysis.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(tables_info, f, ensure_ascii=False, indent=2)
    print(f"\n详细分析已保存到: {output_file}")

    print("\n" + "=" * 60)
    print("按 Enter 关闭浏览器...")
    input()

    await browser.close()
    await playwright.stop()


if __name__ == '__main__':
    asyncio.run(analyze_page())
