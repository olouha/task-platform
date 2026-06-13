"""
重新登录并保存Cookie
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

DATA_DIR = Path(__file__).parent.absolute() / 'data'
DATA_DIR.mkdir(exist_ok=True)
COOKIE_FILE = DATA_DIR / 'mysteel_cookies.json'
CONFIG_FILE = DATA_DIR / 'mysteel_config.json'


def load_credentials():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
            return config.get('username', 'M6616592358'), config.get('password', 'mysteel573005')
    return 'M6616592358', 'mysteel573005'


async def login_and_save_cookie():
    print("=" * 60)
    print("登录并保存Cookie")
    print("=" * 60)

    username, password = load_credentials()
    print(f"\n使用凭据: {username[:3]}***")

    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=False)
    context = await browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        locale='zh-CN'
    )
    page = await context.new_page()

    try:
        print("\n1. 访问登录页面...")
        await page.goto('https://passport.mysteel.com/', wait_until='domcontentloaded', timeout=60000)
        await asyncio.sleep(5)

        print("2. 切换到账号登录...")
        try:
            account_tab = await page.query_selector('.form-tab-account, a[data-tab="account"]')
            if account_tab:
                await account_tab.click()
                await asyncio.sleep(2)
        except:
            pass

        print("3. 填写登录表单...")
        await page.evaluate(f'''() => {{
            const inputs = document.querySelectorAll('input');
            for (const inp of inputs) {{
                const ph = inp.placeholder || '';
                if (ph.includes('用户名')) inp.value = '{username}';
                if (ph.includes('密码') && inp.type === 'password') inp.value = '{password}';
            }}
        }}''')
        await asyncio.sleep(1)

        print("4. 点击登录...")
        try:
            login_btn = await page.query_selector('.form-button-login, button:has-text("登录")')
            if login_btn:
                await login_btn.click()
        except:
            pass

        print("5. 等待登录完成...")
        await asyncio.sleep(10)

        print("6. 保存Cookie...")
        cookies = await context.cookies()
        with open(COOKIE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cookies, f, ensure_ascii=False)

        print(f"   已保存 {len(cookies)} 条Cookie到: {COOKIE_FILE}")

        print("\n[完成] 请按回车键关闭浏览器...")
        input()

    except Exception as e:
        print(f"错误: {e}")

    await browser.close()
    await playwright.stop()

    print("\n" + "=" * 60)
    print("登录完成！请重新运行收集脚本")
    print("=" * 60)


if __name__ == '__main__':
    try:
        asyncio.run(login_and_save_cookie())
    except KeyboardInterrupt:
        print("\n\n[中断]")