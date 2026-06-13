"""
深入分析价格查询页面并尝试模拟查询操作
"""
import asyncio
from playwright.async_api import async_playwright
from datetime import datetime, timedelta


async def analyze_and_test_query():
    """分析页面并测试查询功能"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # 使用有界面模式便于调试
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080}, locale='zh-CN')
        page = await context.new_page()

        print("1. 访问价格查询页面...")
        url = 'https://price.mysteel.com/#/price-search?breedId=1-1'
        await page.goto(url, wait_until='networkidle', timeout=60000)
        await page.wait_for_timeout(5000)

        print(f"   当前URL: {page.url}")

        # 查找所有包含日期的元素
        print("\n2. 查找日期相关元素...")
        date_elements = await page.query_selector_all('[class*="date"], [class*="time"], [class*="calendar"], input[type="text"]')
        print(f"   找到 {len(date_elements)} 个可能相关的元素")

        for i, el in enumerate(date_elements[:15]):
            try:
                tag = await el.evaluate('e => e.tagName')
                class_name = await el.get_attribute('class')
                placeholder = await el.get_attribute('placeholder')
                value = await el.input_value() if tag == 'INPUT' else ''
                print(f"   [{i}] {tag} - class={class_name[:40]}, placeholder={placeholder}, value={value}")
            except:
                pass

        # 查找地区相关的元素
        print("\n3. 查找地区选择元素...")
        region_elements = await page.query_selector_all('select, [class*="region"], [class*="city"], [class*="area"]')
        print(f"   找到 {len(region_elements)} 个地区相关元素")

        # 尝试找到烟台相关的选项
        print("\n4. 尝试查找烟台地区...")
        all_text = await page.text_content('body')
        if '烟台' in all_text:
            print("   页面包含'烟台'文字")
            # 查找包含烟台的元素
            yantai_elements = await page.query_selector_all('*:has-text("烟台")')
            print(f"   找到 {len(yantai_elements)} 个包含'烟台'的元素")

            for el in yantai_elements[:5]:
                try:
                    tag = await el.evaluate('e => e.tagName')
                    class_name = await el.get_attribute('class')
                    text = await el.text_content()
                    print(f"     - {tag} class={class_name[:30]} text={text.strip()[:50]}")
                except:
                    pass

        # 查找查询按钮
        print("\n5. 查找查询按钮...")
        buttons = await page.query_selector_all('button, [role="button"], [class*="btn"], [class*="search"]')
        print(f"   找到 {len(buttons)} 个按钮")

        for btn in buttons[:15]:
            try:
                text = await btn.text_content()
                btn_class = await btn.get_attribute('class')
                if text and any(kw in text for kw in ['查询', '搜索', '确定', '重置']):
                    print(f"     - [{text.strip()}] class={btn_class[:50] if btn_class else ''}")
            except:
                pass

        # 查看当前表格数据
        print("\n6. 查看当前表格数据...")
        tables = await page.query_selector_all('table')
        print(f"   找到 {len(tables)} 个表格")

        for idx, table in enumerate(tables[:3]):
            try:
                rows = await table.query_selector_all('tr')
                print(f"   表格 {idx + 1}: {len(rows)} 行")

                # 获取前3行数据
                for row_idx, row in enumerate(rows[:3]):
                    cells = await row.query_selector_all('td, th')
                    row_data = []
                    for cell in cells:
                        text = await cell.text_content()
                        if text:
                            row_data.append(text.strip()[:20])
                    if row_data:
                        print(f"     行{row_idx}: {row_data}")
            except:
                pass

        print("\n7. 等待10秒，请手动查看页面...")
        await page.wait_for_timeout(10000)

        await browser.close()


if __name__ == '__main__':
    asyncio.run(analyze_and_test_query())
