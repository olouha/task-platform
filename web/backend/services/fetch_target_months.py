#!/usr/bin/env python3
"""
Mysteel 烟台钢筋价格抓取脚本 - 仅抓取指定月份
"""
import asyncio
import json
import re
import sqlite3
from pathlib import Path
from playwright.async_api import async_playwright

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / 'data'
COOKIE_FILE = DATA_DIR / 'mysteel_cookies.json'
DB_FILE = DATA_DIR / 'yantai_rebar.db'

async def fetch_links(url, max_retries=3):
    """获取页面中的烟台价格链接"""
    for attempt in range(max_retries):
        try:
            with open(COOKIE_FILE, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
            if not cookies:
                print('错误: Cookie文件为空，请重新登录')
                return []

            pw = await async_playwright().start()
            browser = await pw.chromium.launch(headless=False)
            context = await browser.new_context()
            await context.add_cookies(cookies)
            page = await context.new_page()

            # 先访问主页激活会话
            await page.goto('https://www.mysteel.com/', wait_until='domcontentloaded', timeout=60000)
            await asyncio.sleep(3)

            # 访问目标页面
            await page.goto(url, wait_until='domcontentloaded', timeout=60000)
            await asyncio.sleep(10)

            links = await page.evaluate('''() => {
                const results = [];
                document.querySelectorAll('a[href]').forEach(link => {
                    const href = link.href;
                    const text = link.textContent.trim();
                    if (href.includes('/m/') && href.includes('jiancai.mysteel.com') && text.includes('烟台')) {
                        results.push({url: href, text: text});
                    }
                });
                return results;
            }''')

            dated = []
            for link in links:
                match = re.search(r'/(\d{2})(\d{2})(\d{2})(\d{2})/', link['url'])
                if match:
                    date = f"20{match.group(1)}-{match.group(2)}-{match.group(3)}"
                    hour = match.group(4)
                    dated.append({'url': link['url'], 'date': date, 'hour': hour})

            # 按日期+小时分组，保留每天所有时间点的链接
            seen = {}
            for link in dated:
                key = f"{link['date']}_{link['hour']}"
                seen[key] = link
            unique = list(seen.values())
            unique.sort(key=lambda x: (x['date'], x['hour']))

            await browser.close()
            await pw.stop()
            return unique

        except Exception as e:
            print(f'获取链接失败 (尝试 {attempt+1}/{max_retries}): {e}')
            try:
                await browser.close()
                await pw.stop()
            except:
                pass
            if attempt < max_retries - 1:
                await asyncio.sleep(5)
    return []


def save_prices(date_str, rows, fetch_time):
    """保存价格数据到数据库"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    inserted = 0
    for row in rows:
        if len(row) >= 5:
            name = str(row[0]).strip()
            spec = str(row[1]).strip()
            if any(kw in name for kw in ['高线', '螺纹', '盘螺', '圆钢', '线材']) and (spec.startswith('Φ') or 'HPB' in spec or 'HRB' in spec):
                for cell in row[4:]:
                    match = re.search(r'\d{4}', str(cell))
                    if match:
                        price = int(match.group())
                        if 3000 < price < 10000:
                            # 检查是否已存在相同记录
                            c.execute('''SELECT COUNT(*) FROM rebar_prices WHERE date=? AND material_name=? AND spec=? AND price=? AND fetch_time=?''',
                                (date_str, name, spec, price, fetch_time))
                            if c.fetchone()[0] == 0:
                                c.execute('''INSERT INTO rebar_prices (date, material_name, spec, material_type, brand, price, region, fetch_time) VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                                    (date_str, name, spec, '', '', price, '山东烟台', fetch_time))
                                if c.rowcount > 0:
                                    inserted += 1
                            break
    conn.commit()
    conn.close()
    return inserted


async def fetch_one(url, date, fetch_time, max_retries=2):
    """抓取单个日期的价格数据"""
    for attempt in range(max_retries):
        try:
            with open(COOKIE_FILE, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
            if not cookies:
                print('错误: Cookie为空')
                return 0

            pw = await async_playwright().start()
            browser = await pw.chromium.launch(headless=False)
            context = await browser.new_context()
            await context.add_cookies(cookies)
            page = await context.new_page()

            try:
                await page.goto(url, wait_until='domcontentloaded', timeout=45000)
                await asyncio.sleep(5)

                # 检测是否被登出
                if 'passport.mysteel.com' in page.url:
                    print('Cookie已过期')
                    await browser.close()
                    await pw.stop()
                    return -1  # 表示需要重新登录

                rows = await page.evaluate('''() => {
                    const tables = document.querySelectorAll('table');
                    let results = [];
                    tables.forEach(t => {
                        t.querySelectorAll('tr').forEach(row => {
                            let cells = Array.from(row.querySelectorAll('td')).map(c => c.textContent.trim());
                            if (cells.length >= 5) results.push(cells);
                        });
                    });
                    return results;
                }''')
                result = save_prices(date, rows, fetch_time)

            finally:
                await browser.close()
                await pw.stop()

            return result

        except Exception as e:
            print(f'抓取失败 (尝试 {attempt+1}/{max_retries}): {e}')
            try:
                await browser.close()
                await pw.stop()
            except:
                pass
            if attempt < max_retries - 1:
                await asyncio.sleep(3)
    return 0


async def main():
    # 只抓取目标月份
    urls = [
        ('2025年9月', 'https://jiancai.mysteel.com/market/pa228aa010101a0a01010205aaaa1.html?startTime=2025-09-01&endTime=2025-09-30'),
        ('2025年10月', 'https://jiancai.mysteel.com/market/pa228aa010101a0a01010205aaaa1.html?startTime=2025-10-01&endTime=2025-10-31'),
        ('2025年11月', 'https://jiancai.mysteel.com/market/pa228aa010101a0a01010205aaaa1.html?startTime=2025-11-01&endTime=2025-11-30'),
        ('2025年12月', 'https://jiancai.mysteel.com/market/pa228aa010101a0a01010205aaaa1.html?startTime=2025-12-01&endTime=2025-12-31'),
        ('2026年1月', 'https://jiancai.mysteel.com/market/pa228aa010101a0a01010205aaaa1.html?startTime=2026-01-01&endTime=2026-01-31'),
        ('2026年2月', 'https://jiancai.mysteel.com/market/pa228aa010101a0a01010205aaaa1.html?startTime=2026-02-01&endTime=2026-02-28'),
        ('2026年3月', 'https://jiancai.mysteel.com/market/pa228aa010101a0a01010205aaaa1.html?startTime=2026-03-01&endTime=2026-03-31'),
    ]

    total_success = total_new = 0

    for month, url in urls:
        print(f'\n=== 抓取{month} ===')
        links = await fetch_links(url)
        print(f'找到 {len(links)} 个链接')

        if not links:
            print('获取链接失败，可能需要重新登录')
            continue

        for i, link in enumerate(links):
            ft = f"{link['hour']}:00:00"
            print(f'[{i+1}/{len(links)}] {link["date"]} {link["hour"]}:00...', end=' ', flush=True)

            result = await fetch_one(link['url'], link['date'], ft)

            if result == -1:
                print('Cookie过期，需要重新登录')
                print(f'\n=== 已完成 ===')
                print(f'成功: {total_success} 个日期, 新增: {total_new} 条')
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                c.execute('SELECT COUNT(*) FROM rebar_prices')
                print(f'数据库: {c.fetchone()[0]}条')
                conn.close()
                return

            if result > 0:
                print(f'+{result}条')
                total_success += 1
                total_new += result
            else:
                print('已有')
            await asyncio.sleep(2)

    print(f'\n=== 总计 ===')
    print(f'成功: {total_success} 个日期, 新增: {total_new} 条')

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM rebar_prices')
    print(f'数据库: {c.fetchone()[0]}条')
    conn.close()


if __name__ == '__main__':
    asyncio.run(main())