"""
工程调差计算引擎
根据配置计算材料调差
"""

import logging
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple
from decimal import Decimal, ROUND_HALF_UP

logger = logging.getLogger(__name__)


class AdjustmentCalculator:
    """工程调差计算器"""

    def __init__(self, database):
        self.db = database

    def calculate_phase_adjustment(self, project_id: str, phase_id: str) -> Dict:
        """计算某个阶段的调差"""
        # 获取阶段信息
        phases = self.db.get_phases(project_id)
        phase = next((p for p in phases if p.get('id') == phase_id), None)

        if not phase:
            return {'success': False, 'error': 'Phase not found'}

        # 获取项目材料
        materials = self.db.get_project_materials(project_id)

        results = {
            'phase': phase,
            'materials': [],
            'total_adjustment': 0
        }

        for material in materials:
            # 获取阶段内平均价格
            avg_price = self._get_average_price(
                material.get('material_id'),
                phase.get('start_date'),
                phase.get('end_date')
            )

            if avg_price is None:
                # 如果没有抓取数据，使用基准价
                avg_price = material.get('base_price', 0)

            # 计算调差
            base_price = material.get('base_price', 0)
            quantity = material.get('quantity', 0)
            adjustment_type = material.get('adjustment_type', 'adjustable')
            threshold = material.get('threshold', 5.0)

            change_rate = 0
            adjustment_amount = 0
            is_over_threshold = False

            if base_price > 0:
                change_rate = ((avg_price - base_price) / base_price) * 100

                # 根据调差类型计算
                if adjustment_type == 'full':
                    # 全调
                    adjustment_amount = (avg_price - base_price) * quantity
                elif adjustment_type == 'adjustable':
                    # 可调（超过阈值才调）
                    if abs(change_rate) > threshold:
                        # 超过阈值，只调超出的部分
                        effective_rate = change_rate - (threshold if change_rate > 0 else -threshold)
                        adjustment_amount = base_price * (effective_rate / 100) * quantity
                        is_over_threshold = True
                else:
                    # 固定，不调
                    adjustment_amount = 0

            material_result = {
                'material_id': material.get('material_id'),
                'material_name': material.get('material_name'),
                'spec': material.get('spec'),
                'unit': material.get('unit'),
                'quantity': quantity,
                'base_price': base_price,
                'avg_price': avg_price,
                'change_rate': round(change_rate, 2),
                'adjustment_type': adjustment_type,
                'threshold': threshold,
                'adjustment_amount': round(adjustment_amount, 2),
                'is_over_threshold': is_over_threshold
            }

            results['materials'].append(material_result)
            results['total_adjustment'] += adjustment_amount

            # 保存调差记录
            self.db.add_adjustment_record({
                'project_id': project_id,
                'material_id': material.get('material_id'),
                'phase_id': phase_id,
                'phase_name': phase.get('phase_name'),
                'base_price': base_price,
                'current_price': avg_price,
                'change_rate': round(change_rate, 4),
                'adjustment_amount': round(adjustment_amount, 2)
            })

        results['total_adjustment'] = round(results['total_adjustment'], 2)

        return results

    def calculate_project_adjustment(self, project_id: str) -> Dict:
        """计算整个项目的调差"""
        # 获取项目
        project = self.db.get_project(project_id)
        if not project:
            return {'success': False, 'error': 'Project not found'}

        # 获取所有阶段
        phases = self.db.get_phases(project_id)

        results = {
            'project': project,
            'phases': [],
            'total_adjustment': 0,
            'material_summary': {}
        }

        for phase in phases:
            phase_result = self.calculate_phase_adjustment(project_id, phase.get('id'))
            results['phases'].append(phase_result)
            results['total_adjustment'] += phase_result.get('total_adjustment', 0)

            # 汇总材料
            for m in phase_result.get('materials', []):
                mid = m.get('material_id')
                if mid not in results['material_summary']:
                    results['material_summary'][mid] = {
                        'name': m.get('material_name'),
                        'adjustment_amount': 0
                    }
                results['material_summary'][mid]['adjustment_amount'] += m.get('adjustment_amount', 0)

        results['total_adjustment'] = round(results['total_adjustment'], 2)

        return results

    def query_price_history(self, material_id: str = None,
                           start_date: str = None,
                           end_date: str = None,
                           category: str = None) -> List[Dict]:
        """查询价格历史"""
        if category:
            # 按分类查询
            materials = self.db.get_all_materials()
            category_id = None

            # 找到分类ID
            categories = self.db.get_material_categories()
            for cat in categories:
                if cat.get('name') == category:
                    category_id = cat.get('id')
                    break

            if category_id:
                materials = [m for m in materials if m.get('category_id') == category_id]

            results = []
            for m in materials:
                history = self.db.get_price_history(m.get('id'), start_date, end_date)
                for h in history:
                    h['material_name'] = m.get('name')
                    h['spec'] = m.get('spec')
                results.extend(history)

            return sorted(results, key=lambda x: x.get('recorded_date', ''), reverse=True)

        return self.db.get_price_history(material_id, start_date, end_date)

    def get_statistics(self, project_id: str = None) -> Dict:
        """获取统计信息"""
        stats = {
            'total_materials': 0,
            'total_projects': 0,
            'price_sources': 0,
            'adjustment_records': 0,
            'latest_prices': []
        }

        # 获取最新价格
        latest_prices = self.db.get_latest_prices()
        stats['latest_prices'] = latest_prices
        stats['price_sources'] = len(self.db.get_price_sources())

        # 获取项目统计
        if project_id:
            records = self.db.get_adjustment_records(project_id)
            stats['adjustment_records'] = len(records)

            total = sum(r.get('adjustment_amount', 0) for r in records)
            stats['total_adjustment'] = round(total, 2)

        return stats

    def _get_average_price(self, material_id: str, start_date: str, end_date: str) -> Optional[float]:
        """获取时间段内平均价格"""
        history = self.db.get_price_history(material_id, start_date, end_date)

        if not history:
            return None

        prices = [h.get('price') for h in history if h.get('price')]
        if prices:
            return sum(prices) / len(prices)

        return None

    def export_to_dict(self, project_id: str) -> Dict:
        """导出项目数据为字典"""
        result = self.calculate_project_adjustment(project_id)

        export_data = {
            'project_name': result.get('project', {}).get('name', ''),
            'contract_no': result.get('project', {}).get('contract_no', ''),
            'base_date': result.get('project', {}).get('base_date', ''),
            'completion_date': result.get('project', {}).get('completion_date', ''),
            'total_adjustment': result.get('total_adjustment', 0),
            'adjustment_text': self._number_to_chinese(result.get('total_adjustment', 0)),
            'phases': []
        }

        for phase in result.get('phases', []):
            phase_data = {
                'phase_name': phase.get('phase', {}).get('phase_name', ''),
                'start_date': phase.get('phase', {}).get('start_date', ''),
                'end_date': phase.get('phase', {}).get('end_date', ''),
                'adjustment': phase.get('total_adjustment', 0),
                'materials': []
            }

            for m in phase.get('materials', []):
                phase_data['materials'].append({
                    'name': m.get('material_name'),
                    'spec': m.get('spec'),
                    'unit': m.get('unit'),
                    'quantity': m.get('quantity'),
                    'base_price': m.get('base_price'),
                    'avg_price': m.get('avg_price'),
                    'change_rate': f"{m.get('change_rate', 0):+.2f}%",
                    'adjustment_amount': m.get('adjustment_amount', 0)
                })

            export_data['phases'].append(phase_data)

        return export_data

    def _number_to_chinese(self, num: float) -> str:
        """数字转中文大写"""
        if num == 0:
            return '零元整'

        num = round(abs(num), 2)
        num_str = str(num)

        # 整数部分
        integer = int(num)
        decimal = num_str.split('.')[-1] if '.' in num_str else '00'

        # 中文数字
        CN_NUM = '零壹贰叁肆伍陆柒捌玖'
        CN_UNIT = '元拾佰仟万'

        result = ''

        if num < 0:
            result = '负'

        # 处理整数部分
        integer_str = str(integer)
        length = len(integer_str)

        for i, c in enumerate(integer_str):
            digit = int(c)
            unit = CN_UNIT[len(integer_str) - i - 1]
            result += CN_NUM[digit] + unit

        # 去除连续的零
        result = result.replace('零元', '元').replace('零零', '零')

        # 添加小数部分
        if decimal != '00':
            result += CN_NUM[int(decimal[0])] + '角'
            if len(decimal) > 1:
                result += CN_NUM[int(decimal[1])] + '分'
        else:
            result += '整'

        return result
