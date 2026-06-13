"""
从已登录的浏览器提取烟台历史链接
"""
import asyncio
import json
import re
from pathlib import Path
from playwright.async_api import async_playwright

DATA_DIR = Path(__file__).parent.absolute() / 'data'
DATA_DIR.mkdir(exist_ok=True)
LINKS_FILE = DATA_DIR / 'yantai_links_full.json'


def parse_date_from_url(url):
    match = re.search(r'/(\d{2})(\d{2})(\d{2})\d{2}/', url)
    if match:
        return f"20{match.group(1)}-{match.group(2)}-{match.group(3)}"
    return None


async def fetch_all_links():
    print("=" * 80)
    print("提取烟台市场页面所有历史链接")
    print("=" * 80)

    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=False)

    # 使用已有浏览器上下文（用户已登录）
    context = await browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        locale='zh-CN'
    )

    page = await context.new_page()

    all_links = []
    seen_urls = set()

    # 访问市场页面
    url = 'https://jiancai.mysteel.com/market/pa228aa010101a0a01010205aaaa1.html'
    print(f"\n[访问] {url}")

    await page.goto(url, wait_until='domcontentloaded', timeout=60000)
    await asyncio.sleep(5)

    print("\n[等待] 请在浏览器中手动翻页...")
    print(" 1. 先翻到最前面（最早的日期）")
    print("  2.等待页面加载完成")
    print("  3. 再翻到最后一页（最新的日期）")
    print("  4. 等待页面加载完成")
    print("\n完成后按回车继续...")

    input()

    # 提取所有链接
    print("\n[提取] 当前页面链接...")

    links = await page.evaluate('''() => {
        const results = [];
        const allLinks = document.querySelectorAll('a[href]');

        allLinks.forEach(link => {
            const href = link.href;
            const text = link.textContent.trim();

            if (text.includes('烟台') && href.includes('/m/') && href.includes('jiancai.mysteel.com')) {
                results.push({
                    url: href,
                    text: text
                });
            }
        });

        return results;
    }''')

    print(f"  找到 {len(links)} 个烟台链接")

    # 处理链接
    for link in links:
        url = link['url']
        if url not in seen_urls:
            seen_urls.add(url)
            date = parse_date_from_url(url)
            if date:
                all_links.append({
                    'url': url,
                    'date': date,
                    'text': link['text']
                })

    # 去重排序
    all_links.sort(key=lambda x: x['date'])

    print(f"\n[汇总] 共 {len(all_links)} 个唯一链接")
    if all_links:
        print(f"  最早: {all_links[0]['date']}")
        print(f"  最晚: {all_links[-1]['date']}")

        # 保存
        with open(LINKS_FILE, 'w', encoding='utf-8') as f:
            json.dump(all_links, f, ensure_ascii=False, indent=2)
        print(f"  已保存: {LINKS_FILE}")

        # 显示前10个和后10个
        print("\n前10个:")
        for link in all_links[:10]:
            print(f"  {link['date']}: {link['text']}")

        print("\n后10个:")
        for link in all_links[-10:]:
            print(f"  {link['date']}: {link['text']}")

    await browser.close()
    await playwright.stop()

    print("\n" + "=" * 80)
    print("链接提取完成")
    print("=" * 80)

    return all_links


if __name__ == '__main__':
    try:
        asyncio.run(fetch_all_links())
    except KeyboardInterrupt:
        print("\n\n[中断]")