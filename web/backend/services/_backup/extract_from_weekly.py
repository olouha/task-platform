"""
从周报页面提取单日数据
周报可能包含每日的价格明细
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright
import re

DATA_DIR = Path('services/data')
COOKIE_FILE = DATA_DIR / 'mysteel_cookies.json'


def load_cookies():
    if COOKIE_FILE.exists():
        with open(COOKIE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


async def extract_daily_from_weekly():
    """从周报页面提取单日数据"""
    print("=" * 60)
    print("从周报提取单日数据")
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

        # 访问周报页面
        weekly_url = 'https://jiancai.mysteel.com/m/26051101/AAAAE5CF09F75466.html'
        print(f"\n[访问] {weekly_url}")
        print(f"  (2026年5月4日-5月10日烟台市场建筑钢材周均价格)")

        await page.goto(weekly_url, wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(3)

        # 分析页面内容
        print("\n[分析] 页面内容...")

        page_content = await page.evaluate('''() => {
            const body = document.body;

            return {
                text: body.textContent,
                html: body.innerHTML.substring(0, 10000)
            };
        }''')

        # 查找是否包含每日数据
        text = page_content['text']

        # 查找日期模式
        date_pattern = r'5月\\d+[日号]'
        dates = re.findall(date_pattern, text)
        print(f"\n  找到日期: {dates[:10]}")

        # 查找价格数据
        price_pattern = r'\\d{4}'
        prices = re.findall(price_pattern, text)
        # 过滤出合理价格范围
        valid_prices = [int(p) for p in prices if 3000 < int(p) < 10000]
        print(f"  找到价格: {valid_prices[:20]}")

        # 截图
        await page.screenshot(path='weekly_page.png', full_page=True)
        print(f"\n[截图] weekly_page.png")

        # 深度分析表格
        print("\n[分析] 表格数据...")

        tables = await page.evaluate('''() => {
            const results = [];
            const tables = document.querySelectorAll('table');

            tables.forEach((table, idx) => {
                const rows = table.querySelectorAll('tr');
                const tableData = [];

                rows.forEach((row, rowIdx) => {
                    const cells = row.querySelectorAll('td, th');
                    const rowData = [];
                    cells.forEach(cell => {
                        rowData.push({
                            text: cell.textContent.trim(),
                            colspan: cell.getAttribute('colspan') || '1',
                            rowspan: cell.getAttribute('rowspan') || '1'
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
                        tableIdx: idx,
                        rowCount: tableData.length,
                        data: tableData
                    });
                }
            });

            return results;
        }''')

        print(f"\n  找到 {len(tables)} 个表格")

        for table in tables[:2]:
            print(f"\n  表格 {table['tableIdx']} ({table['rowCount']} 行):")
            # 显示前几行
            for row in table['data'][:8]:
                cells_text = [cell['text'] for cell in row['cells']]
                print(f"    行{row['rowIdx']}: {cells_text[:8]}")

        # 保存分析结果
        with open('weekly_page_analysis.json', 'w', encoding='utf-8') as f:
            json.dump({
                'tables': tables,
                'dates': dates,
                'prices': valid_prices[:50]
            }, f, ensure_ascii=False, indent=2)
        print(f"\n[保存] weekly_page_analysis.json")

        await browser.close()

    print("\n" + "=" * 60)
    print("分析完成")
    print("=" * 60)


if __name__ == '__main__':
    try:
        asyncio.run(extract_daily_from_weekly())
    except KeyboardInterrupt:
        print("\n\n[中断]")
