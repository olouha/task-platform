"""
TaskPlatform - 任务调度平台
支持自动云端同步
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


def create_database():
    """根据配置创建数据库"""
    config_path = 'config/cloud.json'

    # 默认使用本地 SQLite
    from core.database import DatabaseManager
    db = DatabaseManager()

    # 检查云端配置
    if os.path.exists(config_path):
        try:
            import json
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            mode = config.get('mode', 'local')

            if mode == 'supabase':
                logger.info("Connecting to Supabase cloud database...")
                from cloud.supabase_client import CloudDatabase
                supabase_url = config.get('supabase_url')
                supabase_key = config.get('supabase_key')

                if supabase_url and supabase_key:
                    db = CloudDatabase(supabase_url, supabase_key)
                    if db.is_connected():
                        logger.info("Connected to Supabase!")
                        return db
                    else:
                        logger.warning("Supabase connection failed, using local database")

            elif mode == 'cloudflare-workers':
                logger.info("Connecting to Cloudflare Workers...")
                from cloud.cloudflare_client import CloudDatabase
                api_url = config.get('api_url')

                if api_url:
                    db = CloudDatabase(api_url)
                    if db.is_connected():
                        logger.info("Connected to Cloudflare!")
                        return db
                    else:
                        logger.warning("Cloudflare connection failed, using local database")

        except Exception as e:
            logger.warning(f"Cloud config error: {e}, using local database")

    logger.info("Using local database")
    return db


def main():
    """主函数"""
    logger.info("Starting TaskPlatform...")

    try:
        from PyQt6.QtWidgets import QApplication

        app = QApplication(sys.argv)
        app.setApplicationName("TaskPlatform")
        app.setOrganizationName("TaskPlatform")

        # 创建数据库（自动检测云端或本地）
        logger.info("Initializing database...")
        db = create_database()

        # 初始化调度器
        logger.info("Initializing scheduler...")
        from core import Scheduler
        scheduler = Scheduler()

        # 初始化模块管理器
        logger.info("Initializing modules...")
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
        task_fields = set(Task.__dataclass_fields__.keys())

        tasks = db.get_all_tasks()
        for task_data in tasks:
            filtered_data = {k: v for k, v in task_data.items() if k in task_fields}
            task = Task(**filtered_data)
            scheduler.add_task(task)

        # 启动调度器
        scheduler.start()
        logger.info("Scheduler started")

        # 创建主窗口
        from ui.main_window import MainWindow
        window = MainWindow(scheduler, db, None, export_manager)
        window.show()

        logger.info("Application started successfully")
        sys.exit(app.exec())

    except ImportError as e:
        logger.error(f"Missing dependency: {e}")
        print("\n请安装依赖:")
        print("  pip install PyQt6 APScheduler requests beautifulsoup4 openpyxl")
        input("\n按回车键退出...")
        sys.exit(1)

    except Exception as e:
        logger.exception("Application failed to start")
        print(f"\n错误: {e}\n")
        input("按回车键退出...")
        sys.exit(1)


if __name__ == '__main__':
    main()
