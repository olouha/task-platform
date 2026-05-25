"""
网页抓取模块
支持定时抓取网页数据
"""

import requests
from bs4 import BeautifulSoup
import logging
import json
import time
from typing import Dict, List, Optional, Callable

logger = logging.getLogger(__name__)


class WebScraper:
    """网页抓取引擎"""

    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.session = requests.Session()

        # 默认请求头
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
        })

        # 超时设置
        self.timeout = self.config.get('timeout', 30)

    def fetch(self, url: str, method: str = 'GET', **kwargs) -> Optional[requests.Response]:
        """发送请求"""
        try:
            if method.upper() == 'GET':
                response = self.session.get(url, timeout=self.timeout, **kwargs)
            else:
                response = self.session.post(url, timeout=self.timeout, **kwargs)

            response.raise_for_status()
            return response

        except requests.Timeout:
            logger.error(f"Request timeout: {url}")
        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")

        return None

    def parse_html(self, response: requests.Response) -> BeautifulSoup:
        """解析HTML"""
        return BeautifulSoup(response.text, 'html.parser')

    def parse_json(self, response: requests.Response) -> Dict:
        """解析JSON"""
        return response.json()

    def extract_by_css(self, soup: BeautifulSoup, selector: str) -> List[str]:
        """CSS选择器提取"""
        elements = soup.select(selector)
        return [elem.get_text(strip=True) for elem in elements]

    def extract_by_xpath(self, html: str, xpath: str) -> List[str]:
        """XPath提取（需要lxml）"""
        try:
            from lxml import etree
            tree = etree.HTML(html)
            elements = tree.xpath(xpath)
            return [elem.text_content().strip() if hasattr(elem, 'text_content') else str(elem) for elem in elements]
        except ImportError:
            logger.warning("lxml not installed, XPath extraction unavailable")
            return []

    def extract_table(self, soup: BeautifulSoup, selector: str = 'table') -> List[List[str]]:
        """提取表格数据"""
        tables = soup.select(selector)
        results = []

        for table in tables:
            rows = []
            for tr in table.find_all('tr'):
                cells = [td.get_text(strip=True) for td in tr.find_all(['td', 'th'])]
                if cells:
                    rows.append(cells)
            if rows:
                results.append(rows)

        return results


class ScraperTask:
    """抓取任务"""

    def __init__(self, task_data: Dict, database):
        self.task_data = task_data
        self.database = database
        self.config = task_data.get('config', {})
        self.scraper = WebScraper(self.config)

    def execute(self) -> bool:
        """执行抓取任务"""
        url = self.config.get('url')
        if not url:
            logger.error("No URL specified")
            return False

        logger.info(f"Scraping: {url}")

        try:
            # 发送请求
            response = self.scraper.fetch(url)
            if not response:
                self._log_error("Failed to fetch URL")
                return False

            # 解析数据
            data = self._parse_data(response)

            # 保存数据
            self._save_data(data)

            self._log_success(f"Scraped {len(data.get('items', []))} items")
            return True

        except Exception as e:
            self._log_error(str(e))
            return False

    def _parse_data(self, response) -> Dict:
        """解析数据"""
        content_type = response.headers.get('Content-Type', '')

        if 'json' in content_type:
            return {'type': 'json', 'data': self.scraper.parse_json(response)}
        else:
            soup = self.scraper.parse_html(response)

            # 提取配置
            selectors = self.config.get('selectors', {})

            result = {
                'type': 'html',
                'title': soup.title.string if soup.title else '',
                'items': []
            }

            # 按选择器提取
            if selectors.get('items'):
                result['items'] = self.scraper.extract_by_css(soup, selectors['items'])

            # 提取表格
            if selectors.get('table'):
                result['tables'] = self.scraper.extract_table(soup, selectors['table'])

            return result

    def _save_data(self, data: Dict):
        """保存抓取的数据"""
        task_id = self.task_data['id']

        # 保存到数据库
        self.database.save_config(f'scraper_data_{task_id}', {
            'data': data,
            'timestamp': time.time()
        })

        # 保存原始HTML/JSON
        self.database.save_config(f'scraper_raw_{task_id}', {
            'raw': data,
            'fetched_at': time.time()
        })

    def _log_success(self, message: str):
        """记录成功日志"""
        self.database.add_log(self.task_data['id'], 'success', message)

    def _log_error(self, message: str):
        """记录错误日志"""
        self.database.add_log(self.task_data['id'], 'failed', message)


class ScraperManager:
    """抓取任务管理器"""

    def __init__(self, database):
        self.database = database
        self.scrapers: Dict[str, ScraperTask] = {}

    def create_scraper_task(self, task_data: Dict) -> ScraperTask:
        """创建抓取任务"""
        task_id = task_data.get('id', 'unknown')
        scraper = ScraperTask(task_data, self.database)
        self.scrapers[task_id] = scraper
        return scraper

    def get_scraper(self, task_id: str) -> Optional[ScraperTask]:
        """获取抓取任务"""
        return self.scrapers.get(task_id)

    def list_scrapers(self) -> List[Dict]:
        """列出所有抓取任务"""
        return [
            {'task_id': k, 'task_data': v.task_data}
            for k, v in self.scrapers.items()
        ]


def create_scraper_handler(scraper_manager: ScraperManager) -> Callable:
    """创建抓取任务处理器"""
    def handler(task):
        scraper = scraper_manager.create_scraper_task({
            'id': task.id,
            'name': task.name,
            'config': task.config
        })
        return scraper.execute()

    return handler