"""
自动登录并保存Cookie
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

DATA_DIR = Path(__file__).parent.absolute() / 'data'
DATA_DIR.mkdir(exist_ok=True)
COOKIE_FILE = DATA_DIR / 'mysteel_cookies.json'


async def auto_login():
    print("=" * 60)
    print("自动登录并保存Cookie")
    print("=" * 60)

    username = 'M6616592358'
    password = 'mysteel573005'

    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=False)
    context = await browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        locale='zh-CN'
    )
    page = await context.new_page()

    try:
        # 1. 访问登录页面
        print("\n[1/4] 访问登录页面...")
        await page.goto('https://passport.mysteel.com/', wait_until='domcontentloaded', timeout=60000)
        await asyncio.sleep(5)

        # 2. 切换到账号登录
        print("[2/4] 切换到账号登录...")
        try:
            account_tab = await page.query_selector('.form-tab-account, a[data-tab="account"]')
            if account_tab:
                await account_tab.click()
                await asyncio.sleep(2)
                print("      已切换到账号登录")
        except Exception as e:
            print(f"      切换失败: {e}")

        # 3. 填写登录表单
        print("[3/4] 填写登录表单...")
        await page.evaluate(f'''() => {{
            const inputs = document.querySelectorAll('input');
            for (const inp of inputs) {{
                const ph = inp.placeholder || '';
                if (ph.includes('用户名')) inp.value = '{username}';
                if (ph.includes('密码') && inp.type === 'password') inp.value = '{password}';
            }}
        }}''')
        await asyncio.sleep(1)
        print("      已填写表单")

        # 4. 点击登录
        print("[4/4] 点击登录...")
        try:
            login_btn = await page.query_selector('.form-button-login, button:has-text("登录")')
            if login_btn:
                await login_btn.click()
                print("      已点击登录按钮")
        except Exception as e:
            print(f"      点击失败: {e}")

        # 等待登录完成
        print("\n[等待] 等待登录完成...")
        await asyncio.sleep(10)

        # 保存Cookie
        print("\n[保存] 保存Cookie...")
        cookies = await context.cookies()

        if cookies:
            with open(COOKIE_FILE, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, ensure_ascii=False, indent=2)
            print(f"      已保存 {len(cookies)} 条Cookie到: {COOKIE_FILE}")
        else:
            print("      获取Cookie失败")

        # 显示关键Cookie
        important = [c for c in cookies if 'mysteel' in c.get('domain', '').lower() or 'steel' in c.get('name', '').lower()]
        if important:
            print(f"\n      关键Cookie ({len(important)} 条)")
            for c in important[:5]:
                name = c.get('name', '?')
                value = c.get('value', '')[:30]
                print(f"        - {name}: {value}...")

        print("\n" + "=" * 60)
        print("登录完成！")
        print("=" * 60)

    except Exception as e:
        print(f"\n[错误] {e}")

    # 保持浏览器打开让用户确认
    print("\n按Ctrl+C关闭...")
    await asyncio.sleep(60)

    await browser.close()
    await playwright.stop()


if __name__ == '__main__':
    try:
        asyncio.run(auto_login())
    except KeyboardInterrupt:
        print("\n[退出]")
