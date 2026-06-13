"""
深度探索：查找单日价格数据来源
从当前价格页面分析，查找历史单日数据的获取方式
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


async def explore_daily_data_source():
    """探索单日数据来源"""
    print("=" * 60)
    print("探索单日价格数据来源")
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

        # 访问基础价格页面
        base_url = 'https://jiancai.mysteel.com/m/26051410/25B3355C6617BD3C.html'
        print(f"\n[访问] {base_url}")
        await page.goto(base_url, wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(3)

        # 深度分析页面结构
        print("\n[分析] 查找单日数据相关元素...")

        analysis = await page.evaluate('''() => {
            const result = {
                // 查找所有表格
                tables: [],
                // 查找所有可能的分页链接
                paginationLinks: [],
                // 查找日期相关元素
                dateElements: [],
                // 查找"上一页"/"下一页"类型的链接
                navLinks: [],
                // 查找所有包含数字的链接（可能是日期）
                numberLinks: []
            };

            // 分析表格
            const tables = document.querySelectorAll('table');
            tables.forEach((table, idx) => {
                const rows = table.querySelectorAll('tr');
                const tableInfo = {
                    index: idx,
                    rowCount: rows.length,
                    hasHeader: false,
                    sampleData: []
                };

                // 检查表头
                if (rows.length > 0) {
                    const firstRow = rows[0];
                    const headers = firstRow.querySelectorAll('th, td');
                    tableInfo.hasHeader = headers.length > 0;

                    // 采样前5行数据
                    for (let i = 0; i < Math.min(6, rows.length); i++) {
                        const cells = rows[i].querySelectorAll('td, th');
                        const rowData = Array.from(cells).map(c => c.textContent.trim());
                        tableInfo.sampleData.push(rowData);
                    }
                }

                result.tables.push(tableInfo);
            });

            // 查找分页链接
            const allLinks = document.querySelectorAll('a[href]');
            allLinks.forEach(link => {
                const href = link.href;
                const text = link.textContent.trim();

                // 查找分页相关
                if (/上一页|下一页|prev|next|页|\d+/.test(text) && href.includes('mysteel')) {
                    result.paginationLinks.push({
                        url: href,
                        text: text
                    });
                }

                // 查找导航链接
                if (/prev|next|last|first/i.test(href) || /上一页|下一页|首页|末页/.test(text)) {
                    result.navLinks.push({
                        url: href,
                        text: text
                    });
                }
            });

            // 查找日期相关元素
            const dateInputs = document.querySelectorAll('input[type="date"], input[placeholder*="日期"]');
            dateInputs.forEach(el => {
                result.dateElements.push({
                    type: 'input',
                    id: el.id,
                    placeholder: el.placeholder
                });
            });

            // 查找包含纯数字的链接（可能是日期页码）
            const numericLinks = [];
            allLinks.forEach(link => {
                const text = link.textContent.trim();
                if (/^\d+$/.test(text)) {
                    const href = link.href;
                    if (href.includes('mysteel.com/m/')) {
                        result.numberLinks.push({
                            url: href,
                            number: parseInt(text)
                        });
                    }
                }
            });

            return result;
        }''')

        # 输出分析结果
        print(f"\n[表格分析] 找到 {len(analysis['tables'])} 个表格")
        for table in analysis['tables']:
            print(f"\n  表格 {table['index']}:")
            print(f"    行数: {table['rowCount']}")
            print(f"    有表头: {table['hasHeader']}")
            print(f"    示例数据:")
            for row in table['sampleData'][:3]:
                print(f"      {row[:5]}")

        print(f"\n[分页链接] 找到 {len(analysis['paginationLinks'])} 个")
        for link in analysis['paginationLinks'][:10]:
            print(f"  - {link['text']}: {link['url']}")

        print(f"\n[导航链接] 找到 {len(analysis['navLinks'])} 个")
        for link in analysis['navLinks']:
            print(f"  - {link['text']}: {link['url']}")

        print(f"\n[数字链接] 找到 {len(analysis['numberLinks'])} 个（可能包含分页）")
        if analysis['numberLinks']:
            numbers = sorted([link['number'] for link in analysis['numberLinks']])
            print(f"  数字范围: {min(numbers)} ~ {max(numbers)}")

        # 尝试点击"下一页"并观察URL变化
        print("\n[测试] 尝试分页导航...")

        try:
            # 查找"下一页"按钮
            next_selectors = [
                'a:has-text("下一页")',
                'a:has-text(">")',
                'a.next',
                '.next-page'
            ]

            for selector in next_selectors:
                try:
                    next_btn = await page.query_selector(selector)
                    if next_btn:
                        next_href = await next_btn.get_attribute('href')
                        print(f"\n  找到下一页按钮: {next_href}")

                        # 获取当前URL
                        current_url = page.url
                        print(f"  当前URL: {current_url}")

                        # 点击下一页
                        await next_btn.click()
                        await asyncio.sleep(3)

                        new_url = page.url
                        print(f"  点击后URL: {new_url}")

                        # 截图
                        await page.screenshot(path='next_page.png', full_page=True)
                        print(f"  已截图: next_page.png")

                        break
                except:
                    pass
        except Exception as e:
            print(f"  分页测试失败: {e}")

        print("\n[分析完成]")

        # 保存分析结果
        with open('daily_data_analysis.json', 'w', encoding='utf-8') as f:
            json.dump(analysis, f, ensure_ascii=False, indent=2)
        print("分析结果已保存: daily_data_analysis.json")

        await browser.close()

    print("\n" + "=" * 60)
    print("探索完成")
    print("=" * 60)


if __name__ == '__main__':
    try:
        asyncio.run(explore_daily_data_source())
    except KeyboardInterrupt:
        print("\n\n[中断]")
