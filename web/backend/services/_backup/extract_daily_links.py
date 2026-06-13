"""
从烟台价格页面提取历史单日链接
访问当前烟台价格页面，查找历史日期导航
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


async def extract_daily_links():
    """提取单日历史链接"""
    print("=" * 60)
    print("提取烟台单日历史链接")
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

        # 访问烟台价格页面
        url = 'https://jiancai.mysteel.com/m/26051410/25B3355C6617BD3C.html'
        print(f"\n[访问] {url}")
        await page.goto(url, wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(3)

        # 深度分析页面，查找所有可能的日期链接
        print("\n[分析] 查找历史日期链接...")

        analysis = await page.evaluate('''() => {
            const results = {
                dailyLinks: [],
                weeklyLinks: [],
                monthlyLinks: [],
                allMysteelLinks: []
            };

            // 查找所有我的钢铁网链接
            const allLinks = document.querySelectorAll('a[href*="mysteel.com"]');

            allLinks.forEach(link => {
                const href = link.href;
                const text = link.textContent.trim();

                // 匹配 /m/ 或 /p/ 类型的链接
                const matchM = href.match(/\\/m\\/(\\d{8})\\/([A-F0-9]+)\\.html/);
                const matchP = href.match(/\\/p\\/(\\d{8})\\/([A-F0-9]+)\\.html/);

                if (matchM) {
                    const code = matchM[1];
                    const hour = code.substring(6, 8);

                    // 分类
                    if (hour === '01') {
                        if (text.includes('周') || text.includes('星期')) {
                            results.weeklyLinks.push({ url: href, code: code, text: text });
                        } else if (text.includes('月')) {
                            results.monthlyLinks.push({ url: href, code: code, text: text });
                        }
                    } else {
                        // 其他时间可能是单日数据
                        results.dailyLinks.push({ url: href, code: code, text: text });
                    }
                }

                if (matchP) {
                    results.allMysteelLinks.push({ url: href, code: matchP[1], text: text });
                }
            });

            // 查找日期选择器或分页
            const pagination = [];
            const pageLinks = document.querySelectorAll('a[href]');
            pageLinks.forEach(link => {
                const text = link.textContent.trim();
                const href = link.href;

                if (/上一页|下一页|\\d+/.test(text) && href.includes('mysteel.com')) {
                    pagination.push({ url: href, text: text });
                }
            });

            return {
                ...results,
                pagination: pagination
            };
        }''')

        print(f"\n[单日链接] 找到 {len(analysis['dailyLinks'])} 个")
        for link in analysis['dailyLinks'][:10]:
            print(f"  - {link['code']}: {link['url']}")
            print(f"    文本: {link['text']}")

        print(f"\n[周报链接] 找到 {len(analysis['weeklyLinks'])} 个")
        for link in analysis['weeklyLinks']:
            print(f"  - {link['code']}: {link['text']}")

        print(f"\n[月报链接] 找到 {len(analysis['monthlyLinks'])} 个")
        for link in analysis['monthlyLinks']:
            print(f"  - {link['code']}: {link['text']}")

        print(f"\n[分页链接] 找到 {len(analysis['pagination'])} 个")
        for link in analysis['pagination'][:10]:
            print(f"  - {link['text']}: {link['url']}")

        # 保存结果
        with open('daily_links_analysis.json', 'w', encoding='utf-8') as f:
            json.dump(analysis, f, ensure_ascii=False, indent=2)
        print(f"\n[保存] daily_links_analysis.json")

        # 尝试点击"下一页"看是否有更多数据
        print(f"\n[测试] 尝试分页导航...")
        try:
            # 查找可能的历史导航
            nav_selectors = [
                'a:has-text("历史")',
                'a:has-text("上一日")',
                'a:has-text("次日")',
                'a:has-text("前一日")',
                'select[name="date"]',
                'input[placeholder*="日期"]'
            ]

            for selector in nav_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        print(f"  找到: {selector}")
                except:
                    pass
        except Exception as e:
            print(f"  错误: {e}")

        # 截图
        await page.screenshot(path='yantai_page_analysis.png', full_page=True)
        print(f"\n[截图] yantai_page_analysis.png")

        await browser.close()

    print("\n" + "=" * 60)
    print("分析完成")
    print("=" * 60)


if __name__ == '__main__':
    try:
        asyncio.run(extract_daily_links())
    except KeyboardInterrupt:
        print("\n\n[中断]")
