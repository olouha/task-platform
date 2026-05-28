"""
测试账号登录和数据抓取
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

DATA_DIR = Path('services/data')
COOKIE_FILE = DATA_DIR / 'mysteel_cookies.json'

USERNAME = 'M6616592358'
PASSWORD = 'panhui199261'


async def main():
    print('=' * 60)
    print('测试账号登录和数据抓取')
    print('=' * 60)
    print()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 3000},
            locale='zh-CN'
        )
        page = await context.new_page()

        # 1. 访问登录页
        print('1. 访问登录页...')
        await page.goto('https://passport.mysteel.com/', wait_until='domcontentloaded', timeout=60000)
        await page.wait_for_timeout(3000)
        print(f'   URL: {page.url}')

        # 2. 点击账号登录
        print('\n2. 点击账号登录...')
        try:
            tab = await page.query_selector('.form-tab-account, a[data-tab="account"]')
            if tab:
                await tab.click()
                await page.wait_for_timeout(2000)
                print('   已点击账号登录标签')
        except Exception as e:
            print(f'   失败: {e}')

        # 3. 填写表单
        print('\n3. 填写表单...')
        result = await page.evaluate(f'''() => {{
            const inputs = document.querySelectorAll('input');
            let filled = 0;
            for (const inp of inputs) {{
                const ph = (inp.placeholder || '').toLowerCase();
                if (ph.includes('用户名') || ph.includes('账号') || ph.includes('手机')) {{
                    inp.value = 'M6616592358';
                    filled++;
                }}
                if (ph.includes('密码') && inp.type === 'password') {{
                    inp.value = 'panhui199261';
                    filled++;
                }}
            }}
            return filled;
        }}''')
        print(f'   填写: {result} 个字段')

        await page.wait_for_timeout(1000)

        # 4. 点击登录
        print('\n4. 点击登录...')
        try:
            btn = await page.query_selector('button:has-text("登录"), input[type="submit"]')
            if btn:
                await btn.click()
                print('   已点击登录按钮')
                await page.wait_for_timeout(8000)
        except Exception as e:
            print(f'   失败: {e}')

        print(f'\n5. 登录后URL: {page.url}')

        # 5. 保存Cookie
        cookies = await context.cookies()
        COOKIE_FILE.write_text(json.dumps(cookies, ensure_ascii=False), encoding='utf-8')
        print(f'\n6. Cookie已保存: {len(cookies)} 条')

        # 6. 访问市场页面检查数据
        print('\n7. 访问市场页面...')
        await page.goto('https://jiancai.mysteel.com/market/pa228aa010101a0a01010205aaaa1.html',
                       wait_until='domcontentloaded', timeout=60000)
        await page.wait_for_timeout(5000)
        print(f'   URL: {page.url}')

        # 检查是否有价格数据
        body_text = await page.evaluate('() => document.body.textContent')
        if '价格' in body_text or '高线' in body_text or '螺纹钢' in body_text:
            print('   页面包含价格数据 [OK]')
        elif '登录' in body_text and 'passport' in page.url:
            print('   需要登录')
        else:
            print('   页面内容检查中...')

        # 7. 测试访问一个历史数据URL
        print('\n8. 测试访问历史数据页面...')
        # 使用一个可能存在的日期
        test_url = 'https://jiancai.mysteel.com/m/26051410/25B3355C6617BD3C.html'
        await page.goto(test_url, wait_until='domcontentloaded', timeout=60000)
        await page.wait_for_timeout(5000)
        print(f'   URL: {page.url}')

        # 截图
        screenshot = await page.screenshot(full_page=True)
        screenshot_path = DATA_DIR / 'test_fetch.png'
        with open(screenshot_path, 'wb') as f:
            f.write(screenshot)
        print(f'   截图已保存: {screenshot_path}')

        # 检查页面内容
        body_text = await page.evaluate('() => document.body.textContent')
        if '价格' in body_text and ('高线' in body_text or '螺纹钢' in body_text):
            print('   历史数据页面有价格数据 [OK]')
        else:
            print('   检查页面内容...')

        await browser.close()
        print('\n测试完成')


if __name__ == '__main__':
    asyncio.run(main())