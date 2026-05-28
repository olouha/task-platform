"""
调差规则管理服务

提供调差规则的CRUD操作和预设规则管理
"""

import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


# 默认规则配置
DEFAULT_RULES: List[Dict[str, Any]] = [
    {
        'name': '钢材调差规则',
        'material_type': 'steel',
        'risk_percent': 5,
        'risk_fixed': 0,
        'tax_rate': 0.09,
        'threshold': 5
    },
    {
        'name': '混凝土调差规则',
        'material_type': 'concrete',
        'risk_percent': 3,
        'risk_fixed': 0,
        'tax_rate': 0.09,
        'threshold': 3
    }
]


class AdjustmentRules:
    """
    调差规则管理器

    提供规则的查询、保存和管理功能
    """

    def __init__(self):
        """初始化规则管理器"""
        logger.info("[AdjustmentRules] 初始化规则管理器")
        self._rules: Dict[str, Dict[str, Any]] = {}
        self._load_default_rules()

    def _load_default_rules(self) -> None:
        """加载默认规则"""
        logger.debug(f"[_load_default_rules] 加载 {len(DEFAULT_RULES)} 条默认规则")
        for rule in DEFAULT_RULES:
            name = rule.get('name')
            if name:
                self._rules[name] = rule.copy()
                logger.debug(f"[_load_default_rules] 加载规则: {name}")

    def get_rules(self) -> List[Dict[str, Any]]:
        """
        获取所有规则

        Returns:
            所有规则的列表
        """
        logger.info(f"[get_rules] 获取所有规则 | count={len(self._rules)}")
        rules_list = list(self._rules.values())
        logger.debug(f"[get_rules] 返回规则列表 | rules={[r.get('name') for r in rules_list]}")
        return rules_list

    def get_rule(self, name: str) -> Optional[Dict[str, Any]]:
        """
        获取指定名称的规则

        Args:
            name: 规则名称

        Returns:
            规则字典，不存在返回None
        """
        logger.info(f"[get_rule] 查询规则 | name={name}")

        rule = self._rules.get(name)
        if rule:
            logger.info(f"[get_rule] 找到规则 | name={name}")
            return rule.copy()
        else:
            logger.warning(f"[get_rule] 规则不存在 | name={name}")
            return None

    def save_rule(self, rule: Dict[str, Any]) -> bool:
        """
        保存规则

        Args:
            rule: 规则字典，必须包含name字段

        Returns:
            保存是否成功
        """
        name = rule.get('name')
        if not name:
            logger.error("[save_rule] 保存失败 | rule缺少name字段")
            return False

        logger.info(f"[save_rule] 保存规则 | name={name}")

        try:
            # 深拷贝规则数据
            rule_copy = rule.copy()
            rule_copy['_updated_at'] = datetime.now().isoformat()

            # 如果是新规则，添加创建时间
            if name not in self._rules:
                rule_copy['_created_at'] = datetime.now().isoformat()
                logger.info(f"[save_rule] 新增规则 | name={name}")
            else:
                # 保留创建时间
                existing = self._rules[name]
                if '_created_at' in existing:
                    rule_copy['_created_at'] = existing['_created_at']

            self._rules[name] = rule_copy
            logger.info(f"[save_rule] 保存成功 | name={name}")
            return True

        except Exception as e:
            logger.error(f"[save_rule] 保存失败 | name={name}, error={type(e).__name__}: {e}", exc_info=True)
            return False

    def delete_rule(self, name: str) -> bool:
        """
        删除规则

        Args:
            name: 规则名称

        Returns:
            删除是否成功
        """
        logger.info(f"[delete_rule] 删除规则 | name={name}")

        if name not in self._rules:
            logger.warning(f"[delete_rule] 规则不存在 | name={name}")
            return False

        try:
            del self._rules[name]
            logger.info(f"[delete_rule] 删除成功 | name={name}")
            return True

        except Exception as e:
            logger.error(f"[delete_rule] 删除失败 | name={name}, error={type(e).__name__}: {e}", exc_info=True)
            return False

    def get_presets(self) -> List[Dict[str, Any]]:
        """
        获取预设规则

        Returns:
            预设规则列表
        """
        logger.info("[get_presets] 获取预设规则")

        presets = [
            {
                'name': '钢材调差规则(标准)',
                'material_type': 'steel',
                'risk_percent': 5,
                'risk_fixed': 0,
                'tax_rate': 0.09,
                'threshold': 5,
                'is_preset': True,
                'description': '适用于钢筋等钢材调差，风险幅度5%'
            },
            {
                'name': '混凝土调差规则(标准)',
                'material_type': 'concrete',
                'risk_percent': 3,
                'risk_fixed': 0,
                'tax_rate': 0.09,
                'threshold': 3,
                'is_preset': True,
                'description': '适用于商品混凝土调差，风险幅度3%'
            },
            {
                'name': '全额调差规则',
                'material_type': 'steel',
                'risk_percent': 0,
                'risk_fixed': 0,
                'tax_rate': 0.09,
                'threshold': 0,
                'is_preset': True,
                'description': '无风险幅度，全额调差'
            },
            {
                'name': '固定金额风险规则',
                'material_type': 'cable',
                'risk_percent': 0,
                'risk_fixed': 1000,
                'tax_rate': 0.09,
                'threshold': 1000,
                'is_preset': True,
                'description': '使用固定金额作为风险幅度阈值（如电缆调差±1000元/吨）'
            },
            {
                'name': '钢材调差规则(严格)',
                'material_type': 'steel',
                'risk_percent': 3,
                'risk_fixed': 0,
                'tax_rate': 0.09,
                'threshold': 3,
                'is_preset': True,
                'description': '较严格的钢材调差规则，风险幅度3%'
            },
            {
                'name': '混凝土调差规则(宽松)',
                'material_type': 'concrete',
                'risk_percent': 5,
                'risk_fixed': 0,
                'tax_rate': 0.09,
                'threshold': 5,
                'is_preset': True,
                'description': '较宽松的混凝土调差规则，风险幅度5%'
            }
        ]

        logger.info(f"[get_presets] 返回 {len(presets)} 个预设规则")
        return presets

    def get_rule_by_material(self, material_type: str) -> Optional[Dict[str, Any]]:
        """
        根据材料类型获取对应规则

        Args:
            material_type: 材料类型（如 'steel', 'concrete'）

        Returns:
            匹配的规则，不存在返回None
        """
        logger.info(f"[get_rule_by_material] 查询规则 | material_type={material_type}")

        for rule in self._rules.values():
            if rule.get('material_type') == material_type:
                logger.info(f"[get_rule_by_material] 找到匹配规则 | material_type={material_type}")
                return rule.copy()

        logger.warning(f"[get_rule_by_material] 未找到匹配规则 | material_type={material_type}")
        return None

    def export_rules(self) -> str:
        """
        导出所有规则为JSON字符串

        Returns:
            JSON格式的规则数据
        """
        logger.info("[export_rules] 导出规则")
        try:
            data = {
                'rules': list(self._rules.values()),
                'exported_at': datetime.now().isoformat()
            }
            json_str = json.dumps(data, ensure_ascii=False, indent=2)
            logger.info(f"[export_rules] 导出成功 | size={len(json_str)} 字节")
            return json_str
        except Exception as e:
            logger.error(f"[export_rules] 导出失败 | {type(e).__name__}: {e}", exc_info=True)
            raise

    def import_rules(self, json_str: str) -> int:
        """
        从JSON字符串导入规则

        Args:
            json_str: JSON格式的规则数据

        Returns:
            导入的规则数量
        """
        logger.info(f"[import_rules] 开始导入 | size={len(json_str)} 字节")

        try:
            data = json.loads(json_str)
            rules_list = data.get('rules', [])

            count = 0
            for rule in rules_list:
                name = rule.get('name')
                if name:
                    self._rules[name] = rule
                    count += 1

            logger.info(f"[import_rules] 导入成功 | count={count}")
            return count

        except json.JSONDecodeError as e:
            logger.error(f"[import_rules] JSON解析失败 | {type(e).__name__}: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"[import_rules] 导入失败 | {type(e).__name__}: {e}", exc_info=True)
            raise

    def clear(self) -> int:
        """
        清空所有非预设规则

        Returns:
            清空的规则数量
        """
        logger.info("[clear] 清空规则")

        non_preset_count = 0
        names_to_delete = []

        for name, rule in self._rules.items():
            if not rule.get('is_preset'):
                names_to_delete.append(name)
                non_preset_count += 1

        for name in names_to_delete:
            del self._rules[name]

        logger.info(f"[clear] 清空完成 | count={non_preset_count}")
        return non_preset_count


# 全局规则管理器实例
_rules_manager: Optional[AdjustmentRules] = None


def get_rules_manager() -> AdjustmentRules:
    """
    获取全局规则管理器实例（单例模式）

    Returns:
        AdjustmentRules实例
    """
    global _rules_manager
    if _rules_manager is None:
        logger.info("[get_rules_manager] 创建全局规则管理器实例")
        _rules_manager = AdjustmentRules()
    return _rules_manager


def get_all_rules() -> List[Dict[str, Any]]:
    """获取所有规则（快捷函数）"""
    return get_rules_manager().get_rules()


def get_preset_rules() -> List[Dict[str, Any]]:
    """获取预设规则（快捷函数）"""
    return get_rules_manager().get_presets()