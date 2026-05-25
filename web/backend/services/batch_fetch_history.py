"""
批量补全烟台钢筋价格历史数据
从截图文件名获取日期，然后访问对应URL抓取数据
"""

import asyncio
import json
import re
import os
from pathlib import Path
from datetime import datetime

from playwright.async_api import async_playwright
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

# 配置
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / 'data'
EXCEL_FILE = DATA_DIR / '山东烟台钢筋价格.xlsx'
LINKS_FILE = DATA_DIR / 'yantai_links.json'
PROGRESS_FILE = DATA_DIR / 'fetch_progress.json'
COOKIE_FILE = DATA_DIR / 'mysteel_cookies.json'
LOG_FILE = DATA_DIR / 'batch_fetch_log.json'

# 登录凭据
USERNAME = 'M6616592358'
PASSWORD = 'mysteel573005'

# 反检测脚本
ANTI_DETECTION_JS = '''
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']});
window.chrome = {runtime: {}};
'''


def random_sleep(min_sec=1, max_sec=3):
    import random
    return random.uniform(min_sec, max_sec)


def parse_date_from_url(url):
    """从URL解析日期"""
    match = re.search(r'/m/(\d{8})/', url)
    if match:
        full = match.group(1)
        year = 2000 + int(full[0:2])
        month = int(full[2:4])
        day = int(full[4:6])
        hour = int(full[6:8])
        date_str = f'{year}-{month:02d}-{day:02d}'
        period = 'AM' if hour < 12 else 'PM'
        return date_str, period
    return None, None


def parse_date_from_screenshot(filename):
    """从截图文件名解析日期"""
    # screenshot_20240105_AM.png
    parts = filename.replace('screenshot_', '').replace('.png', '').split('_')
    if len(parts) >= 2:
        date_str = parts[0]
        year = date_str[:4]
        month = date_str[4:6]
        day = date_str[6:8]
        period = parts[1]
        return f'{year}-{month}-{day}', period
    return None, None


def get_existing_dates():
    """获取Excel中已有的日期"""
    if not EXCEL_FILE.exists():
        return set()

    try:
        wb = openpyxl.load_workbook(EXCEL_FILE, read_only=True)
        dates = set()
        for sheet_name in wb.sheetnames:
            if '_' in sheet_name:
                date_part = sheet_name.split('_')[0]
                dates.add(date_part)
        wb.close()
        return dates
    except Exception as e:
        print(f'读取Excel失败: {e}')
        return set()


def get_url_from_date(date_str, period):
    """根据日期查找对应的URL"""
    if not LINKS_FILE.exists():
        return None

    with open(LINKS_FILE, 'r', encoding='utf-8') as f:
        links = json.load(f)

    # 解析目标日期（格式: YYYY-MM-DD）
    parts = date_str.split('-')
    if len(parts) != 3:
        return None
    year, month, day = parts
    date_pattern = f'{month}月{int(day)}日'

    for link in links:
        url = link.get('href', '')
        text = link.get('text', '')

        # 匹配日期和时段
        if date_pattern in text:
            if period == 'AM' and '(16:' not in text:
                return url
            elif period == 'PM' and '(16:' in text:
                return url

    return None


async def fetch_prices_from_url(page, url):
    """从URL获取价格数据"""
    try:
        await page.goto(url, wait_until='domcontentloaded', timeout=60000)
        await asyncio.sleep(random_sleep(2, 4))

        # 提取数据
        data = await page.evaluate('''() => {
            const tables = document.querySelectorAll('table');
            const results = [];
            tables.forEach(table => {
                const rows = table.querySelectorAll('tr');
                rows.forEach(row => {
                    const cells = row.querySelectorAll('td');
                    if (cells.length >= 5) {
                        const material_name = cells[0]?.textContent?.trim();
                        const spec = cells[1]?.textContent?.trim();
                        const material_type = cells[2]?.textContent?.trim();
                        const brand = cells[3]?.textContent?.trim();
                        const price = cells[4]?.textContent?.trim();

                        if (['高线', '螺纹钢', '盘螺', '圆钢'].includes(material_name) &&
                            spec && spec.startsWith('Φ') && price && /^\\d+$/.test(price)) {
                            results.push({
                                material_name,
                                spec,
                                material_type,
                                brand,
                                price: parseFloat(price)
                            });
                        }
                    }
                });
            });
            return results;
        }''')

        return list(data)
    except Exception as e:
        print(f'抓取失败: {e}')
        return []


async def check_login(page):
    """检查登录状态"""
    test_url = 'https://jiancai.mysteel.com/market/pa228aa010101a0a01010205aaaa1.html'
    try:
        await page.goto(test_url, wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(2)

        current_url = page.url
        if 'passport' in current_url or 'login' in current_url:
            return False
        return True
    except:
        return False


async def do_login(page):
    """执行登录"""
    print('[LOGIN] 访问登录页...')
    await page.goto('https://passport.mysteel.com/', wait_until='domcontentloaded', timeout=60000)
    await asyncio.sleep(2)

    # 填写表单
    await page.evaluate(f'''
        const inputs = document.querySelectorAll('input');
        for (const inp of inputs) {{
            const ph = inp.placeholder || "";
            const type = inp.type || "";
            if (ph.includes("用户名") || ph.includes("账号")) {{
                inp.value = "{USERNAME}";
                inp.dispatchEvent(new Event('input', {{ bubbles: true }}));
            }}
            if (ph.includes("密码") && type === "password") {{
                inp.value = "{PASSWORD}";
                inp.dispatchEvent(new Event('input', {{ bubbles: true }}));
            }}
        }}
    ''')
    await asyncio.sleep(1)

    # 点击登录
    for selector in ['button:has-text("登录")', '.form-button-login', 'button[type="submit"]']:
        try:
            btn = await page.query_selector(selector)
            if btn:
                await btn.click()
                break
        except:
            continue

    await asyncio.sleep(10)

    # 保存Cookie
    cookies = await page.context.cookies()
    with open(COOKIE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cookies, f, ensure_ascii=False)
    print('[LOGIN] Cookie已保存')


def save_prices_to_excel(prices, date_str, period, fetch_time='09:00:00'):
    """保存价格到Excel"""
    if not prices:
        return False

    try:
        # 打开或创建 workbook
        if EXCEL_FILE.exists():
            try:
                wb = openpyxl.load_workbook(EXCEL_FILE)
            except Exception:
                wb = openpyxl.Workbook()
                if 'Sheet' in wb.sheetnames:
                    del wb['Sheet']
        else:
            wb = openpyxl.Workbook()
            if 'Sheet' in wb.sheetnames:
                del wb['Sheet']

        # 生成 sheet 名称
        time_str = fetch_time.replace(':', '')
        sheet_name = f'{date_str}_{period}_{time_str}'

        # 避免重复
        base_name = sheet_name
        counter = 1
        while sheet_name in wb.sheetnames:
            sheet_name = f'{base_name}_{counter}'
            counter += 1

        ws = wb.create_sheet(title=sheet_name)

        # 样式
        period_text = '上午' if period == 'AM' else '下午'
        header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid') if period == 'AM' else PatternFill(start_color='FF6B6B', end_color='FF6B6B', fill_type='solid')
        thin_border = Border(
            left=Side(style='thin'), right=Side(style='thin'),
            top=Side(style='thin'), bottom=Side(style='thin')
        )

        # 标题行
        ws.merge_cells('A1:K1')
        ws.cell(row=1, column=1, value=f'山东烟台钢筋价格 - {date_str} {period_text}').font = Font(bold=True, size=14)
        ws.cell(row=1, column=1).alignment = Alignment(horizontal='center')

        # 表头
        headers = ['日期', '时间', '品名', '规格', '材质', '品牌/钢厂', '单价(元/吨)', '涨跌', '备注', '钢号', '地区']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=3, column=col, value=header)
            cell.font = Font(bold=True, size=12, color='FFFFFF')
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal='center', vertical='center')
            cell.border = thin_border

        # 数据行
        for i, price in enumerate(prices):
            row = 4 + i
            values = [
                date_str,
                fetch_time,
                price.get('material_name', ''),
                price.get('spec', ''),
                price.get('material_type', ''),
                price.get('brand', ''),
                price.get('price', 0),
                '',
                '',
                '',
                '山东烟台'
            ]
            for col, val in enumerate(values, 1):
                cell = ws.cell(row=row, column=col, value=val)
                cell.border = thin_border

        wb.save(EXCEL_FILE)
        wb.close()

        return True

    except Exception as e:
        print(f'保存失败: {e}')
        return False


def load_log():
    """加载日志"""
    if LOG_FILE.exists():
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'done': [], 'failed': [], 'success_count': 0, 'fail_count': 0}


def save_log(log):
    """保存日志"""
    with open(LOG_FILE, 'w', encoding='utf-8') as f:
        json.dump(log, f, ensure_ascii=False, indent=2)


def get_all_urls_to_fetch():
    """获取所有需要抓取的URL"""
    urls = []

    # 从 remaining 中获取（已有完整URL）
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
            progress = json.load(f)
        remaining = progress.get('remaining', [])
        for item in remaining:
            if len(item) >= 3:
                date_str = item[0]
                period = item[1]
                url = item[2]
                urls.append((date_str, period, url))

    # 去重
    seen = set()
    unique_urls = []
    for date_str, period, url in urls:
        key = f'{date_str}_{period}'
        if key not in seen:
            seen.add(key)
            unique_urls.append((date_str, period, url))

    return unique_urls


async def run_batch_fetch():
    """批量抓取"""
    print('=' * 60)
    print('批量补全烟台钢筋价格历史数据')
    print('=' * 60)

    # 加载日志
    log = load_log()
    done_keys = set(log.get('done', []))

    # 获取已有日期
    existing_dates = get_existing_dates()
    print(f'Excel已有: {len(existing_dates)} 个日期')

    # 获取需要抓取的URL
    urls_to_fetch = get_all_urls_to_fetch()
    print(f'待抓取: {len(urls_to_fetch)} 个')

    # 过滤掉已完成的和已存在的
    to_process = []
    for date_str, period, url in urls_to_fetch:
        key = f'{date_str}_{period}'
        if key in done_keys:
            continue
        if date_str in existing_dates:
            continue
        to_process.append((date_str, period, url))

    print(f'实际需要处理: {len(to_process)} 个')

    if not to_process:
        print('没有需要处理的')
        return

    # 按日期排序
    to_process.sort(key=lambda x: x[0])

    # 启动浏览器
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            locale='zh-CN'
        )
        await context.add_init_script(ANTI_DETECTION_JS)
        page = await context.new_page()

        # 加载Cookie
        if COOKIE_FILE.exists():
            try:
                cookies = json.load(open(COOKIE_FILE))
                await context.add_cookies(cookies)
                print('[OK] Cookie已加载')
            except:
                pass

        # 检查登录状态
        is_logged_in = await check_login(page)
        if not is_logged_in:
            print('[INFO] 需要登录...')
            await do_login(page)
            await asyncio.sleep(2)

        # 开始抓取
        success_count = log.get('success_count', 0)
        fail_count = log.get('fail_count', 0)

        for i, (date_str, period, url) in enumerate(to_process):
            print(f'\n[{i+1}/{len(to_process)}] {date_str} {period}')

            key = f'{date_str}_{period}'

            try:
                prices = await fetch_prices_from_url(page, url)

                if prices:
                    if save_prices_to_excel(prices, date_str, period):
                        print(f'[OK] {date_str} {period} - {len(prices)} 条数据')
                        log['done'].append(key)
                        success_count += 1
                    else:
                        print(f'[FAIL] 保存失败')
                        log['failed'].append(key)
                        fail_count += 1
                else:
                    print(f'[FAIL] 未获取到数据')
                    log['failed'].append(key)
                    fail_count += 1

            except Exception as e:
                print(f'[ERROR] {e}')
                log['failed'].append(key)
                fail_count += 1

            # 每10个保存一次日志
            if (i + 1) % 10 == 0:
                log['success_count'] = success_count
                log['fail_count'] = fail_count
                save_log(log)

            # 随机延时
            await asyncio.sleep(random_sleep(1, 3))

        # 保存最终日志
        log['success_count'] = success_count
        log['fail_count'] = fail_count
        save_log(log)

        await browser.close()

    print('\n' + '=' * 60)
    print('完成')
    print(f'成功: {success_count}')
    print(f'失败: {fail_count}')
    print('=' * 60)


def main():
    import argparse

    parser = argparse.ArgumentParser(description='批量补全烟台钢筋价格历史数据')
    parser.add_argument('--limit', '-n', type=int, default=None, help='限制处理数量')
    parser.add_argument('--reset', action='store_true', help='重置进度')

    args = parser.parse_args()

    if args.reset:
        if LOG_FILE.exists():
            os.remove(LOG_FILE)
        print('日志已重置')

    asyncio.run(run_batch_fetch())


if __name__ == '__main__':
    main()