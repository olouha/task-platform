"""
简化版：自动翻页收集烟台历史链接
"""
import asyncio
import json
import re
from pathlib import Path
from playwright.async_api import async_playwright

SCRIPT_DIR = Path(__file__).parent.absolute()
DATA_DIR = SCRIPT_DIR / 'data'
DATA_DIR.mkdir(exist_ok=True)

COOKIE_FILE = DATA_DIR / 'mysteel_cookies.json'
LINKS_FILE = DATA_DIR / 'collected_yantai_links.json'


def load_cookies():
    if COOKIE_FILE.exists():
        with open(COOKIE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def parse_date_from_url(url):
    match = re.search(r'/(\d{2})(\d{2})(\d{2})\d{2}/', url)
    if match:
        return f"20{match.group(1)}-{match.group(2)}-{match.group(3)}"
    return None


async def auto_collect_links(max_pages=50):
    """自动翻页收集链接"""
    print("=" * 80)
    print("自动收集烟台历史链接")
    print("=" * 80)

    cookies = load_cookies()

    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=False)
    context = await browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        locale='zh-CN'
    )

    if cookies:
        await context.add_cookies(cookies)

    page = await context.new_page()

    all_links = []
    seen_urls = set()

    # 尝试访问不同的页码
    for page_num in range(1, max_pages + 1):
        url = f'https://jiancai.mysteel.com/market/pa228aa010101a0a01010205aaaa{page_num}.html'

        print(f"\n[{page_num}/{max_pages}] 访问: {url}")

        try:
            await page.goto(url, wait_until='domcontentloaded', timeout=45000)
            await asyncio.sleep(4)  # 增加等待时间

            # 提取烟台链接
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

            if links:
                # 处理新链接
                new_links = []
                for link in links:
                    url = link['url']
                    if url not in seen_urls:
                        seen_urls.add(url)
                        date = parse_date_from_url(url)
                        if date:
                            new_links.append({
                                'url': url,
                                'date': date,
                                'text': link['text']
                            })

                if new_links:
                    new_links.sort(key=lambda x: x['date'])
                    print(f"  新增: {len(new_links)} 个")
                    print(f"  日期范围: {new_links[0]['date']} ~ {new_links[-1]['date']}")
                    all_links.extend(new_links)
                else:
                    print(f"  无新链接")
            else:
                print(f"  未找到烟台链接")

        except Exception as e:
            print(f"  错误: {e}")

    # 保存结果
    print(f"\n[汇总] 共收集 {len(all_links)} 个链接")

    if all_links:
        all_links.sort(key=lambda x: x['date'])
        print(f"  最早: {all_links[0]['date']}")
        print(f"  最晚: {all_links[-1]['date']}")

        with open(LINKS_FILE, 'w', encoding='utf-8') as f:
            json.dump(all_links, f, ensure_ascii=False, indent=2)
        print(f"  已保存: {LINKS_FILE}")

    await browser.close()
    await playwright.stop()

    return all_links


if __name__ == '__main__':
    try:
        asyncio.run(auto_collect_links(max_pages=100))
    except KeyboardInterrupt:
        print("\n\n[中断]")
