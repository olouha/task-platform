"""
mysteeel 价格爬虫 - 基于 innerText 解析
通过分析 innerText 获取编码后的价格数据
"""
import asyncio
import logging
import re
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional

from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

USERNAME = 'M6616592358'
PASSWORD = 'panhui199261'
DB_FILE = Path('services/data/yantai_rebar.db')


class PriceParser:
    """价格解析器 - 从页面DOM提取数据"""

    @staticmethod
    def extract_prices_from_page(page) -> List[Dict]:
        """从页面DOM直接提取价格数据"""
        return page.evaluate('''() => {
            const prices = [];
            const validTypes = ['高线', '螺纹钢', '盘螺', '圆钢'];

            // 获取所有表格
            const tables = document.querySelectorAll('table');
            tables.forEach(table => {
                const rows = table.querySelectorAll('tr');
                rows.forEach(row => {
                    const cells = row.querySelectorAll('td');
                    if (cells.length < 4) return;

                    // 收集行的所有文本
                    const cellTexts = Array.from(cells).map(c => c.textContent?.trim() || '');

                    // 查找是否包含有效材料类型
                    const firstCell = cellTexts[0];
                    const materialType = validTypes.find(t => firstCell.includes(t)) || validTypes.find(t => cellTexts.some(c => c.includes(t)));

                    if (materialType) {
                        // 查找价格单元格 - 找 data-type="price" 的td
                        const priceCells = row.querySelectorAll('td[data-type="price"]');

                        priceCells.forEach(priceCell => {
                            const priceText = priceCell.textContent?.trim() || '';
                            // 价格应该是4位数字
                            if (/^\\d{4}$/.test(priceText)) {
                                const price = parseInt(priceText);
                                if (price >= 3000 && price <= 6000) {
                                    // 尝试获取同行的其他信息
                                    const spec = cellTexts[1] || '';
                                    const grade = cellTexts[2] || '';
                                    const brand = cellTexts[3] || '';

                                    prices.push({
                                        material_type: materialType,
                                        spec: spec,
                                        material_grade: grade,
                                        brand: brand,
                                        price: price
                                    });
                                }
                            }
                        });

                        // 如果没有找到 data-type="price" 的单元格，尝试从普通单元格找4位数字
                        if (priceCells.length === 0) {
                            for (const cellText of cellTexts) {
                                if (/^\\d{4}$/.test(cellText)) {
                                    const price = parseInt(cellText);
                                    if (price >= 3000 && price <= 6000) {
                                        prices.push({
                                            material_type: materialType,
                                            spec: cellTexts[1] || '',
                                            material_grade: cellTexts[2] || '',
                                            brand: cellTexts[3] || '',
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

            return prices;
        }''')

    @staticmethod
    def parse_encoded_price(text: str) -> Optional[int]:
        """解析编码后的价格"""
        if not text:
            return None

        text = text.strip()

        # 模式1: 纯数字编码如 "37003" -> 3700.3
        if re.match(r'^(\d{4,6})$', text):
            num = int(text)
            # 如果是5位或6位数字，可能是价格编码
            if 30000 <= num <= 60000:
                return int(num / 10)  # 去掉最后一位
            elif num > 100000:
                return int(num / 100)  # 可能是 37003 格式

        # 模式2: 带分隔符 "212/37003"
        if '/' in text:
            parts = text.split('/')
            for part in parts:
                result = PriceParser.parse_encoded_price(part)
                if result and 3000 <= result <= 6000:
                    return result

        # 模式3: 直接价格 "4350"
        if re.match(r'^\d{4}$', text):
            num = int(text)
            if 3000 <= num <= 6000:
                return num

        # 模式4: 规格价格 "Φ12:4350"
        match = re.search(r'(\d{4})', text)
        if match:
            num = int(match.group(1))
            if 3000 <= num <= 6000:
                return num

        return None

    @staticmethod
    def parse_material_line(line: str) -> Optional[Dict]:
        """解析材料行文本"""
        # 分割成字段
        fields = [f.strip() for f in line.split('\t') if f.strip()]
        if len(fields) < 4:
            return None

        material_type = fields[0] if fields[0] else None
        spec = fields[1] if len(fields) > 1 else None
        material_grade = fields[2] if len(fields) > 2 else None
        brand = fields[3] if len(fields) > 3 else None

        # 检查是否是需要的价格类型
        valid_types = ['高线', '螺纹钢', '盘螺', '圆钢']
        if material_type not in valid_types:
            return None

        # 解析价格
        price = None
        for field in fields:
            price = PriceParser.parse_encoded_price(field)
            if price:
                break

        if not price:
            return None

        return {
            'material_type': material_type,
            'spec': spec,
            'material_grade': material_grade,
            'brand': brand,
            'price': price
        }


class MysteelTextScraper:
    """基于 innerText 的 mysteeel 价格爬虫"""

    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None

    async def init_browser(self):
        """初始化浏览器"""
        logger.info("[init_browser] 初始化浏览器...")

        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
            ]
        )

        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            locale='zh-CN',
            timezone_id='Asia/Shanghai',
        )

        # 反检测脚本
        await self.context.add_init_script('''
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
        ''')

        self.page = await self.context.new_page()
        logger.info("[init_browser] 浏览器初始化完成")
        return True

    async def login(self) -> bool:
        """登录 mysteeel"""
        logger.info("[login] 开始登录...")

        try:
            await self.page.goto('https://passport.mysteel.com/',
                               wait_until='networkidle', timeout=60000)

            await asyncio.sleep(3)

            # 点击切换到账号登录标签
            await self.page.click('.form-tab-account')
            await asyncio.sleep(1)

            # 输入用户名
            await self.page.fill('.form-content-username input', USERNAME)
            await asyncio.sleep(0.5)

            # 输入密码
            await self.page.fill('.form-content-password input', PASSWORD)
            await asyncio.sleep(0.5)

            # 查找并点击登录按钮
            login_btn = await self.page.query_selector('.form-button-login')
            if login_btn:
                await login_btn.click()
                logger.info("[login] 点击了登录按钮 .form-button-login")

            logger.info("[login] 等待登录完成...")
            await asyncio.sleep(10)

            current_url = self.page.url
            if 'passport' not in current_url:
                logger.info(f"[login] 登录成功，当前URL: {current_url}")
                return True

            logger.warning(f"[login] 登录可能失败，当前URL: {current_url}")
            return False

        except Exception as e:
            logger.error(f"[login] 登录错误: {e}", exc_info=True)
            return False

    async def get_price_url(self) -> Optional[Dict]:
        """从首页获取今日价格页面的URL"""
        try:
            # 访问烟台首页
            await self.page.goto('https://yantai.mysteel.com/',
                               wait_until='networkidle', timeout=60000)
            await asyncio.sleep(10)

            # 找到今日价格行情链接
            result = await self.page.evaluate('''() => {
                const links = [];
                const today = new Date();
                const yearShort = String(today.getFullYear()).slice(-2);
                const month = String(today.getMonth() + 1).padStart(2, '0');
                const day = String(today.getDate()).padStart(2, '0');
                const todayStr = month + '-' + day;

                document.querySelectorAll('a[href]').forEach(a => {
                    const text = a.textContent?.trim() || '';
                    const href = a.href;

                    // 找建筑钢材价格行情链接
                    // 文本格式: "5月29日烟台市场建筑钢材价格行情"
                    if (href.includes('jiancai.mysteel.com/m/') &&
                        text.includes('烟台') && text.includes('建筑钢材')) {

                        if (text.includes(todayStr) || href.includes(yearShort + month + day)) {
                            links.unshift({href, text, priority: 1});
                        } else if (href.includes('/26')) {
                            links.push({href, text, priority: 2});
                        }
                    }
                });

                links.sort((a, b) => a.priority - b.priority);
                return links.slice(0, 5);
            }''')

            if result and len(result) > 0:
                logger.info(f"[get_price_url] 找到 {len(result)} 个链接")
                return result[0]

            logger.warning("[get_price_url] 未找到符合条件的链接")
            return None

        except Exception as e:
            logger.error(f"[get_price_url] 获取URL失败: {e}", exc_info=True)
            return None

    async def fetch_today(self) -> Dict:
        """抓取今日数据"""
        logger.info("[fetch_today] 抓取今日数据...")

        try:
            # 获取今日价格URL
            link_info = await self.get_price_url()

            if not link_info:
                logger.warning("[fetch_today] 未找到今日价格链接")
                return {'date': datetime.now().strftime('%Y-%m-%d'), 'prices': [], 'count': 0}

            url = link_info['href']
            logger.info(f"[fetch_today] 访问: {url}")

            await self.page.goto(url, wait_until='domcontentloaded', timeout=60000)
            await asyncio.sleep(15)

            # 从DOM提取价格数据
            prices = await PriceParser.extract_prices_from_page(self.page)

            # 截图保存
            today = datetime.now().strftime('%Y%m%d')
            screenshot_path = Path(f'services/data/screenshots/today_{today}.png')
            screenshot_path.parent.mkdir(exist_ok=True)
            await self.page.screenshot(path=str(screenshot_path), full_page=True)

            result = {
                'date': datetime.now().strftime('%Y-%m-%d'),
                'period': 'AM',
                'prices': prices,
                'count': len(prices),
                'url': url
            }

            logger.info(f"[fetch_today] 抓取完成: {len(prices)} 条数据")
            return result

        except Exception as e:
            logger.error(f"[fetch_today] 抓取失败: {e}", exc_info=True)
            return {'date': datetime.now().strftime('%Y-%m-%d'), 'prices': [], 'count': 0, 'error': str(e)}

    async def fetch_date(self, date: str, period: str = 'AM') -> Dict:
        """抓取指定日期的数据"""
        logger.info(f"[fetch_date] 抓取 {date} {period}...")

        # 正确的URL格式: /m/YYMMDDHH/contentHash.html
        date_str = date.replace('-', '')
        year = date_str[:4]
        month = date_str[4:6]
        day = date_str[6:8]
        hour = '10' if period == 'AM' else '16'

        # 烟台钢筋页面的固定hash (从已有数据获取)
        content_hash = '1BD5F502DA9E50F8'

        # 构建URL
        url = f'https://jiancai.mysteel.com/m/{year[2:]}{month}{day}{hour}/{content_hash}.html'
        logger.info(f"[fetch_date] 访问URL: {url}")

        try:
            response = await self.page.goto(url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(20)  # 等待JS执行

            if response and response.status == 200:
                # 从DOM直接提取价格数据
                prices = await PriceParser.extract_prices_from_page(self.page)

                if prices:
                    logger.info(f"[fetch_date] 从DOM提取到 {len(prices)} 条价格数据")
                else:
                    logger.warning(f"[fetch_date] DOM中未找到价格数据，尝试innerText")

                    # 备用: 从innerText解析
                    page_text = await self.page.evaluate('() => document.body.innerText')
                    lines = page_text.split('\n')
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                        if any(k in line for k in ['高线', '螺纹钢', '盘螺', '圆钢']):
                            parsed = PriceParser.parse_material_line(line)
                            if parsed:
                                prices.append(parsed)

                # 截图保存
                screenshot_path = Path(f'services/data/screenshots/text_{date_str}_{period}.png')
                screenshot_path.parent.mkdir(exist_ok=True)
                await self.page.screenshot(path=str(screenshot_path), full_page=True)

                result = {
                    'date': date,
                    'period': period,
                    'prices': prices,
                    'count': len(prices),
                    'url': url
                }
            else:
                result = {
                    'date': date,
                    'period': period,
                    'prices': [],
                    'count': 0,
                    'error': f'HTTP {response.status if response else "No response"}'
                }

        except Exception as e:
            logger.error(f"[fetch_date] 抓取失败: {e}", exc_info=True)
            result = {
                'date': date,
                'period': period,
                'prices': [],
                'count': 0,
                'error': str(e)
            }

        logger.info(f"[fetch_date] 抓取完成: {result['count']} 条数据")
        return result

    def save_to_database(self, result: Dict) -> int:
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
                    price['material_type'],
                    price['spec'],
                    price['material_grade'],
                    price['brand'],
                    price['price'],
                    '山东烟台'
                ))
                if cursor.rowcount > 0:
                    inserted += 1
            except Exception as e:
                logger.error(f"[save_to_database] 保存失败: {e}")

        conn.commit()
        conn.close()

        logger.info(f"[save_to_database] 保存完成: {inserted} 条")
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

    parser = argparse.ArgumentParser(description='mysteeel 价格爬虫')
    parser.add_argument('--start', '-s', default='2024-02-12', help='开始日期')
    parser.add_argument('--end', '-e', default=None, help='结束日期')
    parser.add_argument('--limit', '-l', type=int, default=3, help='限制抓取天数')
    parser.add_argument('--delay', '-d', type=int, default=30, help='抓取间隔(秒)')

    args = parser.parse_args()
    end_date = args.end or datetime.now().strftime('%Y-%m-%d')

    logger.info("=" * 60)
    logger.info("mysteeel 价格爬虫 (innerText版)")
    logger.info(f"日期范围: {args.start} 至 {end_date}")
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

    scraper = MysteelTextScraper()

    try:
        await scraper.init_browser()

        if not await scraper.login():
            logger.error("[main] 登录失败，退出")
            return

        total_inserted = 0
        success_count = 0

        for i, date in enumerate(dates):
            logger.info(f"\n[{i+1}/{len(dates)}] 抓取 {date}")

            # AM
            result_am = await scraper.fetch_date(date, 'AM')
            inserted_am = scraper.save_to_database(result_am)
            total_inserted += inserted_am
            if result_am['count'] > 0:
                success_count += 1

            await asyncio.sleep(args.delay)

            # PM
            result_pm = await scraper.fetch_date(date, 'PM')
            inserted_pm = scraper.save_to_database(result_pm)
            total_inserted += inserted_pm

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