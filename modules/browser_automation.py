"""
浏览器自动化模块
基于 Playwright/Selenium 实现浏览器自动化
"""

import logging
import time
import json
from typing import Dict, List, Optional, Callable

logger = logging.getLogger(__name__)


class BrowserAutomator:
    """浏览器自动化引擎"""

    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.driver = None
        self.is_headless = self.config.get('headless', True)
        self.browser_type = self.config.get('browser', 'chromium')  # chromium, firefox, webkit

    def start(self) -> bool:
        """启动浏览器"""
        try:
            from playwright.sync_api import sync_playwright

            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=self.is_headless)
            self.context = self.browser.new_context()
            self.page = self.context.new_page()

            logger.info(f"Browser started ({self.browser_type}, headless={self.is_headless})")
            return True

        except ImportError:
            # 回退到 Selenium
            return self._start_selenium()
        except Exception as e:
            logger.error(f"Failed to start browser: {e}")
            return False

    def _start_selenium(self) -> bool:
        """使用 Selenium 启动浏览器"""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service

            options = Options()
            if self.is_headless:
                options.add_argument('--headless')

            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')

            self.driver = webdriver.Chrome(options=options)
            logger.info("Browser started (Selenium)")
            return True

        except ImportError:
            logger.error("No browser automation library available. Install playwright or selenium.")
            return False
        except Exception as e:
            logger.error(f"Selenium failed: {e}")
            return False

    def stop(self):
        """关闭浏览器"""
        try:
            if hasattr(self, 'browser') and self.browser:
                self.browser.close()
                self.playwright.stop()
            if self.driver:
                self.driver.quit()
            logger.info("Browser closed")
        except Exception as e:
            logger.error(f"Error closing browser: {e}")

    # ========== 基本操作 ==========

    def goto(self, url: str, wait_until: str = 'load'):
        """打开页面"""
        try:
            if self.driver:
                self.driver.get(url)
            else:
                self.page.goto(url, wait_until=wait_until)
            logger.info(f"Navigated to: {url}")
        except Exception as e:
            logger.error(f"Failed to navigate: {e}")

    def screenshot(self, path: str = 'screenshot.png'):
        """截图"""
        try:
            if self.driver:
                self.driver.save_screenshot(path)
            else:
                self.page.screenshot(path=path)
            logger.info(f"Screenshot saved: {path}")
        except Exception as e:
            logger.error(f"Failed to take screenshot: {e}")

    def get_html(self) -> str:
        """获取页面源码"""
        try:
            if self.driver:
                return self.driver.page_source
            else:
                return self.page.content()
        except Exception as e:
            logger.error(f"Failed to get HTML: {e}")
            return ""

    # ========== 元素操作 ==========

    def click(self, selector: str, timeout: int = 5000):
        """点击元素"""
        try:
            if self.driver:
                from selenium.webdriver.common.by import By
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                element.click()
            else:
                self.page.click(selector, timeout=timeout)
            logger.info(f"Clicked: {selector}")
        except Exception as e:
            logger.error(f"Failed to click {selector}: {e}")

    def fill(self, selector: str, value: str):
        """填写表单"""
        try:
            if self.driver:
                from selenium.webdriver.common.by import By
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                element.clear()
                element.send_keys(value)
            else:
                self.page.fill(selector, value)
            logger.info(f"Filled {selector}: {value}")
        except Exception as e:
            logger.error(f"Failed to fill {selector}: {e}")

    def select(self, selector: str, value: str):
        """选择下拉选项"""
        try:
            if self.driver:
                from selenium.webdriver.support.ui import Select
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                Select(element).select_by_value(value)
            else:
                self.page.select_option(selector, value)
            logger.info(f"Selected {selector}: {value}")
        except Exception as e:
            logger.error(f"Failed to select {selector}: {e}")

    def check(self, selector: str, checked: bool = True):
        """勾选复选框"""
        try:
            if self.driver:
                from selenium.webdriver.common.by import By
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                if checked != element.is_selected():
                    element.click()
            else:
                if checked:
                    self.page.check(selector)
                else:
                    self.page.uncheck(selector)
            logger.info(f"Checked {selector}: {checked}")
        except Exception as e:
            logger.error(f"Failed to check {selector}: {e}")

    # ========== 等待操作 ==========

    def wait_for_selector(self, selector: str, timeout: int = 10000):
        """等待元素出现"""
        try:
            if self.driver:
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                WebDriverWait(self.driver, timeout / 1000).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
            else:
                self.page.wait_for_selector(selector, timeout=timeout)
            logger.info(f"Element found: {selector}")
            return True
        except Exception as e:
            logger.error(f"Element not found: {selector}")
            return False

    def wait_for_load(self, timeout: int = 30000):
        """等待页面加载"""
        try:
            if self.driver:
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                WebDriverWait(self.driver, timeout / 1000).until(
                    EC.EC.url_changes(self.driver.current_url)
                )
            else:
                self.page.wait_for_load_state('networkidle', timeout=timeout)
            logger.info("Page loaded")
        except Exception as e:
            logger.error(f"Page load timeout: {e}")

    def sleep(self, seconds: float):
        """等待"""
        time.sleep(seconds)

    # ========== 数据提取 ==========

    def get_text(self, selector: str) -> str:
        """获取元素文本"""
        try:
            if self.driver:
                from selenium.webdriver.common.by import By
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                return element.text
            else:
                return self.page.text_content(selector) or ''
        except Exception as e:
            logger.error(f"Failed to get text: {e}")
            return ""

    def get_value(self, selector: str) -> str:
        """获取输入框值"""
        try:
            if self.driver:
                from selenium.webdriver.common.by import By
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                return element.get_attribute('value') or ''
            else:
                return self.page.input_value(selector) or ''
        except Exception as e:
            logger.error(f"Failed to get value: {e}")
            return ""

    def get_attribute(self, selector: str, attr: str) -> str:
        """获取元素属性"""
        try:
            if self.driver:
                from selenium.webdriver.common.by import By
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                return element.get_attribute(attr) or ''
            else:
                return self.page.get_attribute(selector, attr) or ''
        except Exception as e:
            logger.error(f"Failed to get attribute: {e}")
            return ""

    def extract_table(self, selector: str = 'table') -> List[List[str]]:
        """提取表格数据"""
        try:
            if self.driver:
                from selenium.webdriver.common.by import By
                tables = self.driver.find_elements(By.CSS_SELECTOR, selector)
            else:
                tables = self.page.query_selector_all(selector)

            results = []
            for table in tables:
                rows = []
                if self.driver:
                    trs = table.find_elements(By.TAG_NAME, 'tr')
                else:
                    trs = table.query_selector_all('tr')

                for tr in trs:
                    if self.driver:
                        cells = tr.find_elements(By.TAG_NAME, 'td')
                        cells += tr.find_elements(By.TAG_NAME, 'th')
                    else:
                        cells = tr.query_selector_all('td, th')

                    row = [cell.text.strip() for cell in cells]
                    if row:
                        rows.append(row)

                if rows:
                    results.append(rows)

            return results
        except Exception as e:
            logger.error(f"Failed to extract table: {e}")
            return []


class BrowserTask:
    """浏览器自动化任务"""

    def __init__(self, task_data: Dict, database, automator_config: Dict = None):
        self.task_data = task_data
        self.database = database
        self.config = task_data.get('config', {})
        self.automator_config = automator_config or {}
        self.browser: Optional[BrowserAutomator] = None

    def execute(self) -> bool:
        """执行浏览器任务"""
        task_id = self.task_data['id']
        logger.info(f"Starting browser task: {task_id}")

        try:
            # 创建浏览器
            self.browser = BrowserAutomator(self.automator_config)

            if not self.browser.start():
                self._log_error("Failed to start browser")
                return False

            # 执行步骤
            steps = self.config.get('steps', [])
            for i, step in enumerate(steps):
                if not self._execute_step(step):
                    self._log_error(f"Step {i + 1} failed: {step.get('action')}")
                    return False

            # 保存结果
            if self.config.get('save_html'):
                html = self.browser.get_html()
                self.database.save_config(f'browser_html_{task_id}', {
                    'html': html,
                    'timestamp': time.time()
                })

            if self.config.get('screenshot'):
                self.browser.screenshot(f'screenshots/{task_id}.png')

            self.browser.stop()
            self._log_success(f"Completed {len(steps)} steps")
            return True

        except Exception as e:
            self._log_error(str(e))
            return False

        finally:
            if self.browser:
                try:
                    self.browser.stop()
                except:
                    pass

    def _execute_step(self, step: Dict) -> bool:
        """执行单个步骤"""
        action = step.get('action')

        if not self.browser:
            return False

        # 等待浏览器初始化
        if action != 'start':
            pass  # browser 已启动

        if action == 'goto':
            self.browser.goto(step.get('url', ''), step.get('wait_until', 'load'))

        elif action == 'click':
            selector = step.get('selector')
            if selector:
                self.browser.click(selector)

        elif action == 'fill':
            selector = step.get('selector')
            value = step.get('value', '')
            if selector:
                self.browser.fill(selector, value)

        elif action == 'select':
            selector = step.get('selector')
            value = step.get('value', '')
            if selector:
                self.browser.select(selector, value)

        elif action == 'check':
            selector = step.get('selector')
            checked = step.get('checked', True)
            if selector:
                self.browser.check(selector, checked)

        elif action == 'wait':
            timeout = step.get('timeout', 10000)
            selector = step.get('selector')
            if selector:
                self.browser.wait_for_selector(selector, timeout)
            else:
                self.browser.sleep(step.get('seconds', 1))

        elif action == 'extract':
            selector = step.get('selector')
            if selector:
                if step.get('type') == 'table':
                    return self._save_table(selector)
                else:
                    text = self.browser.get_text(selector)
                    return bool(text)

        elif action == 'screenshot':
            path = step.get('path', 'screenshot.png')
            self.browser.screenshot(path)

        elif action == 'sleep':
            self.browser.sleep(step.get('seconds', 1))

        return True

    def _save_table(self, selector: str):
        """保存表格数据"""
        try:
            table_data = self.browser.extract_table(selector)
            if table_data:
                task_id = self.task_data['id']
                self.database.save_config(f'browser_table_{task_id}', {
                    'data': table_data,
                    'timestamp': time.time()
                })
                return True
        except Exception as e:
            logger.error(f"Failed to save table: {e}")
        return False

    def _log_success(self, message: str):
        """记录成功日志"""
        self.database.add_log(self.task_data['id'], 'success', message)

    def _log_error(self, message: str):
        """记录错误日志"""
        self.database.add_log(self.task_data['id'], 'failed', message)


class BrowserManager:
    """浏览器任务管理器"""

    def __init__(self, database):
        self.database = database
        self.tasks: Dict[str, BrowserTask] = {}

    def create_task(self, task_data: Dict, config: Dict = None) -> BrowserTask:
        """创建浏览器任务"""
        task_id = task_data.get('id', 'unknown')
        task = BrowserTask(task_data, self.database, config)
        self.tasks[task_id] = task
        return task

    def get_task(self, task_id: str) -> Optional[BrowserTask]:
        """获取任务"""
        return self.tasks.get(task_id)


def create_browser_handler(browser_manager: BrowserManager) -> Callable:
    """创建浏览器任务处理器"""
    def handler(task):
        browser_task = browser_manager.create_task({
            'id': task.id,
            'name': task.name,
            'config': task.config
        })
        return browser_task.execute()

    return handler