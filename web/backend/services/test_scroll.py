"""
测试滚动后的截图和数据提取
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

DATA_DIR = Path('services/data')
COOKIE_FILE = DATA_DIR / 'mysteel_cookies.json'

USERNAME = 'M6616672758'
PASSWORD = 'panhui199261'

TEST_URL = 'https://jiancai.mysteel.com/m/26051410/25B3355C6617BD3C.html'


async def main():
    print('=' * 60)
    print('测试滚动和截图')
    print('=' * 60)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 3000},
            locale='zh-CN'
        )
        page = await context.new_page()

        # 加载Cookie
        if COOKIE_FILE.exists():
            try:
                cookies = json.loads(COOKIE_FILE.read_text(encoding='utf-8'))
                await context.add_cookies(cookies)
                print('已加载Cookie')
            except:
                pass

        # 访问测试URL
        print('\n1. 访问测试页面...')
        await page.goto(TEST_URL, wait_until='domcontentloaded', timeout=60000)
        await page.wait_for_timeout(5000)

        # 截图初始状态
        await page.screenshot(path=str(DATA_DIR / 'step1_initial.png'))
        print('  初始截图已保存')

        # 滚动页面
        print('\n2. 滚动页面...')
        for i in range(10):
            await page.evaluate('window.scrollBy(0, 500)')
            await page.wait_for_timeout(500)

        await page.screenshot(path=str(DATA_DIR / 'step2_after_scroll.png'))
        print('  滚动后截图已保存')

        # 滚动到顶部
        await page.evaluate('window.scrollTo(0, 0)')
        await page.wait_for_timeout(1000)

        # 等待数据加载
        print('\n3. 等待数据加载...')
        await page.wait_for_timeout(5000)

        # 截图
        await page.screenshot(path=str(DATA_DIR / 'step3_after_wait.png'))
        print('  等待后截图已保存')

        # 提取表格数据
        print('\n4. 提取表格数据...')
        data = await page.evaluate("""
            () => {
                const tables = document.querySelectorAll('table');
                const results = [];
                tables.forEach((table, idx) => {
                    const rows = table.querySelectorAll('tr');
                    rows.forEach((row, rowIdx) => {
                        const cells = row.querySelectorAll('td, th');
                        if (cells.length >= 5) {
                            const rowData = [];
                            cells.forEach(c => rowData.push(c.textContent.trim()));
                            results.push(rowData);
                        }
                    });
                });
                return {tables: tables.length, rows: results.length, sample: results.slice(0, 10)};
            }
        """)
        print(f'  找到 {data["tables"]} 个表格, {data["rows"]} 行数据')
        if data['sample']:
            print('  前5行:')
            for i, row in enumerate(data['sample'][:5]):
                print(f'    {i+1}: {row}')

        # 尝试直接提取价格
        print('\n5. 提取价格数据...')
        prices = await page.evaluate("""
            () => {
                const results = [];
                const tables = document.querySelectorAll('table');
                tables.forEach(table => {
                    const rows = table.querySelectorAll('tr');
                    rows.forEach(row => {
                        const cells = row.querySelectorAll('td');
                        if (cells.length >= 5) {
                            const material = cells[0]?.textContent?.trim() || '';
                            const spec = cells[1]?.textContent?.trim() || '';
                            const type = cells[2]?.textContent?.trim() || '';
                            const brand = cells[3]?.textContent?.trim() || '';
                            const price = cells[4]?.textContent?.trim() || '';

                            if (material && spec && price) {
                                results.push({material, spec, type, brand, price});
                            }
                        }
                    });
                });
                return results;
            }
        """)
        print(f'  找到 {len(prices)} 条价格')
        if prices:
            print('  前5条:')
            for i, p in enumerate(prices[:5]):
                print(f'    {i+1}: {p.material} {p.spec} {p.brand} {p.price}')

        await browser.close()


if __name__ == '__main__':
    asyncio.run(main())