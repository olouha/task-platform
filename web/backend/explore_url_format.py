"""
探索我的钢铁网历史价格URL格式
"""
import asyncio
from playwright.async_api import async_playwright
import json
from pathlib import Path

DATA_DIR = Path('services/data')
COOKIE_FILE = DATA_DIR / 'mysteel_cookies.json'


async def explore_url_format():
    """探索URL格式"""
    print("=" * 60)
    print("探索历史价格URL格式")
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

    # 方法1: 从主页导航到历史价格
    print("\n[方法1] 从主页导航...")

    # 先访问价格页面
    current_url = "https://jiancai.mysteel.com/m/26060916/E3B5B7AB6E55FC6D.html"
    print(f"当前URL: {current_url}")

    await page.goto(current_url, wait_until='networkidle', timeout=60000)
    await asyncio.sleep(3)

    # 尝试找到日期选择器或历史链接
    print("\n[正在分析] 查找日期选择器...")

    # 查找可能的日期选择元素
    date_selectors = await page.evaluate('''() => {
        const results = [];

        // 查找日期相关的元素
        const dateInputs = document.querySelectorAll('input[type="date"], input[name*="date"], input[id*="date"]');
        dateInputs.forEach(el => results.push({
            type: 'date_input',
            id: el.id,
            name: el.name,
            className: el.className,
            value: el.value
        }));

        // 查找日期选择按钮
        const dateButtons = document.querySelectorAll('button, a');
        dateButtons.forEach(el => {
            const text = el.textContent.trim();
            if (/日期|历史|昨日|前日|上期/.test(text)) {
                results.push({
                    type: 'date_button',
                    text: text,
                    href: el.href || '',
                    onclick: el.onclick ? 'has_click' : ''
                });
            }
        });

        return results;
    }''')

    print("\n找到的日期相关元素:")
    for item in date_selectors:
        print(f"  {item}")

    # 方法2: 查找分页链接
    print("\n[正在分析] 查找分页链接...")

    page_links = await page.evaluate('''() => {
        const links = Array.from(document.querySelectorAll('a'));
        return links
            .filter(a => a.href && a.href.includes('mysteel.com'))
            .map(a => ({
                text: a.textContent.trim().substring(0, 50),
                href: a.href
            }))
            .filter(a => a.text && a.href);
    }''')

    print("\n页面链接:")
    for link in page_links[:20]:
        print(f"  {link['text'][:30]} → {link['href']}")

    # 方法3: 检查URL中的日期规律
    print("\n[正在分析] URL日期规律...")
    print("当前URL格式: https://jiancai.mysteel.com/m/YYMMDDXX/HASH.html")
    print("其中 YYMMDD = 260609 表示 2026-06-09")

    print("\n请手动操作:")
    print("1. 在浏览器中查找日期选择器")
    print("2. 选择不同的日期，观察URL变化")
    print("3. 记录不同日期对应的URL格式")

    print("\n等待30秒供您操作...")
    await asyncio.sleep(30)

    # 获取当前页面URL（可能已经变化）
    final_url = page.url
    print(f"\n最终URL: {final_url}")

    await browser.close()
    await playwright.stop()

    return final_url


async def test_url_patterns():
    """测试不同的URL模式"""
    print("\n" + "=" * 60)
    print("测试URL模式")
    print("=" * 60)

    cookies = []
    if COOKIE_FILE.exists():
        with open(COOKIE_FILE, 'r', encoding='utf-8') as f:
            cookies = json.load(f)

    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=False)
    context = await browser.new_context(viewport={'width': 1920, 'height': 1080}, locale='zh-CN')

    if cookies:
        await context.add_cookies(cookies)

    page = await context.new_page()

    # 测试不同日期的URL
    test_dates = [
        '2026-06-08',
        '2026-06-07',
        '2026-06-06',
        '2026-06-05',
        '2026-06-04',
    ]

    print("\n测试URL格式假设:")
    print("假设1: YYMMDDXX固定，只改变日期部分")

    for date in test_dates:
        y, m, d = date.split('-')
        date_code = f"{y[2:]}{m}{d}"

        # 尝试不同的URL模式
        test_urls = [
            f"https://jiancai.mysteel.com/m/{date_code}/E3B5B7AB6E55FC6D.html",
            f"https://jiancai.mysteel.com/m/26060916/E3B5B7AB6E55FC6D.html",  # 固定URL
            f"https://jiancai.mysteel.com/m/{date_code}16/E3B5B7AB6E55FC6D.html",
            f"https://jiancai.mysteel.com/m/{date_code}/index.html",
        ]

        print(f"\n测试日期: {date}")
        for i, url in enumerate(test_urls[:2], 1):  # 只测试前2个
            print(f"  [{i}] {url}")
            try:
                await page.goto(url, wait_until='domcontentloaded', timeout=15000)
                await asyncio.sleep(2)

                # 检查页面内容
                has_data = await page.evaluate('''() => {
                    const tables = document.querySelectorAll('table');
                    if (tables.length > 0) {
                        const rows = tables[0].querySelectorAll('tr');
                        return rows.length > 3;
                    }
                    return false;
                }''')

                if has_data:
                    print(f"      ✓ 有数据!")
                    break
                else:
                    print(f"      ✗ 无数据")
            except Exception as e:
                print(f"      ✗ 错误: {str(e)[:50]}")

    await browser.close()
    await playwright.stop()


async def main():
    result = await explore_url_format()
    await test_url_patterns()


if __name__ == '__main__':
    asyncio.run(main())
