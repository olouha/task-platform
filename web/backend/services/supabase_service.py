"""
Supabase 数据库服务
连接真实数据库并操作数据
"""

import os
import requests
import json
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class SupabaseService:
    """Supabase 数据库服务"""

    def __init__(self, url: str = None, api_key: str = None):
        if not url or not api_key:
            config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'cloud.json')
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    url = config.get('supabase_url')
                    api_key = config.get('supabase_key')

        self.url = url.rstrip('/') if url else None
        self.api_key = api_key
        self.headers = {
            'apikey': api_key,
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'Prefer': 'return=representation'
        }
        self.timeout = 30

    def _request(self, method: str, endpoint: str, **kwargs) -> Optional[Any]:
        """发送请求"""
        if not self.url:
            logger.error("未配置 Supabase URL")
            return None

        url = f"{self.url}/rest/v1{endpoint}"

        try:
            response = requests.request(
                method, url, headers=self.headers, timeout=self.timeout, **kwargs
            )

            if response.status_code in [200, 201, 204]:
                if response.text:
                    return response.json()
                return True

            logger.error(f"请求失败: {response.status_code} - {response.text}")
            return None

        except requests.RequestException as e:
            logger.error(f"请求异常: {e}")
            return None

    def health_check(self) -> bool:
        """健康检查"""
        return self._request('GET', '/projects?select=id&limit=1') is not None

    # ========== 材料分类 ==========

    def get_material_categories(self) -> List[Dict]:
        """获取所有材料分类"""
        result = self._request('GET', '/material_categories?select=*&order=sort_order.asc')
        return result if result else []

    # ========== 材料 ==========

    def get_all_materials(self) -> List[Dict]:
        """获取所有材料"""
        result = self._request('GET', '/materials?select=*&order=name.asc')
        return result if result else []

    def get_material(self, material_id: str) -> Optional[Dict]:
        """获取单个材料"""
        result = self._request('GET', f'/materials?id=eq.{material_id}&select=*')
        if result and len(result) > 0:
            return result[0]
        return None

    def update_material_price(self, material_id: str, base_price: float) -> bool:
        """更新材料价格"""
        return self._request('PATCH', f'/materials?id=eq.{material_id}', json={'base_price': base_price}) is not None

    # ========== 价格来源 ==========

    def get_price_sources(self) -> List[Dict]:
        """获取所有价格来源"""
        result = self._request('GET', '/price_sources?select=*&order=name.asc')
        return result if result else []

    def get_active_price_sources(self) -> List[Dict]:
        """获取活跃的价格来源"""
        result = self._request('GET', '/price_sources?is_active=eq.true&select=*')
        return result if result else []

    def update_price_source_fetch_time(self, source_id: str) -> bool:
        """更新最后抓取时间"""
        from datetime import datetime
        return self._request(
            'PATCH',
            f'/price_sources?id=eq.{source_id}',
            json={'last_fetched_at': datetime.now().isoformat()}
        ) is not None

    # ========== 价格历史 ==========

    def get_price_history(self, material_id: str = None, days: int = 30) -> List[Dict]:
        """获取价格历史"""
        from datetime import datetime, timedelta

        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)

        query = f'/price_history?recorded_date=gte.{start_date}&recorded_date=lte.{end_date}&order=recorded_date.desc&select=*'

        if material_id:
            query = f'/price_history?material_id=eq.{material_id}&recorded_date=gte.{start_date}&recorded_date=lte.{end_date}&order=recorded_date.desc&select=*'

        result = self._request('GET', query)
        return result if result else []

    def add_price_record(self, material_id: str, source_id: str, price: float,
                        unit: str, recorded_date: str, raw_data: Dict = None) -> bool:
        """添加价格记录"""
        import uuid

        data = {
            'id': str(uuid.uuid4()),
            'material_id': material_id,
            'source_id': source_id,
            'price': price,
            'unit': unit,
            'recorded_date': recorded_date,
            'fetch_status': 'success'
        }

        if raw_data:
            data['raw_data'] = json.dumps(raw_data)

        return self._request('POST', '/price_history', json=data) is not None

    def get_latest_prices(self) -> List[Dict]:
        """获取最新价格（每个材料一条）"""
        result = self._request('GET', '/price_history?order=recorded_date.desc&limit=100')
        if not result:
            return []

        latest = {}
        for r in result:
            mid = r.get('material_id')
            if mid and mid not in latest:
                latest[mid] = r

        return list(latest.values())

    # ========== 项目 ==========

    def get_projects(self) -> List[Dict]:
        """获取所有项目"""
        result = self._request('GET', '/projects?select=*&order=created_at.desc')
        return result if result else []

    def get_project(self, project_id: str) -> Optional[Dict]:
        """获取单个项目"""
        result = self._request('GET', f'/projects?id=eq.{project_id}&select=*')
        if result and len(result) > 0:
            return result[0]
        return None

    # ========== 调差记录 ==========

    def add_adjustment_record(self, record: Dict) -> bool:
        """添加调差记录"""
        import uuid
        record['id'] = str(uuid.uuid4())
        return self._request('POST', '/adjustment_records', json=record) is not None

    # ========== 统计 ==========

    def get_statistics(self) -> Dict:
        """获取统计信息"""
        materials = self.get_all_materials()
        projects = self.get_projects()
        sources = self.get_price_sources()
        categories = self.get_material_categories()

        return {
            'total_materials': len(materials),
            'total_projects': len(projects),
            'total_price_sources': len(sources),
            'categories': categories
        }


# ========== 价格抓取器 ==========

class PriceScraper:
    """价格抓取器 - 从网站抓取价格"""

    def __init__(self, supabase: SupabaseService):
        self.supabase = supabase

    def fetch_all_prices(self) -> Dict:
        """抓取所有价格来源的数据"""
        sources = self.supabase.get_active_price_sources()
        results = {
            'success': 0,
            'failed': 0,
            'prices': []
        }

        for source in sources:
            try:
                price = self._fetch_source(source)
                if price:
                    results['success'] += 1
                    results['prices'].append(price)

                    # 保存到数据库
                    self.supabase.add_price_record(
                        material_id=source.get('material_id'),
                        source_id=source.get('id'),
                        price=price,
                        unit=self._get_unit(source.get('material_category')),
                        recorded_date=self._get_today()
                    )

                    # 更新抓取时间
                    self.supabase.update_price_source_fetch_time(source.get('id'))

            except Exception as e:
                logger.error(f"抓取失败 {source.get('name')}: {e}")
                results['failed'] += 1

        return results

    def _fetch_source(self, source: Dict) -> Optional[float]:
        """抓取单个来源的价格"""
        # 这里需要实现具体的抓取逻辑
        # 根据 source 中的 url 和 selector 抓取价格
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

    def _get_today(self) -> str:
        """获取今天的日期字符串"""
        from datetime import date
        return date.today().isoformat()


# ========== 云端定时任务 ==========

def run_price_scraper():
    """
    云端定时执行的价格抓取函数
    用于 Supabase Edge Functions 或其他云端环境
    """
    import os

    # 从环境变量获取配置
    supabase_url = os.environ.get('SUPABASE_URL')
    supabase_key = os.environ.get('SUPABASE_KEY')

    if not supabase_url or not supabase_key:
        logger.error("未配置 Supabase 环境变量")
        return {'error': '未配置 Supabase'}

    # 初始化服务
    supabase = SupabaseService(supabase_url, supabase_key)
    scraper = PriceScraper(supabase)

    # 执行抓取
    results = scraper.fetch_all_prices()

    logger.info(f"价格抓取完成: 成功 {results['success']}, 失败 {results['failed']}")
    return results


if __name__ == '__main__':
    # 本地测试
    service = SupabaseService()
    if service.health_check():
        print("✅ 数据库连接成功")

        # 测试获取数据
        categories = service.get_material_categories()
        print(f"📦 材料分类: {len(categories)} 个")

        materials = service.get_all_materials()
        print(f"🔩 材料: {len(materials)} 种")

        sources = service.get_active_price_sources()
        print(f"🌐 价格来源: {len(sources)} 个")
    else:
        print("❌ 数据库连接失败")