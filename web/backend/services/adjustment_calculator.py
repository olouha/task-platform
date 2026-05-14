"""
调差计算服务
"""

from datetime import datetime, date, timedelta
from typing import Dict, List, Optional
from decimal import Decimal, ROUND_HALF_UP


class AdjustmentCalculator:
    """工程调差计算器"""

    def __init__(self):
        pass

    def calculate_phase_adjustment(
        self,
        project_id: str,
        phase_id: str,
        materials: List[Dict],
        price_history: Dict[str, List[Dict]],
        start_date: str,
        end_date: str
    ) -> Dict:
        """计算某个阶段的调差"""

        results = {
            'phase_id': phase_id,
            'start_date': start_date,
            'end_date': end_date,
            'materials': [],
            'total_adjustment': 0
        }

        for material in materials:
            # 获取阶段内平均价格
            material_id = material.get('material_id')
            history = price_history.get(material_id, [])

            # 筛选时间范围内的记录
            period_prices = [
                h.get('price') for h in history
                if start_date <= h.get('recorded_date', '') <= end_date
                and h.get('price')
            ]

            if period_prices:
                avg_price = sum(period_prices) / len(period_prices)
            else:
                # 没有数据，使用基准价
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

                if adjustment_type == 'full':
                    # 全调
                    adjustment_amount = (avg_price - base_price) * quantity
                elif adjustment_type == 'adjustable':
                    # 可调（超过阈值才调）
                    if abs(change_rate) > threshold:
                        effective_rate = change_rate - (threshold if change_rate > 0 else -threshold)
                        adjustment_amount = base_price * (effective_rate / 100) * quantity
                        is_over_threshold = True
                # fixed: adjustment_amount = 0

            material_result = {
                'material_id': material_id,
                'material_name': material.get('material_name'),
                'spec': material.get('spec'),
                'unit': material.get('unit'),
                'quantity': quantity,
                'base_price': base_price,
                'avg_price': round(avg_price, 2),
                'change_rate': round(change_rate, 2),
                'adjustment_type': adjustment_type,
                'threshold': threshold,
                'adjustment_amount': round(adjustment_amount, 2),
                'is_over_threshold': is_over_threshold
            }

            results['materials'].append(material_result)
            results['total_adjustment'] += adjustment_amount

        results['total_adjustment'] = round(results['total_adjustment'], 2)

        return results

    def calculate_project_adjustment(
        self,
        project_id: str,
        phases: List[Dict],
        materials: List[Dict],
        price_history: Dict[str, List[Dict]]
    ) -> Dict:
        """计算整个项目的调差"""

        results = {
            'project_id': project_id,
            'phases': [],
            'total_adjustment': 0,
            'material_summary': {}
        }

        # 按 material_id 分组材料
        material_map = {m.get('material_id'): m for m in materials}

        for phase in phases:
            phase_result = self.calculate_phase_adjustment(
                project_id,
                phase.get('id'),
                materials,
                price_history,
                phase.get('start_date', ''),
                phase.get('end_date', '')
            )
            phase_result['phase_name'] = phase.get('phase_name')
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

    def export_to_report(self, result: Dict) -> Dict:
        """导出为报表格式"""
        export_data = {
            'project_id': result.get('project_id'),
            'total_adjustment': result.get('total_adjustment', 0),
            'adjustment_text': self.number_to_chinese(result.get('total_adjustment', 0)),
            'phases': []
        }

        for phase in result.get('phases', []):
            phase_data = {
                'phase_name': phase.get('phase_name'),
                'start_date': phase.get('start_date'),
                'end_date': phase.get('end_date'),
                'adjustment': phase.get('total_adjustment', 0),
                'materials': [
                    {
                        'name': m.get('material_name'),
                        'spec': m.get('spec'),
                        'unit': m.get('unit'),
                        'quantity': m.get('quantity'),
                        'base_price': m.get('base_price'),
                        'avg_price': m.get('avg_price'),
                        'change_rate': f"{m.get('change_rate', 0):+.2f}%",
                        'adjustment_amount': m.get('adjustment_amount', 0)
                    }
                    for m in phase.get('materials', [])
                ]
            }
            export_data['phases'].append(phase_data)

        return export_data

    def number_to_chinese(self, num: float) -> str:
        """数字转中文大写"""
        if num == 0:
            return '零元整'

        num = round(abs(num), 2)
        num_str = str(num)
        integer = int(num)
        decimal = num_str.split('.')[-1] if '.' in num_str else '00'

        CN_NUM = '零壹贰叁肆伍陆柒捌玖'
        CN_UNIT = '元拾佰仟万'

        result = ''
        if num < 0:
            result = '负'

        integer_str = str(integer)
        for i, c in enumerate(integer_str):
            digit = int(c)
            unit = CN_UNIT[len(integer_str) - i - 1]
            result += CN_NUM[digit] + unit

        result = result.replace('零元', '元').replace('零零', '零')

        if decimal != '00':
            result += CN_NUM[int(decimal[0])] + '角'
            if len(decimal) > 1:
                result += CN_NUM[int(decimal[1])] + '分'
        else:
            result += '整'

        return result


class IndicatorService:
    """指标服务"""

    def __init__(self):
        pass

    def evaluate_indicators(self, indicators: List[Dict], current_values: Dict[str, float]) -> List[Dict]:
        """评估指标状态"""
        results = []

        for indicator in indicators:
            indicator_id = indicator.get('id')
            current_value = current_values.get(indicator_id)
            target_value = indicator.get('target_value')
            warning_threshold = indicator.get('warning_threshold')
            target_type = indicator.get('target_type', 'max')  # max, min, range

            if current_value is None or target_value is None:
                status = 'unknown'
            elif target_type == 'max':
                # 目标为最大值，不能超过
                if current_value > target_value * (1 + warning_threshold / 100):
                    status = 'danger'
                elif current_value > target_value:
                    status = 'warning'
                else:
                    status = 'normal'
            elif target_type == 'min':
                # 目标为最小值，不能低于
                if current_value < target_value * (1 - warning_threshold / 100):
                    status = 'danger'
                elif current_value < target_value:
                    status = 'warning'
                else:
                    status = 'normal'
            else:
                status = 'normal'

            results.append({
                **indicator,
                'current_value': current_value,
                'status': status
            })

        return results

    def calculate_progress(self, current: float, target: float) -> float:
        """计算进度百分比"""
        if target <= 0:
            return 0
        return min(round(current / target * 100, 1), 100)