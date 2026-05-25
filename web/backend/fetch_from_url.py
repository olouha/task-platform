"""从正确URL提取烟台价格数据"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

DATA_DIR = Path(r'E:\E\任务\task-platform\web\backend\services\data')

async def fetch_from_correct_url():
    """从正确URL提取数据"""
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

        # 访问正确的URL
        url = 'https://jiancai.mysteel.com/m/26051516/06AC8B0B0D2BB9BF.html'
        print(f"访问: {url}")
        await page.goto(url, wait_until='domcontentloaded', timeout=60000)
        await page.wait_for_timeout(10000)

        # 提取表格数据
        data = await page.evaluate('''() => {
            const tables = document.querySelectorAll('table');
            const results = [];

            tables.forEach((table, tableIdx) => {
                const rows = table.querySelectorAll('tr');
                const tableData = [];

                rows.forEach((row, rowIdx) => {
                    const cells = row.querySelectorAll('td, th');
                    const rowData = [];
                    cells.forEach(c => {
                        rowData.push(c.textContent?.trim() || '');
                    });
                    if (rowData.length > 0 && rowData.some(c => c.length > 0)) {
                        tableData.push(rowData);
                    }
                });

                if (tableData.length > 0) {
                    results.push({
                        tableIdx,
                        rowCount: tableData.length,
                        headers: tableData[0],
                        sampleRows: tableData.slice(1, 5)
                    });
                }
            });

            return results;
        }''')

        print(f"\n找到 {len(data)} 个表格")
        for t in data:
            print(f"\n表格 {t['tableIdx']}:")
            print(f"  行数: {t['rowCount']}")
            print(f"  表头: {t['headers'][:10]}")
            print(f"  示例行:")
            for r in t['sampleRows']:
                print(f"    {r[:8]}")

        # 提取完整价格数据
        prices = await page.evaluate('''() => {
            const tables = document.querySelectorAll('table');
            const allPrices = [];

            tables.forEach((table, tableIdx) => {
                const rows = table.querySelectorAll('tr');

                rows.forEach((row, rowIdx) => {
                    const cells = row.querySelectorAll('td');
                    if (cells.length >= 4) {
                        const rowData = [];
                        cells.forEach(c => rowData.push(c.textContent?.trim() || ''));

                        // 检查是否是价格行
                        if (rowData.length > 0 &&
                            (rowData[0].includes('螺纹钢') || rowData[0].includes('盘螺') ||
                             rowData[0].includes('高线') || rowData[0].includes('圆钢'))) {

                            // 查找价格列
                            let price = '';
                            for (let i = 0; i < rowData.length; i++) {
                                const val = rowData[i];
                                if (/^\\d{3,4}$/.test(val)) {
                                    price = val;
                                    break;
                                }
                            }

                            if (price) {
                                allPrices.push({
                                    material_name: rowData[0] || '',
                                    spec: rowData[1] || '',
                                    material_type: rowData[2] || '',
                                    brand: rowData[3] || '',
                                    price: price,
                                    fullRow: rowData.slice(0, 8)
                                });
                            }
                        }
                    }
                });
            });

            return allPrices;
        }''')

        print(f"\n提取到 {len(prices)} 条价格数据:")
        for p in prices[:10]:
            print(f"  {p['material_name']}: {p['spec']}, {p['brand']}, {p['price']}元")

        # 保存结果
        result_file = DATA_DIR / 'fetch_result.json'
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(prices, f, ensure_ascii=False, indent=2)
        print(f"\n结果已保存到: {result_file}")

        await browser.close()

if __name__ == '__main__':
    asyncio.run(fetch_from_correct_url())