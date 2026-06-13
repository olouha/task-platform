"""
等待用户手动翻页，提取烟台历史链接
用户在浏览器中翻页，脚本提取每页的链接
"""
import asyncio
import json
import sqlite3
import re
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright

# 获取脚本所在目录
SCRIPT_DIR = Path(__file__).parent.absolute()
DATA_DIR = SCRIPT_DIR / 'data'
DATA_DIR.mkdir(exist_ok=True)

COOKIE_FILE = DATA_DIR / 'mysteel_cookies.json'
DB_FILE = DATA_DIR / 'yantai_rebar.db'
LINKS_FILE = DATA_DIR / 'collected_yantai_links.json'


def load_cookies():
    if COOKIE_FILE.exists():
        with open(COOKIE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def parse_date_from_url(url):
    """从URL中解析日期"""
    match = re.search(r'/(\d{2})(\d{2})(\d{2})\d{2}/', url)
    if match:
        year = '20' + match.group(1)
        month = match.group(2)
        day = match.group(3)
        return f"{year}-{month}-{day}"
    return None


async def extract_current_page_links():
    """提取当前页面的烟台链接"""
    print("=" * 80)
    print("提取当前页面的烟台历史链接")
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

    # 访问市场页面
    start_url = 'https://jiancai.mysteel.com/market/pa228aa010101a0a01010205aaaa1.html'
    print(f"\n[访问] {start_url}")
    await page.goto(start_url, wait_until='domcontentloaded', timeout=30000)
    await asyncio.sleep(2)

    all_links = []
    page_num = 1

    print("\n" + "=" * 80)
    print("操作说明:")
    print("1. 在浏览器中手动翻页（点击下一页或输入页码）")
    print("2. 翻页完成后，在命令行按回车键")
    print("3. 脚本会提取当前页面的链接")
    print("4. 输入 'q' 退出")
    print("=" * 80)

    loop = asyncio.get_event_loop()

    while True:
        print(f"\n[页码 {page_num}] 请翻页后按回车，或输入 'q' 退出...")

        user_input = await loop.run_in_executor(None, input, "> ")

        if user_input.lower() == 'q':
            print("\n[退出] 用户取消")
            break

            # 提取当前页面的链接
            print("\n[提取] 当前页面的烟台链接...")

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

                # 解析日期
                dated_links = []
                for link in links:
                    url = link['url']
                    date = parse_date_from_url(url)
                    if date:
                        dated_links.append({
                            'url': url,
                            'date': date,
                            'text': link['text']
                        })

                # 显示当前页的链接
                if dated_links:
                    dated_links.sort(key=lambda x: x['date'])
                    print(f"  日期范围: {dated_links[0]['date']} ~ {dated_links[-1]['date']}")

                    for link in dated_links[:5]:
                        print(f"    {link['date']}: {link['text']}")
                    if len(dated_links) > 5:
                        print(f"    ... 还有 {len(dated_links) - 5} 个")

                all_links.extend(dated_links)
                print(f"  [累计] 共收集 {len(all_links)} 个链接")
            else:
                print(f"  未找到烟台链接")

            page_num += 1

        # 去重
        print("\n[去重] 处理收集的链接...")
        seen = set()
        unique_links = []
        for link in all_links:
            key = link['url']
            if key not in seen:
                seen.add(key)
                unique_links.append(link)

        print(f"  原始: {len(all_links)} 个")
        print(f"  去重: {len(unique_links)} 个")

        # 保存结果
        with open(LINKS_FILE, 'w', encoding='utf-8') as f:
            json.dump(unique_links, f, ensure_ascii=False, indent=2)

        print(f"\n[保存] {LINKS_FILE}")

        # 显示日期范围
        if unique_links:
            unique_links.sort(key=lambda x: x['date'])
            print(f"\n[日期范围]")
            print(f"  最早: {unique_links[0]['date']}")
            print(f"  最晚: {unique_links[-1]['date']}")

            # 按月统计
            month_counts = {}
            for link in unique_links:
                month = link['date'][:7]  # YYYY-MM
                month_counts[month] = month_counts.get(month, 0) + 1

            print(f"\n[按月统计]")
            for month in sorted(month_counts.keys()):
                print(f"  {month}: {month_counts[month]} 天")

        await browser.close()
    await playwright.stop()

    print("\n" + "=" * 80)
    print("链接收集完成")
    print("=" * 80)

    return unique_links


async def fetch_from_collected_links():
    """从收集的链接抓取数据"""
    # 读取链接
    if not LINKS_FILE.exists():
        print(f"[错误] 找不到链接文件: {LINKS_FILE}")
        print("请先运行 extract_current_page_links() 收集链接")
        return

    with open(LINKS_FILE, 'r', encoding='utf-8') as f:
        links = json.load(f)

    if not links:
        print("[错误] 没有找到链接")
        return

    print(f"\n[读取] 找到 {len(links)} 个链接")

    # 检查已有数据
    def get_existing_dates():
        if not Path(DB_FILE).exists():
            return {}

        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        try:
            c.execute('''
                SELECT date, COUNT(*) as count FROM rebar_prices
                GROUP BY date ORDER BY date DESC
            ''')
            return {row[0]: row[1] for row in c.fetchall()}
        except:
            return {}
        finally:
            conn.close()

    existing_dates = get_existing_dates()
    print(f"[扫描] 数据库已有 {len(existing_dates)} 个日期")

    # 确定需要抓取的链接
    links_to_fetch = []
    for link in links:
        date = link['date']
        count = existing_dates.get(date, 0)
        if count < 111:
            links_to_fetch.append(link)

    print(f"[目标] 需要抓取 {len(links_to_fetch)} 个日期")

    if not links_to_fetch:
        print("\n所有日期数据充足！")
        return

    # 启动浏览器
    cookies = load_cookies()

    print("\n[启动] 浏览器...")
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=True)
    context = await browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        locale='zh-CN'
    )

    if cookies:
        await context.add_cookies(cookies)

    page = await context.new_page()

    # 批量抓取
    print("\n[开始] 批量抓取...")
    print("=" * 80)

    success_count = 0
    fail_count = 0
    total_inserted = 0

    async def save_to_db(date_str, prices, fetch_time='10:00:00'):
        if not prices:
            return 0

        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()

        inserted = 0
        for price in prices:
            try:
                c.execute('''
                    INSERT OR IGNORE INTO rebar_prices
                    (date, material_name, spec, material_type, brand, price, region, fetch_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    date_str,
                    price.get('material_name', ''),
                    price.get('spec', ''),
                    price.get('material_type', ''),
                    price.get('brand', ''),
                    price.get('price', 0),
                    '山东烟台',
                    fetch_time
                ))
                if c.rowcount > 0:
                    inserted += 1
            except:
                pass

        conn.commit()
        conn.close()
        return inserted

    async def extract_prices_from_page(page):
        try:
            await asyncio.sleep(2)

            data = await page.evaluate('''() => {
                const tables = document.querySelectorAll('table');
                const results = [];

                tables.forEach(table => {
                    const rows = table.querySelectorAll('tr');
                    rows.forEach(row => {
                        const cells = row.querySelectorAll('td');
                        if (cells.length >= 5) {
                            const rowData = Array.from(cells).map(c => c.textContent.trim());
                            results.push(rowData);
                        }
                    });
                });

                return results;
            }''')

            # 解析价格数据
            prices = []
            for row in data:
                if len(row) >= 5:
                    material_name = str(row[0]).strip()
                    spec = str(row[1]).strip()
                    material_type = str(row[2]).strip()
                    brand = str(row[3]).strip()
                    price_str = str(row[4]).strip()

                    valid_names = ['高线', '螺纹钢', '盘螺', '圆钢']

                    if material_name in valid_names and spec.startswith('Φ'):
                        price_match = re.search(r'\d{4}', price_str)
                        if price_match:
                            try:
                                price = int(price_match.group())
                                if 3000 < price < 10000:
                                    prices.append({
                                        'material_name': material_name,
                                        'spec': spec,
                                        'material_type': material_type,
                                        'brand': brand,
                                        'price': price
                                    })
                            except:
                                pass

            return prices

        except Exception as e:
            return []

    def parse_time_from_url(url):
        match = re.search(r'/(\d{8})/', url)
        if match:
            hour = match.group(1)[6:8]
            return f"{hour}:00:00"
        return "10:00:00"

    for i, link in enumerate(links_to_fetch, 1):
        url = link['url']
        date = link['date']
        fetch_time = parse_time_from_url(url)

        print(f"\n[{i}/{len(links_to_fetch)}] {date}")
        print(f"  URL: {url}")

        try:
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(2)

            # 提取价格
            prices = await extract_prices_from_page(page)

            if prices:
                # 保存到数据库
                inserted = await save_to_db(date, prices, fetch_time)
                print(f"  OK 提取 {len(prices)} 条，新增 {inserted} 条")
                success_count += 1
                total_inserted += inserted
            else:
                print(f"  X 未提取到数据")
                fail_count += 1

        except Exception as e:
            print(f"  X 错误: {e}")
            fail_count += 1

        # 避免请求过快
        if i < len(links_to_fetch):
            await asyncio.sleep(1.5)

    # 汇总
    print("\n" + "=" * 80)
    print("抓取完成!")
    print(f"  成功: {success_count}/{len(links_to_fetch)}")
    print(f"  失败: {fail_count}/{len(links_to_fetch)}")
    print(f"  总计: {total_inserted} 条新数据")
    print(f"  数据库: {DB_FILE}")
    print("=" * 80)

    await browser.close()
    await playwright.stop()


async def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("烟台历史数据收集工具")
    print("=" * 80)
    print("\n请选择操作:")
    print("  1. 收集链接 (需要手动翻页)")
    print("  2. 从已有链接抓取数据")
    print("  3. 全部执行 (先收集链接再抓取)")

    choice = input("\n请输入选项 (1/2/3): ").strip()

    if choice == '1':
        await extract_current_page_links()
    elif choice == '2':
        await fetch_from_collected_links()
    elif choice == '3':
        await extract_current_page_links()
        print("\n" + "=" * 80)
        print("链接收集完成，开始抓取数据...")
        print("=" * 80)
        await fetch_from_collected_links()
    else:
        print("[错误] 无效选项")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n[中断] 用户取消操作")
