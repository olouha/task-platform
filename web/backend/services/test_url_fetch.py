"""
测试单个URL的抓取 - 调试"无数据"问题
账号: M6616672758 / panhui199261
"""
import asyncio
import json
import base64
from pathlib import Path
from playwright.async_api import async_playwright

DATA_DIR = Path('services/data')
COOKIE_FILE = DATA_DIR / 'mysteel_cookies.json'

USERNAME = 'M6616672758'
PASSWORD = 'panhui199261'

# 测试一个具体的URL - 使用已知的有效URL
TEST_URL = 'https://jiancai.mysteel.com/m/26051410/25B3355C6617BD3C.html'


async def main():
    print('=' * 60)
    print('测试单个URL抓取')
    print('=' * 60)
    print(f'URL: {TEST_URL}')
    print()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 3000},
            locale='zh-CN'
        )
        page = await context.new_page()

        # 加载Cookie
        if COOKIE_FILE.exists():
            try:
                cookies = json.loads(COOKIE_FILE.read_text(encoding='utf-8'))
                if cookies:
                    await context.add_cookies(cookies)
                    print(f'已加载 {len(cookies)} 条Cookie')
            except Exception as e:
                print(f'Cookie加载失败: {e}')

        # 先访问登录页面进行登录
        print('\n1. 执行登录...')
        await page.goto('https://passport.mysteel.com/', wait_until='domcontentloaded', timeout=60000)
        await page.wait_for_timeout(3000)

        # 点击账号登录标签
        try:
            account_tab = await page.query_selector('.form-tab-account, a[data-tab="account"], .tab-item:has-text("账号")')
            if account_tab:
                await account_tab.click()
                await page.wait_for_timeout(2000)
                print('已点击账号登录标签')
        except Exception as e:
            print(f'点击账号登录标签失败: {e}')

        # 填写表单
        await page.wait_for_timeout(1000)

        # 找到用户名和密码输入框
        username_filled = await page.evaluate('''() => {
            const inputs = document.querySelectorAll('input');
            let filled = false;
            for (const inp of inputs) {
                const type = inp.type || '';
                const placeholder = (inp.placeholder || '').toLowerCase();
                if (placeholder.includes('用户名') || placeholder.includes('手机') || placeholder.includes('账号')) {
                    inp.value = 'M6616672758';
                    filled = true;
                }
                if ((placeholder.includes('密码') && type === 'password') || placeholder.includes('password')) {
                    inp.value = 'panhui199261';
                    filled = true;
                }
            }
            return filled;
        }''')

        print(f'表单填写: {username_filled}')
        await page.wait_for_timeout(1000)

        # 点击登录按钮
        try:
            login_btn = await page.query_selector('button:has-text("登录"), input[type="submit"], .btn-login, [class*="login"]')
            if login_btn:
                await login_btn.click()
                print('已点击登录按钮')
                await page.wait_for_timeout(8000)
        except Exception as e:
            print(f'登录按钮点击失败: {e}')

        # 保存Cookie
        cookies = await context.cookies()
        COOKIE_FILE.write_text(json.dumps(cookies, ensure_ascii=False), encoding='utf-8')
        print(f'Cookie已保存: {len(cookies)} 条')

        print(f'\n当前URL: {page.url}')

        # 访问目标URL
        print('\n2. 访问目标页面...')
        await page.goto(TEST_URL, wait_until='domcontentloaded', timeout=60000)
        await page.wait_for_timeout(5000)

        print(f'当前URL: {page.url}')

        # 截图保存
        screenshot_path = DATA_DIR / 'debug_test_url.png'
        screenshot = await page.screenshot(full_page=True)
        with open(screenshot_path, 'wb') as f:
            f.write(screenshot)
        print(f'截图已保存: {screenshot_path}')

        # 等待JavaScript渲染
        print('\n3. 等待JavaScript渲染...')
        await page.wait_for_timeout(5000)

        # 滚动页面触发懒加载
        print('滚动页面触发懒加载...')
        for i in range(5):
            await page.evaluate('window.scrollBy(0, 500)')
            await page.wait_for_timeout(1000)

        # 再等一会儿让动态内容加载
        await page.wait_for_timeout(3000)

        # 截图保存
        screenshot = await page.screenshot(full_page=True)
        with open(screenshot_path, 'wb') as f:
            f.write(screenshot)
        print(f'滚动后截图已更新: {screenshot_path}')

        # 提取数据
        print('\n4. 提取数据...')

        data = await page.evaluate('''() => {
            const tables = document.querySelectorAll('table');
            const results = [];
            tables.forEach(table => {
                const rows = table.querySelectorAll('tr');
                rows.forEach(row => {
                    const cells = row.querySelectorAll('td, th');
                    if (cells.length >= 5) {
                        const material_name = cells[0]?.textContent?.trim().replace(/\\s+/g, ' ');
                        const spec = cells[1]?.textContent?.trim().replace(/\\s+/g, ' ');
                        const material_type = cells[2]?.textContent?.trim().replace(/\\s+/g, ' ');
                        const brand = cells[3]?.textContent?.trim().replace(/\\s+/g, ' ');
                        const price_text = cells[4]?.textContent?.trim().replace(/\\s+/g, ' ');

                        let price = 0;
                        const priceMatch = price_text.match(/(\\d{3,5})/);
                        if (priceMatch) {
                            price = parseInt(priceMatch[1]);
                        }

                        const valid_names = ['高线', '螺纹钢', '盘螺', '圆钢', '拉丝材'];
                        if (valid_names.some(n => material_name.includes(n)) && price > 0) {
                            results.push({
                                material_name,
                                spec,
                                material_type,
                                brand,
                                price
                            });
                        }
                    }
                });
            });
            return {tables_count: tables.length, rows_count: results.length, data: results};
        }''')

        print(f'找到 {data["tables_count"]} 个表格, {data["rows_count"]} 条价格数据')

        if data["data"]:
            print('\n价格数据:')
            for item in data["data"][:10]:
                print(f'  {item["material_name"]} {item["spec"]} {item["material_type"]} {item["brand"]}: {item["price"]}')
        else:
            print('\n未找到价格数据，检查页面内容...')
            body_text = await page.evaluate('() => document.body.textContent')
            if '无权限' in body_text or '登录' in body_text:
                print('  页面需要登录权限')
            elif '价格' in body_text:
                print('  页面有价格相关内容但解析失败')
            else:
                print(f'  页面文本(前1000字符):\n{body_text[:1000]}')

        await browser.close()


if __name__ == '__main__':
    asyncio.run(main())