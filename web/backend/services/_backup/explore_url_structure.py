"""
探索我的钢铁网历史价格URL结构
访问价格页面，提取所有历史日期链接，分析URL模式
"""
import asyncio
import json
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright

DATA_DIR = Path('services/data')
COOKIE_FILE = DATA_DIR / 'mysteel_cookies.json'


def load_cookies():
    """加载Cookie"""
    if COOKIE_FILE.exists():
        with open(COOKIE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


async def explore_url_structure():
    """探索URL结构"""
    print("=" * 60)
    print("探索我的钢铁网历史价格URL结构")
    print("=" * 60)

    # 加载Cookie
    cookies = load_cookies()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # 显示浏览器便于观察
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            locale='zh-CN'
        )

        if cookies:
            await context.add_cookies(cookies)
            print(f"\n[Cookie] 已加载 {len(cookies)} 条")

        page = await context.new_page()

        # 访问基础价格页面
        base_url = 'https://jiancai.mysteel.com/m/26051410/25B3355C6617BD3C.html'
        print(f"\n[1] 访问基础页面: {base_url}")

        await page.goto(base_url, wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(3)

        print(f"    当前URL: {page.url}")

        # 截图
        await page.screenshot(path='explore_page.png', full_page=True)
        print(f"    已截图: explore_page.png")

        # 提取所有可能的日期相关元素
        print("\n[2] 分析页面元素...")

        analysis = await page.evaluate('''() => {
            const result = {
                dateSelectors: [],
                dateLinks: [],
                calendarElements: [],
                allMysteelLinks: []
            };

            // 查找日期选择器
            const dateInputs = document.querySelectorAll('input[type="date"], input[placeholder*="日期"], input[placeholder*="时间"]');
            dateInputs.forEach(el => {
                result.dateSelectors.push({
                    tag: el.tagName,
                    type: el.type,
                    placeholder: el.placeholder,
                    id: el.id,
                    name: el.name
                });
            });

            // 查找所有我的钢铁网链接
            const allLinks = document.querySelectorAll('a[href*="mysteel.com"]');
            allLinks.forEach(link => {
                const href = link.href;
                const text = link.textContent.trim();

                // 检查是否是价格数据链接
                if (href.includes('/m/') && href.includes('.html')) {
                    const match = href.match(/\/(\d{8})\/([A-F0-9]+)\.html/);
                    if (match) {
                        result.allMysteelLinks.push({
                            url: href,
                            code: match[1],
                            hash: match[2],
                            text: text.substring(0, 50)
                        });
                    }
                }
            });

            // 查找日历/日期导航元素
            const calendarEls = document.querySelectorAll('[class*="calendar"], [class*="date"], [id*="calendar"], [id*="date"]');
            calendarEls.forEach(el => {
                result.calendarElements.push({
                    tag: el.tagName,
                    class: el.className,
                    id: el.id,
                    text: el.textContent.substring(0, 50)
                });
            });

            return result;
        }''')

        print(f"\n    日期选择器: {len(analysis['dateSelectors'])} 个")
        for ds in analysis['dateSelectors']:
            print(f"      - {ds}")

        print(f"\n    我的钢铁网链接: {len(analysis['allMysteelLinks'])} 个")
        for link in analysis['allMysteelLinks'][:20]:  # 显示前20个
            print(f"      - {link['code']} / {link['hash']} | {link['text']}")

        # 保存分析结果
        with open('url_structure_analysis.json', 'w', encoding='utf-8') as f:
            json.dump(analysis, f, ensure_ascii=False, indent=2)
        print(f"\n    分析结果已保存: url_structure_analysis.json")

        # 尝试查找并点击日期选择器或历史按钮
        print("\n[3] 查找日期导航...")

        # 尝试查找可能的日期导航按钮
        navigation_attempts = [
            'button:has-text("历史")',
            'a:has-text("历史")',
            'button:has-text("日期")',
            'a:has-text("日期")',
            'button[title*="历史"]',
            'a[title*="历史"]',
            '.date-selector',
            '.calendar-btn',
            '#dateSelector'
        ]

        for selector in navigation_attempts:
            try:
                elements = await page.query_selector_all(selector)
                if elements:
                    print(f"    找到元素 ({selector}): {len(elements)} 个")
            except:
                pass

        # 等待用户观察
        print("\n[4] 请观察浏览器页面，手动探索日期导航功能")
        print("    按回车键继续...")

        input()  # 等待用户输入

        # 再次提取当前页面的所有链接
        print("\n[5] 再次提取页面链接...")

        final_links = await page.evaluate('''() => {
            const links = [];
            const allLinks = document.querySelectorAll('a[href*="mysteel.com/m/"]');

            allLinks.forEach(link => {
                const href = link.href;
                const match = href.match(/\/(\d{8})\/([A-F0-9]+)\.html/);
                if (match) {
                    links.push({
                        url: href,
                        code: match[1],
                        hash: match[2],
                        text: link.textContent.trim()
                    });
                }
            });

            // 去重
            const unique = [];
            const seen = new Set();
            links.forEach(l => {
                if (!seen.has(l.url)) {
                    seen.add(l.url);
                    unique.push(l);
                }
            });

            return unique;
        }''')

        print(f"\n    找到 {len(final_links)} 个唯一链接")

        # 分析URL模式
        print("\n[6] URL模式分析...")

        if final_links:
            # 按日期代码分组
            from collections import defaultdict
            date_groups = defaultdict(list)

            for link in final_links:
                code = link['code']
                date_part = code[:6]  # YYMMDD
                hour_part = code[6:8] if len(code) >= 8 else ''
                date_groups[date_part].append({
                    'hour': hour_part,
                    'hash': link['hash'],
                    'url': link['url']
                })

            print(f"\n    按日期分组 (共 {len(date_groups)} 个不同日期):")

            for date_part in sorted(date_groups.keys())[:10]:  # 显示前10个
                group = date_groups[date_part]
                print(f"\n      日期代码 {date_part}:")
                for item in group:
                    print(f"        - {item['hour']}时 | {item['hash']}")

            # 保存分组结果
            with open('url_date_groups.json', 'w', encoding='utf-8') as f:
                json.dump(dict(date_groups), f, ensure_ascii=False, indent=2)
            print(f"\n    分组结果已保存: url_date_groups.json")

            # 分析Hash模式
            print("\n[7] Hash模式分析...")

            all_hashes = [link['hash'] for link in final_links]
            unique_hashes = list(set(all_hashes))

            print(f"    总链接数: {len(final_links)}")
            print(f"    唯一Hash数: {len(unique_hashes)}")

            if len(unique_hashes) < len(final_links):
                print(f"    ⚠️ Hash存在复用，可能不是随机生成的")

            # 检查Hash是否与日期相关
            print(f"\n    示例Hash:")
            for h in unique_hashes[:10]:
                print(f"      - {h}")

        await browser.close()

    print("\n" + "=" * 60)
    print("探索完成!")
    print("  - explore_page.png: 页面截图")
    print("  - url_structure_analysis.json: 页面元素分析")
    print("  - url_date_groups.json: 日期URL分组")
    print("=" * 60)


if __name__ == '__main__':
    try:
        asyncio.run(explore_url_structure())
    except KeyboardInterrupt:
        print("\n\n[中断] 用户取消操作")
