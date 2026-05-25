"""
步骤1: 获取烟台市场所有历史链接
"""

import asyncio
from playwright.async_api import async_playwright
from pathlib import Path
import json
import random

DATA_DIR = Path('services/data')
COOKIE_FILE = DATA_DIR / 'mysteel_cookies.json'
MARKET_URL = 'https://jiancai.mysteel.com/market/pa228aa010101a0a01010205aaaa1.html'
LINKS_FILE = DATA_DIR / 'yantai_links.json'

USERNAME = 'M6616592358'
PASSWORD = 'mysteel573005'


async def login(page):
    """登录"""
    print('登录中...')
    cookies = []
    if COOKIE_FILE.exists():
        try:
            cookies = json.loads(COOKIE_FILE.read_text(encoding='utf-8'))
            if cookies:
                await page.context.add_cookies(cookies)
        except:
            pass

    await page.goto('https://passport.mysteel.com/', wait_until='domcontentloaded', timeout=60000)
    await asyncio.sleep(random.uniform(2, 4))

    try:
        account_tab = await page.query_selector('.form-tab-account')
        if account_tab:
            await account_tab.click()
            await asyncio.sleep(random.uniform(1, 2))
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

    await asyncio.sleep(random.uniform(1, 2))

    try:
        checkbox = await page.query_selector('input[type="checkbox"]')
        if checkbox and not await checkbox.is_checked():
            await checkbox.click()
    except:
        pass

    await asyncio.sleep(random.uniform(0.5, 1))

    try:
        login_btn = await page.query_selector('.form-button-login')
        if login_btn:
            await login_btn.click()
    except:
        pass

    await asyncio.sleep(random.uniform(8, 12))

    cookies = await page.context.cookies()
    with open(COOKIE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cookies, f, ensure_ascii=False)
    print('登录完成\n')


async def main():
    print('=' * 60)
    print('步骤1: 获取烟台市场所有历史链接')
    print('=' * 60)

    all_links = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 3000},
            locale='zh-CN',
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = await context.new_page()

        await login(page)

        # 访问市场页面
        print(f'访问市场页面...')
        await page.goto(MARKET_URL, wait_until='domcontentloaded', timeout=60000)
        await asyncio.sleep(random.uniform(3, 5))

        for page_num in range(1, 51):  # 50页
            print(f'获取第{page_num}页链接...', end=' ')

            if page_num > 1:
                page_url = f'https://jiancai.mysteel.com/market/pa228aa010101a0a01010205aaaa{page_num}.html?keyWord='
                try:
                    await page.goto(page_url, wait_until='domcontentloaded', timeout=60000)
                except:
                    print('访问失败')
                    break
            else:
                page_url = page.url

            await asyncio.sleep(random.uniform(2, 4))

            # 获取烟台链接
            links = await page.evaluate('''() => {
                const links = [];
                document.querySelectorAll('a[href]').forEach(a => {
                    const href = a.href;
                    const text = a.textContent.trim();
                    if (href.includes('jiancai.mysteel.com/m/') &&
                        href.includes('.html') &&
                        text.includes('烟台')) {
                        links.push({href: href, text: text});
                    }
                });
                return links;
            }''')

            if not links:
                print('无数据，停止')
                break

            all_links.extend(links)
            print(f'{len(links)}条 (累计{len(all_links)})')

            # 检查是否有下一页
            has_next = await page.evaluate('''() => {
                const nextBtn = Array.from(document.querySelectorAll('a'))
                    .find(a => a.textContent.trim() === '下一页');
                return nextBtn && nextBtn.href;
            }''')

            if not has_next:
                print('没有更多页面')
                break

        await browser.close()

    # 保存链接
    with open(LINKS_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_links, f, ensure_ascii=False, indent=2)

    print(f'\\n总共获取到 {len(all_links)} 个烟台链接')
    print(f'链接已保存到: {LINKS_FILE}')


if __name__ == '__main__':
    asyncio.run(main())