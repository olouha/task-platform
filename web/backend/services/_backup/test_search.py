"""
通过搜索功能查找烟台钢筋价格
"""
import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, '.')

from playwright.async_api import async_playwright
import sqlite3

DATA_DIR = Path('web/backend/services/data')
DB_FILE = DATA_DIR / 'yantai_rebar.db'
COOKIE_FILE = DATA_DIR / 'mysteel_cookies_new.json'
USERNAME = 'M6616592358'
PASSWORD = 'panhui199261'


def save_to_database(date: str, fetch_time: str, prices: list) -> int:
    """保存到数据库"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    inserted = 0
    for p in prices:
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO rebar_prices
                (date, fetch_time, material_name, spec, material_type, brand, price, region)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (date, fetch_time, p['material_name'], p['spec'],
                  p.get('material_type', ''), p.get('brand', ''),
                  p['price'], '山东烟台'))
            if cursor.rowcount > 0:
                inserted += 1
        except:
            pass
    conn.commit()
    conn.close()
    return inserted


async def test_search():
    """测试搜索功能"""
    print("=" * 60)
    print("测试搜索功能")
    print("=" * 60)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 3000},
            locale='zh-CN'
        )
        page = await context.new_page()

        # 登录
        print("\n1. 登录...")
        await page.goto('https://passport.mysteel.com/', wait_until='networkidle', timeout=60000)
        await page.wait_for_timeout(3000)

        try:
            await page.click('.form-tab-account', timeout=5000)
        except:
            pass

        await page.evaluate(f'''() => {{
            const inputs = document.querySelectorAll('input');
            for (const inp of inputs) {{
                const ph = inp.placeholder || '';
                if (ph.includes('用户名')) inp.value = '{USERNAME}';
                if (ph.includes('密码') && inp.type === 'password') inp.value = '{PASSWORD}';
            }}
        }}''')
        await page.wait_for_timeout(500)

        try:
            checkbox = await page.query_selector('input[type="checkbox"]')
            if checkbox and not await checkbox.is_checked():
                checkbox.click()
        except:
            pass

        try:
            await page.click('.form-button-login', timeout=5000)
        except:
            pass

        print("等待登录...")
        await page.wait_for_timeout(10000)

        # 访问搜索页面
        print("\n2. 测试搜索...")
        search_url = "https://search.mysteel.com/?keyword=%E7%83%AD%E8%BD%AC%E5%B8%A6%E9%92%A2%E6%A0%BC&sitetype=jiancai"
        await page.goto(search_url, wait_until='domcontentloaded', timeout=60000)
        await page.wait_for_timeout(5000)

        text = await page.evaluate('() => document.body.innerText')
        print(f"搜索页文本长度: {len(text)}")

        # 查找搜索结果
        search_results = await page.evaluate('''() => {{
            const results = [];
            document.querySelectorAll('.result-item, .news-item, .list-item, li, div').forEach(item => {{
                const text = item.textContent.trim();
                if (text && text.length > 50 && text.length < 500) {{
                    results.push(text.substring(0, 200));
                }}
            }});
            return results.slice(0, 20);
        }}''')

        print("\n搜索结果示例:")
        for r in search_results[:5]:
            print(f"  {r}...")

        # 查找搜索框
        print("\n尝试在首页搜索...")
        await page.goto('https://jiancai.mysteel.com/', wait_until='domcontentloaded', timeout=60000)
        await page.wait_for_timeout(3000)

        # 查找搜索框
        search_input = await page.query_selector('input[type="text"], input[name*="search"], input[name*="keyword"]')
        if search_input:
            print("找到搜索框")
            await search_input.fill('烟台钢筋')
            await page.wait_for_timeout(1000)

            # 尝试提交
            submit_btn = await page.query_selector('button[type="submit"], .search-btn, input[type="submit"]')
            if submit_btn:
                await submit_btn.click()
                await page.wait_for_timeout(3000)
                text = await page.evaluate('() => document.body.innerText')
                print(f"搜索后文本长度: {len(text)}")
        else:
            print("未找到搜索框")

        await browser.close()


if __name__ == '__main__':
    asyncio.run(test_search())