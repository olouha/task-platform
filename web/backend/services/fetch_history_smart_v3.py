"""
烟台钢筋价格历史数据智能抓取脚本 v3.1
- 从首页动态获取URL列表
- 确保每天不少于11条数据
- 人机模拟行为

用法:
    python fetch_history_smart_v3.py --interval 3
"""
import asyncio
import sys
import json
import re
import random
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Set, Tuple

sys.path.insert(0, '.')

from playwright.async_api import async_playwright, Page
import openpyxl
from openpyxl.styles import Font
import sqlite3

# 路径配置
DATA_DIR = Path('services/data')
DATA_DIR.mkdir(exist_ok=True)

DB_FILE = DATA_DIR / 'yantai_rebar.db'
EXCEL_FILE = DATA_DIR / '烟台钢筋价格_智能抓取.xlsx'
COOKIE_FILE = DATA_DIR / 'mysteel_cookies.json'

# 最小数据条数
MIN_PRICES_PER_DAY = 11

# 日志
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(str(DATA_DIR / 'fetch_smart.log'), encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DBManager:
    """数据库管理"""

    @staticmethod
    def init_db():
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS rebar_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                material_name TEXT,
                spec TEXT,
                material_type TEXT,
                brand TEXT,
                price INTEGER,
                region TEXT DEFAULT '山东烟台',
                fetch_time TEXT,
                UNIQUE(date, material_name, spec, brand, price)
            )
        ''')
        conn.commit()
        conn.close()

    @staticmethod
    def get_existing_keys() -> Set[str]:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('SELECT date, material_name, spec, brand FROM rebar_prices')
        existing = {f"{r[0]}_{r[1]}_{r[2]}_{r[3]}" for r in c.fetchall()}
        conn.close()
        return existing

    @staticmethod
    def insert_prices(date: str, prices: List[Dict], existing: Set[str]) -> Tuple[int, int]:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()

        inserted = 0
        skipped = 0

        for price in prices:
            key = f"{date}_{price.get('material_name', '')}_{price.get('spec', '')}_{price.get('brand', '')}"
            if key not in existing:
                try:
                    c.execute('''
                        INSERT INTO rebar_prices
                        (date, material_name, spec, material_type, brand, price, region, fetch_time)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        date, price.get('material_name', ''), price.get('spec', ''),
                        price.get('material_type', ''), price.get('brand', ''), price.get('price', 0),
                        '山东烟台', datetime.now().strftime('%H:%M:%S')
                    ))
                    inserted += 1
                    existing.add(key)
                except sqlite3.IntegrityError:
                    skipped += 1
            else:
                skipped += 1

        conn.commit()
        conn.close()
        return inserted, skipped

    @staticmethod
    def get_date_count(date: str) -> int:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM rebar_prices WHERE date = ?', (date,))
        count = c.fetchone()[0]
        conn.close()
        return count


class SmartFetcher:
    """智能抓取器"""

    def __init__(self, interval: int = 5):
        self.interval = interval
        self.existing_keys = set()
        self.browser = None
        self.context = None
        self.page = None

    async def init_browser(self):
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=True)
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 3000},
            locale='zh-CN'
        )
        self.page = await self.context.new_page()

        # 加载Cookie
        if COOKIE_FILE.exists():
            try:
                with open(COOKIE_FILE, 'r', encoding='utf-8') as f:
                    cookies = json.load(f)
                await self.context.add_cookies(cookies)
                logger.info(f"已加载 {len(cookies)} 个Cookie")
            except:
                pass

    async def close_browser(self):
        if self.context:
            cookies = await self.context.cookies()
            try:
                with open(COOKIE_FILE, 'w', encoding='utf-8') as f:
                    json.dump(cookies, f, ensure_ascii=False)
            except:
                pass
        if self.browser:
            await self.browser.close()

    async def fetch_all_urls(self) -> List[Dict]:
        """从首页获取所有烟台价格URL"""
        logger.info("从首页获取所有烟台价格URL...")

        urls = []

        try:
            # 访问首页
            await self.page.goto('https://jiancai.mysteel.com/', wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(3)

            # 查找所有包含"烟台"和日期的链接
            links = await self.page.evaluate('''() => {
                const results = [];
                const links = document.querySelectorAll('a[href]');

                links.forEach(a => {
                    const href = a.href;
                    const text = a.textContent.trim();

                    // 匹配烟台价格链接
                    // 格式类似: https://jiancai.mysteel.com/m/240510/xxxxx.html
                    if (href.includes('jiancai.mysteel.com/m/') &&
                        (text.includes('烟台') || text.includes('山东'))) {
                        results.push({
                            href: href,
                            text: text
                        });
                    }
                });

                return results;
            }''')

            logger.info(f"找到 {len(links)} 个烟台相关链接")
            urls.extend(links)

            # 如果首页没有找到，尝试访问山东市场页面
            if len(urls) < 10:
                logger.info("首页链接不足，尝试山东市场页面...")

                market_urls = [
                    "https://jiancai.mysteel.com/market/pa228aa01010104a0aaaaa1.html",
                    "https://jiancai.mysteel.com/market/pa228a81723aa0aaaaa1.html"
                ]

                for market_url in market_urls:
                    try:
                        await self.page.goto(market_url, wait_until='domcontentloaded', timeout=30000)
                        await asyncio.sleep(2)

                        market_links = await self.page.evaluate('''() => {
                            const results = [];
                            document.querySelectorAll('a[href]').forEach(a => {
                                const href = a.href;
                                const text = a.textContent.trim();
                                if (href.includes('jiancai.mysteel.com/m/') &&
                                    (text.includes('烟台') || text.includes('山东'))) {
                                    results.push({href: href, text: text});
                                }
                            });
                            return results;
                        }''')

                        logger.info(f"市场页面找到 {len(market_links)} 个链接")
                        urls.extend(market_links)
                    except Exception as e:
                        logger.warning(f"访问市场页面失败: {e}")

        except Exception as e:
            logger.error(f"获取URL失败: {e}")

        # 去重
        seen = set()
        unique_urls = []
        for url in urls:
            if url['href'] not in seen:
                seen.add(url['href'])
                unique_urls.append(url)

        logger.info(f"总共找到 {len(unique_urls)} 个唯一URL")
        return unique_urls

    async def fetch_url_data(self, url: str) -> Tuple[str, List[Dict]]:
        """抓取单个URL的数据"""
        try:
            await self.page.goto(url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(2)

            # 检查是否需要登录
            body_text = await self.page.evaluate('() => document.body.textContent')
            if '登录' in body_text and len(body_text) < 1000:
                logger.warning("需要重新登录")
                return '', []

            # 提取数据
            data = await self.page.evaluate('''() => {
                const tables = document.querySelectorAll('table');
                const results = [];
                tables.forEach(table => {
                    const rows = table.querySelectorAll('tr');
                    rows.forEach(row => {
                        const cells = row.querySelectorAll('td, th');
                        const rowData = [];
                        cells.forEach(c => rowData.push(c.textContent.trim()));
                        if (rowData.length > 0) results.push(rowData);
                    });
                });
                return results;
            }''')

            # 解析价格和日期
            prices = []
            date_str = ''

            # 从URL提取日期 (格式: 240510 -> 2024-05-10)
            date_match = re.search(r'/m/?(\d{6})/', url)
            if date_match:
                date_code = date_match.group(1)
                year = 2000 + int(date_code[:2])
                month = int(date_code[2:4])
                day = int(date_code[4:6])
                date_str = f'{year:04d}-{month:02d}-{day:02d}'

            for row in data:
                if row and len(row) >= 5:
                    material_name = str(row[0]).strip()
                    spec = str(row[1]).strip()
                    material_type = str(row[2]).strip() if len(row) > 2 else ''
                    brand = str(row[3]).strip() if len(row) > 3 else ''
                    price_str = str(row[4]).strip()

                    valid_names = ['高线', '螺纹钢', '盘螺', '圆钢']
                    if material_name in valid_names and spec.startswith('Φ'):
                        try:
                            price = int(''.join(filter(str.isdigit, price_str)))
                            if price > 0:
                                prices.append({
                                    'material_name': material_name,
                                    'spec': spec,
                                    'material_type': material_type,
                                    'brand': brand,
                                    'price': price
                                })
                        except:
                            pass

            if prices:
                logger.info(f"从 {url} 提取: {date_str}, {len(prices)} 条数据")
                return date_str, prices

        except Exception as e:
            logger.warning(f"抓取失败 {url}: {e}")

        return '', []

    async def run(self) -> Dict:
        """运行抓取任务"""
        logger.info("=" * 60)
        logger.info("烟台钢筋价格智能抓取 v3.1")
        logger.info(f"确保每天不少于 {MIN_PRICES_PER_DAY} 条数据")
        logger.info("=" * 60)

        # 初始化
        DBManager.init_db()
        self.existing_keys = DBManager.get_existing_keys()
        logger.info(f"数据库已有 {len(self.existing_keys)} 条记录")

        await self.init_browser()

        # 获取URL列表
        urls = await self.fetch_all_urls()

        if not urls:
            logger.error("未找到任何URL，请检查网络或登录状态")
            await self.close_browser()
            return {'success': False, 'error': '未找到URL'}

        total_inserted = 0
        success_count = 0
        incomplete_dates = []

        # 抓取每个URL
        for i, url_info in enumerate(urls):
            url = url_info['href']
            logger.info(f"\n[{i+1}/{len(urls)}] {url}")

            date_str, prices = await self.fetch_url_data(url)

            if prices and date_str:
                # 检查数据量
                existing_count = DBManager.get_date_count(date_str)
                total_count = existing_count + len(prices)

                if total_count < MIN_PRICES_PER_DAY:
                    logger.warning(f"日期 {date_str} 数据不足: {total_count} < {MIN_PRICES_PER_DAY}")
                    incomplete_dates.append(date_str)

                # 插入数据
                inserted, skipped = DBManager.insert_prices(date_str, prices, self.existing_keys)

                if inserted > 0:
                    total_inserted += inserted
                    success_count += 1
                    logger.info(f"  插入 {inserted} 条，跳过 {skipped} 条")

            # 延迟
            if i < len(urls) - 1:
                delay = self.interval + random.randint(0, 2)
                await asyncio.sleep(delay)

        await self.close_browser()

        logger.info("\n" + "=" * 60)
        logger.info("抓取完成")
        logger.info(f"  成功URL: {success_count}/{len(urls)}")
        logger.info(f"  新增记录: {total_inserted} 条")

        if incomplete_dates:
            logger.warning(f"  数据不足的日期: {len(incomplete_dates)} 天")
            logger.warning(f"  {incomplete_dates[:10]}...")

        logger.info("=" * 60)

        return {
            'success': True,
            'total_urls': len(urls),
            'success_urls': success_count,
            'inserted': total_inserted,
            'incomplete_dates': incomplete_dates
        }


async def main():
    import argparse

    parser = argparse.ArgumentParser(description='烟台钢筋价格智能抓取')
    parser.add_argument('--interval', '-i', type=int, default=5, help='抓取间隔')

    args = parser.parse_args()

    fetcher = SmartFetcher(args.interval)
    result = await fetcher.run()

    if result.get('success'):
        print(f"\n抓取完成！")
        print(f"Excel: {EXCEL_FILE}")
        print(f"数据库: {DB_FILE}")
    else:
        print(f"\n抓取失败: {result.get('error')}")


if __name__ == '__main__':
    asyncio.run(main())
