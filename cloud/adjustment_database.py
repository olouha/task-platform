"""
工程调差计算系统 - Supabase数据库客户端
"""

import requests
import json
import logging
from datetime import datetime, date
from typing import Dict, List, Optional, Any
import uuid

logger = logging.getLogger(__name__)


class AdjustmentDatabase:
    """工程调差数据库客户端"""

    def __init__(self, url: str = None, api_key: str = None):
        if not url or not api_key:
            import os
            config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'cloud.json')
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
            logger.error("No URL configured")
            return None

        url = f"{self.url}/rest/v1{endpoint}"

        try:
            response = requests.request(
                method, url, headers=self.headers, timeout=self.timeout, **kwargs
            )

            if response.status_code in [200, 201]:
                if response.text:
                    return response.json()
                return {'success': True}

            logger.error(f"Request failed: {response.status_code} - {response.text}")
            return None

        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            return None

    def health_check(self) -> bool:
        """健康检查"""
        result = self._request('GET', '/projects?select=id&limit=1')
        return result is not None

    # ========== 材料分类 ==========

    def get_material_categories(self) -> List[Dict]:
        """获取材料分类"""
        result = self._request('GET', '/material_categories?select=*&order=sort_order.asc')
        return result if result else []

    def get_materials_by_category(self, category_id: str) -> List[Dict]:
        """按分类获取材料"""
        result = self._request('GET', f'/materials?category_id=eq.{category_id}&select=*')
        return result if result else []

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
        """更新材料基准价"""
        return self._request('PATCH', f'/materials?id=eq.{material_id}', json={'base_price': base_price}) is not None

    # ========== 价格来源 ==========

    def get_price_sources(self) -> List[Dict]:
        """获取价格来源"""
        result = self._request('GET', '/price_sources?select=*&order=name.asc')
        return result if result else []

    def get_price_sources_by_category(self, category: str) -> List[Dict]:
        """按分类获取价格来源"""
        result = self._request('GET', f'/price_sources?material_category=eq.{category}&select=*')
        return result if result else []

    def update_price_source(self, source_id: str, data: Dict) -> bool:
        """更新价格来源"""
        return self._request('PATCH', f'/price_sources?id=eq.{source_id}', json=data) is not None

    # ========== 价格历史 ==========

    def get_price_history(self, material_id: str = None, start_date: str = None,
                          end_date: str = None, limit: int = 1000) -> List[Dict]:
        """获取价格历史"""
        params = []

        if material_id:
            params.append(f"material_id=eq.{material_id}")
        if start_date:
            params.append(f"recorded_date=gte.{start_date}")
        if end_date:
            params.append(f"recorded_date=lte.{end_date}")

        query = '&'.join(params) if params else ''
        endpoint = f'/price_history?select=*&order=recorded_date.desc&limit={limit}'
        if query:
            endpoint = f'/price_history?{query}&select=*&order=recorded_date.desc&limit={limit}'

        result = self._request('GET', endpoint)
        return result if result else []

    def add_price_record(self, material_id: str, source_id: str, price: float,
                        unit: str, recorded_date: str, raw_data: Dict = None) -> bool:
        """添加价格记录"""
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
        """获取最新价格"""
        result = self._request('GET', '''
            /price_history?select=*&order=recorded_date.desc&limit=100
        ''')
        if not result:
            return []

        # 按material_id去重，只保留最新
        latest = {}
        for r in result:
            mid = r.get('material_id')
            if mid and (mid not in latest or r.get('recorded_date') > latest[mid].get('recorded_date')):
                latest[mid] = r

        return list(latest.values())

    def get_average_price(self, material_id: str, start_date: str, end_date: str) -> Optional[float]:
        """获取时间段内平均价格"""
        result = self._request('GET',
            f"/rpc/get_avg_price?material_id={material_id}&start_date={start_date}&end_date={end_date}")
        if result:
            return result[0].get('avg_price') if isinstance(result, list) else result.get('avg_price')
        return None

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

    def create_project(self, project: Dict) -> Optional[str]:
        """创建项目"""
        project['id'] = str(uuid.uuid4())
        result = self._request('POST', '/projects', json=project)
        if result:
            return project['id']
        return None

    def update_project(self, project_id: str, data: Dict) -> bool:
        """更新项目"""
        return self._request('PATCH', f'/projects?id=eq.{project_id}', json=data) is not None

    # ========== 项目材料 ==========

    def get_project_materials(self, project_id: str) -> List[Dict]:
        """获取项目材料"""
        result = self._request('GET', f'/project_materials?project_id=eq.{project_id}&select=*&order=sort_order.asc')
        return result if result else []

    def add_project_material(self, project_id: str, material: Dict) -> Optional[str]:
        """添加项目材料"""
        material['id'] = str(uuid.uuid4())
        material['project_id'] = project_id
        result = self._request('POST', '/project_materials', json=material)
        if result:
            return material['id']
        return None

    def update_project_material(self, pm_id: str, data: Dict) -> bool:
        """更新项目材料"""
        return self._request('PATCH', f'/project_materials?id=eq.{pm_id}', json=data) is not None

    def delete_project_material(self, pm_id: str) -> bool:
        """删除项目材料"""
        return self._request('DELETE', f'/project_materials?id=eq.{pm_id}') is not None

    # ========== 施工阶段 ==========

    def get_phases(self, project_id: str) -> List[Dict]:
        """获取施工阶段"""
        result = self._request('GET', f'/construction_phases?project_id=eq.{project_id}&select=*&order=sort_order.asc')
        return result if result else []

    def create_phase(self, phase: Dict) -> Optional[str]:
        """创建施工阶段"""
        phase['id'] = str(uuid.uuid4())
        result = self._request('POST', '/construction_phases', json=phase)
        if result:
            return phase['id']
        return None

    def update_phase(self, phase_id: str, data: Dict) -> bool:
        """更新施工阶段"""
        return self._request('PATCH', f'/construction_phases?id=eq.{phase_id}', json=data) is not None

    def delete_phase(self, phase_id: str) -> bool:
        """删除施工阶段"""
        return self._request('DELETE', f'/construction_phases?id=eq.{phase_id}') is not None

    # ========== 调差记录 ==========

    def get_adjustment_records(self, project_id: str = None, phase_id: str = None) -> List[Dict]:
        """获取调差记录"""
        conditions = []
        if project_id:
            conditions.append(f"project_id=eq.{project_id}")
        if phase_id:
            conditions.append(f"phase_id=eq.{phase_id}")

        query = '&'.join(conditions)
        endpoint = '/adjustment_records?select=*'
        if query:
            endpoint = f'/adjustment_records?{query}&select=*'

        result = self._request('GET', endpoint)
        return result if result else []

    def add_adjustment_record(self, record: Dict) -> Optional[str]:
        """添加调差记录"""
        record['id'] = str(uuid.uuid4())
        result = self._request('POST', '/adjustment_records', json=record)
        if result:
            return record['id']
        return None

    def calculate_adjustment(self, project_id: str, material_id: str, phase_id: str,
                           base_price: float, current_price: float,
                           quantity: float) -> Dict:
        """计算调差"""
        if base_price <= 0:
            return {'change_rate': 0, 'adjustment_amount': 0}

        change_rate = ((current_price - base_price) / base_price) * 100
        adjustment_amount = (current_price - base_price) * quantity

        return {
            'base_price': base_price,
            'current_price': current_price,
            'change_rate': round(change_rate, 4),
            'adjustment_amount': round(adjustment_amount, 2)
        }

    # ========== 指标 ==========

    def get_indicator_categories(self, project_id: str = None) -> List[Dict]:
        """获取指标分类"""
        if project_id:
            result = self._request('GET', f'/indicator_categories?project_id=eq.{project_id}&select=*&order=sort_order.asc')
        else:
            result = self._request('GET', '/indicator_categories?select=*&order=sort_order.asc')
        return result if result else []

    def get_indicators(self, project_id: str = None, category_id: str = None) -> List[Dict]:
        """获取指标"""
        conditions = []
        if project_id:
            conditions.append(f"project_id=eq.{project_id}")
        if category_id:
            conditions.append(f"category_id=eq.{category_id}")

        query = '&'.join(conditions)
        endpoint = '/indicators?select=*'
        if query:
            endpoint = f'/indicators?{query}&select=*'

        result = self._request('GET', endpoint)
        return result if result else []

    def add_indicator(self, indicator: Dict) -> Optional[str]:
        """添加指标"""
        indicator['id'] = str(uuid.uuid4())
        result = self._request('POST', '/indicators', json=indicator)
        if result:
            return indicator['id']
        return None

    def update_indicator(self, indicator_id: str, data: Dict) -> bool:
        """更新指标"""
        data['updated_at'] = datetime.now().isoformat()
        return self._request('PATCH', f'/indicators?id=eq.{indicator_id}', json=data) is not None

    def delete_indicator(self, indicator_id: str) -> bool:
        """删除指标"""
        return self._request('DELETE', f'/indicators?id=eq.{indicator_id}') is not None

    # ========== 统计 ==========

    def get_statistics(self, project_id: str = None) -> Dict:
        """获取统计数据"""
        materials = self.get_all_materials()
        projects = self.get_projects()
        sources = self.get_price_sources()

        stats = {
            'total_materials': len(materials),
            'total_projects': len(projects),
            'total_price_sources': len(sources),
            'categories': []
        }

        # 按分类统计
        categories = self.get_material_categories()
        for cat in categories:
            cat_materials = [m for m in materials if m.get('category_id') == cat.get('id')]
            stats['categories'].append({
                'name': cat.get('name'),
                'count': len(cat_materials)
            })

        return stats
