"""
登录后测试多种URL模式
"""
import asyncio
import sys
import json
from pathlib import Path

sys.path.insert(0, '.')

from playwright.async_api import async_playwright

DATA_DIR = Path('web/backend/services/data')
COOKIE_FILE = DATA_DIR / 'mysteel_cookies_new.json'
USERNAME = 'M6616592358'
PASSWORD = 'panhui199261'


async def test_urls():
    """测试多种URL模式"""
    print("=" * 60)
    print("测试多种URL模式")
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

        # 保存Cookie
        cookies = await context.cookies()
        with open(COOKIE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cookies, f, ensure_ascii=False)

        # 测试多种URL
        test_urls = [
            ("首页", "https://jiancai.mysteel.com/"),
            ("直接", "https://jiancai.mysteel.com/m/24070110/25B3355C6617BD3C.html"),
            ("market", "https://jiancai.mysteel.com/market/pa228aa01010104a0aaaaa1.html"),
            ("搜索", "https://search.mysteel.com/?keyword=%E7%83%AD%E8%BD%AC%E5%B8%A6%E9%92%A2%E6%A0%BC&sitetype=jiancai"),
        ]

        for name, url in test_urls:
            print(f"\n[{name}]: {url}")
            try:
                await page.goto(url, wait_until='domcontentloaded', timeout=60000)
                await page.wait_for_timeout(5000)

                text = await page.evaluate('() => document.body.innerText')
                print(f"  文本长度: {len(text)}")

                if len(text) > 100:
                    # 查找烟台相关链接
                    links = await page.evaluate('''() => {
                        const links = [];
                        document.querySelectorAll('a[href]').forEach(a => {
                            const href = a.href;
                            const text = a.textContent.trim();
                            if (href.includes('jiancai.mysteel.com') && text.includes('烟台')) {
                                links.push({text, href});
                            }
                        });
                        return links;
                    }''')
                    print(f"  烟台相关链接: {links[:3]}")
            except Exception as e:
                print(f"  错误: {e}")

        await browser.close()


if __name__ == '__main__':
    asyncio.run(test_urls())