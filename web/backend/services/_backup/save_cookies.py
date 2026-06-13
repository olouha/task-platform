"""
保存Cookie工具
打开浏览器，用户登录后自动保存Cookie
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

DATA_DIR = Path(__file__).parent.absolute() / 'data'
DATA_DIR.mkdir(exist_ok=True)
COOKIE_FILE = DATA_DIR / 'mysteel_cookies.json'


async def save_cookies():
    print("=" * 60)
    print("保存Cookie工具")
    print("=" * 60)

    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=False)
    context = await browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        locale='zh-CN'
    )
    page = await context.new_page()

    print("\n1. 访问我的钢铁网...")
    await page.goto('https://www.mysteel.com/', wait_until='domcontentloaded', timeout=60000)
    await asyncio.sleep(3)

    print("\n2. 请在浏览器中手动登录...")
    print("   - 点击右上角'登录'")
    print("   - 输入用户名: M6616592358")
    print("   - 输入密码: mysteel573005")
    print("   - 完成登录")
    print("\n3. 登录完成后，在浏览器中访问:")
    print("   https://jiancai.mysteel.com/market/pa228aa010101a0a01010205aaaa1.html")
    print("\n4. 确认登录成功后，在此窗口按回车键保存Cookie...")

    input()

    print("\n5. 保存Cookie...")
    cookies = await context.cookies()
    print(f"   获取到 {len(cookies)} 条Cookie")

    if cookies:
        with open(COOKIE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cookies, f, ensure_ascii=False, indent=2)
        print(f"   已保存到: {COOKIE_FILE}")

        # 显示关键Cookie
        important = [c for c in cookies if 'mysteel' in c.get('domain', '').lower() or 'steel' in c.get('name', '').lower()]
        if important:
            print(f"\n   关键Cookie ({len(important)} 条):")
            for c in important[:5]:
                print(f"     - {c.get('name')}: {c.get('value', '')[:30]}...")
    else:
        print("   获取Cookie失败，请确保已登录")

    print("\n[完成] 按回车键关闭浏览器...")
    input()

    await browser.close()
    await playwright.stop()

    print("\n" + "=" * 60)
    print("Cookie保存完成！现在可以运行抓取脚本")
    print("=" * 60)


if __name__ == '__main__':
    try:
        asyncio.run(save_cookies())
    except KeyboardInterrupt:
        print("\n\n[中断]")
