"""
分析市场页面URL结构
尝试通过修改参数获取不同时间范围的数据
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright
import re

DATA_DIR = Path('services/data')
COOKIE_FILE = DATA_DIR / 'mysteel_cookies.json'


def load_cookies():
    if COOKIE_FILE.exists():
        with open(COOKIE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


async def analyze_market_url_structure():
    """分析市场URL结构"""
    print("=" * 80)
    print("分析市场页面URL结构")
    print("=" * 80)

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

        # 原始URL
        base_url = 'https://jiancai.mysteel.com/market/pa228aa010101a0a01010205aaaa1.html'

        print(f"\n[分析] 原始URL: {base_url}")

        # 尝试不同的页码参数
        test_urls = [
            'https://jiancai.mysteel.com/market/pa228aa010101a0a01010205aaaa2.html',  # 页码2
            'https://jiancai.mysteel.com/market/pa228aa010101a0a01010205aaaa3.html',  # 页码3
            'https://jiancai.mysteel.com/market/pa228aa010101a0a01010205aaaa4.html',  # 页码4
            'https://jiancai.mysteel.com/market/pa228aa010101a0a01010205aaaa5.html',  # 页码5
            'https://jiancai.mysteel.com/market/pa228aa010101a0a01010205aaaa10.html', # 页码10
        ]

        all_yantai_links = []

        for i, test_url in enumerate(test_urls, 1):
            print(f"\n[{i}/{len(test_urls)}] 测试: {test_url}")

            try:
                await page.goto(test_url, wait_until='domcontentloaded', timeout=30000)
                await asyncio.sleep(2)

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
                    print(f"  找到 {len(links)} 个烟台链接")
                    all_yantai_links.extend(links)
                else:
                    print(f"  未找到烟台链接")

                # 截图
                await page.screenshot(path=f'market_page_{i}.png')
                print(f"  已截图: market_page_{i}.png")

                await asyncio.sleep(1)

            except Exception as e:
                print(f"  错误: {e}")

        print(f"\n[汇总] 共找到 {len(all_yantai_links)} 个烟台链接")

        # 去重
        seen = set()
        unique_links = []
        for link in all_yantai_links:
            if link['url'] not in seen:
                seen.add(link['url'])
                unique_links.append(link)

        print(f"去重后: {len(unique_links)} 个")

        # 保存结果
        with open('market_yantai_links.json', 'w', encoding='utf-8') as f:
            json.dump(unique_links, f, ensure_ascii=False, indent=2)

        # 解析日期
        dated_links = []
        for link in unique_links:
            url = link['url']
            match = re.search(r'/(\d{2})(\d{2})(\d{2})\d{2}/', url)
            if match:
                date = f"20{match.group(1)}-{match.group(2)}-{match.group(3)}"
                dated_links.append({
                    'url': url,
                    'date': date,
                    'text': link['text']
                })

        # 按日期排序
        dated_links.sort(key=lambda x: x['date'])

        print(f"\n[日期范围] ")
        if dated_links:
            print(f"  最早: {dated_links[0]['date']}")
            print(f"  最晚: {dated_links[-1]['date']}")
            print(f"\n前10个:")
            for link in dated_links[:10]:
                print(f"  {link['date']}: {link['text']}")
            print(f"\n后10个:")
            for link in dated_links[-10:]:
                print(f"  {link['date']}: {link['text']}")

        await browser.close()

    print("\n" + "=" * 80)
    print("分析完成")
    print("=" * 80)


if __name__ == '__main__':
    try:
        asyncio.run(analyze_market_url_structure())
    except KeyboardInterrupt:
        print("\n\n[中断]")
