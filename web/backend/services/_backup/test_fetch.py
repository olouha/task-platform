"""
测试脚本 - 测试登录和抓取功能
先抓取3天数据进行测试
"""
import asyncio
import sys
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, '.')

from playwright.async_api import async_playwright

# 配置
DATA_DIR = Path('web/backend/services/data')
DB_FILE = DATA_DIR / 'yantai_rebar.db'
COOKIE_FILE = DATA_DIR / 'mysteel_cookies_test.json'

USERNAME = 'M6616592358'
PASSWORD = 'panhui199261'

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def generate_url(date: str, period: str) -> str:
    """生成URL"""
    yymmdd = date[2:4] + date[5:7] + date[8:10]
    hour = '10' if period == 'AM' else '16'
    return f"https://jiancai.mysteel.com/m/{yymmdd}{hour}/25B3355C6617BD3C.html"


async def test_login():
    """测试登录"""
    logger.info("=" * 60)
    logger.info("测试1: 登录功能")
    logger.info("=" * 60)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 3000},
            locale='zh-CN'
        )
        page = await context.new_page()

        try:
            # 访问登录页
            logger.info("访问登录页...")
            await page.goto('https://passport.mysteel.com/', wait_until='networkidle', timeout=60000)
            await page.wait_for_timeout(3000)

            # 截图登录页
            await page.screenshot(path=str(DATA_DIR / 'test_login_page.png'), full_page=True)
            logger.info("已截图: test_login_page.png")

            # 切换到账号登录
            try:
                account_tab = await page.query_selector('.form-tab-account')
                if account_tab:
                    await account_tab.click()
                    logger.info("已切换到账号登录")
                    await page.wait_for_timeout(2000)
            except Exception as e:
                logger.warning(f"切换账号登录失败: {e}")

            # 填写表单
            await page.evaluate(f'''() => {{
                const inputs = document.querySelectorAll('input');
                for (const inp of inputs) {{
                    const ph = inp.placeholder || '';
                    if (ph.includes('用户名')) inp.value = '{USERNAME}';
                    if (ph.includes('密码') && inp.type === 'password') inp.value = '{PASSWORD}';
                }}
            }}''')
            logger.info("已填写用户名密码")

            await page.wait_for_timeout(500)

            # 勾选协议
            try:
                checkbox = await page.query_selector('input[type="checkbox"]')
                if checkbox and not await checkbox.is_checked():
                    await checkbox.click()
                    logger.info("已勾选协议")
            except:
                pass

            await page.wait_for_timeout(500)

            # 点击登录
            try:
                login_btn = await page.query_selector('.form-button-login')
                if login_btn:
                    await login_btn.click()
                    logger.info("已点击登录按钮")
                else:
                    btns = await page.query_selector_all('button')
                    for btn in btns:
                        text = await btn.text_content()
                        if text and '登录' in text:
                            await btn.click()
                            logger.info("已点击登录按钮(备用)")
                            break
            except Exception as e:
                logger.warning(f"点击登录失败: {e}")

            logger.info("等待登录完成...")
            await page.wait_for_timeout(10000)

            # 截图登录后页面
            await page.screenshot(path=str(DATA_DIR / 'test_after_login.png'), full_page=True)
            logger.info("已截图: test_after_login.png")

            # 检查URL
            current_url = page.url
            logger.info(f"当前URL: {current_url}")

            if 'passport' in current_url and 'login' in current_url:
                logger.warning("仍在登录页，登录可能失败")
            else:
                logger.info("登录可能成功")

            # 保存Cookie
            cookies = await context.cookies()
            with open(COOKIE_FILE, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, ensure_ascii=False)
            logger.info(f"Cookie已保存: {COOKIE_FILE}")

        except Exception as e:
            logger.error(f"登录测试失败: {e}")
            import traceback
            traceback.print_exc()

        finally:
            await browser.close()

    return True


async def test_fetch():
    """测试抓取功能"""
    logger.info("=" * 60)
    logger.info("测试2: 抓取功能")
    logger.info("=" * 60)

    # 加载Cookie
    if not COOKIE_FILE.exists():
        logger.error("没有Cookie文件，请先运行登录测试")
        return False

    with open(COOKIE_FILE, 'r', encoding='utf-8') as f:
        cookies = json.load(f)

    # 测试抓取3天
    test_dates = ['2024-01-02', '2024-01-03', '2024-01-04']

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 3000},
            locale='zh-CN'
        )
        page = await context.new_page()

        # 添加Cookie
        await context.add_cookies(cookies)
        logger.info("已加载Cookie")

        for date in test_dates:
            logger.info(f"\n抓取 {date}")

            for period in ['AM', 'PM']:
                url = generate_url(date, period)
                logger.info(f"  {period}: {url}")

                try:
                    await page.goto(url, wait_until='domcontentloaded', timeout=60000)
                    await page.wait_for_timeout(5000)

                    # 截图
                    screenshot_path = DATA_DIR / 'screenshots' / f"test_{date}_{period}.png"
                    screenshot_path.parent.mkdir(exist_ok=True)
                    await page.screenshot(path=str(screenshot_path), full_page=True)
                    logger.info(f"  截图: {screenshot_path}")

                    # 提取数据
                    data = await page.evaluate('''() => {
                        const tables = document.querySelectorAll('table');
                        const results = [];
                        tables.forEach((table) => {
                            const rows = table.querySelectorAll('tr');
                            rows.forEach((row) => {
                                const cells = row.querySelectorAll('td, th');
                                const rowData = [];
                                cells.forEach(c => rowData.push(c.textContent.trim()));
                                if (rowData.length >= 5) results.push(rowData);
                            });
                        });
                        return results;
                    }''')

                    # 解析数据
                    prices = []
                    for row in data:
                        material_name = str(row[0]).strip()
                        spec = str(row[1]).strip()
                        price_str = str(row[4]).strip() if len(row) > 4 else ''

                        valid_names = ['高线', '螺纹钢', '盘螺', '圆钢']
                        if material_name in valid_names and spec.startswith('Φ') and price_str.isdigit():
                            try:
                                price = int(price_str)
                                if price > 0:
                                    prices.append({
                                        'material_name': material_name,
                                        'spec': spec,
                                        'price': price
                                    })
                            except:
                                pass

                    logger.info(f"  提取到 {len(prices)} 条数据")
                    if prices:
                        for p in prices[:3]:
                            logger.info(f"    - {p['material_name']} {p['spec']} {p['price']}")

                except Exception as e:
                    logger.error(f"  抓取失败: {e}")

                # 等待
                await page.wait_for_timeout(3000)

        await browser.close()

    return True


async def main():
    """主函数"""
    logger.info("开始测试脚本...")

    # 测试1: 登录
    await test_login()

    # 等待5秒后自动继续测试抓取
    logger.info("等待5秒后自动继续...")
    await asyncio.sleep(5)

    # 测试2: 抓取
    await test_fetch()

    logger.info("\n测试完成！")
    logger.info(f"截图保存在: {DATA_DIR / 'screenshots'}")


if __name__ == '__main__':
    asyncio.run(main())