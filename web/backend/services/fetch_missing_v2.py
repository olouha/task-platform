"""
烟台钢筋价格历史数据批量补充抓取脚本 v2
功能：
1. 抓取缺失日期的历史数据（2024-01-01至2024-06-30）
2. 使用已有Cookie（已保存的登录状态）
3. 每天上午(AM)和下午(PM)各抓取一次
4. 每隔几秒抓取一天，防止被封
5. 保存截图和数据到数据库
"""
import asyncio
import sys
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Tuple, Optional

sys.path.insert(0, '.')

from playwright.async_api import async_playwright
import sqlite3

# 配置
DATA_DIR = Path('web/backend/services/data')
DB_FILE = DATA_DIR / 'yantai_rebar.db'
COOKIE_FILE = DATA_DIR / 'mysteel_cookies_test.json'  # 测试脚本生成的Cookie
PROGRESS_FILE = DATA_DIR / 'fetch_progress_v2.json'
SCREENSHOT_DIR = DATA_DIR / 'screenshots'

USERNAME = 'M6616592358'
PASSWORD = 'panhui199261'

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(DATA_DIR / 'fetch_missing_v2.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def get_existing_dates() -> set:
    """获取数据库中已存在的日期"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT date FROM rebar_prices ORDER BY date')
    dates = set(row[0] for row in cursor.fetchall())
    conn.close()
    return dates


def save_to_database(date: str, fetch_time: str, prices: List[dict]) -> int:
    """保存价格数据到数据库"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    inserted = 0
    for p in prices:
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO rebar_prices
                (date, fetch_time, material_name, spec, material_type, brand, price, region)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                date, fetch_time, p['material_name'], p['spec'],
                p.get('material_type', ''), p.get('brand', ''),
                p['price'], '山东烟台'
            ))
            if cursor.rowcount > 0:
                inserted += 1
        except Exception as e:
            logger.debug(f"插入失败: {e}")

    conn.commit()
    conn.close()
    return inserted


def save_progress(date: str, status: str, message: str = ""):
    """保存抓取进度"""
    progress = {
        'last_date': date,
        'status': status,
        'message': message,
        'timestamp': datetime.now().isoformat()
    }
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


def load_progress() -> Optional[dict]:
    """加载抓取进度"""
    if PROGRESS_FILE.exists():
        try:
            with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return None


def get_missing_dates(start_date: str, end_date: str) -> List[str]:
    """获取缺失的日期列表"""
    existing = get_existing_dates()

    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')

    missing = []
    current = start
    while current <= end:
        if current.weekday() < 5:  # 工作日
            date_str = current.strftime('%Y-%m-%d')
            if date_str not in existing:
                missing.append(date_str)
        current += timedelta(days=1)

    return missing


def generate_url(date: str, period: str) -> str:
    """生成历史价格URL"""
    yymmdd = date[2:4] + date[5:7] + date[8:10]
    hour = '10' if period == 'AM' else '16'
    return f"https://jiancai.mysteel.com/m/{yymmdd}{hour}/25B3355C6617BD3C.html"


async def fetch_date_data(page, date: str, period: str) -> Tuple[int, str]:
    """抓取指定日期的数据"""
    url = generate_url(date, period)
    logger.info(f"  访问: {url}")

    try:
        await page.goto(url, wait_until='domcontentloaded', timeout=60000)
        await page.wait_for_timeout(5000)

        # 截图
        screenshot_name = f"{date.replace('-', '')}_{period}.png"
        screenshot_path = SCREENSHOT_DIR / screenshot_name
        await page.screenshot(path=str(screenshot_path), full_page=True)

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

        prices = []
        for row in data:
            material_name = str(row[0]).strip()
            spec = str(row[1]).strip()
            material_type = str(row[2]).strip() if len(row) > 2 else ''
            brand = str(row[3]).strip() if len(row) > 3 else ''
            price_str = str(row[4]).strip() if len(row) > 4 else ''

            valid_names = ['高线', '螺纹钢', '盘螺', '圆钢']
            if material_name in valid_names and spec.startswith('Φ') and price_str.isdigit():
                try:
                    price = int(price_str)
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
            fetch_time = '09:00' if period == 'AM' else '15:00'
            inserted = save_to_database(date, fetch_time, prices)
            logger.info(f"  提取 {len(prices)} 条，新增 {inserted} 条")
            return inserted, str(screenshot_path)
        else:
            logger.warning(f"  未提取到钢筋数据")
            return 0, str(screenshot_path)

    except Exception as e:
        logger.error(f"  抓取失败: {e}")
        return 0, ""


async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='烟台钢筋价格历史数据批量补充抓取')
    parser.add_argument('--start', '-s', default='2024-01-01', help='开始日期')
    parser.add_argument('--end', '-e', default='2024-06-28', help='结束日期')
    parser.add_argument('--interval', '-i', type=int, default=5, help='抓取间隔秒数')
    parser.add_argument('--resume', '-r', action='store_true', help='从上次中断处继续')

    args = parser.parse_args()

    # 获取缺失日期
    missing = get_missing_dates(args.start, args.end)

    if not missing:
        logger.info("没有缺失日期，数据已完整！")
        return

    logger.info(f"需要抓取 {len(missing)} 个工作日")
    logger.info(f"日期范围: {missing[0]} 至 {missing[-1]}")

    # 断点续传
    if args.resume:
        progress = load_progress()
        if progress and progress.get('last_date'):
            last_date = progress['last_date']
            try:
                resume_idx = missing.index(last_date)
                missing = missing[resume_idx + 1:]
                logger.info(f"从 {last_date} 继续，剩余 {len(missing)} 天")
            except:
                pass

    logger.info("开始抓取...")

    # 加载Cookie
    if not COOKIE_FILE.exists():
        logger.error(f"没有Cookie文件: {COOKIE_FILE}")
        return

    with open(COOKIE_FILE, 'r', encoding='utf-8') as f:
        cookies = json.load(f)

    total_inserted = 0

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

        for i, date in enumerate(missing):
            logger.info(f"[{i+1}/{len(missing)}] 抓取 {date}")

            # AM 上午
            inserted_am, _ = await fetch_date_data(page, date, 'AM')
            await page.wait_for_timeout(args.interval * 1000)

            # PM 下午
            inserted_pm, _ = await fetch_date_data(page, date, 'PM')

            total_inserted += inserted_am + inserted_pm
            save_progress(date, 'completed', f"AM:{inserted_am} PM:{inserted_pm}")

            if i < len(missing) - 1:
                logger.info(f"  等待 {args.interval} 秒...")
                await page.wait_for_timeout(args.interval * 1000)

        await browser.close()

    logger.info("=" * 60)
    logger.info(f"抓取完成！新增 {total_inserted} 条记录")
    logger.info("=" * 60)


if __name__ == '__main__':
    asyncio.run(main())