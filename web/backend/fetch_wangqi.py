"""获取往期历史数据"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

DATA_DIR = Path(r'E:\E\任务\task-platform\web\backend\services\data')

async def fetch_history():
    """获取历史数据"""
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

        # 查找"往期"按钮
        wangqi_btn = await page.query_selector('text=往期')
        if wangqi_btn:
            print("找到往期按钮")
            await wangqi_btn.click()
            await page.wait_for_timeout(3000)

            # 截图
            screenshot = await page.screenshot(full_page=True)
            screenshot_path = DATA_DIR / 'wangqi_clicked.png'
            with open(screenshot_path, 'wb') as f:
                f.write(screenshot)
            print(f"截图已保存")

            # 查找往期数据
            wangqi_data = await page.evaluate('''() => {
                const tables = document.querySelectorAll('table');
                const results = [];

                tables.forEach((table, idx) => {
                    const rows = table.querySelectorAll('tr');
                    const tableData = [];

                    rows.forEach((row) => {
                        const cells = row.querySelectorAll('td');
                        const rowData = [];
                        cells.forEach(c => rowData.push(c.textContent?.trim() || ''));
                        if (rowData.length > 0 && rowData.some(c => c.length > 0)) {
                            tableData.push(rowData);
                        }
                    });

                    if (tableData.length > 0) {
                        results.push({
                            idx,
                            rowCount: tableData.length,
                            headers: tableData[0] if tableData.length > 0 else [],
                            sampleRows: tableData.slice(1, 5)
                        });
                    }
                });

                return results;
            }''')

            print(f"\n找到 {len(wangqi_data)} 个表格")
            for t in wangqi_data:
                print(f"\n表格 {t['idx']}:")
                print(f"  行数: {t['rowCount']}")
                print(f"  表头: {t['headers'][:10]}")
                print(f"  示例行:")
                for r in t['sampleRows']:
                    print(f"    {r[:8]}")

        else:
            print("未找到往期按钮")

        await browser.close()

if __name__ == '__main__':
    asyncio.run(fetch_history())