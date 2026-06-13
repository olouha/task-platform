"""
检测我的钢铁网是否支持历史价格查询
"""
import asyncio
from playwright.async_api import async_playwright
from datetime import datetime


async def check_history_support():
    """检查是否有历史价格查询功能"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080}, locale='zh-CN')
        page = await context.new_page()

        print("1. 访问我的钢铁网价格页...")
        url = 'https://jiancai.mysteel.com/m/26051410/25B3355C6617BD3C.html'
        await page.goto(url, wait_until='domcontentloaded', timeout=60000)
        await page.wait_for_timeout(5000)

        print("2. 检查是否有日期选择器...")

        # 查找日期选择器
        date_pickers = await page.query_selector_all('''
            input[type="date"],
            input[type="text"][placeholder*="日期"],
            .date-picker,
            [class*="datepicker"],
            [class*="calendar"]
        ''')
        print(f"   找到日期选择器: {len(date_pickers)} 个")

        # 查找历史/导航按钮
        nav_buttons = await page.query_selector_all('''
            button:has-text("历史"),
            a:has-text("历史"),
            button:has-text("查询"),
            a:has-text("查询")
        ''')
        print(f"   找到历史/查询按钮: {len(nav_buttons)} 个")

        # 查找分页链接（可能包含日期参数）
        page_links = await page.query_selector_all('a[href*="page"], a[href*="date"], a[href*="time"]')
        print(f"   找到分页/日期链接: {len(page_links)} 个")

        # 截图
        await page.screenshot(path='check_history_page.png', full_page=True)
        print("3. 页面截图已保存: check_history_page.png")

        # 查看当前URL
        print(f"   当前URL: {page.url}")

        # 尝试查找所有链接
        all_links = await page.query_selector_all('a')
        print(f"   页面上共有 {len(all_links)} 个链接")

        # 查找可能相关的链接
        interesting_links = []
        for link in all_links:
            try:
                text = await link.text_content()
                href = await link.get_attribute('href')
                if text and href and any(kw in text.lower() for kw in ['历史', '查询', '日期', '价格', '导航']):
                    interesting_links.append((text.strip(), href))
            except:
                pass

        if interesting_links:
            print("\n   可能相关的链接:")
            for text, href in interesting_links[:10]:
                print(f"     - [{text}]: {href}")

        await browser.close()

        return {
            'has_date_picker': len(date_pickers) > 0,
            'has_history_button': len(nav_buttons) > 0,
            'has_page_links': len(page_links) > 0,
            'interesting_links': interesting_links
        }


if __name__ == '__main__':
    result = asyncio.run(check_history_support())
    print(f"\n检测结果:")
    print(f"  日期选择器: {result['has_date_picker']}")
    print(f"  历史按钮: {result['has_history_button']}")
    print(f"  分页链接: {result['has_page_links']}")

    if not any([result['has_date_picker'], result['has_history_button'], result['has_page_links']]):
        print("\n⚠️ 该页面可能不支持历史价格查询")
        print("   建议联系网站客服或寻找其他数据源")
