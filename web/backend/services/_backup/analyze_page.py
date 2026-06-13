"""
分析 mysteeel 价格页面，查找价格数据
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

async def main():
    """获取页面数据"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 3000},
            locale='zh-CN'
        )
        page = await context.new_page()

        # 登录
        print("Login...")
        await page.goto('https://passport.mysteel.com/', wait_until='networkidle', timeout=60000)
        await page.wait_for_timeout(3000)

        await page.evaluate('''() => {
            const inputs = document.querySelectorAll('input');
            for (const inp of inputs) {
                const ph = inp.placeholder || '';
                if (ph.includes('用户名')) inp.value = 'M6616592358';
                if (ph.includes('密码') && inp.type === 'password') inp.value = 'panhui199261';
            }
        }''')
        await page.wait_for_timeout(500)

        try:
            checkbox = await page.query_selector('input[type="checkbox"]')
            if checkbox and not await checkbox.is_checked():
                await checkbox.click()
        except: pass

        try:
            await page.click('.form-button-login', timeout=5000)
        except: pass

        await page.wait_for_timeout(10000)
        print("Login successful")

        test_url = 'https://jiancai.mysteel.com/m/24010210/1BD5F502DA9E50F8.html'
        print(f"\nAccessing: {test_url}")

        await page.goto(test_url, wait_until='domcontentloaded', timeout=60000)
        await page.wait_for_timeout(30000)

        # 获取页面文本内容
        page_text = await page.evaluate('() => document.body.innerText')

        # 分析文本，查找包含钢筋和价格的行
        lines = page_text.split('\n')
        results = []
        keywords = ['线材', '螺纹钢', '高线', '盘螺', '圆钢', '钢筋']

        for line in lines:
            trimmed = line.strip()
            if trimmed:
                has_material = any(k in trimmed for k in keywords)
                if has_material:
                    results.append(trimmed[:100])

        print(f"\nFound {len(results)} lines with material names")
        for item in results[:30]:
            print(f"  {item}")

        # 保存分析结果
        with open('services/data/material_lines.txt', 'w', encoding='utf-8') as f:
            for item in results:
                f.write(item + '\n')

        print("\nAnalysis saved")

        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())