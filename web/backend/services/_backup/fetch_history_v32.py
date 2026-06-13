"""
烟台钢筋价格智能抓取 v3.2
- 改进数据提取逻辑
- 支持多种页面格式
"""
import asyncio
import sys
import json
import re
import random
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Set, Tuple

sys.path.insert(0, '.')
from playwright.async_api import async_playwright, Page
import sqlite3

DATA_DIR = Path('services/data')
DATA_DIR.mkdir(exist_ok=True)

DB_FILE = DATA_DIR / 'yantai_rebar.db'
COOKIE_FILE = DATA_DIR / 'mysteel_cookies.json'

MIN_PRICES = 11

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(str(DATA_DIR / 'fetch_v32.log'), encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DBManager:
    @staticmethod
    def init_db():
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS rebar_prices (
            id INTEGER PRIMARY KEY,
            date TEXT NOT NULL,
            material_name TEXT,
            spec TEXT,
            material_type TEXT,
            brand TEXT,
            price INTEGER,
            region TEXT DEFAULT '山东烟台',
            UNIQUE(date, material_name, spec, brand, price)
        )''')
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
        inserted, skipped = 0, 0
        for price in prices:
            key = f"{date}_{price['material_name']}_{price['spec']}_{price['brand']}"
            if key not in existing:
                try:
                    c.execute('INSERT INTO rebar_prices (date, material_name, spec, material_type, brand, price, region) VALUES (?, ?, ?, ?, ?, ?, ?)',
                        (date, price['material_name'], price['spec'], price['material_type'], price['brand'], price['price'], '山东烟台'))
                    inserted += 1
                    existing.add(key)
                except:
                    skipped += 1
            else:
                skipped += 1
        conn.commit()
        conn.close()
        return inserted, skipped


async def fetch_with_playwright():
    """使用playwright抓取"""
    logger.info("开始抓取...")

    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=True)
    context = await browser.new_context(viewport={'width': 1920, 'height': 3000}, locale='zh-CN')
    page = await context.new_page()

    # 加载Cookie
    if COOKIE_FILE.exists():
        try:
            with open(COOKIE_FILE, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
            await context.add_cookies(cookies)
            logger.info(f"加载了 {len(cookies)} 个Cookie")
        except: pass

    DBManager.init_db()
    existing_keys = DBManager.get_existing_keys()
    logger.info(f"数据库已有 {len(existing_keys)} 条记录")

    total_inserted = 0
    success_count = 0
    all_urls = []

    try:
        # 从首页获取URL
        logger.info("访问首页获取URL...")
        await page.goto('https://jiancai.mysteel.com/', wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(3)

        # 获取所有烟台价格链接
        links = await page.evaluate('''() => {
            const results = [];
            document.querySelectorAll('a[href]').forEach(a => {
                const href = a.href;
                const text = a.textContent.trim();
                // 匹配 /m/ 开头的价格页面
                if (href.includes('/m/') && href.includes('jiancai.mysteel.com')) {
                    results.push({href, text});
                }
            });
            return results;
        }''')

        logger.info(f"找到 {len(links)} 个链接")

        # 去重
        seen = set()
        unique_links = []
        for link in links:
            if link['href'] not in seen:
                seen.add(link['href'])
                unique_links.append(link)

        logger.info(f"去重后 {len(unique_links)} 个唯一URL")

        # 抓取每个URL
        for i, link in enumerate(unique_links):
            url = link['href']
            logger.info(f"\n[{i+1}/{len(unique_links)}] {url}")

            try:
                await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                await asyncio.sleep(2)

                # 检查登录状态
                body_text = await page.evaluate('() => document.body.textContent')
                if '登录' in body_text and len(body_text) < 500:
                    logger.warning("需要登录，跳过")
                    continue

                # 多种方式提取数据
                prices = []
                date_str = ''

                # 方式1: 从URL提取日期
                date_match = re.search(r'(\d{6})', url)
                if date_match:
                    d = date_match.group(1)
                    date_str = f'20{d[:2]}-{d[2:4]}-{d[4:6]}'

                # 方式2: 提取表格数据
                table_data = await page.evaluate('''() => {
                    // 尝试多种选择器
                    const tables = [
                        ...document.querySelectorAll('table'),
                        ...document.querySelectorAll('[class*="table"]'),
                        ...document.querySelectorAll('[class*="list"]')
                    ];

                    let results = [];
                    tables.forEach(table => {
                        const rows = table.querySelectorAll('tr');
                        rows.forEach(row => {
                            const cells = row.querySelectorAll('td, th');
                            if (cells.length >= 4) {
                                const rowData = [];
                                cells.forEach(c => rowData.push(c.textContent.trim()));
                                results.push(rowData);
                            }
                        });
                    });
                    return results;
                }''')

                # 解析价格数据
                for row in table_data:
                    if len(row) >= 4:
                        # 尝试不同的列顺序
                        material = row[0] if row[0] else ''
                        spec = row[1] if len(row) > 1 else ''
                        brand = row[2] if len(row) > 2 else ''
                        price_str = row[3] if len(row) > 3 else (row[4] if len(row) > 4 else '')

                        # 也可能是其他顺序
                        if not spec.startswith('Φ') and len(row) > 4:
                            material = row[0]
                            spec = row[2]
                            brand = row[3]
                            price_str = row[4]

                        valid_names = ['高线', '螺纹钢', '盘螺', '圆钢']
                        if material in valid_names and spec.startswith('Φ'):
                            try:
                                price = int(''.join(filter(str.isdigit, str(price_str))))
                                if price > 0:
                                    prices.append({
                                        'material_name': material,
                                        'spec': spec,
                                        'material_type': '',
                                        'brand': str(brand),
                                        'price': price
                                    })
                            except:
                                pass

                if prices:
                    logger.info(f"  提取 {len(prices)} 条数据: {date_str}")

                    # 插入数据库
                    inserted, skipped = DBManager.insert_prices(date_str, prices, existing_keys)
                    if inserted > 0:
                        total_inserted += inserted
                        success_count += 1
                        logger.info(f"  插入 {inserted} 条，跳过 {skipped} 条")

                        # 检查是否满足要求
                        from DBManager import DBManager as DB
                        current_count = DB.get_date_count(date_str)
                        if current_count < MIN_PRICES:
                            logger.warning(f"  警告: {date_str} 只有 {current_count} 条，需要 {MIN_PRICES} 条")

                else:
                    logger.info(f"  未提取到数据")

            except Exception as e:
                logger.error(f"  错误: {e}")

            # 延迟
            if i < len(unique_links) - 1:
                await asyncio.sleep(random.uniform(2, 5))

    except Exception as e:
        logger.error(f"抓取失败: {e}")

    finally:
        # 保存Cookie
        cookies = await context.cookies()
        try:
            with open(COOKIE_FILE, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, ensure_ascii=False)
        except: pass

        await browser.close()

    logger.info("\n" + "=" * 50)
    logger.info("抓取完成")
    logger.info(f"成功URL: {success_count}/{len(unique_links)}")
    logger.info(f"新增记录: {total_inserted} 条")
    logger.info("=" * 50)


if __name__ == '__main__':
    asyncio.run(fetch_with_playwright())
