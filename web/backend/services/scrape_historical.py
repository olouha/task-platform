"""
批量抓取 mysteeel 历史价格数据
从已获取的历史链接列表中抓取价格数据
"""
import asyncio
import logging
import re
import sqlite3
import os
from pathlib import Path
from typing import List, Dict, Optional

from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Mysteel凭据 - 从环境变量或使用默认值
MYSTEEL_USERNAME = os.environ.get('MYSTEEL_USERNAME', 'M6616592358')
MYSTEEL_PASSWORD = os.environ.get('MYSTEEL_PASSWORD', 'panhui199261')

# 数据库和链接文件路径
DB_FILE = Path(__file__).parent / 'data' / 'yantai_rebar.db'
LINKS_FILE = Path(__file__).parent / 'data' / 'all_historical_links.txt'


class HistoricalScraper:
    """历史数据批量抓取器"""

    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self.username = MYSTEEL_USERNAME
        self.password = MYSTEEL_PASSWORD

    async def init_browser(self):
        """初始化浏览器"""
        logger.info("初始化浏览器...")

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
        )

        # 反检测
        await self.context.add_init_script('''
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
        ''')

        self.page = await self.context.new_page()
        logger.info("浏览器初始化完成")
        return True

    async def login(self) -> bool:
        """登录 mysteeel"""
        logger.info("开始登录...")

        try:
            await self.page.goto('https://passport.mysteel.com/',
                               wait_until='networkidle', timeout=60000)
            await asyncio.sleep(3)

            await self.page.click('.form-tab-account')
            await asyncio.sleep(1)
            await self.page.fill('.form-content-username input', self.username)
            await asyncio.sleep(0.5)
            await self.page.fill('.form-content-password input', self.password)
            await asyncio.sleep(0.5)
            await self.page.click('.form-button-login')

            logger.info("等待登录完成...")
            await asyncio.sleep(10)

            if 'passport' not in self.page.url:
                logger.info(f"登录成功: {self.page.url}")
                return True

            logger.warning(f"登录可能失败: {self.page.url}")
            return False

        except Exception as e:
            logger.error(f"登录错误: {e}", exc_info=True)
            return False

    async def extract_prices(self) -> List[Dict]:
        """从页面提取价格数据"""
        return await self.page.evaluate('''() => {
            const prices = [];
            const validTypes = ["高线", "螺纹钢", "盘螺", "圆钢"];

            const tables = document.querySelectorAll("table");
            tables.forEach(table => {
                const rows = table.querySelectorAll("tr");
                rows.forEach(row => {
                    const cells = row.querySelectorAll("td");
                    const cellTexts = Array.from(cells).map(c => c.textContent?.trim() || "");

                    const hasMaterial = cellTexts.some(t =>
                        validTypes.some(m => t.includes(m)));

                    if (hasMaterial) {
                        for (let i = 0; i < cellTexts.length; i++) {
                            const text = cellTexts[i];
                            if (/^\\d{4}$/.test(text)) {
                                const price = parseInt(text);
                                if (price >= 3000 && price <= 6000) {
                                    prices.push({
                                        material_type: cellTexts[0] || "",
                                        spec: cellTexts[1] || "",
                                        material_grade: cellTexts[2] || "",
                                        brand: cellTexts[3] || "",
                                        price: price
                                    });
                                    break;
                                }
                            }
                        }
                    }
                });
            });

            return prices;
        }''')

    async def fetch_one(self, url: str) -> Dict:
        """抓取单个URL"""
        try:
            response = await self.page.goto(url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(10)

            if response and response.status == 200:
                # 从URL提取日期
                match = re.search(r'/m/(\d{8})/', url)
                date = f"20{match.group(1)[:6]}" if match else ""
                period = "AM" if url.endswith("10/") else "PM"

                prices = await self.extract_prices()

                return {
                    'date': date,
                    'period': period,
                    'url': url,
                    'prices': prices,
                    'count': len(prices),
                    'status': 'success'
                }
            else:
                return {
                    'url': url,
                    'status': 'failed',
                    'status_code': response.status if response else 0
                }

        except Exception as e:
            return {
                'url': url,
                'status': 'error',
                'error': str(e)[:100]
            }

    def save_to_db(self, result: Dict) -> int:
        """保存到数据库"""
        if result['status'] != 'success' or not result.get('prices'):
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
                pass

        conn.commit()
        conn.close()
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

    parser = argparse.ArgumentParser(description='批量抓取历史价格数据')
    parser.add_argument('--limit', '-l', type=int, default=0, help='限制抓取数量，0=全部')
    parser.add_argument('--delay', '-d', type=int, default=15, help='间隔秒数')
    parser.add_argument('--year', '-y', type=str, default=None, help='只抓取指定年份，如 2024')

    args = parser.parse_args()

    # 读取链接列表
    if not LINKS_FILE.exists():
        logger.error(f"链接文件不存在: {LINKS_FILE}")
        return

    with open(LINKS_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # 解析链接
    links = []
    for line in lines:
        if '|' in line:
            url = line.split('|')[1].strip()
            # 按年份筛选
            match = re.search(r'/m/(\d{8})/', url)
            if match:
                year = f"20{match.group(1)[:2]}"
                if args.year is None or args.year == year:
                    links.append(url)

    if args.limit > 0:
        links = links[:args.limit]

    logger.info(f"待抓取: {len(links)} 个URL")

    # 初始化爬虫
    scraper = HistoricalScraper()

    try:
        await scraper.init_browser()

        if not await scraper.login():
            logger.error("登录失败")
            return

        # 抓取
        success = 0
        failed = 0
        total_inserted = 0

        for i, url in enumerate(links):
            logger.info(f"[{i+1}/{len(links)}] 抓取: {url[:80]}")

            result = await scraper.fetch_one(url)

            if result['status'] == 'success':
                success += 1
                inserted = scraper.save_to_db(result)
                total_inserted += inserted
                logger.info(f"  成功: {result['count']}条数据, 新增{inserted}条")
            else:
                failed += 1
                logger.warning(f"  失败: {result.get('status')}")

            # 间隔
            if i < len(links) - 1:
                await asyncio.sleep(args.delay)

        logger.info("\n" + "=" * 50)
        logger.info("抓取完成")
        logger.info(f"成功: {success}, 失败: {failed}")
        logger.info(f"新增记录: {total_inserted} 条")
        logger.info("=" * 50)

    except KeyboardInterrupt:
        logger.info("用户中断")
    finally:
        await scraper.close()


if __name__ == '__main__':
    asyncio.run(main())
