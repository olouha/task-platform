"""
云端部署版本主程序
本地运行，但数据同步到云端数据库
"""

import sys
import logging
import os

os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def main():
    """主函数"""
    logger.info("Starting TaskPlatform Cloud Edition...")

    try:
        from PyQt6.QtWidgets import QApplication

        app = QApplication(sys.argv)
        app.setApplicationName("TaskPlatform")
        app.setOrganizationName("TaskPlatform")

        from core import Scheduler, DatabaseManager
        from cloud.client import CloudClient, SyncManager

        # 初始化本地数据库
        logger.info("Initializing local database...")
        db = DatabaseManager()

        # 初始化云端客户端
        logger.info("Initializing cloud client...")
        cloud_url = db.get_config('cloud_url', 'http://localhost:5000')
        cloud_client = CloudClient(cloud_url)

        # 初始化同步管理器
        sync_manager = SyncManager(db, cloud_client)

        # 检查云端连接
        if cloud_client.is_connected():
            logger.info(f"Connected to cloud: {cloud_url}")
            sync_manager.set_mode('sync')
            sync_manager.sync_tasks()
        else:
            logger.warning("Cloud not connected, running in offline mode")
            sync_manager.set_mode('offline')

        # 初始化调度器
        logger.info("Initializing scheduler...")
        scheduler = Scheduler()

        # 初始化模块管理器
        from modules import (
            ScraperManager, create_scraper_handler,
            BrowserManager, create_browser_handler,
            ExportManager
        )

        scraper_manager = ScraperManager(db)
        browser_manager = BrowserManager(db)
        export_manager = ExportManager(db)

        # 注册任务处理器
        def default_handler(task):
            logger.info(f"Executing task: {task.name}")
            db.add_log(task.id, 'success', f'Task {task.name} executed successfully')
            return True

        scheduler.register_handler('custom', default_handler)
        scheduler.register_handler('interval', default_handler)
        scheduler.register_handler('cron', default_handler)
        scheduler.register_handler('scraper', create_scraper_handler(scraper_manager))
        scheduler.register_handler('browser', create_browser_handler(browser_manager))

        # 加载任务
        from core.scheduler import Task
        task_fields = {f.name for f in Task.__dataclass_fields__.values()}

        tasks = db.get_all_tasks()
        for task_data in tasks:
            filtered_data = {k: v for k, v in task_data.items() if k in task_fields}
            task = Task(**filtered_data)
            scheduler.add_task(task)

        # 启动调度器
        scheduler.start()
        logger.info("Scheduler started")

        # 创建主窗口（带云端功能）
        from ui.cloud_main_window import CloudMainWindow
        window = CloudMainWindow(scheduler, db, cloud_client, sync_manager, export_manager)
        window.show()

        logger.info("Application started successfully")
        sys.exit(app.exec())

    except ImportError as e:
        logger.error(f"Missing dependency: {e}")
        print("\n请安装依赖:")
        print("  pip install flask flask-cors requests PyQt6 apscheduler")
        input("\n按回车键退出...")
        sys.exit(1)

    except Exception as e:
        logger.exception("Application failed to start")
        print(f"\n错误: {e}\n")
        input("按回车键退出...")
        sys.exit(1)


if __name__ == '__main__':
    main()