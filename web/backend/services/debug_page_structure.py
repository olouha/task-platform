"""
调试脚本：访问已知有效的页面，分析数据提取方式
"""
import asyncio
from playwright.async_api import async_playwright
import json
from pathlib import Path

DATA_DIR = Path('services/data')
COOKIE_FILE = DATA_DIR / 'mysteel_cookies.json'


def load_cookies():
    if COOKIE_FILE.exists():
        with open(COOKIE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


async def debug_page_structure():
    """调试页面结构"""
    print("=" * 60)
    print("调试：分析页面数据结构")
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

        # 测试已知有效的URL
        test_urls = [
            'https://jiancai.mysteel.com/p/26051409/864C3A3F5673C262.html',  # 5月14日螺纹钢
            'https://jiancai.mysteel.com/p/26051409/F604D782F4BDF4E5.html',  # 5月14日线材
        ]

        for url in test_urls:
            print(f"\n[访问] {url}")
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(3)

            # 获取页面文本
            page_text = await page.evaluate('() => document.body.textContent')
            print(f"  页面长度: {len(page_text)} 字符")

            if '烟台' in page_text:
                print(f"  OK 页面包含'烟台'")
            else:
                print(f"  X 页面不包含'烟台'")

            # 截图
            screenshot_name = url.split('/')[-1].replace('.html', '')
            await page.screenshot(path=f'debug_{screenshot_name}.png', full_page=True)
            print(f"  已截图: debug_{screenshot_name}.png")

            # 提取所有表格数据
            tables_data = await page.evaluate('''() => {
                const results = [];
                const tables = document.querySelectorAll('table');

                tables.forEach((table, tableIdx) => {
                    const rows = table.querySelectorAll('tr');
                    const tableData = [];

                    rows.forEach((row, rowIdx) => {
                        const cells = row.querySelectorAll('td, th');
                        const rowData = [];
                        cells.forEach(cell => {
                            rowData.push({
                                text: cell.textContent.trim(),
                                html: cell.innerHTML.substring(0, 100)
                            });
                        });
                        if (rowData.length > 0) {
                            tableData.push({
                                rowIdx: rowIdx,
                                cells: rowData
                            });
                        }
                    });

                    if (tableData.length > 0) {
                        results.push({
                            tableIdx: tableIdx,
                            rowCount: tableData.length,
                            data: tableData.slice(0, 5)  // 只保存前5行
                        });
                    }
                });

                return results;
            }''')

            print(f"  提取到 {len(tables_data)} 个表格")

            for table in tables_data[:2]:  # 只显示前2个表格
                print(f"\n  表格 {table['tableIdx']}:")
                print(f"    总行数: {table['rowCount']}")
                print(f"    前5行数据:")

                for row in table['data']:
                    cells_text = [cell['text'] for cell in row['cells']]
                    print(f"      行{row['rowIdx']}: {cells_text[:6]}")

            print(f"\n  [分析完成]")

            # 等待一下再处理下一个URL
            await asyncio.sleep(2)

        await browser.close()

    print("\n" + "=" * 60)
    print("调试完成")
    print("=" * 60)


if __name__ == '__main__':
    try:
        asyncio.run(debug_page_structure())
    except KeyboardInterrupt:
        print("\n\n[中断]")
