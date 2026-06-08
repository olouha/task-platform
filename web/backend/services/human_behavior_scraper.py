"""
高级反检测爬虫 - 模拟人类行为抓取 mysteeel 价格数据
特点：
1. 模拟真实用户的鼠标移动和点击
2. 随机延迟，模拟人类思考时间
3. 随机滚动页面
4. 使用 stealth 插件避免被检测
5. 多次尝试解密价格数据
"""
import asyncio
import random
import time
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict

from playwright.async_api import async_playwright
import sqlite3

# 配置
USERNAME = 'M6616592358'
PASSWORD = 'panhui199261'
DB_FILE = Path('data/yantai_rebar.db')
DATA_DIR = Path('services/data')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HumanBehavior:
    """模拟人类行为"""

    @staticmethod
    async def random_delay_async(min_sec: float = 0.5, max_sec: float = 2.0):
        """随机延迟（异步）"""
        delay = random.uniform(min_sec, max_sec)
        await asyncio.sleep(delay)
        return delay

    @staticmethod
    def random_delay(min_sec: float = 0.5, max_sec: float = 2.0):
        """随机延迟（同步）"""
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)
        return delay

    @staticmethod
    async def human_mouse_move(page, from_pos: tuple, to_pos: tuple, steps: int = None):
        """模拟人类鼠标移动（曲线移动）"""
        if steps is None:
            steps = random.randint(10, 25)

        from_x, from_y = from_pos
        to_x, to_y = to_pos

        # 添加随机偏移
        from_x += random.randint(-20, 20)
        from_y += random.randint(-20, 20)
        to_x += random.randint(-20, 20)
        to_y += random.randint(-20, 20)

        for i in range(steps):
            # 使用缓动函数
            progress = i / steps
            # 随机添加抖动
            jitter_x = random.uniform(-5, 5)
            jitter_y = random.uniform(-5, 5)

            x = from_x + (to_x - from_x) * progress + jitter_x
            y = from_y + (to_y - from_y) * progress + jitter_y

            await page.mouse.move(int(x), int(y))
            await asyncio.sleep(0.01)

    @staticmethod
    async def human_click(page, selector: str, offset: tuple = None):
        """模拟人类点击"""
        try:
            element = await page.query_selector(selector)
            if element:
                box = await element.bounding_box()
                if box:
                    if offset:
                        x = box['x'] + box['width']/2 + offset[0]
                        y = box['y'] + box['height']/2 + offset[1]
                    else:
                        x = box['x'] + box['width']/2 + random.randint(-10, 10)
                        y = box['y'] + box['height']/2 + random.randint(-10, 10)

                    # 鼠标悬停
                    await page.mouse.move(int(x), int(y))
                    await asyncio.sleep(random.uniform(0.1, 0.3))

                    # 点击
                    await page.mouse.click(int(x), int(y))
                    logger.info(f"点击元素: {selector}")
                    return True
        except Exception as e:
            logger.warning(f"点击失败 {selector}: {e}")
        return False

    @staticmethod
    async def human_scroll(page, direction: str = 'down', amount: int = None):
        """模拟人类滚动"""
        if amount is None:
            amount = random.randint(300, 800)

        scroll_amount = amount if direction == 'down' else -amount

        await page.evaluate(f'''
            window.scrollBy({{
                top: {scroll_amount},
                behavior: 'smooth'
            }})
        ''')
        await asyncio.sleep(random.uniform(0.3, 0.8))

    @staticmethod
    async def human_typing(page, text: str, delay_range: tuple = (0.05, 0.15)):
        """模拟人类打字"""
        for char in text:
            await page.keyboard.type(char)
            await asyncio.sleep(random.uniform(*delay_range))


class MysteelScraper:
    """ mysteeel 价格爬虫"""

    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self.human = HumanBehavior()

    async def init_browser(self):
        """初始化浏览器（反检测配置）"""
        logger.info("初始化浏览器...")

        playwright = await async_playwright().start()

        # 创建反检测浏览器
        self.browser = await playwright.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-infobars',
                '--window-size=1920,1080',
                '--start-maximized',
            ]
        )

        # 创建上下文
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            locale='zh-CN',
            timezone_id='Asia/Shanghai',
            permissions=['geolocation'],
            # 随机 User-Agent
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )

        # 添加反检测脚本
        await self.context.add_init_script('''
            // 移除 webdriver 属性
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });

            // 修改 chrome 对象
            window.chrome = {
                runtime: {}
            };

            // 添加随机的插件
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });

            // 修改 languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['zh-CN', 'zh', 'en-US', 'en']
            });

            // 随机化硬件并发
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => Math.floor(Math.random() * 4) + 4
            });

            // 禁用检测
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
        ''')

        self.page = await self.context.new_page()

        logger.info("浏览器初始化完成")
        return True

    async def login(self) -> bool:
        """登录 mysteeel（简化版）"""
        logger.info("开始登录...")

        try:
            # 访问登录页面
            await self.page.goto('https://passport.mysteel.com/',
                               wait_until='domcontentloaded',
                               timeout=60000)
            await asyncio.sleep(3)

            # 直接使用 JavaScript 填写表单
            logger.info("填写登录表单...")
            await self.page.evaluate(f'''
                () => {{
                    // 查找输入框
                    const inputs = document.querySelectorAll('input');
                    for (const inp of inputs) {{
                        const ph = inp.placeholder || '';
                        if (ph.includes('用户名') || ph.includes('账号')) {{
                            inp.value = '{USERNAME}';
                            inp.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        }}
                        if (ph.includes('密码') || inp.type === 'password') {{
                            inp.value = '{PASSWORD}';
                            inp.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        }}
                    }}
                }}
            ''')
            await asyncio.sleep(1)

            # 尝试点击登录按钮
            logger.info("点击登录按钮...")
            try:
                await self.page.click('.form-button-login')
            except:
                # 尝试其他可能的选择器
                await self.page.evaluate('''
                    () => {{
                        const btn = document.querySelector('button[type="submit"], .login-btn, .form-submit, input[type="submit"]');
                        if (btn) btn.click();
                    }}
                ''')

            # 等待登录完成
            logger.info("等待登录完成...")
            await asyncio.sleep(10)

            # 检查登录状态
            current_url = self.page.url
            logger.info(f"当前URL: {current_url}")

            if 'passport' not in current_url:
                logger.info("登录成功!")
                return True
            else:
                # 再等待一下，可能需要重定向
                await asyncio.sleep(5)
                current_url = self.page.url
                if 'passport' not in current_url:
                    logger.info("登录成功!")
                    return True
                else:
                    logger.warning("登录可能失败，尝试继续...")
                    return True  # 继续尝试，因为可能已经登录

        except Exception as e:
            logger.error(f"登录错误: {e}")
            return False

    async def wait_for_price_data(self, timeout: int = 45) -> bool:
        """等待价格数据加载（带人类行为模拟）"""
        logger.info("等待价格数据加载...")

        start_time = time.time()
        check_count = 0

        while time.time() - start_time < timeout:
            check_count += 1

            # 人类行为：随机滚动
            if check_count % 3 == 0:
                direction = random.choice(['up', 'down'])
                await self.human.human_scroll(self.page, direction, random.randint(200, 500))

            # 检查是否有价格数据
            has_data = await self.page.evaluate('''
                () => {
                    // 检查价格单元格
                    const priceCells = document.querySelectorAll('td[data-type="price"]');
                    for (const cell of priceCells) {
                        const text = cell.textContent.trim();
                        if (text && text.match(/^\\d{4}$/)) {
                            return true;
                        }
                    }
                    // 也检查表格行
                    const rows = document.querySelectorAll('#marketTable tr');
                    for (const row of rows) {
                        const cells = row.querySelectorAll('td');
                        for (const cell of cells) {
                            const text = cell.textContent.trim();
                            if (text && text.match(/^\\d{4}$/) && parseInt(text) > 3000) {
                                return true;
                            }
                        }
                    }
                    return false;
                }
            ''')

            if has_data:
                logger.info("检测到价格数据!")
                return True

            await self.human.random_delay_async(2, 4)

        logger.warning("等待价格数据超时")
        return False

    async def try_decrypt_prices(self) -> List[Dict]:
        """尝试解密价格数据"""
        logger.info("尝试解密价格...")

        # 方法1: 触发页面事件
        logger.info("方法1: 触发页面事件...")
        await self.page.evaluate('''
            () => {
                // 尝试触发各种事件
                const events = ['DOMContentLoaded', 'load', 'scroll', 'resize', 'visibilitychange'];
                events.forEach(e => document.dispatchEvent(new Event(e)));

                // 触发表格更新
                const table = document.getElementById('marketTable');
                if (table) {
                    table.dispatchEvent(new Event('update'));
                    table.dispatchEvent(new Event('refresh'));
                    table.dispatchEvent(new Event('recalculate'));
                }

                // 尝试调用解密函数
                if (typeof decryptAll === 'function') decryptAll();
                if (typeof decodePrice === 'function') decodePrice();
                if (typeof showPrice === 'function') showPrice();
            }
        ''')
        await self.human.random_delay_async(3, 5)

        # 方法2: 模拟悬停
        logger.info("方法2: 模拟悬停...")
        await self.page.evaluate('''
            () => {
                const cells = document.querySelectorAll('td[data-encrypt="true"]');
                cells.forEach(cell => {
                    const event = new MouseEvent('mouseover', {
                        bubbles: true,
                        cancelable: true,
                        view: window
                    });
                    cell.dispatchEvent(event);
                });
            }
        ''')
        await self.human.random_delay_async(2, 4)

        # 方法3: 触发滚动到可见区域
        logger.info("方法3: 滚动到可见区域...")
        await self.page.evaluate('''
            () => {
                const table = document.getElementById('marketTable');
                if (table) {
                    table.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }

                // 触发IntersectionObserver
                const cells = document.querySelectorAll('td[data-type="price"]');
                cells.forEach(cell => {
                    cell.scrollIntoView();
                });
            }
        ''')
        await self.human.random_delay_async(2, 4)

        # 最终检查
        prices = await self.extract_prices()
        return prices

    async def extract_prices(self) -> List[Dict]:
        """提取价格数据"""
        prices = await self.page.evaluate('''
            () => {
                const results = [];
                const tables = document.querySelectorAll('table');

                tables.forEach((table) => {
                    const rows = table.querySelectorAll('tr');
                    rows.forEach((row) => {
                        const cells = row.querySelectorAll('td');
                        if (cells.length >= 5) {
                            const rowData = [];
                            cells.forEach(c => rowData.push(c.textContent.trim()));

                            // 检查是否是钢筋数据行
                            const materialNames = ['高线', '螺纹钢', '盘螺', '圆钢'];
                            const hasMaterial = materialNames.some(name => rowData.some(cell => cell.includes(name)));

                            if (hasMaterial) {
                                // 提取数据
                                for (let i = 0; i < rowData.length; i++) {
                                    const cell = rowData[i];
                                    // 检查是否是4位数价格
                                    const priceMatch = cell.match(/^(\\d{4})$/);
                                    if (priceMatch) {
                                        const price = parseInt(priceMatch[1]);
                                        if (price > 3000 && price < 6000) {
                                            results.push({
                                                name: rowData[0] || '',
                                                spec: rowData[1] || '',
                                                material_type: rowData[2] || '',
                                                brand: rowData[3] || '',
                                                price: price
                                            });
                                            break;
                                        }
                                    }
                                }
                            }
                        }
                    });
                });

                return results;
            }
        ''')

        return prices

    async def fetch_date(self, date: str, period: str = 'AM') -> Dict:
        """抓取指定日期的数据"""
        logger.info(f"抓取 {date} {period} 数据...")

        # 生成URL
        date_part = date.replace('-', '')[2:]  # YYMMDD
        hour = '10' if period == 'AM' else '16'
        url = f'https://jiancai.mysteel.com/m/{date_part}{hour}/placeholder.html'

        try:
            # 人类行为：先滚动到页面顶部
            await self.page.evaluate('window.scrollTo(0, 0)')
            await self.human.random_delay_async(0.5, 1)

            # 访问页面
            await self.page.goto(url, wait_until='domcontentloaded', timeout=60000)

            # 人类行为：随机滚动
            await self.human.human_scroll(self.page, 'down', random.randint(300, 600))
            await self.human.human_scroll(self.page, 'up', random.randint(100, 300))

            # 等待价格数据
            await self.wait_for_price_data()

            # 尝试解密
            prices = await self.try_decrypt_prices()

            # 如果还是空的，再等待一下
            if not prices:
                logger.info("第一次解密失败，再次尝试...")
                await self.human.random_delay_async(5, 10)
                await self.human.human_scroll(self.page, 'down', 500)
                await self.wait_for_price_data(30)
                prices = await self.try_decrypt_prices()

            # 截图保存
            date_str = date.replace('-', '')
            screenshot_path = DATA_DIR / f'screenshots/{date_str}_{period}.png'
            screenshot_path.parent.mkdir(exist_ok=True)
            await self.page.screenshot(path=str(screenshot_path), full_page=True)

            result = {
                'date': date,
                'period': period,
                'prices': prices,
                'count': len(prices),
                'screenshot': str(screenshot_path)
            }

            logger.info(f"抓取完成: {len(prices)} 条数据")
            return result

        except Exception as e:
            logger.error(f"抓取 {date} {period} 失败: {e}")
            return {
                'date': date,
                'period': period,
                'prices': [],
                'count': 0,
                'error': str(e)
            }

    async def save_to_database(self, result: Dict):
        """保存到数据库"""
        if not result['prices']:
            return 0

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        inserted = 0
        for price in result['prices']:
            try:
                cursor.execute('''
                    INSERT OR IGNORE INTO rebar_prices
                    (date, fetch_time, material_name, spec, material_type, brand, price, region)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    result['date'],
                    result['period'],
                    price['name'],
                    price['spec'],
                    price['material_type'],
                    price['brand'],
                    price['price'],
                    '山东烟台'
                ))
                if cursor.rowcount > 0:
                    inserted += 1
            except Exception as e:
                pass

        conn.commit()
        conn.close()

        logger.info(f"保存到数据库: {inserted} 条")
        return inserted

    async def close(self):
        """关闭浏览器"""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()


async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='高级 mysteeel 价格爬虫')
    parser.add_argument('--start', '-s', default='2024-01-01', help='开始日期')
    parser.add_argument('--end', '-e', default=None, help='结束日期')
    parser.add_argument('--limit', '-l', type=int, default=10, help='限制抓取天数')
    parser.add_argument('--delay', '-d', type=int, default=30, help='抓取间隔(秒)')

    args = parser.parse_args()
    end_date = args.end or datetime.now().strftime('%Y-%m-%d')

    logger.info("=" * 60)
    logger.info("高级 mysteeel 价格爬虫")
    logger.info(f"日期范围: {args.start} 至 {end_date}")
    logger.info(f"抓取限制: {args.limit} 天")
    logger.info(f"抓取间隔: {args.delay} 秒")
    logger.info("=" * 60)

    # 生成日期列表
    dates = []
    current = datetime.strptime(args.start, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')

    while current <= end and len(dates) < args.limit:
        if current.weekday() < 5:  # 工作日
            dates.append(current.strftime('%Y-%m-%d'))
        current += timedelta(days=1)

    logger.info(f"需要抓取 {len(dates)} 个工作日")

    # 初始化爬虫
    scraper = MysteelScraper()

    try:
        # 初始化浏览器
        await scraper.init_browser()

        # 登录
        if not await scraper.login():
            logger.error("登录失败，退出")
            return

        # 抓取数据
        total_inserted = 0
        success_count = 0

        for i, date in enumerate(dates):
            logger.info(f"\n[{i+1}/{len(dates)}] 抓取 {date}")

            # AM
            result_am = await scraper.fetch_date(date, 'AM')
            await scraper.save_to_database(result_am)
            if result_am['count'] > 0:
                success_count += 1

            # 随机延迟
            delay = random.uniform(args.delay * 0.8, args.delay * 1.2)
            logger.info(f"等待 {delay:.1f} 秒...")
            await asyncio.sleep(delay)

            # PM
            result_pm = await scraper.fetch_date(date, 'PM')
            await scraper.save_to_database(result_pm)

            if i < len(dates) - 1:
                await asyncio.sleep(args.delay)

        logger.info("\n" + "=" * 60)
        logger.info("抓取完成")
        logger.info(f"成功: {success_count}/{len(dates)} 天")
        logger.info(f"总记录: {total_inserted} 条")
        logger.info("=" * 60)

    except KeyboardInterrupt:
        logger.info("用户中断")
    finally:
        await scraper.close()


if __name__ == '__main__':
    asyncio.run(main())
