"""
测试单个URL的抓取 - 调试登录问题
账号: M6616672758 / panhui199261
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

DATA_DIR = Path('services/data')
COOKIE_FILE = DATA_DIR / 'mysteel_cookies.json'

USERNAME = 'M6616672758'
PASSWORD = 'panhui199261'

TEST_URL = 'https://jiancai.mysteel.com/m/26051410/25B3355C6617BD3C.html'


async def main():
    print('=' * 60)
    print('测试登录流程')
    print('=' * 60)
    print()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 3000},
            locale='zh-CN'
        )
        page = await context.new_page()

        # 访问登录页
        print('1. 访问登录页...')
        await page.goto('https://passport.mysteel.com/', wait_until='domcontentloaded', timeout=60000)
        await page.wait_for_timeout(3000)

        # 截图
        screenshot_path = DATA_DIR / 'login_page.png'
        await page.screenshot(path=str(screenshot_path))
        print(f'  截图: {screenshot_path}')

        # 检查页面内容
        content = await page.content()
        print(f'  页面标题: {await page.title()}')

        # 点击账号登录
        print('\n2. 点击账号登录标签...')
        try:
            # 尝试多种选择器
            selectors = [
                '.form-tab-account',
                'a[data-tab="account"]',
                '.tab-item:has-text("账号")',
                'text=账号',
                '[class*="tab"]:has-text("账号")'
            ]
            for selector in selectors:
                try:
                    elem = await page.query_selector(selector)
                    if elem:
                        await elem.click()
                        print(f'  点击成功: {selector}')
                        break
                except:
                    pass
            await page.wait_for_timeout(2000)
        except Exception as e:
            print(f'  点击失败: {e}')

        # 截图
        await page.screenshot(path=str(DATA_DIR / 'after_tab_click.png'))

        # 填写表单
        print('\n3. 填写表单...')
        result = await page.evaluate(f'''() => {{
            const inputs = document.querySelectorAll('input');
            let filled = 0;
            for (const inp of inputs) {{
                const type = inp.type || '';
                const placeholder = (inp.placeholder || '').toLowerCase();
                const id = (inp.id || '').toLowerCase();
                const name = (inp.name || '').toLowerCase();

                if (placeholder.includes('用户名') || placeholder.includes('手机') ||
                    placeholder.includes('账号') || id.includes('username') || name.includes('username')) {{
                    inp.value = 'M6616672758';
                    filled++;
                }}
                if ((placeholder.includes('密码') && type === 'password') ||
                    placeholder.includes('password') || id.includes('password') || name.includes('password')) {{
                    inp.value = 'panhui199261';
                    filled++;
                }}
            }}
            return filled;
        }}''')
        print(f'  填写结果: {result} 个字段')

        await page.wait_for_timeout(1000)

        # 截图
        await page.screenshot(path=str(DATA_DIR / 'after_form_fill.png'))

        # 点击登录
        print('\n4. 点击登录按钮...')
        try:
            selectors = [
                'button:has-text("登录")',
                'input[type="submit"]',
                '.btn-login',
                '[class*="login"]:not([class*="tab"])'
            ]
            for selector in selectors:
                try:
                    elem = await page.query_selector(selector)
                    if elem and await elem.is_visible():
                        print(f'  点击: {selector}')
                        await elem.click()
                        break
                except:
                    pass

            # 等待登录完成
            print('  等待页面跳转...')
            await page.wait_for_timeout(8000)

        except Exception as e:
            print(f'  点击失败: {e}')

        print(f'\n5. 登录后URL: {page.url}')

        # 截图
        await page.screenshot(path=str(DATA_DIR / 'after_login.png'))

        # 保存Cookie
        cookies = await context.cookies()
        COOKIE_FILE.write_text(json.dumps(cookies, ensure_ascii=False), encoding='utf-8')
        print(f'\n6. Cookie已保存: {len(cookies)} 条')

        # 访问目标页面
        print('\n7. 访问目标页面...')
        await page.goto(TEST_URL, wait_until='domcontentloaded', timeout=60000)
        await page.wait_for_timeout(5000)

        print(f'  URL: {page.url}')

        # 截图
        await page.screenshot(path=str(DATA_DIR / 'target_page.png'))

        # 检查页面内容
        body_text = await page.evaluate('() => document.body.textContent.substring(0, 500)')
        print(f'\n8. 页面内容(前500字符):\n{body_text}')

        await browser.close()


if __name__ == '__main__':
    asyncio.run(main())