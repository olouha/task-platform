"""
多材料认证爬虫 v3.1
支持每个网站抓取多种材料
"""

import time
import logging
import json
import re
import ssl
import urllib.request
import urllib.error
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from pathlib import Path
from http.cookiejar import CookieJar, MozillaCookieJar

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/authenticated_scraper.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

Path('logs').mkdir(exist_ok=True)


@dataclass
class SiteCredentials:
    """网站认证信息"""
    source_id: str = ""
    source_name: str = ""
    website_url: str = ""
    username: str = ""
    password: str = ""
    extra_data: Dict = field(default_factory=dict)


@dataclass
class MaterialPrice:
    """单个材料价格"""
    material_id: str = ""      # 材料ID（如 aaaa1111-...）
    material_name: str = ""    # 材料名称
    spec: str = ""             # 规格
    price: float = 0.0         # 价格
    unit: str = ""             # 单位
    change_rate: float = 0.0   # 涨跌百分比


@dataclass
class CrawlResult:
    """抓取结果 - 支持多种材料"""
    success: bool = False
    source_name: str = ""
    url: str = ""
    fetched_at: str = ""
    error_message: str = ""
    prices: List[MaterialPrice] = field(default_factory=list)
    raw_html: str = ""         # 原始HTML（用于调试）


# ========== 基类实现 ==========

class AuthenticatedScraper(ABC):
    """认证爬虫基类 - 支持多材料"""

    def __init__(self, credentials: SiteCredentials = None):
        self.credentials = credentials
        self.session = None
        self.last_fetch_file = f"logs/fetch_{self.get_source_id()}.json"
        self.cookie_file = f"logs/cookies_{self.get_source_id()}.txt"

    def get_source_id(self) -> str:
        return self.credentials.source_id if self.credentials else self.__class__.__name__

    def _check_rate_limit(self) -> Tuple[bool, str]:
        """检查频率限制 - 每天最多一次"""
        path = Path(self.last_fetch_file)
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    last_fetch = datetime.fromisoformat(data['last_fetch'])
                    now = datetime.now()

                    if last_fetch.date() == now.date():
                        return False, f"今日({now.strftime('%Y-%m-%d')})已抓取，下次于明日 00:00 后执行"

                    hours_since = (now - last_fetch).total_seconds() / 3600
                    if hours_since < 24:
                        next_time = last_fetch + timedelta(hours=24)
                        return False, f"需等待 {24 - hours_since:.1f} 小时，下次抓取: {next_time.strftime('%Y-%m-%d %H:%M')}"
            except Exception as e:
                logger.warning(f"读取抓取记录失败: {e}")

        return True, "可以抓取"

    def _save_fetch_record(self, success: bool, price_count: int = 0, error: str = None):
        """保存抓取记录"""
        path = Path(self.last_fetch_file)
        path.parent.mkdir(exist_ok=True)

        record = {
            'last_fetch': datetime.now().isoformat(),
            'success': success,
            'source_id': self.get_source_id(),
            'source_name': self.get_source_name(),
            'prices_count': price_count,
        }

        if error:
            record['error'] = error

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(record, f, ensure_ascii=False, indent=2)

    def _load_cookies(self) -> Optional[CookieJar]:
        """加载保存的 cookies"""
        path = Path(self.cookie_file)
        if path.exists():
            try:
                cookie_jar = MozillaCookieJar(self.cookie_file)
                cookie_jar.load(ignore_discard=True, ignore_expires=True)
                return cookie_jar
            except:
                pass
        return None

    def _save_cookies(self, cookie_jar: CookieJar):
        """保存 cookies"""
        try:
            cookie_jar.save(ignore_discard=True, ignore_expires=True)
        except:
            pass

    def _create_ssl_context(self) -> ssl.SSLContext:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx

    def _get_user_agent(self) -> str:
        return (
            "TaskPlatform-PriceMonitor/3.1 "
            f"(purpose: engineering cost analysis; "
            f"frequency: 1/day; "
            f"source: {self.get_source_name()})"
        )

    def _fetch_page(self, url: str, timeout: int = 30, need_auth: bool = True) -> Optional[str]:
        """抓取页面"""
        ctx = self._create_ssl_context()
        headers = {
            'User-Agent': self._get_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }

        cookie_jar = self._load_cookies() if need_auth else None
        if cookie_jar:
            opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))
        else:
            opener = urllib.request.build_opener()

        req = urllib.request.Request(url, headers=headers)

        try:
            logger.info(f"📡 请求: {url}")
            with opener.open(req, timeout=timeout, context=ctx) as response:
                if response.status == 200:
                    logger.info(f"✅ 响应成功")
                    if cookie_jar:
                        self._save_cookies(cookie_jar)
                    return response.read().decode('utf-8')

        except urllib.error.HTTPError as e:
            logger.error(f"❌ HTTP 错误: {e.code}")
            if e.code == 401:
                self._handle_auth_required()
        except Exception as e:
            logger.error(f"❌ 请求失败: {e}")

        return None

    def _handle_auth_required(self):
        if not self.credentials or not self.credentials.username:
            logger.warning("⚠️ 未配置认证信息")
            return False
        return self.login()

    def login(self) -> bool:
        """登录网站"""
        if not self.credentials or not self.credentials.username:
            return False

        login_url = self.get_login_url()
        if not login_url:
            return False

        data = self.get_login_data()
        if not data:
            return False

        ctx = self._create_ssl_context()
        import urllib.parse
        post_data = urllib.parse.urlencode(data).encode('utf-8')

        headers = {
            'User-Agent': self._get_user_agent(),
            'Content-Type': 'application/x-www-form-urlencoded',
        }

        req = urllib.request.Request(login_url, data=post_data, headers=headers)

        try:
            logger.info(f"🔐 正在登录: {login_url}")
            with urllib.request.urlopen(req, timeout=30, context=ctx) as response:
                if response.status == 200:
                    logger.info("✅ 登录成功")
                    return True
        except Exception as e:
            logger.error(f"❌ 登录失败: {e}")

        return False

    @abstractmethod
    def get_source_name(self) -> str:
        pass

    @abstractmethod
    def get_login_url(self) -> str:
        pass

    @abstractmethod
    def get_login_data(self) -> Dict[str, str]:
        pass

    @abstractmethod
    def get_price_url(self) -> str:
        pass

    @abstractmethod
    def parse_prices(self, html: str) -> List[MaterialPrice]:
        """解析页面中的所有材料价格"""
        pass

    def fetch(self, force: bool = False) -> CrawlResult:
        """执行抓取 - 返回多种材料价格"""
        result = CrawlResult(success=False, source_name=self.get_source_name())

        # 检查频率限制
        if not force:
            can_fetch, reason = self._check_rate_limit()
            if not can_fetch:
                logger.info(f"⏭️ 跳过抓取: {reason}")
                result.error_message = reason
                return result

        # 登录
        if self.credentials and self.credentials.username:
            if not self.login():
                result.error_message = "登录失败"
                return result

        # 抓取
        price_url = self.get_price_url()
        if not price_url:
            result.error_message = "未配置价格 URL"
            return result

        html = self._fetch_page(price_url)
        if not html:
            result.error_message = "页面抓取失败"
            self._save_fetch_record(False, error=result.error_message)
            return result

        # 解析所有材料价格
        prices = self.parse_prices(html)
        if not prices:
            result.error_message = "未解析到任何材料价格"
            self._save_fetch_record(False, error=result.error_message)
            return result

        # 成功
        result.success = True
        result.prices = prices
        result.url = price_url
        result.fetched_at = datetime.now().isoformat()

        self._save_fetch_record(True, len(prices))
        logger.info(f"✅ 抓取成功: {len(prices)} 种材料")
        for p in prices:
            logger.info(f"   - {p.material_name}: ¥{p.price:.2f}/{p.unit}")

        return result


# ========== 我的钢铁网爬虫（多材料）==========

class MysteelScraper(AuthenticatedScraper):
    """我的钢铁网 - 抓取钢筋、混凝土、钢材等多种材料"""

    # 材料配置：CSS选择器 -> (材料ID前缀, 材料名称, 单位, 价格范围)
    MATERIAL_CONFIGS = [
        {
            'id_prefix': 'aaaa1111',
            'name_pattern': r'HRB400[螺纹]*钢筋',
            'selector': '.rebar-price, [class*="rebar"], .price-rebar',
            'unit': '元/吨',
            'min_price': 3000,
            'max_price': 6000,
            'name': 'HRB400螺纹钢筋',
            'spec': '12-25mm',
        },
        {
            'id_prefix': 'aaaa2222',
            'name_pattern': r'HPB300[光圆]*钢筋',
            'selector': '.hpb-price, [class*="hpb"]',
            'unit': '元/吨',
            'min_price': 3000,
            'max_price': 6000,
            'name': 'HPB300光圆钢筋',
            'spec': '8-10mm',
        },
        {
            'id_prefix': 'bbbb4444',
            'name_pattern': r'C30混凝土',
            'selector': '.concrete-price, [class*="concrete"], .price-c30',
            'unit': '元/m³',
            'min_price': 400,
            'max_price': 1000,
            'name': 'C30混凝土',
            'spec': '普通',
        },
        {
            'id_prefix': 'bbbb3333',
            'name_pattern': r'C25混凝土',
            'selector': '.price-c25',
            'unit': '元/m³',
            'min_price': 400,
            'max_price': 1000,
            'name': 'C25混凝土',
            'spec': '普通',
        },
        {
            'id_prefix': 'bbbb5555',
            'name_pattern': r'C35混凝土',
            'selector': '.price-c35',
            'unit': '元/m³',
            'min_price': 400,
            'max_price': 1200,
            'name': 'C35混凝土',
            'spec': '普通',
        },
    ]

    def get_source_name(self) -> str:
        return "我的钢铁网"

    def get_login_url(self) -> str:
        return "https://www.mysteel.com.cn/login"

    def get_login_data(self) -> Dict[str, str]:
        if not self.credentials:
            return {}
        return {
            'username': self.credentials.username,
            'password': self.credentials.password,
        }

    def get_price_url(self) -> str:
        return "https://www.mysteel.com.cn/price/index.html"

    def parse_prices(self, html: str) -> List[MaterialPrice]:
        """解析页面中的所有材料价格"""
        from bs4 import BeautifulSoup

        try:
            soup = BeautifulSoup(html, 'html.parser')
            prices = []

            # 遍历所有材料配置
            for config in self.MATERIAL_CONFIGS:
                found_price = self._extract_price_for_material(soup, config)
                if found_price:
                    prices.append(found_price)

            # 如果特定选择器没找到，尝试通用提取
            if not prices:
                prices = self._extract_all_prices(soup)

            return prices

        except Exception as e:
            logger.error(f"解析失败: {e}")
            return []

    def _extract_price_for_material(self, soup: BeautifulSoup, config: Dict) -> Optional[MaterialPrice]:
        """从页面提取特定材料的的价格"""
        try:
            # 尝试多个选择器
            selectors = config['selector'].split(', ')

            for selector in selectors:
                elements = soup.select(selector.strip())
                for elem in elements:
                    text = elem.get_text(strip=True)
                    price = self._parse_price_from_text(text, config['min_price'], config['max_price'])

                    if price:
                        return MaterialPrice(
                            material_id=config['id_prefix'] + '-1111-1111-111111111111',
                            material_name=config['name'],
                            spec=config['spec'],
                            price=price,
                            unit=config['unit'],
                            change_rate=0.0  # 可从页面解析
                        )

        except Exception as e:
            logger.debug(f"提取 {config['name']} 价格失败: {e}")

        return None

    def _parse_price_from_text(self, text: str, min_price: float, max_price: float) -> Optional[float]:
        """从文本中解析价格"""
        # 清理文本
        text = text.replace('¥', '').replace('元', '').replace(',', '').replace('，', '').strip()

        # 提取数字
        match = re.search(r'(\d+(?:,\d{3})*(?:\.\d+)?)', text)
        if match:
            try:
                price = float(match.group(1).replace(',', ''))
                if min_price < price < max_price:
                    return price
            except:
                pass

        return None

    def _extract_all_prices(self, soup: BeautifulSoup) -> List[MaterialPrice]:
        """通用提取：从页面中提取所有价格"""
        prices = []
        seen_values = set()

        # 遍历所有可能包含价格的元素
        price_elements = soup.find_all(class_=lambda x: x and 'price' in x.lower())
        price_elements += soup.find_all(attrs={'data-price': True})

        for elem in price_elements:
            text = elem.get_text(strip=True)
            match = re.search(r'(\d{3,5}(?:\.\d+)?)', text.replace(',', ''))
            if match:
                try:
                    value = float(match.group(1))
                    if value not in seen_values and 300 < value < 100000:
                        seen_values.add(value)

                        # 根据价格范围判断材料类型
                        if 3000 < value < 7000:  # 钢筋
                            prices.append(MaterialPrice(
                                material_id='aaaa1111-1111-1111-1111-111111111111',
                                material_name='HRB400螺纹钢筋',
                                spec='12-25mm',
                                price=value,
                                unit='元/吨'
                            ))
                        elif 400 < value < 1200:  # 混凝土
                            prices.append(MaterialPrice(
                                material_id='bbbb4444-4444-4444-4444-444444444444',
                                material_name='C30混凝土',
                                spec='普通',
                                price=value,
                                unit='元/m³'
                            ))

                except:
                    pass

        return prices


# ========== 有色金属网爬虫（多材料）==========

class CcmnScraper(AuthenticatedScraper):
    """有色金属网 - 抓取铝、铜、锌等多种材料"""

    MATERIAL_CONFIGS = [
        {
            'id_prefix': 'cccc3333',
            'name': '铝锭',
            'spec': 'A00',
            'selector': '.al-price, [class*="aluminum"], .price-al',
            'unit': '元/吨',
            'min_price': 15000,
            'max_price': 25000,
        },
        {
            'id_prefix': 'cccc4444',
            'name': '铜锭',
            'spec': '1#电解铜',
            'selector': '.cu-price, [class*="copper"], .price-cu',
            'unit': '元/吨',
            'min_price': 50000,
            'max_price': 90000,
        },
        {
            'id_prefix': 'cccc5555',
            'name': '锌锭',
            'spec': '0#',
            'selector': '.zn-price, [class*="zinc"], .price-zn',
            'unit': '元/吨',
            'min_price': 15000,
            'max_price': 30000,
        },
    ]

    def get_source_name(self) -> str:
        return "有色金属网"

    def get_login_url(self) -> str:
        return "https://www.ccmn.cn/login"

    def get_login_data(self) -> Dict[str, str]:
        if not self.credentials:
            return {}
        return {
            'username': self.credentials.username,
            'password': self.credentials.password,
        }

    def get_price_url(self) -> str:
        return "https://www.ccmn.cn/market.html"  # 综合市场页面

    def parse_prices(self, html: str) -> List[MaterialPrice]:
        """解析有色金属价格"""
        from bs4 import BeautifulSoup

        try:
            soup = BeautifulSoup(html, 'html.parser')
            prices = []

            for config in self.MATERIAL_CONFIGS:
                found_price = self._extract_price(soup, config)
                if found_price:
                    prices.append(found_price)

            return prices

        except Exception as e:
            logger.error(f"解析失败: {e}")
            return []

    def _extract_price(self, soup: BeautifulSoup, config: Dict) -> Optional[MaterialPrice]:
        """提取特定金属价格"""
        try:
            selectors = config['selector'].split(', ')
            for selector in selectors:
                elements = soup.select(selector.strip())
                for elem in elements:
                    text = elem.get_text(strip=True)
                    match = re.search(r'(\d{4,5}(?:\.\d+)?)', text)
                    if match:
                        price = float(match.group(1))
                        if config['min_price'] < price < config['max_price']:
                            return MaterialPrice(
                                material_id=config['id_prefix'] + '-3333-3333-333333333333',
                                material_name=config['name'],
                                spec=config['spec'],
                                price=price,
                                unit=config['unit']
                            )

        except Exception:
            pass

        return None


# ========== 爬虫工厂 ==========

class ScraperFactory:
    """爬虫工厂 - 支持多材料抓取"""

    _scrapers = {
        'mysteel': MysteelScraper,
        'ccmn': CcmnScraper,
    }

    @classmethod
    def get_scraper(cls, scraper_type: str, credentials: SiteCredentials = None) -> Optional[AuthenticatedScraper]:
        """获取爬虫实例"""
        scraper_class = cls._scrapers.get(scraper_type)
        if scraper_class:
            return scraper_class(credentials)
        return None

    @classmethod
    def get_all_materials(cls) -> Dict[str, List[Dict]]:
        """获取所有爬虫支持的材料"""
        result = {}
        for scraper_type, scraper_class in cls._scrapers.items():
            instance = scraper_class()
            materials = []

            # 从 MATERIAL_CONFIGS 提取材料信息
            if hasattr(scraper_class, 'MATERIAL_CONFIGS'):
                for config in scraper_class.MATERIAL_CONFIGS:
                    materials.append({
                        'id_prefix': config['id_prefix'],
                        'name': config['name'],
                        'spec': config.get('spec', ''),
                        'unit': config['unit'],
                    })

            result[scraper_type] = materials

        return result

    @classmethod
    def register_scraper(cls, scraper_type: str, scraper_class: type):
        """注册新爬虫"""
        cls._scrapers[scraper_type] = scraper_class


# ========== 主程序 ==========

def main():
    """测试多材料抓取"""
    print("=" * 60)
    print("TaskPlatform 多材料爬虫 v3.1")
    print("=" * 60)

    credentials = SiteCredentials(
        source_id='mysteel',
        source_name='我的钢铁网',
        website_url='https://www.mysteel.com.cn',
        username='',  # 请填写
        password='',  # 请填写
    )

    print("\n📊 支持的材料：")
    all_materials = ScraperFactory.get_all_materials()
    for scraper_type, materials in all_materials.items():
        print(f"\n  {scraper_type}:")
        for m in materials:
            print(f"    - {m['name']} ({m['spec']}) - {m['unit']}")

    # 测试抓取
    print("\n" + "=" * 60)
    print("开始抓取...")
    print("=" * 60)

    scraper = MysteelScraper(credentials)
    result = scraper.fetch()

    print("\n📊 抓取结果：")
    print(f"   成功: {result.success}")
    print(f"   材料数量: {len(result.prices)}")
    for p in result.prices:
        print(f"   - {p.material_name}: ¥{p.price:.2f}/{p.unit}")

    if result.error_message:
        print(f"   错误: {result.error_message}")


if __name__ == '__main__':
    main()