#!/usr/bin/env python3
"""
Mysteel 登录脚本 - 获取Cookie
需要手动完成人机验证
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / 'data'
COOKIE_FILE = DATA_DIR / 'mysteel_cookies.json'

USERNAME = 'M6616592358'
PASSWORD = 'mysteel573005'

async def login_and_save_cookies():
    """登录Mysteel并保存Cookie"""
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=False)
    context = await browser.new_context()
    page = await context.new_page()

    try:
        # 1. 先访问主页
        print('正在访问Mysteel主页...')
        await page.goto('https://www.mysteel.com/', wait_until='domcontentloaded', timeout=60000)
        await asyncio.sleep(3)
        print('主页加载完成')

        # 2. 点击登录按钮
        print('点击登录按钮...')
        login_button = page.locator('text=登录').first
        await login_button.click()
        await asyncio.sleep(2)

        # 3. 输入用户名密码
        print(f'输入用户名: {USERNAME}')
        await page.fill('#username', USERNAME)
        await page.fill('#password', PASSWORD)

        # 4. 点击登录
        print('点击登录确认...')
        submit_button = page.locator('button[type=submit], input[type=submit]').first
        await submit_button.click()
        await asyncio.sleep(2)

        # 5. 等待人机验证（用户需要手动完成）
        print('='*50)
        print('请在浏览器窗口中完成人机验证...')
        print('验证完成后按 Enter 继续...')
        print('='*50)
        input()

        # 6. 等待一下让登录完成
        await asyncio.sleep(5)

        # 7. 保存Cookie
        cookies = await context.cookies()
        print(f'获取到 {len(cookies)} 个Cookie')

        with open(COOKIE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cookies, f, ensure_ascii=False, indent=2)
        print(f'Cookie已保存到: {COOKIE_FILE}')

        # 验证登录状态
        await page.goto('https://www.mysteel.com/', wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(2)
        title = await page.title()
        print(f'当前页面标题: {title}')

    except Exception as e:
        print(f'登录过程中出错: {e}')
        raise
    finally:
        await browser.close()
        await pw.stop()

if __name__ == '__main__':
    asyncio.run(login_and_save_cookies())