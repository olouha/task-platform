"""
Supabase 数据库服务
连接真实数据库并操作数据
支持环境变量配置优先
"""

import os
import requests
import json
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class SupabaseService:
    """Supabase 数据库服务"""

    def __init__(self, url: str = None, api_key: str = None):
        # 优先级：1. 构造函数参数 2. 环境变量 3. 配置文件(config/cloud.json)
        # 由 cloud.json 的 mode 字段控制是否启用 Supabase：
        #   mode="supabase" → 启用，读取 supabase_url/supabase_key
        #   mode="local"(或其他) → 禁用，使用本地 SQLite，所有请求静默返回 None
        if not url:
            url = os.environ.get('SUPABASE_URL')
        if not api_key:
            api_key = os.environ.get('SUPABASE_KEY')

        # 仅当 cloud.json 的 mode="supabase" 时，才加载其中的账号信息
        config_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'config', 'cloud.json')
        if (not url or not api_key) and os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
                if config.get('mode') == 'supabase':
                    url = url or config.get('supabase_url')
                    api_key = api_key or config.get('supabase_key')

        self.url = url.rstrip('/') if url else None
        self.api_key = api_key
        self.headers = {
            'apikey': api_key,
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'Prefer': 'return=representation'
        }
        self.timeout = 30

        if self.url:
            logger.info(f"[SupabaseService] 已启用 | url={self.url[:30] + '...'}")
        else:
            logger.info("[SupabaseService] 未启用，使用本地 SQLite 存储（Supabase 相关功能已禁用）")

    def _request(self, method: str, endpoint: str, **kwargs) -> Optional[Any]:
        """发送请求"""
        if not self.url:
            # Supabase 未启用（本地 SQLite 模式），静默返回 None，避免刷错误日志
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

    def create_project(self, project_data: Dict) -> Optional[Dict]:
        """创建项目"""
        import uuid
        project_data['id'] = str(uuid.uuid4())
        if self._request('POST', '/projects', json=project_data):
            return project_data
        return None

    def update_project(self, project_id: str, update_data: Dict) -> bool:
        """更新项目"""
        return self._request('PATCH', f'/projects?id=eq.{project_id}', json=update_data) is not None

    def delete_project(self, project_id: str) -> bool:
        """删除项目"""
        return self._request('DELETE', f'/projects?id=eq.{project_id}') is not None

    # ========== 施工阶段 ==========

    def get_project_phases(self, project_id: str) -> List[Dict]:
        """获取项目施工阶段"""
        result = self._request('GET', f'/construction_phases?project_id=eq.{project_id}&select=*&order=start_date.asc')
        return result if result else []

    def create_project_phase(self, phase_data: Dict) -> Optional[Dict]:
        """创建施工阶段"""
        import uuid
        phase_data['id'] = str(uuid.uuid4())
        if self._request('POST', '/construction_phases', json=phase_data):
            return phase_data
        return None

    # ========== 项目材料 ==========

    def get_project_materials(self, project_id: str) -> List[Dict]:
        """获取项目材料"""
        result = self._request('GET', f'/project_materials?project_id=eq.{project_id}&select=*')
        return result if result else []

    def create_project_material(self, material_data: Dict) -> Optional[Dict]:
        """创建项目材料"""
        import uuid
        material_data['id'] = str(uuid.uuid4())
        if self._request('POST', '/project_materials', json=material_data):
            return material_data
        return None

    def update_project_material(self, material_id: str, update_data: Dict) -> bool:
        """更新项目材料"""
        return self._request('PATCH', f'/project_materials?id=eq.{material_id}', json=update_data) is not None

    def delete_project_material(self, material_id: str) -> bool:
        """删除项目材料"""
        return self._request('DELETE', f'/project_materials?id=eq.{material_id}') is not None

    # ========== 材料分类 ==========

    def create_material_category(self, category_data: Dict) -> Optional[Dict]:
        """创建材料分类"""
        import uuid
        category_data['id'] = str(uuid.uuid4())
        if self._request('POST', '/material_categories', json=category_data):
            return category_data
        return None

    def update_material_category(self, category_id: str, update_data: Dict) -> bool:
        """更新材料分类"""
        return self._request('PATCH', f'/material_categories?id=eq.{category_id}', json=update_data) is not None

    def delete_material_category(self, category_id: str) -> bool:
        """删除材料分类"""
        return self._request('DELETE', f'/material_categories?id=eq.{category_id}') is not None

    # ========== 材料 ==========

    def create_material(self, material_data: Dict) -> Optional[Dict]:
        """创建材料"""
        import uuid
        material_data['id'] = str(uuid.uuid4())
        if self._request('POST', '/materials', json=material_data):
            return material_data
        return None

    def update_material(self, material_id: str, update_data: Dict) -> bool:
        """更新材料"""
        return self._request('PATCH', f'/materials?id=eq.{material_id}', json=update_data) is not None

    def delete_material(self, material_id: str) -> bool:
        """删除材料"""
        return self._request('DELETE', f'/materials?id=eq.{material_id}') is not None

    # ========== 指标分类 ==========

    def get_indicator_categories(self, project_id: str = None) -> List[Dict]:
        """获取指标分类"""
        query = '/indicator_categories?select=*&order=sort_order.asc'
        if project_id:
            query = f'/indicator_categories?project_id=eq.{project_id}&select=*&order=sort_order.asc'
        result = self._request('GET', query)
        return result if result else []

    def create_indicator_category(self, category_data: Dict) -> Optional[Dict]:
        """创建指标分类"""
        import uuid
        category_data['id'] = str(uuid.uuid4())
        if self._request('POST', '/indicator_categories', json=category_data):
            return category_data
        return None

    def update_indicator_category(self, category_id: str, update_data: Dict) -> bool:
        """更新指标分类"""
        return self._request('PATCH', f'/indicator_categories?id=eq.{category_id}', json=update_data) is not None

    def delete_indicator_category(self, category_id: str) -> bool:
        """删除指标分类"""
        return self._request('DELETE', f'/indicator_categories?id=eq.{category_id}') is not None

    # ========== 指标 ==========

    def get_indicators(self, project_id: str = None, category_id: str = None) -> List[Dict]:
        """获取指标列表"""
        query = '/indicators?select=*'
        filters = []
        if project_id:
            filters.append(f'project_id=eq.{project_id}')
        if category_id:
            filters.append(f'category_id=eq.{category_id}')
        if filters:
            query = f'/indicators?{"&".join(filters)}&select=*'
        result = self._request('GET', query)
        return result if result else []

    def create_indicator(self, indicator_data: Dict) -> Optional[Dict]:
        """创建指标"""
        import uuid
        indicator_data['id'] = str(uuid.uuid4())
        if self._request('POST', '/indicators', json=indicator_data):
            return indicator_data
        return None

    def get_indicator(self, indicator_id: str) -> Optional[Dict]:
        """获取单个指标"""
        result = self._request('GET', f'/indicators?id=eq.{indicator_id}&select=*')
        if result and len(result) > 0:
            return result[0]
        return None

    def update_indicator(self, indicator_id: str, update_data: Dict) -> bool:
        """更新指标"""
        return self._request('PATCH', f'/indicators?id=eq.{indicator_id}', json=update_data) is not None

    def delete_indicator(self, indicator_id: str) -> bool:
        """删除指标"""
        return self._request('DELETE', f'/indicators?id=eq.{indicator_id}') is not None

    # ========== 指标库项目 ==========

    def get_indicator_projects(
        self,
        category: str = None,
        location: str = None,
        limit: int = 100
    ) -> List[Dict]:
        """获取指标库项目列表"""
        query = f'/indicator_projects?select=*&limit={limit}&order=created_at.desc'
        if category:
            query += f'&category=eq.{category}'
        if location:
            query += f'&location=ilike.%25{location}%25'
        result = self._request('GET', query)
        return result if result else []

    def get_indicator_project(self, project_id: str) -> Optional[Dict]:
        """获取单个指标库项目"""
        result = self._request('GET', f'/indicator_projects?id=eq.{project_id}&select=*')
        if result and len(result) > 0:
            return result[0]
        return None

    def create_indicator_project(self, project_data: Dict) -> Optional[Dict]:
        """创建指标库项目"""
        import uuid
        from datetime import datetime
        project_data['id'] = str(uuid.uuid4())
        project_data['created_at'] = datetime.now().isoformat()
        if self._request('POST', '/indicator_projects', json=project_data):
            return project_data
        return None

    def update_indicator_project(self, project_id: str, update_data: Dict) -> bool:
        """更新指标库项目"""
        from datetime import datetime
        update_data['updated_at'] = datetime.now().isoformat()
        return self._request('PATCH', f'/indicator_projects?id=eq.{project_id}', json=update_data) is not None

    def delete_indicator_project(self, project_id: str) -> bool:
        """删除指标库项目"""
        return self._request('DELETE', f'/indicator_projects?id=eq.{project_id}') is not None

    def import_indicator_projects(self, projects: List[Dict]) -> Dict:
        """批量导入指标库项目"""
        imported = 0
        errors = []
        for i, project in enumerate(projects):
            try:
                result = self.create_indicator_project(project)
                if result:
                    imported += 1
                else:
                    errors.append({"index": i, "error": "插入失败"})
            except Exception as e:
                errors.append({"index": i, "error": str(e)})
        return {"imported": imported, "total": len(projects), "errors": errors}

    # ========== 烟台钢筋价格 ==========

    def get_rebar_prices(
        self,
        date: str = None,
        start_date: str = None,
        end_date: str = None,
        material_name: str = None,
        spec: str = None,
        brand: str = None,
        limit: int = 500
    ) -> List[Dict]:
        """获取钢筋价格列表"""
        query = f'/rebar_prices?select=*&order=date.desc,fetch_time.desc&limit={limit}'
        if date:
            query += f'&date=eq.{date}'
        if start_date:
            query += f'&date=gte.{start_date}'
        if end_date:
            query += f'&date=lte.{end_date}'
        if material_name:
            query += f'&material_name=ilike.%25{material_name}%25'
        if spec:
            query += f'&spec=ilike.%25{spec}%25'
        if brand:
            query += f'&brand=ilike.%25{brand}%25'
        result = self._request('GET', query)
        return result if result else []

    def get_rebar_latest(self, limit: int = 500) -> Dict:
        """获取最新价格（按最新日期）"""
        result = self._request('GET', f'/rebar_prices?select=*&order=date.desc,fetch_time.desc&limit={limit}')
        if not result:
            return {'success': True, 'count': 0, 'prices': []}
        latest_date = result[0].get('date') if result else None
        filtered = [r for r in result if r.get('date') == latest_date]
        return {'success': True, 'count': len(filtered), 'prices': filtered}

    def get_rebar_trend(
        self,
        material_name: str = None,
        spec: str = None,
        days: int = 365,
        start_date: str = None,
        end_date: str = None
    ) -> Dict:
        """获取价格趋势（日均价的 max/min/avg）"""
        from datetime import datetime, timedelta
        query = '/rebar_prices?select=date,material_name,spec,brand,price&order=date.asc'
        if material_name:
            query += f'&material_name=ilike.%25{material_name}%25'
        if spec:
            query += f'&spec=ilike.%25{spec}%25'
        if start_date:
            query += f'&date=gte.{start_date}'
        elif end_date:
            cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            query += f'&date=gte.{cutoff}'
        if end_date:
            query += f'&date=lte.{end_date}'
        result = self._request('GET', query)
        if not result:
            return {'success': True, 'count': 0, 'data': []}
        # 按日期聚合
        daily: Dict[str, Dict] = {}
        for r in result:
            d = r.get('date')
            if d not in daily:
                daily[d] = {'date': d, 'prices': []}
            daily[d]['prices'].append(r.get('price', 0))
        trend = []
        for date_str, item in sorted(daily.items()):
            prices = item['prices']
            trend.append({
                'date': date_str,
                'avg_price': round(sum(prices) / len(prices), 2) if prices else 0,
                'min_price': min(prices) if prices else 0,
                'max_price': max(prices) if prices else 0,
                'cnt': len(prices)
            })
        return {'success': True, 'count': len(trend), 'data': trend}

    def get_rebar_stats(self) -> Dict:
        """获取钢筋价格统计"""
        result = self._request('GET', '/rebar_prices?select=date,material_name,spec,brand,price&limit=10000')
        if not result:
            return {'total_count': 0, 'dates_count': 0, 'date_range': {}, 'materials': {}, 'specs': {}}
        dates = set(r.get('date') for r in result if r.get('date'))
        materials: Dict[str, int] = {}
        specs: Dict[str, int] = {}
        for r in result:
            mn = r.get('material_name')
            if mn:
                materials[mn] = materials.get(mn, 0) + 1
            sp = r.get('spec')
            if sp:
                specs[sp] = specs.get(sp, 0) + 1
        sorted_dates = sorted(dates)
        return {
            'total_count': len(result),
            'dates_count': len(dates),
            'date_range': {'start': sorted_dates[0] if sorted_dates else None, 'end': sorted_dates[-1] if sorted_dates else None},
            'materials': dict(sorted(materials.items(), key=lambda x: -x[1])[:20]),
            'specs': dict(sorted(specs.items(), key=lambda x: -x[1])[:20])
        }

    def insert_rebar_prices(self, prices: List[Dict]) -> Dict:
        """批量插入钢筋价格数据"""
        imported = 0
        errors = []
        for i, p in enumerate(prices):
            data = {
                'date': p.get('date', ''),
                'fetch_time': p.get('fetch_time') or None,
                'material_name': p.get('material_name', ''),
                'spec': p.get('spec') or None,
                'material_type': p.get('material_type') or None,
                'brand': p.get('brand') or None,
                'price': p.get('price', 0),
                'region': p.get('region', '山东烟台'),
            }
            try:
                resp = self._request('POST', '/rebar_prices', json=data)
                if resp:
                    imported += 1
                else:
                    errors.append({'index': i, 'error': '插入失败'})
            except Exception as e:
                errors.append({'index': i, 'error': str(e)})
        return {'imported': imported, 'total': len(prices), 'errors': errors}

    # ========== 造价参考价 ==========

    def get_cost_reference_prices(
        self,
        category: str = None,
        period: str = None,
        spec: str = None,
        steel_type: str = None,
        min_grade: str = None,
        max_grade: str = None,
        limit: int = 500
    ) -> List[Dict]:
        """获取造价参考价列表"""
        query = f'/cost_reference_prices?select=*&order=name.asc&limit={limit}'
        if category:
            query += f'&category=eq.{category}'
        if period:
            query += f'&period=eq.{period}'
        if spec:
            query += f'&spec=ilike.%25{spec}%25'
        if min_grade:
            query += f'&grade=gte.{min_grade}'
        if max_grade:
            query += f'&grade=lte.{max_grade}'
        result = self._request('GET', query)
        return result if result else []

    def get_cost_reference_categories(self) -> List[Dict]:
        """获取所有分类及统计"""
        result = self._request('GET', '/cost_reference_prices?select=category,period&limit=10000')
        if not result:
            return []
        cats: Dict[str, Dict] = {}
        for r in result:
            cat = r.get('category', '')
            if cat not in cats:
                cats[cat] = {'id': cat, 'name': f'{cat}价格', 'count': 0}
            cats[cat]['count'] += 1
        return list(cats.values())

    def get_cost_reference_summary(self) -> Dict:
        """获取造价参考价汇总"""
        result = self._request('GET', '/cost_reference_prices?select=category,unit_price,pump_price,non_pump_price&limit=10000')
        if not result:
            return {}
        steel_prices = [r.get('unit_price', 0) for r in result if r.get('category') == '钢筋' and r.get('unit_price')]
        concrete_pump = [r.get('pump_price', 0) for r in result if r.get('category') == '混凝土' and r.get('pump_price')]
        concrete_non = [r.get('non_pump_price', 0) for r in result if r.get('category') == '混凝土' and r.get('non_pump_price')]
        mortar_prices = [r.get('unit_price', 0) for r in result if r.get('category') == '砂浆' and r.get('unit_price')]
        return {
            '钢筋': {'count': len(steel_prices), 'price_range': {'min': min(steel_prices) if steel_prices else 0, 'max': max(steel_prices) if steel_prices else 0}, 'unit': '元/吨'},
            '混凝土': {'count': len(concrete_pump), 'price_range': {'min_pump': min(concrete_pump) if concrete_pump else 0, 'max_pump': max(concrete_pump) if concrete_pump else 0}, 'unit': '元/立方米'},
            '砂浆': {'count': len(mortar_prices), 'price_range': {'min': min(mortar_prices) if mortar_prices else 0, 'max': max(mortar_prices) if mortar_prices else 0}, 'unit': '元/吨'},
        }

    def insert_cost_reference_prices(self, items: List[Dict]) -> Dict:
        """批量插入造价参考价"""
        imported = 0
        errors = []
        for i, item in enumerate(items):
            data = {
                'category': item.get('category', ''),
                'code': item.get('code') or None,
                'name': item.get('name', ''),
                'spec': item.get('spec') or None,
                'unit': item.get('unit', 't'),
                'unit_price': item.get('unit_price') or item.get('pump_price') or 0,
                'tax_rate': item.get('tax_rate', 13.0),
                'pump_price': item.get('pump_price') or None,
                'non_pump_price': item.get('non_pump_price') or None,
                'source': item.get('source', '烟台工程建设标准造价管理'),
                'period': item.get('period', '2024年第一季度'),
                'region': item.get('region', '山东烟台'),
                'notes': item.get('notes') or None,
            }
            try:
                resp = self._request('POST', '/cost_reference_prices', json=data)
                if resp:
                    imported += 1
                else:
                    errors.append({'index': i, 'error': '插入失败'})
            except Exception as e:
                errors.append({'index': i, 'error': str(e)})
        return {'imported': imported, 'total': len(items), 'errors': errors}

    def get_cost_reference_price(self, item_id: str) -> Optional[Dict]:
        """获取单条造价参考价"""
        result = self._request('GET', f'/cost_reference_prices?id=eq.{item_id}&select=*')
        if result and len(result) > 0:
            return result[0]
        return None

    # ========== 价格历史 ==========

    def create_price_record(self, record_data: Dict) -> Optional[Dict]:
        """创建价格记录"""
        import uuid
        record_data['id'] = str(uuid.uuid4())
        if self._request('POST', '/price_history', json=record_data):
            return record_data
        return None

    def get_price_records(self, material_id: str = None, source_id: str = None,
                          start_date: str = None, end_date: str = None,
                          limit: int = 100) -> List[Dict]:
        """获取价格记录"""
        filters = []
        if material_id:
            filters.append(f'material_id=eq.{material_id}')
        if source_id:
            filters.append(f'source_id=eq.{source_id}')
        if start_date:
            filters.append(f'recorded_date=gte.{start_date}')
        if end_date:
            filters.append(f'recorded_date=lte.{end_date}')

        query = f'/price_history?order=recorded_date.desc&limit={limit}'
        if filters:
            query = f'/price_history?{"&".join(filters)}&order=recorded_date.desc&limit={limit}'

        result = self._request('GET', query)
        return result if result else []

    # ========== 调差记录 ==========

    def add_adjustment_record(self, record: Dict) -> bool:
        """添加调差记录"""
        import uuid
        record['id'] = str(uuid.uuid4())
        return self._request('POST', '/adjustment_records', json=record) is not None

    # ========== 调差规则 ==========

    def get_adjustment_rules(self) -> List[Dict]:
        """获取所有调差规则"""
        result = self._request('GET', '/adjustment_rules?select=*&order=created_at.desc')
        return result if result else []

    def get_adjustment_rule(self, rule_id: str) -> Optional[Dict]:
        """获取单个调差规则"""
        result = self._request('GET', f'/adjustment_rules?id=eq.{rule_id}&select=*')
        if result and len(result) > 0:
            return result[0]
        return None

    def create_adjustment_rule(self, rule_data: Dict) -> bool:
        """创建调差规则"""
        return self._request('POST', '/adjustment_rules', json=rule_data) is not None

    def update_adjustment_rule(self, rule_id: str, update_data: Dict) -> bool:
        """更新调差规则"""
        return self._request('PATCH', f'/adjustment_rules?id=eq.{rule_id}', json=update_data) is not None

    def delete_adjustment_rule(self, rule_id: str) -> bool:
        """删除调差规则"""
        return self._request('DELETE', f'/adjustment_rules?id=eq.{rule_id}') is not None

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

    # ========== AI 对话会话 ==========

    def get_ai_conversations(self, user_id: str, limit: int = 20, offset: int = 0) -> List[Dict]:
        """获取用户的 AI 对话会话列表"""
        result = self._request(
            'GET',
            f'/ai_conversations?user_id=eq.{user_id}&order=last_message_at.desc&limit={limit}&offset={offset}'
        )
        return result if result else []

    def get_ai_conversation(self, conversation_id: str, user_id: str) -> Optional[Dict]:
        """获取单个 AI 对话会话"""
        result = self._request(
            'GET',
            f'/ai_conversations?id=eq.{conversation_id}&user_id=eq.{user_id}&select=*'
        )
        if result and len(result) > 0:
            conv = result[0]
            # 获取消息数量
            msg_count = self._request(
                'GET',
                f'/ai_messages?conversation_id=eq.{conversation_id}&select=id'
            )
            conv['message_count'] = len(msg_count) if msg_count else 0
            return conv
        return None

    def create_ai_conversation(
        self,
        user_id: str,
        title: str = "新对话",
        model: str = "gpt-4",
        system_prompt: str = None
    ) -> Optional[Dict]:
        """创建新的 AI 对话会话"""
        import uuid
        import time

        conversation = {
            'id': str(uuid.uuid4()),
            'user_id': user_id,
            'title': title,
            'model': model,
            'system_prompt': system_prompt,
            'is_active': True,
            'last_message_at': time.time()
        }

        if self._request('POST', '/ai_conversations', json=conversation):
            return conversation
        return None

    def update_ai_conversation(self, conversation_id: str, user_id: str, data: Dict) -> bool:
        """更新 AI 对话会话"""
        return self._request(
            'PATCH',
            f'/ai_conversations?id=eq.{conversation_id}&user_id=eq.{user_id}',
            json=data
        ) is not None

    def delete_ai_conversation(self, conversation_id: str, user_id: str) -> bool:
        """删除 AI 对话会话（级联删除消息）"""
        return self._request(
            'DELETE',
            f'/ai_conversations?id=eq.{conversation_id}&user_id=eq.{user_id}'
        ) is not None

    def get_ai_messages(
        self,
        conversation_id: str,
        user_id: str,
        limit: int = 50
    ) -> List[Dict]:
        """获取 AI 对话消息历史"""
        # 先验证用户是否有权访问这个会话
        conv = self.get_ai_conversation(conversation_id, user_id)
        if not conv:
            return []

        result = self._request(
            'GET',
            f'/ai_messages?conversation_id=eq.{conversation_id}&order=created_at.asc&limit={limit}'
        )
        return result if result else []

    def save_ai_message(
        self,
        user_id: str,
        role: str,
        content: str,
        conversation_id: str = None,
        metadata: Dict = None
    ) -> bool:
        """保存 AI 对话消息"""
        import uuid
        import time

        # 如果没有指定会话，查找或创建最新会话
        if not conversation_id:
            conversations = self.get_ai_conversations(user_id, limit=1)
            if conversations and conversations[0].get('is_active'):
                conversation_id = conversations[0]['id']
            else:
                # 创建新会话
                new_conv = self.create_ai_conversation(user_id, title=f"对话 {time.strftime('%Y-%m-%d %H:%M')}")
                if new_conv:
                    conversation_id = new_conv['id']

        if not conversation_id:
            return False

        # 生成标题（如果这是第一条消息）
        messages_count = self._request(
            'GET',
            f'/ai_messages?conversation_id=eq.{conversation_id}&select=id'
        )
        is_first = not messages_count or len(messages_count) == 0

        message = {
            'id': str(uuid.uuid4()),
            'conversation_id': conversation_id,
            'role': role,
            'content': content,
            'created_at': time.time()
        }

        if metadata:
            message['metadata'] = metadata

        if self._request('POST', '/ai_messages', json=message):
            # 更新会话的最后消息时间
            self._request(
                'PATCH',
                f'/ai_conversations?id=eq.{conversation_id}',
                json={'last_message_at': time.time()}
            )

            # 如果是第一条消息，更新会话标题
            if is_first and role == "user":
                title = content[:30] + "..." if len(content) > 30 else content
                self._request(
                    'PATCH',
                    f'/ai_conversations?id=eq.{conversation_id}',
                    json={'title': title}
                )

            return True

        return False

    # ========== 知识库文档 ==========

    def list_kb_documents(
        self,
        category: str = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict]:
        """获取知识库文档列表"""
        query = f'/kb_documents?order=created_at.desc&limit={limit}&offset={offset}'
        if category:
            query = f'/kb_documents?category=eq.{category}&order=created_at.desc&limit={limit}&offset={offset}'

        result = self._request('GET', query)
        return result if result else []

    def search_knowledge_base(
        self,
        query: str,
        top_k: int = 5,
        min_similarity: float = 0.7,
        category: str = None
    ) -> List[Dict]:
        """
        搜索知识库（简化的全文搜索）

        注意：完整的向量搜索需要 Supabase pgvector RPC 函数
        这里使用回退的全文搜索方案
        """
        keywords = query.split()[:5]
        search_parts = []

        for kw in keywords:
            if kw.strip():
                search_parts.append(f"content.ilike.%{kw}%")

        if not search_parts:
            return []

        # 构建 OR 查询
        search_query = ",".join(search_parts)
        api_query = f'/kb_documents?or=({search_query})&limit={top_k}'

        if category:
            api_query += f"&category=eq.{category}"

        result = self._request('GET', api_query)
        if result:
            return [{
                'id': r.get('id'),
                'title': r.get('title'),
                'content_chunk': r.get('content', '')[:500],
                'similarity': 0.8,  # 模拟相似度
                'category': r.get('category'),
                'source_url': r.get('source_url')
            } for r in result]
        return []

    def create_kb_document(
        self,
        title: str,
        content: str,
        category: str = None,
        tags: List[str] = None,
        source_url: str = None,
        created_by: str = None
    ) -> Optional[Dict]:
        """创建知识库文档"""
        import uuid

        doc = {
            'id': str(uuid.uuid4()),
            'title': title,
            'content': content,
            'category': category,
            'tags': tags or [],
            'source_url': source_url,
            'created_by': created_by
        }

        if self._request('POST', '/kb_documents', json=doc):
            return doc
        return None

    def delete_kb_document(self, document_id: str) -> bool:
        """删除知识库文档"""
        return self._request(
            'DELETE',
            f'/kb_documents?id=eq.{document_id}'
        ) is not None


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