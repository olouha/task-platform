"""调试脚本 - 登录并检查页面结构"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

DATA_DIR = Path(r'E:\E\任务\task-platform\web\backend\services\data')
username = 'M6616592358'
password = 'mysteel573005'

async def debug_page_with_login():
    """登录后检查页面结构"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # 不隐藏，方便调试
        context = await browser.new_context(viewport={'width': 1920, 'height': 3000}, locale='zh-CN')
        page = await context.new_page()

        # 1. 登录
        print("开始登录...")
        await page.goto('https://passport.mysteel.com/', wait_until='domcontentloaded', timeout=60000)
        await page.wait_for_timeout(5000)

        # 切换到账号登录
        try:
            account_tab = await page.query_selector('.form-tab-account')
            if account_tab:
                await account_tab.click()
                await page.wait_for_timeout(2000)
                print("已切换到账号登录")
        except:
            pass

        # 填写表单
        await page.evaluate(f'''() => {{
            const inputs = document.querySelectorAll('input');
            for (const inp of inputs) {{
                const ph = inp.placeholder || '';
                if (ph.includes('用户名')) inp.value = '{username}';
                if (ph.includes('密码') && inp.type === 'password') inp.value = '{password}';
            }}
        }}''')
        await page.wait_for_timeout(500)

        # 勾选同意
        try:
            checkbox = await page.query_selector('input[type="checkbox"]')
            if checkbox and not await checkbox.is_checked():
                await checkbox.click()
        except:
            pass

        await page.wait_for_timeout(500)

        # 点击登录
        try:
            login_btn = await page.query_selector('.form-button-login')
            if login_btn:
                await login_btn.click()
                print("已点击登录")
        except:
            pass

        await page.wait_for_timeout(10000)

        # 保存 Cookie
        cookies = await context.cookies()
        with open(DATA_DIR / 'mysteel_cookies.json', 'w', encoding='utf-8') as f:
            json.dump(cookies, f, ensure_ascii=False)
        print(f"Cookie已保存: {len(cookies)}条")

        # 2. 访问价格页
        url = 'https://jiancai.mysteel.com/m/26051510/25B3355C6617BD3C.html'
        print(f"\n访问: {url}")
        await page.goto(url, wait_until='domcontentloaded', timeout=60000)
        await page.wait_for_timeout(10000)

        # 截图
        screenshot = await page.screenshot(full_page=True)
        screenshot_path = DATA_DIR / 'debug_page_logged_in.png'
        with open(screenshot_path, 'wb') as f:
            f.write(screenshot)
        print(f"截图已保存: {screenshot_path}")

        # 3. 检查页面结构
        print("\n=== 页面结构分析 ===")

        # 查找所有表格
        table_count = await page.evaluate('''() => {
            return document.querySelectorAll('table').length;
        }''')
        print(f"标准 table 标签数量: {table_count}")

        # 获取页面 HTML 内容
        html_snippet = await page.evaluate('''() => {
            const body = document.body.innerHTML;

            // 查找包含螺纹钢、盘螺等关键词的区域
            const keywords = ['螺纹钢', '盘螺', '高线', '圆钢', '品名', '规格', '价格'];
            const results = [];

            // 按行分割
            const lines = body.split('\\n');
            for (let i = 0; i < lines.length && results.length < 100; i++) {
                const line = lines[i].trim();
                if (line.length > 5 && line.length < 500) {
                    for (const keyword of keywords) {
                        if (line.includes(keyword)) {
                            results.push(line);
                            break;
                        }
                    }
                }
            }

            return {
                htmlLines: results.slice(0, 50),
                allDivsWithPrice: Array.from(document.querySelectorAll('*')).slice(0, 30).map(el => ({
                    tag: el.tagName,
                    class: el.className || '',
                    text: el.textContent?.slice(0, 100) || ''
                }))
            };
        }''')

        print("\n包含关键词的HTML行:")
        for line in html_snippet['htmlLines'][:30]:
            print(f"  {line[:150]}")

        # 查找数据元素
        data_elements = await page.evaluate('''() => {
            // 查找所有包含数字价格文本的元素
            const allElements = document.querySelectorAll('*');
            const priceElements = [];

            for (const el of allElements) {
                const text = el.textContent?.trim() || '';
                // 查找包含数字且可能是价格的文本
                if (/\\d{3,4}/.test(text) && text.length > 5 && text.length < 100) {
                    priceElements.push({
                        tag: el.tagName,
                        class: el.className || '',
                        text: text,
                        html: el.outerHTML?.slice(0, 200) || ''
                    });
                }
            }

            return priceElements.slice(0, 20);
        }''')

        print("\n可能包含价格的元素:")
        for el in data_elements:
            print(f"  {el['tag']}.{el['class'][:30]}: {el['text'][:80]}")

        await browser.close()

if __name__ == '__main__':
    asyncio.run(debug_page_with_login())