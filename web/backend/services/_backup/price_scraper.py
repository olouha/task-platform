"""
价格抓取服务
支持：我的钢铁网、有色金属网、信息价
"""

import requests
from bs4 import BeautifulSoup
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class PriceFetcher(ABC):
    """价格抓取器基类"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        })
        self.timeout = 30

    @abstractmethod
    def fetch(self) -> Optional[Dict]:
        """抓取价格数据"""
        pass

    def parse_price(self, text: str) -> Optional[float]:
        """解析价格文本"""
        text = text.replace('¥', '').replace('元', '').replace(',', '').replace('，', '')
        text = text.replace('吨', '').replace('m³', '').replace('m3', '').strip()
        match = re.search(r'[\d,]+\.?\d*', text)
        if match:
            price_str = match.group().replace(',', '')
            try:
                return float(price_str)
            except:
                pass
        return None


class MysteelFetcher(PriceFetcher):
    """我的钢铁网价格抓取器"""

    def __init__(self):
        super().__init__()
        self.base_url = "https://www.mysteel.com.cn"

    async def fetch_rebar_price(self) -> Optional[Dict]:
        """抓取钢筋价格"""
        return await self._fetch_category('钢筋', 'rebar')

    async def fetch_concrete_price(self) -> Optional[Dict]:
        """抓取混凝土价格"""
        return await self._fetch_category('混凝土', 'concrete')

    async def fetch_steel_price(self) -> Optional[Dict]:
        """抓取钢材价格"""
        return await self._fetch_category('钢材', 'steel')

    async def _fetch_category(self, category: str, price_type: str) -> Optional[Dict]:
        """按分类抓取"""
        # 实际 URL 需要根据网站结构调整
        urls = {
            'rebar': f'{self.base_url}/price/rebar.html',
            'concrete': f'{self.base_url}/price/concrete.html',
            'steel': f'{self.base_url}/price/steel.html',
        }

        url = urls.get(price_type)
        if not url:
            return None

        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # 尝试多种选择器
            selectors = [
                '.price-value',
                '.price',
                '[class*="price"]',
                '.data-value',
                '#price',
            ]

            prices = []
            for selector in selectors:
                elements = soup.select(selector)
                for elem in elements:
                    price = self.parse_price(elem.get_text())
                    if price and price > 0:
                        prices.append(price)

            if prices:
                return {
                    'source': '我的钢铁网',
                    'category': category,
                    'price': sum(prices) / len(prices),
                    'prices': prices,
                    'unit': '吨',
                    'fetched_at': datetime.now().isoformat(),
                    'url': url
                }

        except Exception as e:
            logger.error(f"抓取失败 {category}: {e}")

        return None

    def fetch(self) -> Optional[Dict]:
        """同步抓取接口"""
        return None


class CcmnFetcher(PriceFetcher):
    """有色金属网价格抓取器"""

    def __init__(self):
        super().__init__()
        self.base_url = "https://www.ccmn.cn"

    async def fetch_aluminum_price(self) -> Optional[Dict]:
        """抓取铝价"""
        return await self._fetch_metal('铝', 'aluminum')

    async def fetch_copper_price(self) -> Optional[Dict]:
        """抓取铜价"""
        return await self._fetch_metal('铜', 'copper')

    async def fetch_zinc_price(self) -> Optional[Dict]:
        """抓取锌价"""
        return await self._fetch_metal('锌', 'zinc')

    async def _fetch_metal(self, name: str, metal_type: str) -> Optional[Dict]:
        """抓取有色金属价格"""
        urls = {
            'aluminum': f'{self.base_url}/aluminum/',
            'copper': f'{self.base_url}/copper/',
            'zinc': f'{self.base_url}/zinc/',
        }

        url = urls.get(metal_type)
        if not url:
            return None

        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # 有色金属网选择器
            selectors = [
                '.latest-price',
                '.price-current',
                '.market-price',
                '[class*="price"]',
            ]

            prices = []
            for selector in selectors:
                elements = soup.select(selector)
                for elem in elements:
                    price = self.parse_price(elem.get_text())
                    if price and price > 100:  # 有色金属价格通常较高
                        prices.append(price)

            if prices:
                return {
                    'source': '有色金属网',
                    'category': f'{name}锭',
                    'price': sum(prices) / len(prices),
                    'prices': prices,
                    'unit': '吨',
                    'fetched_at': datetime.now().isoformat(),
                    'url': url
                }

        except Exception as e:
            logger.error(f"抓取失败 {name}: {e}")

        return None

    def fetch(self) -> Optional[Dict]:
        return None


class InfoPriceFetcher(PriceFetcher):
    """信息价抓取器（地方造价信息网）"""

    def __init__(self):
        super().__init__()
        # 信息价通常需要登录或付费，这里提供配置框架
        self.config = {
            # 各省市信息价网站配置
            'shanghai': 'https://www.shsjc.com.cn',
            'beijing': 'https://www.bjcosta.com.cn',
            'guangzhou': 'https://www.gzq.com.cn',
        }

    async def fetch_info_price(self, region: str = 'shanghai') -> Optional[Dict]:
        """抓取信息价"""
        base_url = self.config.get(region)
        if not base_url:
            return None

        try:
            # 信息价通常为 JSON API
            api_url = f'{base_url}/api/info_price/latest'

            response = self.session.get(api_url, timeout=self.timeout)
            if response.status_code == 200:
                data = response.json()
                return {
                    'source': f'{region}信息价',
                    'category': '综合',
                    'price': data.get('price'),
                    'unit': data.get('unit', '吨'),
                    'fetched_at': datetime.now().isoformat(),
                    'region': region
                }

        except Exception as e:
            logger.error(f"抓取信息价失败 {region}: {e}")

        return None

    def fetch(self) -> Optional[Dict]:
        return None


class PriceScraperService:
    """价格抓取服务"""

    def __init__(self):
        self.mysteel = MysteelFetcher()
        self.ccmn = CcmnFetcher()
        self.info_price = InfoPriceFetcher()

    async def fetch_all(self) -> Dict[str, List[Dict]]:
        """抓取所有来源的价格"""
        results = {
            '钢筋类': [],
            '混凝土类': [],
            '金属类': [],
            '有色金属类': [],
            '信息价': []
        }

        # 我的钢铁网
        for category, fetcher in [
            ('钢筋类', self.mysteel.fetch_rebar_price),
            ('混凝土类', self.mysteel.fetch_concrete_price),
        ]:
            result = await fetcher()
            if result:
                results[category].append(result)

        # 有色金属网
        for name, fetcher in [
            ('铝锭', self.ccmn.fetch_aluminum_price),
            ('铜锭', self.ccmn.fetch_copper_price),
            ('锌锭', self.ccmn.fetch_zinc_price),
        ]:
            result = await fetcher()
            if result:
                results['有色金属类'].append(result)

        return results

    async def fetch_by_category(self, category: str) -> List[Dict]:
        """按分类抓取"""
        if category == '钢筋类':
            result = await self.mysteel.fetch_rebar_price()
            return [result] if result else []
        elif category == '混凝土类':
            result = await self.mysteel.fetch_concrete_price()
            return [result] if result else []
        elif category == '有色金属类':
            results = []
            for fetcher in [
                self.ccmn.fetch_aluminum_price(),
                self.ccmn.fetch_copper_price(),
                self.ccmn.fetch_zinc_price(),
            ]:
                result = await fetcher()
                if result:
                    results.append(result)
            return results

        return []

    def test_connection(self, source: str) -> Dict:
        """测试连接"""
        try:
            if source == 'mysteel':
                response = self.session.get(
                    'https://www.mysteel.com.cn',
                    timeout=10
                )
                return {
                    'success': response.status_code == 200,
                    'status_code': response.status_code,
                    'url': 'https://www.mysteel.com.cn'
                }
            elif source == 'ccmn':
                response = self.session.get(
                    'https://www.ccmn.cn',
                    timeout=10
                )
                return {
                    'success': response.status_code == 200,
                    'status_code': response.status_code,
                    'url': 'https://www.ccmn.cn'
                }

        except Exception as e:
            return {'success': False, 'error': str(e)}

        return {'success': False, 'error': 'Unknown source'}