"""
从首页找到烟台价格链接并抓取
"""
import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, '.')

from playwright.async_api import async_playwright

DATA_DIR = Path('web/backend/services/data')
COOKIE_FILE = DATA_DIR / 'mysteel_cookies_new.json'
USERNAME = 'M6616592358'
PASSWORD = 'panhui199261'


async def find_and_fetch():
    """从首页找到链接并抓取"""
    print("=" * 60)
    print("从首页找到烟台价格链接")
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
                await checkbox.click()
        except:
            pass

        try:
            await page.click('.form-button-login', timeout=5000)
        except:
            pass

        print("等待登录...")
        await page.wait_for_timeout(10000)
        print(f"当前URL: {page.url}")

        # 访问首页
        print("\n2. 访问首页...")
        await page.goto('https://jiancai.mysteel.com/', wait_until='domcontentloaded', timeout=60000)
        await page.wait_for_timeout(5000)

        # 查找所有链接
        print("\n3. 查找链接...")
        all_links = await page.evaluate('''() => {
            const links = [];
            document.querySelectorAll('a[href]').forEach(a => {
                links.push({
                    text: a.textContent.trim().substring(0, 50),
                    href: a.href
                });
            });
            return links;
        }''')

        # 打印包含"烟台"的链接
        print("\n包含'烟台'的链接:")
        yantai_links = [l for l in all_links if '烟台' in l['text']]
        for l in yantai_links[:10]:
            print(f"  {l['text']}: {l['href']}")

        # 打印包含日期的链接
        print("\n包含日期的链接(m/开头):")
        date_links = [l for l in all_links if '/m/' in l['href']]
        for l in date_links[:10]:
            print(f"  {l['text']}: {l['href']}")

        # 尝试访问山东市场页面
        print("\n4. 访问山东市场页面...")
        shandong_url = "https://jiancai.mysteel.com/market/pa228aa010101a0a01010205aaaa1.html"
        await page.goto(shandong_url, wait_until='domcontentloaded', timeout=60000)
        await page.wait_for_timeout(5000)

        text = await page.evaluate('() => document.body.innerText')
        print(f"页面文本长度: {len(text)}")

        # 查找市场页面中的链接
        market_links = await page.evaluate('''() => {
            const links = [];
            document.querySelectorAll('a[href]').forEach(a => {
                const href = a.href;
                const text = a.textContent.trim();
                if (href.includes('jiancai.mysteel.com') && text.length > 0 && text.length < 30) {
                    links.push({text, href});
                }
            });
            return links;
        }''')

        print(f"\n市场页面中的链接({len(market_links)}个):")
        yantai_in_market = [l for l in market_links if '烟台' in l['text'] or '山东' in l['text']]
        for l in yantai_in_market[:10]:
            print(f"  {l['text']}: {l['href']}")

        await browser.close()


if __name__ == '__main__':
    asyncio.run(find_and_fetch())