"""
详细测试登录并验证Cookie
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
    print('详细测试登录')
    print('=' * 60)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 3000},
            locale='zh-CN',
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = await context.new_page()

        # 1. 访问登录页
        print('\n1. 访问登录页...')
        await page.goto('https://passport.mysteel.com/', wait_until='networkidle', timeout=60000)
        await page.wait_for_timeout(3000)
        await page.screenshot(path=str(DATA_DIR / 'login1.png'))

        # 2. 检查页面状态
        page_text = await page.evaluate('() => document.body.textContent')

        # 点击账号登录
        print('\n2. 点击账号登录...')
        try:
            # 尝试多种选择器
            selectors = [
                'text=账号登录',
                '.form-tab-account',
                'a[data-tab="account"]',
                '[class*="tab"]:has-text("账号")'
            ]
            for sel in selectors:
                try:
                    elem = await page.query_selector(sel)
                    if elem:
                        await elem.click()
                        print(f'  点击成功: {sel}')
                        await page.wait_for_timeout(2000)
                        await page.screenshot(path=str(DATA_DIR / 'login2.png'))
                        break
                except:
                    pass
        except Exception as e:
            print(f'  点击失败: {e}')

        # 3. 填写表单
        print('\n3. 填写表单...')
        filled = await page.evaluate(f'''
            () => {{
                let count = 0;
                const inputs = document.querySelectorAll('input');
                for (const inp of inputs) {{
                    const ph = inp.placeholder || '';
                    if (ph.includes('用户名') || ph.includes('手机')) {{
                        inp.value = '{USERNAME}';
                        count++;
                        console.log('填入用户名: ' + ph);
                    }}
                    if (ph.includes('密码') && inp.type === 'password') {{
                        inp.value = '{PASSWORD}';
                        count++;
                        console.log('填入密码: ' + ph);
                    }}
                }}
                return count;
            }}
        ''')
        print(f'  填写了 {filled} 个字段')
        await page.wait_for_timeout(1000)
        await page.screenshot(path=str(DATA_DIR / 'login3.png'))

        # 4. 点击登录
        print('\n4. 点击登录...')
        try:
            btn_selectors = [
                'button:has-text("登录")',
                'input[type="submit"]',
                '.form-button-login'
            ]
            for sel in btn_selectors:
                try:
                    btn = await page.query_selector(sel)
                    if btn:
                        print(f'  点击按钮: {sel}')
                        await btn.click()
                        break
                except:
                    pass

            # 等待登录完成
            print('  等待登录...')
            for i in range(20):
                await page.wait_for_timeout(1000)
                current_url = page.url
                if 'passport' not in current_url:
                    print(f'  登录成功，跳转到: {current_url}')
                    break
                if i % 5 == 0:
                    print(f'  等待中... ({i+1}/20)')
            else:
                print('  登录可能失败，继续...')

            await page.screenshot(path=str(DATA_DIR / 'login4.png'))

        except Exception as e:
            print(f'  登录失败: {e}')

        print(f'\n5. 最终URL: {page.url}')

        # 5. 检查Cookie
        cookies = await context.cookies()
        print(f'\n6. Cookie数量: {len(cookies)}')

        # 检查是否有会员相关的Cookie
        vip_cookies = [c for c in cookies if any(x in c.get('name', '').lower() for x in ['vip', 'member', 'user', 'uid', 'token'])]
        print(f'   会员相关Cookie: {len(vip_cookies)}')

        # 保存Cookie
        COOKIE_FILE.write_text(json.dumps(cookies, ensure_ascii=False), encoding='utf-8')
        print('   Cookie已保存')

        # 6. 访问数据页面验证
        print('\n7. 验证登录状态...')
        test_urls = [
            'https://jiancai.mysteel.com/m/26051410/25B3355C6617BD3C.html',
            'https://jiancai.mysteel.com/market/pa228aa010101a0a01010205aaaa1.html'
        ]

        for test_url in test_urls:
            print(f'\n   测试: {test_url}')
            await page.goto(test_url, wait_until='domcontentloaded', timeout=60000)
            await page.wait_for_timeout(5000)

            body = await page.evaluate('() => document.body.textContent')
            if '登录' in body and 'passport' in page.url:
                print('   结果: 需要登录')
            elif '高线' in body or '螺纹钢' in body:
                print('   结果: 有价格数据 [OK]')
            elif '价格' in body:
                print('   结果: 有价格相关内容')
            else:
                print('   结果: 无价格数据')

            await page.screenshot(path=str(DATA_DIR / f'verify_{test_url.split("/")[-1][:20]}.png'))

        await browser.close()


if __name__ == '__main__':
    asyncio.run(main())