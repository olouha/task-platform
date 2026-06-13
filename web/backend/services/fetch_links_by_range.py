"""
根据日期范围提取烟台历史链接
"""
import asyncio
import json
import re
from pathlib import Path
from playwright.async_api import async_playwright

DATA_DIR = Path(__file__).parent / 'data'
COOKIE_FILE = DATA_DIR / 'mysteel_cookies.json'


def parse_date_from_url(url):
    match = re.search(r'/(\d{2})(\d{2})(\d{2})\d{2}/', url)
    if match:
        return f"20{match.group(1)}-{m.group(2)}-{m.group(3)}"
    return None


async def fetch_links_for_range(start_date, end_date):
    """获取日期范围内的链接"""
    print(f"=" * 60)
    print(f"获取 {start_date} 至 {end_date} 的链接")
    print(f"=" * 60)

    # 加载Cookie
    with open(COOKIE_FILE, 'r', encoding='utf-8') as f:
        cookies = json.load(f)

    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=False)
    context = await browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        locale='zh-CN'
    )
    await context.add_cookies(cookies)

    page = await context.new_page()

    # 访问带日期参数的页面
    url = f'https://jiancai.mysteel.com/market/pa228aa010101a0a01010205aaaa1.html?startTime={start_date}&endTime={end_date}'
    print(f"访问: {url}")

    await page.goto(url, wait_until='domcontentloaded', timeout=60000)
    await asyncio.sleep(5)

    # 截图
    await page.screenshot(path=f'range_{start_date}_{end_date}.png')
    print(f"截图: range_{start_date}_{end_date}.png")

    # 提取链接
    links = await page.evaluate('''() => {
        const results = [];
        const allLinks = document.querySelectorAll('a[href]');
        allLinks.forEach(link => {
            const href = link.href;
            const text = link.textContent.trim();
            if (href.includes('/m/') && href.includes('jiancai.mysteel.com') && text.includes('烟台')) {
                results.push({url: href, text: text});
            }
        });
        return results;
    }''')

    print(f"找到 {len(links)} 个链接")

    # 解析日期
    dated_links = []
    for link in links:
        url = link['url']
        match = re.search(r'/(\d{2})(\d{2})(\d{2})\d{2}/', url)
        if match:
            date = f"20{match.group(1)}-{match.group(2)}-{match.group(3)}"
            dated_links.append({'url': url, 'date': date, 'text': link['text']})

    # 去重排序
    seen = set()
    unique = []
    for link in dated_links:
        if link['url'] not in seen:
            seen.add(link['url'])
            unique.append(link)

    unique.sort(key=lambda x: x['date'])

    print(f"去重后: {len(unique)} 个链接")
    if unique:
        print(f"日期范围: {unique[0]['date']} ~ {unique[-1]['date']}")

        # 保存
        filename = f"links_{start_date}_{end_date}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(unique, f, ensure_ascii=False, indent=2)
        print(f"已保存: {filename}")

        # 显示前10个
        print("\n前10个链接:")
        for link in unique[:10]:
            print(f"  {link['date']}: {link['url']}")

    print("\n按回车关闭...")
    input()

    await browser.close()
    await playwright.stop()


if __name__ == '__main__':
    start = '2024-07-01'
    end = '2024-07-31'
    asyncio.run(fetch_links_for_range(start, end))
