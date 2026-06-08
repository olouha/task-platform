"""
TaskPlatform 定时任务调度器
每天早上 5:00 自动执行价格抓取
"""
import asyncio
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('services/logs/scheduler.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


async def fetch_yantai_prices():
    """抓取烟台价格"""
    logger.info("[scheduler] 开始执行定时抓取任务")
    try:
        from services.price.scraper import YantaiScraper
        scraper = YantaiScraper()
        result = await scraper.fetch()

        if result['success']:
            logger.info(f"[scheduler] 抓取成功 | 数据={len(result.get('prices', []))}条")
        else:
            logger.error(f"[scheduler] 抓取失败 | {result.get('error', 'Unknown')}")

        return result
    except Exception as e:
        logger.error(f"[scheduler] 抓取异常 | {e}", exc_info=True)
        return {'success': False, 'error': str(e)}


async def push_notification(message: str):
    """推送通知到前端（通过 WebSocket）"""
    try:
        from services.websocket_manager import ws_manager
        await ws_manager.broadcast_price_update("scheduler_notification", {
            "message": message,
            "timestamp": datetime.now().isoformat()
        })
        logger.info(f"[scheduler] 推送通知成功 | {message}")
    except Exception as e:
        logger.warning(f"[scheduler] 推送通知失败 | {e}")


async def scheduled_job():
    """定时任务：每天早上 5:00 执行"""
    logger.info("="*50)
    logger.info("[scheduler] 定时任务开始执行")
    logger.info(f"[scheduler] 执行时间: {datetime.now()}")

    # 执行抓取
    result = await fetch_yantai_prices()

    # 推送结果通知
    if result['success']:
        await push_notification(f"定时抓取完成！共获取 {len(result.get('prices', []))} 条数据")
    else:
        await push_notification(f"定时抓取失败: {result.get('error', 'Unknown')}")

    logger.info("[scheduler] 定时任务执行完成")
    logger.info("="*50)


async def main():
    """启动调度器"""
    logger.info("[scheduler] 调度器启动中...")

    # 创建调度器
    scheduler = AsyncIOScheduler()

    # 添加定时任务：每天早上 5:00
    scheduler.add_job(
        scheduled_job,
        CronTrigger(hour=5, minute=0),
        id='daily_fetch',
        name='每日价格抓取',
        replace_existing=True
    )

    # 启动调度器
    scheduler.start()
    logger.info("[scheduler] 调度器已启动")

    # 获取下次执行时间
    job = scheduler.get_job('daily_fetch')
    if job:
        logger.info(f"[scheduler] 下次执行时间: {job.next_run_time}")

    # 保持程序运行
    try:
        # 无限期运行，直到被中断
        while True:
            await asyncio.sleep(3600)  # 每小时检查一次
    except (KeyboardInterrupt, SystemExit):
        logger.info("[scheduler] 调度器已停止")
        scheduler.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
