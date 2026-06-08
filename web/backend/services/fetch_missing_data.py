"""
烟台钢筋价格历史数据批量补充抓取脚本
功能：
1. 抓取缺失日期的历史数据
2. 每天上午(09:00)和下午(15:00-16:00)各抓取一次
3. 每隔几秒抓取一天，防止被封
4. 保存截图和数据到数据库
5. 支持断点续传

使用方法：
    python fetch_missing_data.py [--start 2024-01-01] [--end 2026-05-30] [--interval 5]
"""
import asyncio
import sys
import json
import base64
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Tuple, Optional

sys.path.insert(0, '.')

try:
    from playwright.async_api import async_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

try:
    import sqlite3
except ImportError:
    print("需要安装 sqlite3")

import openpyxl

# 配置
DATA_DIR = Path('web/backend/services/data')
DB_FILE = DATA_DIR / 'yantai_rebar.db'
COOKIE_FILE = DATA_DIR / 'mysteel_cookies.json'
PROGRESS_FILE = DATA_DIR / 'fetch_progress.json'
SCREENSHOT_DIR = DATA_DIR / 'screenshots'

SCREENSHOT_DIR.mkdir(exist_ok=True)

# 登录凭据
USERNAME = 'M6616592358'
PASSWORD = 'panhui199261'

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(DATA_DIR / 'fetch_missing.log', encoding='utf-8'),
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


def get_existing_keys() -> set:
    """获取数据库中已存在的记录键（用于去重）"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT date, fetch_time, material_name, spec, brand, price FROM rebar_prices')
    keys = set(str(r) for r in cursor.fetchall())
    conn.close()
    return keys


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
    """保存抓取进度（用于断点续传）"""
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


def save_cookie(cookies: List):
    """保存Cookie"""
    with open(COOKIE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cookies, f, ensure_ascii=False)
    logger.info("Cookie已保存")


def load_cookie() -> List:
    """加载Cookie"""
    if COOKIE_FILE.exists():
        try:
            with open(COOKIE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return []


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


async def login(page, context) -> bool:
    """执行登录流程"""
    logger.info("[login] 开始登录...")

    try:
        await page.goto('https://passport.mysteel.com/', wait_until='networkidle', timeout=60000)
        await page.wait_for_timeout(3000)

        # 切换到账号登录
        try:
            account_tab = await page.query_selector('.form-tab-account')
            if account_tab:
                await account_tab.click()
                logger.info("[login] 已切换到账号登录")
                await page.wait_for_timeout(2000)
        except:
            pass

        # 填写登录表单
        await page.evaluate(f'''() => {{
            const inputs = document.querySelectorAll('input');
            for (const inp of inputs) {{
                const ph = inp.placeholder || '';
                if (ph.includes('用户名')) inp.value = '{USERNAME}';
                if (ph.includes('密码') && inp.type === 'password') inp.value = '{PASSWORD}';
            }}
        }}''')

        await page.wait_for_timeout(500)

        # 勾选协议
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
            else:
                btns = await page.query_selector_all('button')
                for btn in btns:
                    text = await btn.text_content()
                    if text and '登录' in text:
                        await btn.click()
                        break
        except:
            pass

        logger.info("[login] 等待登录完成...")
        await page.wait_for_timeout(8000)

        # 验证登录
        if 'passport' in page.url and 'login' in page.url:
            logger.warning("[login] 登录可能未完成")
            return False

        # 保存cookie
        cookies = await context.cookies()
        save_cookie(cookies)
        logger.info("[login] 登录成功")
        return True

    except Exception as e:
        logger.error(f"[login] 登录失败: {e}")
        return False


async def fetch_date_data(page, date: str, period: str, existing_keys: set) -> Tuple[int, str]:
    """抓取指定日期的数据

    Args:
        page: Playwright页面
        date: 日期 (YYYY-MM-DD)
        period: 时段 ('AM' 上午, 'PM' 下午)
        existing_keys: 已存在的记录键

    Returns:
        (新增记录数, 截图路径)
    """
    # 生成URL
    url = generate_url(date, period)
    logger.info(f"[fetch_date_data] 访问: {url}")

    try:
        await page.goto(url, wait_until='domcontentloaded', timeout=60000)
        await page.wait_for_timeout(8000)

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
            # 保存到数据库
            fetch_time = '09:00' if period == 'AM' else '15:00'
            inserted = save_to_database(date, fetch_time, prices)

            # 去除重复
            new_prices = []
            for p in prices:
                key = f"{date}_{fetch_time}_{p['material_name']}_{p['spec']}_{p['brand']}"
                if key not in existing_keys:
                    new_prices.append(p)
                    existing_keys.add(key)

            logger.info(f"[fetch_date_data] 提取 {len(prices)} 条，新增 {len(new_prices)} 条")
            return len(new_prices), str(screenshot_path)
        else:
            logger.warning(f"[fetch_date_data] {date} {period} 未提取到钢筋数据")
            return 0, str(screenshot_path)

    except Exception as e:
        logger.error(f"[fetch_date_data] 抓取失败: {e}")
        return 0, ""


def generate_url(date: str, period: str) -> str:
    """生成历史价格URL

    URL格式: https://jiancai.mysteel.com/m/YYMMDDHH/XXXXXXXX.html
    AM = 10 (上午), PM = 16 (下午)
    """
    yymmdd = date[2:4] + date[5:7] + date[8:10]
    hour = '10' if period == 'AM' else '16'
    # 使用固定的商户ID
    return f"https://jiancai.mysteel.com/m/{yymmdd}{hour}/25B3355C6617BD3C.html"


async def fetch_batch(dates: List[str], interval: int = 5, force: bool = False):
    """批量抓取一组日期的数据

    Args:
        dates: 日期列表
        interval: 抓取间隔（秒）
        force: 强制抓取（跳过已有）
    """
    logger.info(f"[fetch_batch] 开始批量抓取，共 {len(dates)} 天，间隔 {interval} 秒")

    if not HAS_PLAYWRIGHT:
        logger.error("未安装 playwright")
        return

    existing_keys = get_existing_keys()
    total_inserted = 0
    total_screenshots = 0

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 3000},
            locale='zh-CN'
        )
        page = await context.new_page()

        # 尝试加载Cookie
        cookies = load_cookie()
        if cookies:
            await context.add_cookies(cookies)
            logger.info("[fetch_batch] 已加载Cookie")

        # 登录
        login_success = await login(page, context)
        if not login_success:
            logger.warning("[fetch_batch] 登录未成功，继续尝试...")

        for i, date in enumerate(dates):
            logger.info(f"[{i+1}/{len(dates)}] 抓取 {date}")

            # AM 上午
            logger.info(f"  上午 (AM)...")
            inserted_am, screenshot_am = await fetch_date_data(page, date, 'AM', existing_keys)

            # 等待间隔
            await page.wait_for_timeout(interval * 1000)

            # PM 下午
            logger.info(f"  下午 (PM)...")
            inserted_pm, screenshot_pm = await fetch_date_data(page, date, 'PM', existing_keys)

            total_inserted += inserted_am + inserted_pm
            if screenshot_am:
                total_screenshots += 1
            if screenshot_pm:
                total_screenshots += 1

            # 更新进度
            save_progress(date, 'completed', f"AM:{inserted_am} PM:{inserted_pm}")

            # 等待间隔（天与天之间）
            if i < len(dates) - 1:
                logger.info(f"  等待 {interval} 秒...")
                await page.wait_for_timeout(interval * 1000)

        await browser.close()

    logger.info(f"[fetch_batch] 抓取完成！新增 {total_inserted} 条记录，{total_screenshots} 张截图")


async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='烟台钢筋价格历史数据批量补充抓取')
    parser.add_argument('--start', '-s', default='2024-01-01', help='开始日期 (YYYY-MM-DD)')
    parser.add_argument('--end', '-e', default='2026-05-30', help='结束日期 (YYYY-MM-DD)')
    parser.add_argument('--interval', '-i', type=int, default=5, help='抓取间隔秒数')
    parser.add_argument('--resume', '-r', action='store_true', help='从上次中断处继续')

    args = parser.parse_args()

    # 获取缺失日期
    missing = get_missing_dates(args.start, args.end)

    if not missing:
        logger.info("没有缺失日期，数据已完整！")
        return

    logger.info(f"缺失 {len(missing)} 个工作日")
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

    # 开始抓取
    await fetch_batch(missing, interval=args.interval)

    logger.info("=" * 60)
    logger.info("批量抓取完成！")
    logger.info(f"缺失日期总数: {len(missing)}")


if __name__ == '__main__':
    asyncio.run(main())