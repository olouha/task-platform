"""
检测价格查询页面是否支持历史日期查询
"""
import asyncio
from playwright.async_api import async_playwright
import json


async def check_price_search():
    """检查价格查询页面的功能"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080}, locale='zh-CN')
        page = await context.new_page()

        print("1. 访问价格查询页面...")
        url = 'https://price.mysteel.com/#/price-search?breedId=1-1'
        await page.goto(url, wait_until='domcontentloaded', timeout=60000)
        await page.wait_for_timeout(8000)

        print(f"   当前URL: {page.url}")

        # 截图
        await page.screenshot(path='price_search_page.png', full_page=True)
        print("   截图已保存: price_search_page.png")

        # 查找输入框
        inputs = await page.query_selector_all('input, select')
        print(f"\n2. 找到 {len(inputs)} 个输入控件:")

        for i, inp in enumerate(inputs[:20]):
            try:
                inp_type = await inp.get_attribute('type')
                placeholder = await inp.get_attribute('placeholder')
                name = await inp.get_attribute('name')
                inp_id = await inp.get_attribute('id')
                inp_class = await inp.get_attribute('class')
                tag = await inp.evaluate('el => el.tagName')

                print(f"   [{i}] {tag} - type={inp_type}, id={inp_id}, name={name}, placeholder={placeholder}, class={inp_class[:50] if inp_class else ''}")
            except:
                pass

        # 查找日期相关控件
        print("\n3. 查找日期相关控件...")
        date_inputs = await page.query_selector_all('input[type="date"], input[placeholder*="日期"], input[placeholder*="时间"]')
        print(f"   日期输入框: {len(date_inputs)} 个")

        # 查找地区选择
        print("\n4. 查找地区选择...")
        region_selects = await page.query_selector_all('select, [class*="region"], [class*="area"], [class*="city"]')
        print(f"   地区选择: {len(region_selects)} 个")

        # 尝试选择烟台地区
        for sel in region_selects[:5]:
            try:
                options = await sel.query_selector_all('option')
                if options:
                    print(f"   选项数量: {len(options)}")
                    for opt in options[:10]:
                        text = await opt.text_content()
                        val = await opt.get_attribute('value')
                        if '烟台' in text or 'yantai' in text.lower():
                            print(f"     - 找到烟台选项: {text} (value={val})")
            except:
                pass

        # 查找查询按钮
        print("\n5. 查找查询按钮...")
        buttons = await page.query_selector_all('button, [role="button"], a:has-text("查询")')
        print(f"   按钮/链接: {len(buttons)} 个")

        for btn in buttons[:10]:
            try:
                text = await btn.text_content()
                btn_type = await btn.get_attribute('type')
                if text and any(kw in text for kw in ['查询', '搜索', '确定', '搜索']):
                    print(f"     - [{text}] (type={btn_type})")
            except:
                pass

        # 查看表格
        print("\n6. 查找数据表格...")
        tables = await page.query_selector_all('table')
        print(f"   表格数量: {len(tables)} 个")

        # 尝试获取表格数据
        for idx, table in enumerate(tables[:2]):
            try:
                rows = await table.query_selector_all('tr')
                print(f"   表格 {idx + 1}: {len(rows)} 行")

                # 获取表头
                headers = await table.query_selector_all('th')
                if headers:
                    header_texts = []
                    for h in headers[:10]:
                        text = await h.text_content()
                        if text:
                            header_texts.append(text.strip())
                    print(f"     表头: {header_texts}")
            except:
                pass

        await browser.close()


if __name__ == '__main__':
    asyncio.run(check_price_search())
