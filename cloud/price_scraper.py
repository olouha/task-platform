"""
价格抓取模块
支持从我的钢铁网、有色金属网等网站抓取价格
"""

import requests
from bs4 import BeautifulSoup
import logging
import json
from datetime import datetime, date
from typing import Dict, List, Optional, Callable
import re
import time

logger = logging.getLogger(__name__)


class PriceScraper:
    """价格抓取器"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        })
        self.timeout = 30

    def fetch(self, url: str, selector: str = None, method: str = 'GET', **kwargs) -> Optional[Dict]:
        """抓取网页"""
        try:
            response = self.session.request(method, url, timeout=self.timeout, **kwargs)
            response.raise_for_status()

            result = {
                'url': url,
                'status_code': response.status_code,
                'content': response.text,
                'success': True
            }

            if selector:
                soup = BeautifulSoup(response.text, 'html.parser')
                elements = soup.select(selector)

                if elements:
                    result['data'] = [elem.get_text(strip=True) for elem in elements]
                    result['raw_elements'] = [str(elem) for elem in elements]

            return result

        except requests.RequestException as e:
            logger.error(f"Fetch failed: {e}")
            return {'url': url, 'success': False, 'error': str(e)}

    def parse_price(self, text: str) -> Optional[float]:
        """解析价格文本"""
        # 移除常见非数字字符
        text = text.replace('¥', '').replace('元', '').replace(',', '').replace('，', '')
        text = text.replace('吨', '').replace('m³', '').strip()

        # 匹配数字
        match = re.search(r'[\d,]+\.?\d*', text)
        if match:
            price_str = match.group().replace(',', '')
            try:
                return float(price_str)
            except:
                pass

        return None

    def fetch_mysteel_price(self, selector: str = '.price') -> Optional[float]:
        """抓取我的钢铁网价格"""
        # 示例URL - 实际使用时需要配置
        urls = [
            'https://www.mysteel.com.cn/price/rebar',
            'https://www.mysteel.com.cn/price/steel',
        ]

        for url in urls:
            result = self.fetch(url, selector)
            if result and result.get('success') and result.get('data'):
                prices = [self.parse_price(p) for p in result['data']]
                prices = [p for p in prices if p]
                if prices:
                    return sum(prices) / len(prices)

        return None

    def fetch_ccmn_price(self, selector: str = '.price') -> Optional[float]:
        """抓取有色金属网价格"""
        urls = [
            'https://www.ccmn.cn/aluminum/',
            'https://www.ccmn.cn/copper/',
        ]

        for url in urls:
            result = self.fetch(url, selector)
            if result and result.get('success') and result.get('data'):
                prices = [self.parse_price(p) for p in result['data']]
                prices = [p for p in prices if p]
                if prices:
                    return sum(prices) / len(prices)

        return None

    def test_selector(self, url: str, selector: str) -> Dict:
        """测试选择器"""
        result = self.fetch(url, selector)

        if not result or not result.get('success'):
            return {
                'success': False,
                'error': result.get('error', 'Unknown error'),
                'data': []
            }

        data = result.get('data', [])
        prices = []

        for item in data:
            price = self.parse_price(item)
            if price:
                prices.append(price)

        return {
            'success': True,
            'url': url,
            'selector': selector,
            'total_elements': len(data),
            'valid_prices': prices,
            'average_price': sum(prices) / len(prices) if prices else None,
            'sample_data': data[:5]  # 返回前5个样本
        }


class PriceFetcher:
    """价格获取器 - 管理多个价格来源"""

    def __init__(self, database):
        self.db = database
        self.scraper = PriceScraper()

    def fetch_all_prices(self, on_progress: Callable = None) -> Dict:
        """抓取所有配置的价格"""
        sources = self.db.get_price_sources()
        results = {
            'success': 0,
            'failed': 0,
            'prices': []
        }

        for i, source in enumerate(sources):
            if not source.get('is_active'):
                continue

            if on_progress:
                on_progress(i + 1, len(sources), source.get('name'))

            price = self._fetch_source(source)
            if price:
                results['success'] += 1
                results['prices'].append(price)

                # 保存到数据库
                self.db.add_price_record(
                    material_id=source.get('material_id'),
                    source_id=source.get('id'),
                    price=price,
                    unit=self._get_unit(source.get('material_category')),
                    recorded_date=date.today().isoformat()
                )
            else:
                results['failed'] += 1

        return results

    def _fetch_source(self, source: Dict) -> Optional[float]:
        """抓取单个来源"""
        url = source.get('price_url')
        selector = source.get('selector')

        if not url:
            return None

        result = self.scraper.fetch(url, selector)
        if result and result.get('success') and result.get('data'):
            prices = [self.scraper.parse_price(p) for p in result['data']]
            prices = [p for p in prices if p and p > 0]
            if prices:
                return sum(prices) / len(prices)

        return None

    def _get_unit(self, category: str) -> str:
        """获取材料单位"""
        units = {
            '钢筋类': '吨',
            '混凝土类': 'm³',
            '金属类': '吨',
            '有色金属类': '吨'
        }
        return units.get(category, '吨')

    def test_source(self, source_id: str) -> Dict:
        """测试价格来源"""
        source = self.db.get_price_sources()
        source = next((s for s in source if s.get('id') == source_id), None)

        if not source:
            return {'success': False, 'error': 'Source not found'}

        url = source.get('price_url')
        selector = source.get('selector')

        return self.scraper.test_selector(url, selector)

    def fetch_by_category(self, category: str) -> List[Dict]:
        """按分类抓取"""
        sources = self.db.get_price_sources_by_category(category)
        results = []

        for source in sources:
            if not source.get('is_active'):
                continue

            price = self._fetch_source(source)
            if price:
                results.append({
                    'source_id': source.get('id'),
                    'source_name': source.get('name'),
                    'category': category,
                    'price': price,
                    'unit': self._get_unit(category),
                    'fetched_at': datetime.now().isoformat()
                })

                # 保存
                self.db.add_price_record(
                    material_id=source.get('material_id'),
                    source_id=source.get('id'),
                    price=price,
                    unit=self._get_unit(category),
                    recorded_date=date.today().isoformat()
                )

        return results
