# TaskPlatform 重构与腾讯云部署实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 重构 services 目录结构，删除废弃文件，配置腾讯云部署环境

**Architecture:**
- 代码重构：重组 `web/backend/services/` 为按功能分组的子目录（price/、adjustment/、cost/、ai/）
- 部署架构：Nginx 反向代理 + FastAPI (uvicorn) + systemd 服务

**Tech Stack:** Python 3.11+, FastAPI, uvicorn, Nginx, systemd, SQLite

---

## 文件变更概览

| 操作 | 文件 |
|------|------|
| **创建** | `web/backend/services/price/__init__.py` |
| **创建** | `web/backend/services/price/scraper.py` (从 fetch_yantai.py 合并) |
| **创建** | `web/backend/services/price/yantai_db_service.py` |
| **创建** | `web/backend/services/price/ocr_parse.py` |
| **创建** | `web/backend/services/adjustment/__init__.py` |
| **创建** | `web/backend/services/adjustment/calculator.py` |
| **创建** | `web/backend/services/adjustment/rules.py` |
| **创建** | `web/backend/services/cost/__init__.py` |
| **创建** | `web/backend/services/cost/reference.py` |
| **创建** | `web/backend/services/cost/history.py` |
| **创建** | `web/backend/services/ai/__init__.py` |
| **创建** | `web/backend/services/ai/service.py` |
| **保留** | `services/*.py` (核心服务文件，不移动) |
| **删除** | `services/fetch_*.py` (废弃变体) |
| **删除** | `services/daily_fetch*.py` |
| **删除** | `services/test_*.py` |
| **删除** | `services/debug_*.py` |
| **删除** | `services/step*.py` |
| **删除** | `services/check_*.py` |
| **删除** | `services/collect_urls*.py` |
| **删除** | `services/integrate*.py` |
| **删除** | `services/merge*.py` |
| **删除** | `services/generate*.py` (保留 generate_history_urls.py) |
| **删除** | `services/quick_import.py` |
| **删除** | `services/import_to_sqlite.py` |
| **删除** | `services/import_sqlite.py` |
| **删除** | `services/parse_all_rebar.py` |
| **删除** | `services/paddle_ocr_parse.py` |
| **删除** | `services/safe_fetch_history.py` |
| **删除** | `services/scroll_fetch_history.py` |
| **删除** | `services/fetch_0527.py` |
| **删除** | `services/yantai_rebar_scraper.py` |
| **删除** | `services/adjustment_engine.py` |
| **删除** | `services/sqlite_service.py` |
| **创建** | `deploy/tencent_cloud/nginx.conf` |
| **创建** | `deploy/tencent_cloud/taskplatform.service` |
| **创建** | `deploy/tencent_cloud/deploy.sh` |
| **创建** | `deploy/tencent_cloud/backup.sh` |

---

## 阶段一：代码重构

### Task 1: 创建目录结构

**Files:**
- Create: `web/backend/services/price/__init__.py`
- Create: `web/backend/services/adjustment/__init__.py`
- Create: `web/backend/services/cost/__init__.py`
- Create: `web/backend/services/ai/__init__.py`

- [ ] **Step 1: 创建 price 目录**

```bash
mkdir -p "e:/E/任务/task-platform/web/backend/services/price"
```

- [ ] **Step 2: 创建 adjustment 目录**

```bash
mkdir -p "e:/E/任务/task-platform/web/backend/services/adjustment"
```

- [ ] **Step 3: 创建 cost 目录**

```bash
mkdir -p "e:/E/任务/task-platform/web/backend/services/cost"
```

- [ ] **Step 4: 创建 ai 目录**

```bash
mkdir -p "e:/E/任务/task-platform/web/backend/services/ai"
```

- [ ] **Step 5: 创建 __init__.py 文件**

每个目录创建 `__init__.py`：

```python
"""
Price related services
"""

from .scraper import YantaiScraper
from .yantai_db_service import YantaiDBService
from .ocr_parse import OCRParser

__all__ = ['YantaiScraper', 'YantaiDBService', 'OCRParser']
```

- [ ] **Step 6: 提交变更**

```bash
git add web/backend/services/price web/backend/services/adjustment web/backend/services/cost web/backend/services/ai
git commit -m "feat: 创建 services 子目录结构"
```

---

### Task 2: 创建价格抓取服务 (scraper.py)

**Files:**
- Create: `web/backend/services/price/scraper.py`

- [ ] **Step 1: 创建 scraper.py**

复制 `fetch_yantai.py` 的核心逻辑到新文件：

```python
"""
山东烟台钢筋价格抓取服务
从我的钢铁网抓取实时价格数据
"""
import asyncio
import sys
import json
import base64
import logging
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from typing import List, Dict, Optional

sys.path.insert(0, '.')

from playwright.async_api import async_playwright
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.drawing.image import Image

logger = logging.getLogger(__name__)

DATA_DIR = Path('services/data')
DATA_DIR.mkdir(exist_ok=True)


@dataclass
class MaterialPrice:
    material_name: str = ''
    spec: str = ''
    material_type: str = ''
    brand: str = ''
    price: float = 0.0
    unit: str = '元/吨'
    region: str = '山东烟台'


class YantaiScraper:
    """烟台钢筋价格抓取器"""

    def __init__(self):
        self.cookie_file = DATA_DIR / 'mysteel_cookies.json'
        self.excel_file = DATA_DIR / '山东烟台钢筋价格.xlsx'
        self.username, self.password = self._load_credentials()

    def _load_credentials(self) -> tuple:
        """加载凭据"""
        config_file = DATA_DIR / 'mysteel_config.json'
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    return (
                        config.get('username', 'M6616592358'),
                        config.get('password', 'mysteel573005')
                    )
            except Exception as e:
                logger.warning(f"加载配置失败: {e}")
        return 'M6616592358', 'mysteel573005'

    def save_to_excel_with_screenshot(self, prices: List[Dict], screenshot_b64: str) -> None:
        """保存到Excel（含截图）"""
        header_font = Font(bold=True, size=12, color='FFFFFF')
        now_hour = datetime.now().hour

        if now_hour >= 12:
            header_fill = PatternFill(start_color='FF6B6B', end_color='FF6B6B', fill_type='solid')
            period = 'PM'
            period_text = '下午(晚)'
        else:
            header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
            period = 'AM'
            period_text = '上午'

        thin_border = Border(
            left=Side(style='thin'), right=Side(style='thin'),
            top=Side(style='thin'), bottom=Side(style='thin')
        )

        # 累积sheet页
        if Path(self.excel_file).exists():
            wb = openpyxl.load_workbook(self.excel_file)
        else:
            wb = openpyxl.Workbook()
            if 'Sheet' in wb.sheetnames:
                del wb['Sheet']

        today_str = datetime.now().strftime('%Y-%m-%d')
        fetch_time_str = datetime.now().strftime('%H:%M:%S')
        sheet_name = f'{today_str}_{period}_{fetch_time_str.replace(":", "")}'

        ws = wb.create_sheet(title=sheet_name)

        # 标题
        ws.merge_cells('A1:K1')
        ws.cell(row=1, column=1, value=f'山东烟台钢筋价格 - {today_str} {period_text}').font = Font(bold=True, size=14)
        ws.cell(row=1, column=1).alignment = Alignment(horizontal='center')

        # 表头
        headers = ['日期', '时间', '品名', '规格', '材质', '品牌/钢厂', '单价(元/吨)', '涨跌', '备注', '钢号', '地区']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=3, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal='center', vertical='center')
            cell.border = thin_border

        # 数据
        for i, price in enumerate(prices):
            row = 4 + i
            for col, val in enumerate([
                today_str, fetch_time_str,
                price.get('material_name', ''),
                price.get('spec', ''),
                price.get('material_type', ''),
                price.get('brand', ''),
                price.get('price', 0),
                '', '', '', price.get('region', '山东烟台')
            ], 1):
                cell = ws.cell(row=row, column=col, value=val)
                cell.border = thin_border

        # 嵌入截图
        if screenshot_b64:
            screenshot_path = DATA_DIR / f'screenshot_{today_str.replace("-", "")}_{period}.png'
            with open(screenshot_path, 'wb') as f:
                f.write(base64.b64decode(screenshot_b64))

            row = 4 + len(prices) + 2
            ws.cell(row=row, column=1, value='当日截图').font = Font(bold=True, size=12)

            img = Image(str(screenshot_path))
            img.width = 900
            img.height = 500
            img.anchor = f'A{row + 1}'
            ws.add_image(img)

        wb.save(self.excel_file)
        wb.close()
        logger.info(f"Excel已保存: {self.excel_file}, Sheet: {sheet_name}, 数据: {len(prices)}条")

    async def fetch(self) -> Dict:
        """执行抓取"""
        from services.websocket_manager import ws_manager

        logger.info("[YantaiScraper] 开始抓取")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(viewport={'width': 1920, 'height': 3000}, locale='zh-CN')
            page = await context.new_page()

            try:
                # 1. 登录
                logger.info("[YantaiScraper] 登录...")
                await page.goto('https://passport.mysteel.com/', wait_until='domcontentloaded', timeout=60000)
                await page.wait_for_timeout(5000)

                # 切换账号登录
                try:
                    account_tab = await page.query_selector('.form-tab-account, a[data-tab="account"]')
                    if account_tab:
                        await account_tab.click()
                        await page.wait_for_timeout(2000)
                except Exception as e:
                    logger.warning(f"切换账号登录失败: {e}")

                # 填写表单
                await page.evaluate(f'''() => {{
                    const inputs = document.querySelectorAll('input');
                    for (const inp of inputs) {{
                        const ph = inp.placeholder || '';
                        if (ph.includes('用户名')) inp.value = '{self.username}';
                        if (ph.includes('密码') && inp.type === 'password') inp.value = '{self.password}';
                    }}
                }}''')
                await page.wait_for_timeout(500)

                # 点击登录
                try:
                    login_btn = await page.query_selector('.form-button-login, button:has-text("登录")')
                    if login_btn:
                        await login_btn.click()
                except Exception as e:
                    logger.warning(f"点击登录失败: {e}")

                await page.wait_for_timeout(8000)
                logger.info("[YantaiScraper] 登录完成")

                # 保存Cookie
                cookies = await context.cookies()
                with open(self.cookie_file, 'w', encoding='utf-8') as f:
                    json.dump(cookies, f, ensure_ascii=False)

                # 2. 访问价格页
                logger.info("[YantaiScraper] 访问价格页...")
                await page.goto('https://jiancai.mysteel.com/m/26051410/25B3355C6617BD3C.html',
                               wait_until='domcontentloaded', timeout=60000)
                await page.wait_for_timeout(10000)

                # 截图
                screenshot = await page.screenshot(full_page=True)
                screenshot_b64 = base64.b64encode(screenshot).decode('utf-8')

                # 3. 提取价格
                logger.info("[YantaiScraper] 提取价格...")
                prices = []
                page_num = 1
                max_pages = 10

                while page_num <= max_pages:
                    data = await page.evaluate('''() => {
                        const tables = document.querySelectorAll('table');
                        const results = [];
                        tables.forEach((table, idx) => {
                            const rows = table.querySelectorAll('tr');
                            const tableData = [];
                            rows.forEach((row) => {
                                const cells = row.querySelectorAll('td, th');
                                const rowData = [];
                                cells.forEach(c => rowData.push(c.textContent.trim()));
                                if (rowData.length > 0) tableData.push(rowData);
                            });
                            if (tableData.length > 0) results.push({idx, rows: tableData});
                        });
                        return results;
                    }''')

                    page_prices = []
                    for t in data:
                        for row in t['rows']:
                            if row and len(row) >= 5:
                                material_name = row[0].strip()
                                spec = row[1].strip()
                                material_type = row[2].strip()
                                brand = row[3].strip()
                                price_str = row[4].strip()

                                valid_names = ['高线', '螺纹钢', '盘螺', '圆钢']
                                if material_name in valid_names and spec.startswith('Φ') and price_str.isdigit():
                                    try:
                                        page_prices.append({
                                            'material_name': material_name,
                                            'spec': spec,
                                            'material_type': material_type,
                                            'brand': brand,
                                            'price': float(price_str),
                                            'region': '山东烟台'
                                        })
                                    except Exception:
                                        pass

                    logger.info(f"[YantaiScraper] 第{page_num}页: {len(page_prices)}条")
                    prices.extend(page_prices)

                    # 检查下一页
                    has_next = await page.evaluate('''() => {
                        const buttons = Array.from(document.querySelectorAll('a'))
                            .filter(a => /下一页|>/i.test(a.textContent) && a.href && a.href !== window.location.href);
                        return buttons.length > 0;
                    }''')

                    if not has_next:
                        break

                    try:
                        next_btn = await page.query_selector('a:has-text("下一页"), a:has-text(">")')
                        if next_btn:
                            await next_btn.click()
                            await page.wait_for_timeout(5000)
                            page_num += 1
                        else:
                            break
                    except Exception:
                        break

                # 去重
                seen = set()
                unique_prices = []
                for p in prices:
                    key = (p['material_name'], p['spec'], p['brand'], p['price'])
                    if key not in seen:
                        seen.add(key)
                        unique_prices.append(p)
                prices = unique_prices
                logger.info(f"[YantaiScraper] 共提取: {len(prices)}条")

                # 4. 保存
                today_str = datetime.now().strftime('%Y-%m-%d')
                if prices:
                    self.save_to_excel_with_screenshot(prices, screenshot_b64)
                    await ws_manager.notify_fetch_success(len(prices), today_str)
                else:
                    await ws_manager.notify_fetch_failed('未提取到价格数据')

                await browser.close()

                return {
                    'success': len(prices) > 0,
                    'prices': prices,
                    'source_name': '我的钢铁网-山东烟台',
                    'fetched_at': datetime.now().isoformat()
                }

            except Exception as e:
                logger.error(f"[YantaiScraper] 抓取失败: {e}", exc_info=True)
                await ws_manager.notify_fetch_failed(str(e))
                return {'success': False, 'error': str(e), 'prices': []}


# 兼容旧接口
async def run_fetch():
    """兼容旧接口"""
    scraper = YantaiScraper()
    return await scraper.fetch()
```

- [ ] **Step 2: 提交变更**

```bash
git add web/backend/services/price/scraper.py
git commit -m "feat: 创建 price/scraper.py 价格抓取服务"
```

---

### Task 3: 创建烟台数据库服务 (yantai_db_service.py)

**Files:**
- Create: `web/backend/services/price/yantai_db_service.py`

- [ ] **Step 1: 创建 yantai_db_service.py**

```python
"""
烟台钢筋数据库服务
提供 SQLite 数据库操作接口
"""
import sqlite3
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

DATA_DIR = Path('services/data')
DB_FILE = DATA_DIR / 'yantai_rebar.db'


def get_db_connection() -> sqlite3.Connection:
    """获取数据库连接"""
    conn = sqlite3.connect(str(DB_FILE))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """初始化数据库"""
    DATA_DIR.mkdir(exist_ok=True)
    conn = get_db_connection()
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS rebar_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            material_name TEXT NOT NULL,
            spec TEXT NOT NULL,
            material_type TEXT,
            brand TEXT,
            price INTEGER NOT NULL,
            region TEXT DEFAULT '山东烟台',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 创建索引
    c.execute('CREATE INDEX IF NOT EXISTS idx_date ON rebar_prices(date)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_material ON rebar_prices(material_name)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_spec ON rebar_prices(spec)')

    conn.commit()
    conn.close()
    logger.info(f"[YantaiDBService] 数据库初始化完成: {DB_FILE}")


class YantaiDBService:
    """烟台钢筋数据库服务"""

    def __init__(self):
        self.db_file = DB_FILE

    def insert_prices(self, prices: List[Dict]) -> int:
        """批量插入价格数据"""
        if not prices:
            return 0

        conn = get_db_connection()
        c = conn.cursor()

        today = datetime.now().strftime('%Y-%m-%d')
        inserted = 0

        for price in prices:
            try:
                c.execute('''
                    INSERT INTO rebar_prices (date, material_name, spec, material_type, brand, price, region)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    today,
                    price.get('material_name', ''),
                    price.get('spec', ''),
                    price.get('material_type', ''),
                    price.get('brand', ''),
                    int(price.get('price', 0)),
                    price.get('region', '山东烟台')
                ))
                inserted += 1
            except Exception as e:
                logger.warning(f"[YantaiDBService] 插入失败: {e}")

        conn.commit()
        conn.close()
        logger.info(f"[YantaiDBService] 插入 {inserted} 条记录")
        return inserted

    def get_latest(self, date: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """获取最新价格"""
        conn = get_db_connection()
        c = conn.cursor()

        if date:
            c.execute('''
                SELECT date, material_name, spec, material_type, brand, price, region
                FROM rebar_prices
                WHERE date = ?
                ORDER BY material_name, spec
                LIMIT ?
            ''', (date, limit))
        else:
            c.execute('''
                SELECT date, material_name, spec, material_type, brand, price, region
                FROM rebar_prices
                WHERE date = (SELECT MAX(date) FROM rebar_prices)
                ORDER BY material_name, spec
                LIMIT ?
            ''', (limit,))

        rows = c.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_by_range(
        self,
        start_date: str,
        end_date: str,
        material: Optional[str] = None,
        spec: Optional[str] = None
    ) -> Dict:
        """获取日期范围数据"""
        conn = get_db_connection()
        c = conn.cursor()

        sql = '''
            SELECT date, material_name, spec, material_type, brand, price, region
            FROM rebar_prices
            WHERE date BETWEEN ? AND ?
        '''
        params = [start_date, end_date]

        if material:
            sql += ' AND material_name LIKE ?'
            params.append(f'%{material}%')

        if spec:
            sql += ' AND spec LIKE ?'
            params.append(f'%{spec}%')

        sql += ' ORDER BY date, material_name, spec'

        c.execute(sql, params)
        rows = c.fetchall()

        # 按日期分组
        dates_data = {}
        for row in rows:
            d = dict(row)
            date_str = d['date']
            if date_str not in dates_data:
                dates_data[date_str] = []
            dates_data[date_str].append(d)

        conn.close()
        return dates_data

    def get_trend(
        self,
        material: Optional[str] = None,
        spec: Optional[str] = None,
        days: int = 365
    ) -> List[Dict]:
        """获取价格趋势"""
        conn = get_db_connection()
        c = conn.cursor()

        sql = '''
            SELECT date, AVG(price) as avg_price, MIN(price) as min_price, MAX(price) as max_price, COUNT(*) as cnt
            FROM rebar_prices
            WHERE 1=1
        '''
        params = []

        if material:
            sql += ' AND material_name LIKE ?'
            params.append(f'%{material}%')

        if spec:
            sql += ' AND spec LIKE ?'
            params.append(f'%{spec}%')

        cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        sql += ' AND date >= ?'
        params.append(cutoff)

        sql += ' GROUP BY date ORDER BY date'

        c.execute(sql, params)
        rows = c.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_stats(self) -> Dict:
        """获取统计信息"""
        conn = get_db_connection()
        c = conn.cursor()

        c.execute('SELECT COUNT(*) FROM rebar_prices')
        total = c.fetchone()[0]

        c.execute('SELECT COUNT(DISTINCT date) FROM rebar_prices')
        dates = c.fetchone()[0]

        c.execute('SELECT MIN(date), MAX(date) FROM rebar_prices')
        range_row = c.fetchone()

        c.execute('SELECT material_name, COUNT(*) as cnt FROM rebar_prices GROUP BY material_name ORDER BY cnt DESC')
        materials = {row[0]: row[1] for row in c.fetchall()}

        c.execute('SELECT spec, COUNT(*) as cnt FROM rebar_prices GROUP BY spec ORDER BY cnt DESC LIMIT 20')
        specs = {row[0]: row[1] for row in c.fetchall()}

        conn.close()

        return {
            'total_count': total,
            'dates_count': dates,
            'date_range': {'start': range_row[0], 'end': range_row[1]},
            'materials': materials,
            'specs': specs
        }
```

- [ ] **Step 2: 提交变更**

```bash
git add web/backend/services/price/yantai_db_service.py
git commit -m "feat: 创建 price/yantai_db_service.py 数据库服务"
```

---

### Task 4: 创建调差计算服务

**Files:**
- Create: `web/backend/services/adjustment/calculator.py`
- Create: `web/backend/services/adjustment/rules.py`

- [ ] **Step 1: 创建 calculator.py**

```python
"""
调差计算服务
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class AdjustmentCalculator:
    """调差计算器"""

    def __init__(self, risk_percent: float = 0, risk_fixed: float = 0, tax_rate: float = 0.09):
        self.risk_percent = risk_percent
        self.risk_fixed = risk_fixed
        self.tax_rate = tax_rate

    def calculate(
        self,
        base_price: float,
        current_price: float,
        quantity: float
    ) -> Dict:
        """
        计算调差金额

        Args:
            base_price: 基准价格
            current_price: 当前价格
            quantity: 数量

        Returns:
            调差计算结果
        """
        price_diff = current_price - base_price
        price_change_rate = (price_diff / base_price * 100) if base_price > 0 else 0

        # 基础调差
        base_adjustment = price_diff * quantity

        # 风险调整
        risk_adjustment = base_adjustment * (self.risk_percent / 100) + self.risk_fixed * quantity

        # 税前调差
        pre_tax = base_adjustment + risk_adjustment

        # 税额
        tax = pre_tax * self.tax_rate

        # 税后调差
        total = pre_tax + tax

        return {
            'base_price': base_price,
            'current_price': current_price,
            'price_diff': price_diff,
            'price_change_rate': price_change_rate,
            'quantity': quantity,
            'base_adjustment': base_adjustment,
            'risk_adjustment': risk_adjustment,
            'pre_tax': pre_tax,
            'tax': tax,
            'total': total
        }

    def calculate_simple(
        self,
        base_price: float,
        avg_price: float,
        quantity: float,
        risk_percent: float = 0,
        risk_fixed: float = 0,
        tax_rate: float = 0.09
    ) -> Dict:
        """
        简单调差计算

        Args:
            base_price: 基准价格
            avg_price: 期间平均价格
            quantity: 数量
            risk_percent: 风险比例 (%)
            risk_fixed: 风险固定值
            tax_rate: 税率

        Returns:
            计算结果
        """
        price_diff = avg_price - base_price
        price_change_rate = (price_diff / base_price * 100) if base_price > 0 else 0

        pre_tax = price_diff * quantity
        risk_amount = pre_tax * (risk_percent / 100) + risk_fixed * quantity
        total_pre_tax = pre_tax + risk_amount
        tax = total_pre_tax * tax_rate
        total = total_pre_tax + tax

        return {
            'base_price': base_price,
            'avg_price': avg_price,
            'price_diff': price_diff,
            'price_change_rate': price_change_rate,
            'quantity': quantity,
            'risk_percent': risk_percent,
            'risk_fixed': risk_fixed,
            'pre_tax': pre_tax,
            'risk_amount': risk_amount,
            'total_pre_tax': total_pre_tax,
            'tax_rate': tax_rate,
            'tax': tax,
            'total': total
        }

    def validate_config(self, config: Dict) -> Dict:
        """验证配置"""
        errors = []

        if config.get('base_price', 0) <= 0:
            errors.append('基准价格必须大于0')

        if config.get('quantity', 0) <= 0:
            errors.append('数量必须大于0')

        risk_percent = config.get('risk_percent', 0)
        if risk_percent < 0 or risk_percent > 100:
            errors.append('风险比例必须在0-100之间')

        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
```

- [ ] **Step 2: 创建 rules.py**

```python
"""
调差规则服务
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

DATA_DIR = Path('services/data')
RULES_FILE = DATA_DIR / 'adjustment_rules.json'


class AdjustmentRules:
    """调差规则管理器"""

    def __init__(self):
        self.rules_file = RULES_FILE
        self.rules = self._load_rules()

    def _load_rules(self) -> List[Dict]:
        """加载规则"""
        if self.rules_file.exists():
            try:
                with open(self.rules_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"加载规则失败: {e}")
        return self._get_default_rules()

    def _get_default_rules(self) -> List[Dict]:
        """获取默认规则"""
        return [
            {
                'name': '钢材调差规则',
                'material_type': 'steel',
                'risk_percent': 5,
                'risk_fixed': 0,
                'tax_rate': 0.09,
                'threshold': 5
            },
            {
                'name': '混凝土调差规则',
                'material_type': 'concrete',
                'risk_percent': 3,
                'risk_fixed': 0,
                'tax_rate': 0.09,
                'threshold': 3
            }
        ]

    def get_rules(self) -> List[Dict]:
        """获取所有规则"""
        return self.rules

    def get_rule(self, name: str) -> Optional[Dict]:
        """获取指定规则"""
        for rule in self.rules:
            if rule.get('name') == name:
                return rule
        return None

    def save_rule(self, rule: Dict) -> bool:
        """保存规则"""
        try:
            self.rules.append(rule)
            with open(self.rules_file, 'w', encoding='utf-8') as f:
                json.dump(self.rules, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"保存规则失败: {e}")
            return False

    def get_presets(self) -> List[Dict]:
        """获取预设规则"""
        return [
            {'name': '标准钢材', 'risk_percent': 5, 'risk_fixed': 0, 'tax_rate': 0.09},
            {'name': '低风险钢材', 'risk_percent': 3, 'risk_fixed': 0, 'tax_rate': 0.09},
            {'name': '高风险钢材', 'risk_percent': 10, 'risk_fixed': 0, 'tax_rate': 0.09}
        ]
```

- [ ] **Step 3: 提交变更**

```bash
git add web/backend/services/adjustment/calculator.py web/backend/services/adjustment/rules.py
git commit -m "feat: 创建 adjustment 调差计算服务"
```

---

### Task 5: 删除废弃文件

**Files:**
- Delete: `services/fetch_*.py` (保留 fetch_yantai.py)
- Delete: `services/daily_fetch*.py`
- Delete: `services/test_*.py`
- Delete: `services/debug_*.py`
- Delete: `services/step*.py`
- Delete: `services/check_*.py`
- Delete: `services/collect_urls*.py`
- Delete: `services/integrate*.py`
- Delete: `services/merge*.py`
- Delete: `services/quick_import.py`
- Delete: `services/import_*.py`
- Delete: `services/parse_all_rebar.py`
- Delete: `services/paddle_ocr_parse.py`
- Delete: `services/safe_fetch_history.py`
- Delete: `services/scroll_fetch_history.py`
- Delete: `services/fetch_0527.py`
- Delete: `services/yantai_rebar_scraper.py`
- Delete: `services/adjustment_engine.py`
- Delete: `services/sqlite_service.py`

- [ ] **Step 1: 删除 fetch 变体**

```bash
cd "e:/E/任务/task-platform/web/backend/services"

# 删除 fetch 变体 (保留 fetch_yantai.py)
rm -f fetch_yantai_补充.py fetch_yantai_multi.py fetch_yantai_api.py fetch_yantai_history.py
rm -f fetch_month.py fetch_monthly_history.py fetch_year_history.py fetch_older_history.py
rm -f fetch_history.py fetch_history_v2.py fetch_history_resume.py fetch_history_by_urls.py
rm -f fetch_missing.py fetch_missing_history.py fetch_continue_missing.py
rm -f fetch_recent.py fetch_recent_v2.py fetch_recent_v3.py
rm -f fetch_available.py fetch_available_dates.py
rm -f fetch_full_history.py
```

- [ ] **Step 2: 删除 daily_fetch 变体**

```bash
rm -f daily_fetch.py daily_fetch_v2.py daily_fetch_v3.py daily_fetch_yantai.py
rm -f daily_fetch_ocr.py daily_fetch_ocr_v2.py
```

- [ ] **Step 3: 删除调试/测试脚本**

```bash
rm -f test_*.py debug_*.py step*.py check_*.py
rm -f collect_urls.py collect_urls_v2.py
rm -f integrate_data.py strict_integrate.py
rm -f merge_data.py merge_price_history.py merge_and_import.py
rm -f quick_import.py import_to_sqlite.py import_sqlite.py
rm -f parse_all_rebar.py paddle_ocr_parse.py
rm -f safe_fetch_history.py scroll_fetch_history.py
rm -f fetch_0527.py yantai_rebar_scraper.py
rm -f adjustment_engine.py sqlite_service.py
```

- [ ] **Step 4: 提交删除**

```bash
git add -A
git commit -m "refactor: 删除废弃的服务文件 (保留核心功能)"
```

---

## 阶段二：部署配置

### Task 6: 创建部署配置

**Files:**
- Create: `deploy/tencent_cloud/nginx.conf`
- Create: `deploy/tencent_cloud/taskplatform.service`
- Create: `deploy/tencent_cloud/deploy.sh`
- Create: `deploy/tencent_cloud/backup.sh`
- Create: `deploy/tencent_cloud/DEPLOY.md`

- [ ] **Step 1: 创建 nginx.conf**

```nginx
server {
    listen 80;
    server_name _;

    # 前端静态文件
    location / {
        root /opt/taskplatform/frontend/dist;
        index index.html;
        try_files $uri $uri/ /index.html;
        expires -1;
    }

    # API 反向代理
    location /api/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # WebSocket 支持
    location /ws {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400s;
    }

    # 健康检查
    location /health {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
    }

    # 静态资源缓存
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
        root /opt/taskplatform/frontend/dist;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # 日志
    access_log /var/log/nginx/taskplatform_access.log;
    error_log /var/log/nginx/taskplatform_error.log;
}
```

- [ ] **Step 2: 创建 systemd 服务文件**

```ini
[Unit]
Description=TaskPlatform Backend Service
Documentation=https://github.com/olouha/task-platform
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/taskplatform/app
Environment="PYTHONUNBUFFERED=1"
Environment="PATH=/opt/taskplatform/venv/bin"

# 启动命令
ExecStart=/opt/taskplatform/venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8001 --workers 2

# 重启策略
Restart=always
RestartSec=5

# 日志
StandardOutput=append:/opt/taskplatform/logs/stdout.log
StandardError=append:/opt/taskplatform/logs/stderr.log

# 资源限制
LimitNOFILE=65536
MemoryMax=512M

[Install]
WantedBy=multi-user.target
```

- [ ] **Step 3: 创建 deploy.sh**

```bash
#!/bin/bash
# TaskPlatform 腾讯云部署脚本

set -e

APP_DIR="/opt/taskplatform"
VENV_DIR="$APP_DIR/venv"
FRONTEND_DIR="$APP_DIR/frontend"
BACKEND_DIR="$APP_DIR/app"

echo "=== TaskPlatform 部署开始 ==="
echo "时间: $(date)"
echo "目录: $APP_DIR"

# 1. 创建目录结构
echo "[1/7] 创建目录结构..."
mkdir -p $APP_DIR/{app,frontend,logs,backups}
mkdir -p /var/log/nginx
mkdir -p /var/log/taskplatform

# 2. 安装系统依赖
echo "[2/7] 安装系统依赖..."
apt-get update
apt-get install -y python3 python3-pip python3-venv nginx curl

# 3. 创建 Python 虚拟环境
echo "[3/7] 创建虚拟环境..."
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv $VENV_DIR
fi
source $VENV_DIR/bin/activate

# 4. 安装 Python 依赖
echo "[4/7] 安装 Python 依赖..."
pip install --upgrade pip
pip install fastapi uvicorn[standard] sqlalchemy aiosqlite \
    pydantic python-multipart openpyxl pandas \
    beautifulsoup4 requests httpx playwright \
    APScheduler python-jose[cryptography] passlib[bcrypt]

# 安装 Playwright 浏览器
playwright install chromium

# 5. 复制应用代码 (需要先通过 SCP 或 Git 部署)
echo "[5/7] 检查应用代码..."
if [ ! -d "$BACKEND_DIR" ]; then
    echo "错误: 后端代码不存在，请先上传代码到 $BACKEND_DIR"
    echo "可以使用: git clone 或 scp"
    exit 1
fi

# 6. 配置 Nginx
echo "[6/7] 配置 Nginx..."
cp deploy/tencent_cloud/nginx.conf /etc/nginx/sites-available/taskplatform
ln -sf /etc/nginx/sites-available/taskplatform /etc/nginx/sites-enabled/taskplatform
nginx -t && systemctl reload nginx

# 7. 配置 systemd 服务
echo "[7/7] 配置 systemd 服务..."
cp deploy/tencent_cloud/taskplatform.service /etc/systemd/system/taskplatform.service
systemctl daemon-reload
systemctl enable taskplatform
systemctl restart taskplatform

# 检查状态
echo ""
echo "=== 服务状态 ==="
systemctl status taskplatform --no-pager
nginx -t

echo ""
echo "=== 部署完成 ==="
echo "访问地址: http://$(curl -s ifconfig.me):80"
```

- [ ] **Step 4: 创建 backup.sh**

```bash
#!/bin/bash
# TaskPlatform 数据库备份脚本

BACKUP_DIR="/opt/taskplatform/backups"
DATE=$(date +%Y%m%d)
DB_DIR="/opt/taskplatform/app/services/data"
RETENTION_DAYS=7

echo "=== TaskPlatform 备份开始 ==="
echo "时间: $(date)"

# 创建备份目录
mkdir -p $BACKUP_DIR

# 备份所有数据库文件
for db in $DB_DIR/*.db; do
    if [ -f "$db" ]; then
        filename=$(basename "$db")
        cp "$db" "$BACKUP_DIR/${DATE}_${filename}"
        echo "备份: ${DATE}_${filename}"
    fi
done

# 备份配置文件
if [ -f "$DB_DIR/mysteel_config.json" ]; then
    cp "$DB_DIR/mysteel_config.json" "$BACKUP_DIR/${DATE}_mysteel_config.json"
    echo "备份: ${DATE}_mysteel_config.json"
fi

# 删除过期备份
find $BACKUP_DIR -name "*.db" -mtime +$RETENTION_DAYS -delete
find $BACKUP_DIR -name "*_mysteel_config.json" -mtime +$RETENTION_DAYS -delete

echo "=== 备份完成 ==="
echo "备份目录: $BACKUP_DIR"
ls -la $BACKUP_DIR | tail -10
```

- [ ] **Step 5: 创建 DEPLOY.md**

```markdown
# 腾讯云部署指南

## 前提条件

- 腾讯云轻量应用服务器 (Ubuntu 22.04)
- SSH 访问权限
- 已上传代码到服务器

## 快速部署

### 方式一：使用部署脚本

```bash
# 1. 上传代码到服务器
scp -r . root@your-server:/opt/taskplatform/

# 2. 运行部署脚本
chmod +x deploy/tencent_cloud/deploy.sh
./deploy/tencent_cloud/deploy.sh
```

### 方式二：手动部署

```bash
# 1. 安装依赖
apt-get update && apt-get install -y python3 python3-pip python3-venv nginx

# 2. 创建虚拟环境
python3 -m venv /opt/taskplatform/venv
source /opt/taskplatform/venv/bin/activate

# 3. 安装 Python 依赖
pip install fastapi uvicorn[standard] openpyxl pandas

# 4. 配置 Nginx
cp deploy/tencent_cloud/nginx.conf /etc/nginx/sites-available/taskplatform
ln -sf /etc/nginx/sites-available/taskplatform /etc/nginx/sites-enabled/taskplatform
nginx -t && systemctl reload nginx

# 5. 配置 systemd
cp deploy/tencent_cloud/taskplatform.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable taskplatform
systemctl start taskplatform
```

## 验证部署

```bash
# 检查服务状态
systemctl status taskplatform

# 检查端口
netstat -tulpn | grep 8001

# 测试 API
curl http://localhost:8001/health

# 测试前端
curl http://localhost/
```

## 常用命令

| 操作 | 命令 |
|------|------|
| 重启服务 | `systemctl restart taskplatform` |
| 查看日志 | `tail -f /opt/taskplatform/logs/stdout.log` |
| 查看 Nginx 日志 | `tail -f /var/log/nginx/taskplatform_access.log` |
| 备份数据库 | `/opt/taskplatform/backup.sh` |

## 定时备份

```bash
# 添加 crontab
crontab -e

# 每天凌晨 3 点备份
0 3 * * * /opt/taskplatform/backup.sh >> /var/log/taskplatform/backup.log 2>&1
```
```

- [ ] **Step 6: 提交部署配置**

```bash
git add deploy/tencent_cloud/
git commit -m "feat: 添加腾讯云部署配置 (Nginx + systemd)"
```

---

## 验收检查清单

### 功能验证

- [ ] 价格抓取 API 正常响应
- [ ] 调差计算结果正确
- [ ] 前端页面全部加载
- [ ] WebSocket 连接正常
- [ ] 数据库读写正常

### 部署验证

- [ ] 服务自动启动
- [ ] Nginx 反向代理正常
- [ ] 日志正常输出
- [ ] 备份脚本可执行

---

**计划版本**: v1.0
**创建日期**: 2026-05-28