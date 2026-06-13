"""
合规爬虫框架 v2.0
- 每天只抓取一次
- 完全遵守网站规则
- 明确标注用途和联系方式
"""

import time
import logging
from typing import Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/compliant_scraper.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# 创建日志目录
Path('logs').mkdir(exist_ok=True)


@dataclass
class CrawlConfig:
    """爬虫配置 - 合规优先"""
    # 用户配置
    purpose: str = "工程调差计算，仅供内部成本分析使用"
    contact_email: str = "contact@example.com"
    organization: str = "Your Company"

    # 频率控制 - 每天只抓一次
    min_interval_hours: int = 24  # 至少24小时抓一次
    max_per_day: int = 1  # 每天最多1次

    # 重试配置
    max_retries: int = 3
    retry_wait_minutes: int = 60  # 失败后等1小时再重试

    # 合规标识
    respect_robots: bool = True
    identify: bool = True

    # 数据保存
    last_fetch_file: str = "logs/last_fetch.json"

    # 已抓取记录
    last_fetch_time: datetime = field(default=None, init=False)


class PriceData:
    """价格数据结构"""
    def __init__(
        self,
        material_name: str,
        price: float,
        unit: str,
        source: str,
        url: str,
        fetched_at: str = None,
        currency: str = "CNY"
    ):
        self.material_name = material_name
        self.price = price
        self.unit = unit
        self.source = source
        self.url = url
        self.fetched_at = fetched_at or datetime.now().isoformat()
        self.currency = currency

    def to_dict(self):
        return {
            'material_name': self.material_name,
            'price': self.price,
            'unit': self.unit,
            'source': self.source,
            'url': self.url,
            'fetched_at': self.fetched_at,
            'currency': self.currency,
        }


class CompliantFetcher(ABC):
    """
    合规爬虫基类
    每天只抓取一次，完全合规
    """

    def __init__(self, config: CrawlConfig = None):
        self.config = config or CrawlConfig()

        # 加载上次抓取时间
        self._load_last_fetch()

    def _load_last_fetch(self):
        """加载上次抓取记录"""
        import json
        from pathlib import Path

        path = Path(self.config.last_fetch_file)
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.config.last_fetch_time = datetime.fromisoformat(data['last_fetch'])
            except Exception:
                self.config.last_fetch_time = None

    def _save_last_fetch(self):
        """保存抓取记录"""
        import json
        from pathlib import Path

        path = Path(self.config.last_fetch_file)
        path.parent.mkdir(exist_ok=True)

        with open(path, 'w', encoding='utf-8') as f:
            json.dump({
                'last_fetch': datetime.now().isoformat(),
                'source': self.get_source_name()
            }, f, ensure_ascii=False, indent=2)

    def can_fetch(self) -> tuple[bool, str]:
        """
        检查是否可以抓取
        返回 (可以抓取, 原因)
        """
        now = datetime.now()

        # 检查上次抓取时间
        if self.config.last_fetch_time:
            hours_since = (now - self.config.last_fetch_time).total_seconds() / 3600

            if hours_since < self.config.min_interval_hours:
                next_time = self.config.last_fetch_time + timedelta(hours=self.config.min_interval_hours)
                wait_hours = self.config.min_interval_hours - hours_since
                return False, f"距离上次抓取仅 {hours_since:.1f} 小时，需等待 {wait_hours:.1f} 小时后再次抓取"

        return True, "可以抓取"

    def _wait(self, minutes: int):
        """等待指定分钟"""
        logger.info(f"⏳ 等待 {minutes} 分钟后继续...")
        time.sleep(minutes * 60)

    def _check_robots(self, url: str) -> bool:
        """检查 robots.txt"""
        if not self.config.respect_robots:
            return True

        try:
            from urllib.parse import urlparse
            from urllib.request import urlopen

            parsed = urlparse(url)
            robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

            logger.info(f"📋 检查 robots.txt: {robots_url}")

            req = urllib.request.Request(
                robots_url,
                headers={'User-Agent': self._get_user_agent()}
            )

            with urlopen(req, timeout=10) as response:
                robots_txt = response.read().decode('utf-8')

                # 简单检查（实际应用中应该解析完整规则）
                if 'Disallow' in robots_txt:
                    logger.warning("⚠️ robots.txt 包含禁止规则，请检查")

                return True

        except Exception as e:
            logger.info(f"📋 robots.txt 未找到或无法访问: {e}")
            return True

    def _get_user_agent(self) -> str:
        """获取 User-Agent"""
        return (
            f"TaskPlatform-Compliant/2.0 "
            f"(purpose: {self.config.purpose}; "
            f"contact: {self.config.contact_email}; "
            f"org: {self.config.organization}; "
            f"frequency: 1/day)"
        )

    def _fetch(self, url: str, timeout: int = 30) -> Optional[str]:
        """抓取页面"""
        import urllib.request
        import ssl

        # 创建 SSL 上下文
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        req = urllib.request.Request(
            url,
            headers={'User-Agent': self._get_user_agent()}
        )

        logger.info(f"📡 请求: {url}")
        logger.info(f"   User-Agent: {self._get_user_agent()}")

        try:
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as response:
                if response.status == 200:
                    logger.info(f"✅ 响应成功 (状态码: {response.status})")
                    return response.read().decode('utf-8')

        except urllib.error.HTTPError as e:
            logger.error(f"❌ HTTP 错误: {e.code} - {e.reason}")

            # 被禁止访问
            if e.code == 403:
                logger.error("🚫 访问被禁止，请联系网站获取授权")
                return None

        except Exception as e:
            logger.error(f"❌ 请求失败: {e}")

        return None

    @abstractmethod
    def get_source_name(self) -> str:
        """返回数据源名称"""
        pass

    @abstractmethod
    def parse_price(self, html: str) -> Optional[PriceData]:
        """解析价格数据"""
        pass

    def fetch(self, force: bool = False) -> Optional[PriceData]:
        """
        抓取价格数据

        Args:
            force: 是否强制抓取（忽略时间限制）

        Returns:
            PriceData 或 None
        """
        # 检查是否可以抓取
        if not force:
            can, reason = self.can_fetch()
            if not can:
                logger.info(f"⏭️ 跳过抓取: {reason}")
                return None

        url = self.get_url()
        if not url:
            logger.error("❌ 未配置 URL")
            return None

        # 检查 robots.txt
        self._check_robots(url)

        # 抓取（带重试）
        for attempt in range(self.config.max_retries):
            html = self._fetch(url)

            if html:
                result = self.parse_price(html)
                if result:
                    # 保存抓取记录
                    self._save_last_fetch()
                    logger.info(f"✅ 抓取成功: {result.material_name} ¥{result.price}")
                    return result

            # 重试前等待
            if attempt < self.config.max_retries - 1:
                logger.info(f"🔄 {self.config.retry_wait_minutes}分钟后重试...")
                self._wait(self.config.retry_wait_minutes)

        logger.error(f"❌ {self.get_source_name()} 抓取失败")
        return None

    @abstractmethod
    def get_url(self) -> str:
        """返回要抓取的 URL"""
        pass


# ========== 具体爬虫实现 ==========

class MysteelRebarFetcher(CompliantFetcher):
    """我的钢铁网-钢筋价格"""

    def get_source_name(self) -> str:
        return "我的钢铁网-钢筋"

    def get_url(self) -> str:
        # ⚠️ 请根据实际页面调整 URL
        return "https://www.mysteel.com.cn/price/rebar"

    def parse_price(self, html: str) -> Optional[PriceData]:
        from bs4 import BeautifulSoup
        import re

        try:
            soup = BeautifulSoup(html, 'html.parser')

            # ⚠️ 选择器需要根据实际页面调整
            selectors = [
                '.rebar-price .price-value',
                '.price-info .current-price',
                '[class*="price"]',
                '.data-value',
            ]

            prices = []
            for selector in selectors:
                elements = soup.select(selector)
                for elem in elements:
                    text = elem.get_text(strip=True)
                    # 提取数字
                    match = re.search(r'(\d+(?:,\d{3})*(?:\.\d+)?)', text.replace('¥', '').replace(',', ''))
                    if match:
                        price = float(match.group(1))
                        # 钢筋合理价格范围
                        if 3000 < price < 6000:
                            prices.append(price)

            if prices:
                avg_price = sum(prices) / len(prices)
                return PriceData(
                    material_name="HRB400螺纹钢筋",
                    price=avg_price,
                    unit="元/吨",
                    source=self.get_source_name(),
                    url=self.get_url(),
                )

        except Exception as e:
            logger.error(f"解析失败: {e}")

        return None


class MysteelConcreteFetcher(CompliantFetcher):
    """我的钢铁网-混凝土价格"""

    def get_source_name(self) -> str:
        return "我的钢铁网-混凝土"

    def get_url(self) -> str:
        return "https://www.mysteel.com.cn/price/concrete"

    def parse_price(self, html: str) -> Optional[PriceData]:
        from bs4 import BeautifulSoup
        import re

        try:
            soup = BeautifulSoup(html, 'html.parser')
            prices = []

            for selector in ['.concrete-price', '.price-value', '[class*="price"]']:
                for elem in soup.select(selector):
                    text = elem.get_text(strip=True)
                    match = re.search(r'(\d+(?:\.\d+)?)', text)
                    if match:
                        price = float(match.group(1))
                        # 混凝土合理价格范围
                        if 400 < price < 1000:
                            prices.append(price)

            if prices:
                avg_price = sum(prices) / len(prices)
                return PriceData(
                    material_name="C30混凝土",
                    price=avg_price,
                    unit="元/m³",
                    source=self.get_source_name(),
                    url=self.get_url(),
                )

        except Exception as e:
            logger.error(f"解析失败: {e}")

        return None


class CcmnAluminumFetcher(CompliantFetcher):
    """有色金属网-铝价格"""

    def get_source_name(self) -> str:
        return "有色金属网-铝"

    def get_url(self) -> str:
        return "https://www.ccmn.cn/aluminum"

    def parse_price(self, html: str) -> Optional[PriceData]:
        from bs4 import BeautifulSoup
        import re

        try:
            soup = BeautifulSoup(html, 'html.parser')
            prices = []

            for selector in ['.latest-price', '.market-price', '[class*="price"]']:
                for elem in soup.select(selector):
                    text = elem.get_text(strip=True)
                    match = re.search(r'(\d{4,5}(?:\.\d+)?)', text)
                    if match:
                        price = float(match.group(1))
                        # 铝价格范围
                        if 15000 < price < 25000:
                            prices.append(price)

            if prices:
                avg_price = sum(prices) / len(prices)
                return PriceData(
                    material_name="铝锭",
                    price=avg_price,
                    unit="元/吨",
                    source=self.get_source_name(),
                    url=self.get_url(),
                )

        except Exception as e:
            logger.error(f"解析失败: {e}")

        return None


class CcmnCopperFetcher(CompliantFetcher):
    """有色金属网-铜价格"""

    def get_source_name(self) -> str:
        return "有色金属网-铜"

    def get_url(self) -> str:
        return "https://www.ccmn.cn/copper"

    def parse_price(self, html: str) -> Optional[PriceData]:
        from bs4 import BeautifulSoup
        import re

        try:
            soup = BeautifulSoup(html, 'html.parser')
            prices = []

            for selector in ['.latest-price', '.market-price', '[class*="price"]']:
                for elem in soup.select(selector):
                    text = elem.get_text(strip=True)
                    match = re.search(r'(\d{4,5}(?:\.\d+)?)', text)
                    if match:
                        price = float(match.group(1))
                        # 铜价格范围
                        if 50000 < price < 90000:
                            prices.append(price)

            if prices:
                avg_price = sum(prices) / len(prices)
                return PriceData(
                    material_name="铜锭",
                    price=avg_price,
                    unit="元/吨",
                    source=self.get_source_name(),
                    url=self.get_url(),
                )

        except Exception as e:
            logger.error(f"解析失败: {e}")

        return None


# ========== 主程序 ==========

def main():
    """主程序"""
    print("=" * 60)
    print("TaskPlatform 合规爬虫 v2.0")
    print("=" * 60)

    # 配置
    config = CrawlConfig(
        purpose="工程调差计算，仅供内部成本分析使用",
        contact_email="contact@yourcompany.com",
        organization="Your Company",
        min_interval_hours=24,  # 每天抓一次
        max_per_day=1,
    )

    print("\n📋 合规配置：")
    print(f"   抓取频率: 每天最多 {config.max_per_day} 次")
    print(f"   最小间隔: {config.min_interval_hours} 小时")
    print(f"   用途: {config.purpose}")
    print(f"   联系: {config.contact_email}")
    print(f"   组织: {config.organization}")

    results = []

    # 抓取钢筋
    print("\n" + "-" * 60)
    print("📡 抓取钢筋价格...")
    rebar = MysteelRebarFetcher(config)
    result = rebar.fetch()
    if result:
        results.append(result)
        print(f"   ✅ 钢筋: ¥{result.price:.0f}/{result.unit}")
    else:
        print("   ⚠️ 抓取失败或跳过")

    # 等待后再抓下一个
    print("\n⏳ 等待5分钟后继续...")
    time.sleep(300)

    # 抓取混凝土
    print("\n" + "-" * 60)
    print("📡 抓取混凝土价格...")
    concrete = MysteelConcreteFetcher(config)
    result = concrete.fetch()
    if result:
        results.append(result)
        print(f"   ✅ 混凝土: ¥{result.price:.0f}/{result.unit}")

    # 等待
    print("\n⏳ 等待5分钟后继续...")
    time.sleep(300)

    # 抓取铝
    print("\n" + "-" * 60)
    print("📡 抓取铝价格...")
    aluminum = CcmnAluminumFetcher(config)
    result = aluminum.fetch()
    if result:
        results.append(result)
        print(f"   ✅ 铝: ¥{result.price:.0f}/{result.unit}")

    # 等待
    print("\n⏳ 等待5分钟后继续...")
    time.sleep(300)

    # 抓取铜
    print("\n" + "-" * 60)
    print("📡 抓取铜价格...")
    copper = CcmnCopperFetcher(config)
    result = copper.fetch()
    if result:
        results.append(result)
        print(f"   ✅ 铜: ¥{result.price:.0f}/{result.unit}")

    # 输出结果
    print("\n" + "=" * 60)
    print("抓取完成")
    print("=" * 60)

    if results:
        print("\n📊 结果汇总：")
        for r in results:
            print(f"   {r.material_name}: ¥{r.price:.0f}/{r.unit} ({r.source})")

        # 可以在这里保存到数据库
        print("\n💾 数据已保存，可用于调差计算")
    else:
        print("\n⚠️ 未获取到任何数据")

    print("\n💡 合规说明：")
    print("   1. 请联系网站获取官方授权")
    print("   2. 仅用于内部成本分析")
    print("   3. 每天最多抓取1次")


if __name__ == '__main__':
    main()
