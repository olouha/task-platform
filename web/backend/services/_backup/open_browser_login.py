#!/usr/bin/env python3
"""
打开浏览器等待用户登录，然后自动保存Cookie
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / 'data'
COOKIE_FILE = DATA_DIR / 'mysteel_cookies.json'

async def main():
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=False)
    context = await browser.new_context()
    page = await context.new_page()

    print('正在打开 Mysteel 登录页面...')
    await page.goto('https://passport.mysteel.com/login', wait_until='domcontentloaded', timeout=60000)

    print('='*50)
    print('请在浏览器中完成登录和人机验证...')
    print('登录成功后，等待5秒自动保存Cookie')
    print('='*50)

    # 等待登录成功（检测URL变化）
    try:
        await page.wait_for_url('**/www.mysteel.com**', timeout=120000)
        print('检测到登录成功！')
    except:
        print('等待URL变化超时，请手动确认是否登录成功')
        print('等待5秒后继续...')
        await asyncio.sleep(5)

    # 额外等待确保Cookie设置完成
    await asyncio.sleep(5)

    # 访问主页确保获取完整Cookie
    await page.goto('https://www.mysteel.com/', wait_until='domcontentloaded', timeout=30000)
    await asyncio.sleep(3)

    # 获取所有Cookie
    cookies = await context.cookies()
    print(f'\n获取到 {len(cookies)} 个Cookie')

    # 保存Cookie
    with open(COOKIE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cookies, f, ensure_ascii=False, indent=2)
    print(f'Cookie已保存到: {COOKIE_FILE}')

    await browser.close()
    await pw.stop()
    print('完成！')

if __name__ == '__main__':
    asyncio.run(main())