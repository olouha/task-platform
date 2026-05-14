"""
价格抓取调度器 v2.0
支持每个网站抓取多种材料
每天定时执行一次
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class FetchTask:
    """抓取任务"""
    source_id: str
    source_name: str
    scraper_type: str = "mysteel"  # mysteel, ccmn
    price_url: str = ""
    auth_username: Optional[str] = None
    auth_password: Optional[str] = None
    auth_type: str = "form"
    last_fetch: Optional[datetime] = None
    next_fetch: Optional[datetime] = None
    status: str = "pending"  # pending, running, success, failed
    last_prices: List[Dict] = field(default_factory=list)  # 支持多种材料
    last_error: Optional[str] = None

    def check_rate_limit(self) -> tuple[bool, str]:
        """检查是否可以执行（每天一次）"""
        now = datetime.now()

        if self.last_fetch:
            if self.last_fetch.date() == now.date():
                next_time = self.last_fetch.replace(hour=2, minute=0, second=0, microsecond=0)
                if now.hour < 2:
                    next_time = now.replace(hour=2, minute=0, second=0, microsecond=0)
                else:
                    next_time += timedelta(days=1)
                wait_hours = (next_time - now).total_seconds() / 3600
                return False, f"今日已抓取，下次于 {next_time.strftime('%H:%M')} 执行（还需等待 {wait_hours:.1f} 小时）"

            hours_since = (now - self.last_fetch).total_seconds() / 3600
            if hours_since < 24:
                next_time = self.last_fetch + timedelta(hours=24)
                return False, f"需等待 {24 - hours_since:.1f} 小时，下次抓取: {next_time.strftime('%Y-%m-%d %H:%M')}"

        return True, "可以执行"


@dataclass
class MaterialPriceResult:
    """材料价格结果"""
    material_id: str
    material_name: str
    spec: str = ""
    price: float = 0.0
    unit: str = ""
    change_rate: float = 0.0


@dataclass
class FetchResult:
    """抓取结果"""
    success: bool
    source_name: str
    prices: List[MaterialPriceResult] = field(default_factory=list)
    error_message: str = ""
    fetched_at: str = ""


class PriceFetchScheduler:
    """价格抓取调度器 - 每天执行一次，支持多材料"""

    def __init__(self, config_path: str = None):
        self.logger = logging.getLogger(__name__)
        self.tasks: Dict[str, FetchTask] = {}
        self.config_path = config_path or "config/price_fetch.json"
        self._load_config()

    def _load_config(self):
        """加载配置"""
        path = Path(self.config_path)
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for task_data in data.get('tasks', []):
                        task = FetchTask(
                            source_id=task_data['source_id'],
                            source_name=task_data['source_name'],
                            scraper_type=task_data.get('scraper_type', 'mysteel'),
                            price_url=task_data.get('price_url', ''),
                            auth_username=task_data.get('auth_username'),
                            auth_type=task_data.get('auth_type', 'form')
                        )
                        self.tasks[task.source_id] = task
                    self.logger.info(f"已加载 {len(self.tasks)} 个抓取任务")
            except Exception as e:
                self.logger.warning(f"加载配置失败: {e}")

    def _save_config(self):
        """保存配置"""
        path = Path(self.config_path)
        path.parent.mkdir(exist_ok=True, parents=True)

        data = {
            'updated_at': datetime.now().isoformat(),
            'tasks': [
                {
                    'source_id': task.source_id,
                    'source_name': task.source_name,
                    'scraper_type': task.scraper_type,
                    'price_url': task.price_url,
                    'auth_username': task.auth_username,
                    'auth_type': task.auth_type,
                    'last_fetch': task.last_fetch.isoformat() if task.last_fetch else None,
                    'next_fetch': task.next_fetch.isoformat() if task.next_fetch else None,
                    'status': task.status,
                    'last_prices': task.last_prices,
                    'last_error': task.last_error
                }
                for task in self.tasks.values()
            ]
        }

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add_task(self, task: FetchTask):
        """添加抓取任务"""
        self.tasks[task.source_id] = task
        self._schedule_next(task)
        self._save_config()
        self.logger.info(f"已添加抓取任务: {task.source_name}")

    def remove_task(self, source_id: str):
        """移除抓取任务"""
        if source_id in self.tasks:
            del self.tasks[source_id]
            self._save_config()
            self.logger.info(f"已移除抓取任务: {source_id}")

    def _schedule_next(self, task: FetchTask):
        """安排下次抓取"""
        now = datetime.now()
        next_hour = 2
        next_minute = 0

        next_run = now.replace(hour=next_hour, minute=next_minute, second=0, microsecond=0)
        if next_run <= now:
            next_run += timedelta(days=1)

        task.next_fetch = next_run

    def get_pending_tasks(self) -> List[FetchTask]:
        """获取待执行的任务"""
        now = datetime.now()
        return [task for task in self.tasks.values() if task.next_fetch and now >= task.next_fetch]

    def execute_task(self, task: FetchTask) -> FetchResult:
        """执行抓取任务 - 支持多材料"""
        task.status = "running"
        result = FetchResult(success=False, source_name=task.source_name)
        self.logger.info(f"开始抓取: {task.source_name}")

        try:
            from services.authenticated_scraper import ScraperFactory, SiteCredentials

            credentials = SiteCredentials(
                source_id=task.source_id,
                source_name=task.source_name,
                website_url=task.price_url.split('/price/')[0] if '/price/' in task.price_url else task.price_url,
                username=task.auth_username or '',
                password=task.auth_password or ''
            )

            scraper = ScraperFactory.get_scraper(task.scraper_type, credentials)
            if not scraper:
                raise ValueError(f"无法创建爬虫: {task.scraper_type}")

            # 执行抓取 - 现在返回多种材料
            crawl_result = scraper.fetch()

            if crawl_result.success:
                task.status = "success"
                task.last_fetch = datetime.now()
                task.last_error = None

                # 转换结果
                prices = []
                for mp in crawl_result.prices:
                    prices.append({
                        'material_id': mp.material_id,
                        'material_name': mp.material_name,
                        'spec': mp.spec,
                        'price': mp.price,
                        'unit': mp.unit,
                        'change_rate': mp.change_rate,
                    })
                task.last_prices = prices

                result.success = True
                result.prices = [MaterialPriceResult(**p) for p in prices]
                result.fetched_at = crawl_result.fetched_at

                self.logger.info(f"✅ 抓取成功: {task.source_name} - {len(prices)} 种材料")
                for p in prices:
                    self.logger.info(f"   - {p['material_name']}: ¥{p['price']:.2f}/{p['unit']}")
            else:
                task.status = "failed"
                task.last_error = crawl_result.error_message
                result.error_message = crawl_result.error_message
                self.logger.error(f"❌ 抓取失败: {task.source_name} - {crawl_result.error_message}")

            self._schedule_next(task)
            self._save_config()

        except Exception as e:
            task.status = "failed"
            task.last_error = str(e)
            result.error_message = str(e)
            self.logger.error(f"❌ 执行失败: {task.source_name} - {e}")

            self._schedule_next(task)
            self._save_config()

        return result

    def execute_all_pending(self) -> List[FetchResult]:
        """执行所有待处理任务"""
        pending = self.get_pending_tasks()
        results = []

        for task in pending:
            result = self.execute_task(task)
            results.append(result)

        return results

    def execute_all_sites(self, force: bool = False) -> List[FetchResult]:
        """执行所有网站的任务（每天抓取一次所有网站）"""
        results = []

        for task in self.tasks.values():
            if not force:
                can_execute, reason = task.check_rate_limit()
                if not can_execute:
                    self.logger.info(f"⏭️ 跳过 {task.source_name}: {reason}")
                    continue

            result = self.execute_task(task)
            results.append(result)

        return results

    def get_task_status(self, source_id: str) -> Optional[Dict]:
        """获取任务状态"""
        task = self.tasks.get(source_id)
        if task:
            return {
                'source_id': task.source_id,
                'source_name': task.source_name,
                'scraper_type': task.scraper_type,
                'status': task.status,
                'last_fetch': task.last_fetch.isoformat() if task.last_fetch else None,
                'next_fetch': task.next_fetch.isoformat() if task.next_fetch else None,
                'last_prices': task.last_prices,
                'last_error': task.last_error
            }
        return None

    def list_tasks(self) -> List[Dict]:
        """列出所有任务"""
        return [
            {
                'source_id': task.source_id,
                'source_name': task.source_name,
                'scraper_type': task.scraper_type,
                'status': task.status,
                'last_fetch': task.last_fetch.isoformat() if task.last_fetch else None,
                'next_fetch': task.next_fetch.isoformat() if task.next_fetch else None,
                'last_prices': task.last_prices,
                'last_error': task.last_error
            }
            for task in self.tasks.values()
        ]

    def force_fetch(self, source_id: str) -> Optional[FetchResult]:
        """强制执行指定任务"""
        task = self.tasks.get(source_id)
        if task:
            return self.execute_task(task)
        return None

    def force_fetch_all(self) -> List[FetchResult]:
        """强制执行所有任务"""
        results = []
        for task in self.tasks.values():
            result = self.execute_task(task)
            results.append(result)
        return results

    def sync_from_database(self, db_sources: List[Dict]):
        """从数据库同步任务"""
        existing_ids = set(self.tasks.keys())
        db_ids = {s['id'] for s in db_sources}

        for source in db_sources:
            scraper_type = self._detect_scraper_type(source.get('website_url', ''))
            if source['id'] not in self.tasks:
                task = FetchTask(
                    source_id=source['id'],
                    source_name=source['name'],
                    scraper_type=scraper_type,
                    price_url=source.get('price_url', ''),
                    auth_username=source.get('auth_username'),
                    auth_type=source.get('auth_type', 'form')
                )
                self.add_task(task)

        for source_id in existing_ids - db_ids:
            self.remove_task(source_id)

        self.logger.info(f"已同步 {len(self.tasks)} 个任务")

    def _detect_scraper_type(self, url: str) -> str:
        """根据 URL 检测爬虫类型"""
        url_lower = url.lower()
        if 'mysteel' in url_lower:
            return 'mysteel'
        elif 'ccmn' in url_lower:
            return 'ccmn'
        return 'mysteel'  # 默认


# ========== 独立运行模式 ==========

def run_scheduler():
    """独立运行调度器（用于 cron 或 Windows 计划任务）"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    logger.info("=" * 60)
    logger.info("TaskPlatform 价格抓取调度器 v2.0")
    logger.info("=" * 60)

    scheduler = PriceFetchScheduler()

    if not scheduler.tasks:
        logger.info("📋 没有配置抓取任务")
        logger.info("💡 请在管理界面配置价格来源和认证信息")
        return

    logger.info(f"\n📊 配置的任务数: {len(scheduler.tasks)}")

    # 执行所有网站
    results = scheduler.execute_all_sites()

    logger.info("\n" + "=" * 60)
    logger.info("执行结果汇总")
    logger.info("=" * 60)

    success_count = sum(1 for r in results if r.success)
    total_materials = sum(len(r.prices) for r in results)

    logger.info(f"\n✅ 成功: {success_count} 个网站")
    logger.info(f"📦 获取: {total_materials} 种材料价格")

    for result in results:
        status = "✅" if result.success else "❌"
        logger.info(f"\n{status} {result.source_name}:")
        if result.success:
            for p in result.prices:
                logger.info(f"   - {p.material_name}: ¥{p.price:.2f}/{p.unit}")
        else:
            logger.info(f"   错误: {result.error_message}")

    logger.info("\n" + "=" * 60)


if __name__ == '__main__':
    run_scheduler()