"""
云端定时价格抓取器
部署后自动运行，不需要个人电脑
支持 Cloudflare Workers / Railway / 其他云端平台
"""

import os
import json
import logging
from datetime import datetime, date
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ========== 配置 ==========

class Config:
    """配置管理"""

    # Supabase 配置（从环境变量读取）
    SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
    SUPABASE_KEY = os.environ.get('SUPABASE_KEY', '')

    # 价格来源配置
    PRICE_SOURCES = [
        {
            'id': 'eeee1111-1111-1111-1111-111111111111',
            'name': '我的钢铁网-钢筋',
            'url': 'https://www.mysteel.com.cn/price/rebar',
            'selector': '.price-value',
            'category': '钢筋类',
            'unit': '吨',
            'material_id': 'aaaa1111-1111-1111-1111-111111111111'
        },
        {
            'id': 'eeee2222-2222-2222-2222-222222222222',
            'name': '我的钢铁网-混凝土',
            'url': 'https://www.mysteel.com.cn/price/concrete',
            'selector': '.price-value',
            'category': '混凝土类',
            'unit': 'm³',
            'material_id': 'bbbb1111-1111-1111-1111-111111111111'
        },
        {
            'id': 'eeee4444-4444-4444-4444-444444444444',
            'name': '有色金属网-铝',
            'url': 'https://www.ccmn.cn/aluminum',
            'selector': '.latest-price',
            'category': '有色金属类',
            'unit': '吨',
            'material_id': 'cccc3333-3333-3333-3333-333333333333'
        },
        {
            'id': 'eeee5555-5555-5555-5555-555555555555',
            'name': '有色金属网-铜',
            'url': 'https://www.ccmn.cn/copper',
            'selector': '.latest-price',
            'category': '有色金属类',
            'unit': '吨',
            'material_id': 'cccc4444-4444-4444-4444-444444444444'
        },
    ]


# ========== 数据库服务 ==========

class CloudDatabase:
    """云端数据库服务"""

    def __init__(self, url: str, api_key: str):
        self.url = url
        self.api_key = api_key
        self.headers = {
            'apikey': api_key,
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }

    def insert_price_record(self, record: Dict) -> bool:
        """插入价格记录"""
        try:
            import urllib.request

            url = f"{self.url}/rest/v1/price_history"
            data = json.dumps(record).encode('utf-8')

            req = urllib.request.Request(
                url,
                data=data,
                headers=self.headers,
                method='POST'
            )

            with urllib.request.urlopen(req, timeout=30) as response:
                return response.status in [200, 201]

        except Exception as e:
            logger.error(f"插入失败: {e}")
            return False

    def update_source_fetch_time(self, source_id: str) -> bool:
        """更新价格来源的最后抓取时间"""
        try:
            import urllib.request
            from urllib.parse import quote

            url = f"{self.url}/rest/v1/price_sources?id=eq.{source_id}"
            data = json.dumps({'last_fetched_at': datetime.now().isoformat()}).encode('utf-8')

            req = urllib.request.Request(
                url,
                data=data,
                headers={**self.headers, 'Prefer': 'return=minimal'},
                method='PATCH'
            )

            with urllib.request.urlopen(req, timeout=30) as response:
                return True

        except Exception as e:
            logger.error(f"更新失败: {e}")
            return False


# ========== 价格抓取器 ==========

class CloudPriceScraper:
    """云端价格抓取器"""

    def __init__(self, db: CloudDatabase):
        self.db = db

    def fetch_all(self) -> Dict:
        """抓取所有价格来源"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'success': 0,
            'failed': 0,
            'prices': []
        }

        for source in Config.PRICE_SOURCES:
            try:
                price = self._fetch_single(source)
                if price:
                    results['success'] += 1
                    results['prices'].append(price)

                    # 保存到数据库
                    self._save_price(source, price)
                    self.db.update_source_fetch_time(source['id'])

                    logger.info(f"✅ {source['name']}: ¥{price}")

                else:
                    results['failed'] += 1
                    logger.warning(f"⚠️ {source['name']}: 抓取失败")

            except Exception as e:
                results['failed'] += 1
                logger.error(f"❌ {source['name']}: {e}")

        return results

    def _fetch_single(self, source: Dict) -> Optional[float]:
        """
        抓取单个来源的价格
        这里需要根据实际网站结构调整
        """
        try:
            import urllib.request

            req = urllib.request.Request(
                source['url'],
                headers={
                    'User-Agent': 'Mozilla/5.0 (compatible; TaskPlatform/1.0)',
                    'Accept': 'text/html'
                }
            )

            with urllib.request.urlopen(req, timeout=30) as response:
                html = response.read().decode('utf-8')

                # 简单的价格解析（需要根据实际网站调整）
                import re
                price_match = re.search(r'(\d{3,5}(?:\.\d{1,2})?)', html)

                if price_match:
                    return float(price_match.group(1))

        except Exception as e:
            logger.error(f"抓取错误: {e}")

        return None

    def _save_price(self, source: Dict, price: float):
        """保存价格到数据库"""
        import uuid

        record = {
            'id': str(uuid.uuid4()),
            'material_id': source['material_id'],
            'source_id': source['id'],
            'price': price,
            'unit': source['unit'],
            'recorded_date': date.today().isoformat(),
            'fetch_status': 'success'
        }

        self.db.insert_price_record(record)


# ========== 主入口（Cloudflare Workers / 任意云函数）==========

def main(request=None):
    """
    主入口函数
    Cloudflare Workers 或其他云端平台调用此函数
    """
    # 获取配置
    supabase_url = Config.SUPABASE_URL or os.environ.get('SUPABASE_URL', '')
    supabase_key = Config.SUPABASE_KEY or os.environ.get('SUPABASE_KEY', '')

    if not supabase_url or not supabase_key:
        return {'error': '未配置 Supabase', 'status': 500}

    # 初始化
    db = CloudDatabase(supabase_url, supabase_key)
    scraper = CloudPriceScraper(db)

    # 执行抓取
    results = scraper.fetch_all()

    return {
        'body': json.dumps(results),
        'headers': {'Content-Type': 'application/json'}
    }


# ========== 本地调试 ==========

if __name__ == '__main__':
    print("=" * 50)
    print("TaskPlatform 云端价格抓取器")
    print("=" * 50)

    # 检查配置
    if not Config.SUPABASE_URL:
        print("⚠️  警告: 未设置 SUPABASE_URL 环境变量")
        print("   请设置后再运行")
        print("   export SUPABASE_URL='你的Supabase项目URL'")
        print("   export SUPABASE_KEY='你的Supabase API Key'")
        print()

    # 显示配置的价格来源
    print(f"📡 配置了 {len(Config.PRICE_SOURCES)} 个价格来源:")
    for source in Config.PRICE_SOURCES:
        print(f"   - {source['name']} ({source['category']})")
    print()

    # 手动测试（如果配置了）
    if Config.SUPABASE_URL and Config.SUPABASE_KEY:
        print("🔄 开始抓取...")
        results = main()
        print(f"\n📊 结果: 成功 {results['success']}, 失败 {results['failed']}")
    else:
        print("💡 提示: 设置环境变量后重新运行即可自动抓取")
        print("   配置会自动保存到 Supabase 数据库")
        print("   无需个人电脑运行，全自动云端执行")