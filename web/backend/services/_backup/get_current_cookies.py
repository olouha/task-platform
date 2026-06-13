#!/usr/bin/env python3
"""
获取当前浏览器Cookie并保存
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / 'data'
COOKIE_FILE = DATA_DIR / 'mysteel_cookies.json'

async def get_current_cookies():
    """获取当前浏览器会话的Cookie"""
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=False)
    context = await browser.new_context()
    page = await context.new_page()

    print('请在浏览器中登录 Mysteel...')
    print('登录完成后按 Enter 继续')
    input()

    # 访问主页确认登录
    await page.goto('https://www.mysteel.com/', wait_until='domcontentloaded', timeout=60000)
    await asyncio.sleep(3)

    # 获取所有Cookie
    cookies = await context.cookies()
    print(f'\n获取到 {len(cookies)} 个Cookie:')

    for c in cookies:
        print(f'  {c["name"]}: {c["value"][:30]}...' if len(c["value"]) > 30 else f'  {c["name"]}: {c["value"]}')

    # 只保存mysteel相关的Cookie
    mysteel_cookies = [c for c in cookies if 'mysteel' in c.get('domain', '')]
    print(f'\nmysteel相关Cookie: {len(mysteel_cookies)}个')

    with open(COOKIE_FILE, 'w', encoding='utf-8') as f:
        json.dump(mysteel_cookies, f, ensure_ascii=False, indent=2)
    print(f'Cookie已保存到: {COOKIE_FILE}')

    await browser.close()
    await pw.stop()

if __name__ == '__main__':
    asyncio.run(get_current_cookies())