"""
初始化指标库数据 - 添加示例项目
"""
import sys
import logging
from pathlib import Path

# 添加web/backend到路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from services.local_indicator_service import LocalIndicatorService

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


# 示例指标库数据
SAMPLE_PROJECTS = [
    {
        "id": "IND-001",
        "name": "济南万科住宅项目A区",
        "category": "住宅",
        "location": "山东",
        "structure": "剪力墙结构",
        "floor_above": 28,
        "floor_below": 2,
        "area_total": 85000,
        "height": 89,
        "unit_cost": 2650,
        "unit_structure": 1550,
        "unit_installation": 420,
        "unit_decoration": 580,
        "unit_measure": 100,
        "steel": 52,
        "concrete": 0.42,
        "source": "示例数据"
    },
    {
        "id": "IND-002",
        "name": "青岛保利商业综合体",
        "category": "商业",
        "location": "山东",
        "structure": "框架结构",
        "floor_above": 6,
        "floor_below": 1,
        "area_total": 42000,
        "height": 28,
        "unit_cost": 3800,
        "unit_structure": 2200,
        "unit_installation": 850,
        "unit_decoration": 650,
        "unit_measure": 100,
        "steel": 58,
        "concrete": 0.45,
        "source": "示例数据"
    },
    {
        "id": "IND-003",
        "name": "烟台龙湖办公楼",
        "category": "办公",
        "location": "山东",
        "structure": "框架核心筒",
        "floor_above": 22,
        "floor_below": 2,
        "area_total": 55000,
        "height": 98,
        "unit_cost": 4200,
        "unit_structure": 2500,
        "unit_installation": 1100,
        "unit_decoration": 500,
        "unit_measure": 100,
        "steel": 65,
        "concrete": 0.48,
        "source": "示例数据"
    },
    {
        "id": "IND-004",
        "name": "济南绿地住宅二期",
        "category": "住宅",
        "location": "山东",
        "structure": "剪力墙结构",
        "floor_above": 33,
        "floor_below": 1,
        "area_total": 120000,
        "height": 99,
        "unit_cost": 2850,
        "unit_structure": 1650,
        "unit_installation": 450,
        "unit_decoration": 650,
        "unit_measure": 100,
        "steel": 55,
        "concrete": 0.44,
        "source": "示例数据"
    },
    {
        "id": "IND-005",
        "name": "潍坊万达广场",
        "category": "商业",
        "location": "山东",
        "structure": "框架结构",
        "floor_above": 5,
        "floor_below": 1,
        "area_total": 68000,
        "height": 24,
        "unit_cost": 3500,
        "unit_structure": 2000,
        "unit_installation": 800,
        "unit_decoration": 600,
        "unit_measure": 100,
        "steel": 54,
        "concrete": 0.43,
        "source": "示例数据"
    },
    {
        "id": "IND-006",
        "name": "烟台万科翡翠公园",
        "category": "住宅",
        "location": "山东",
        "structure": "剪力墙结构",
        "floor_above": 18,
        "floor_below": 1,
        "area_total": 55000,
        "height": 58,
        "unit_cost": 2550,
        "unit_structure": 1500,
        "unit_installation": 400,
        "unit_decoration": 550,
        "unit_measure": 100,
        "steel": 48,
        "concrete": 0.41,
        "source": "示例数据"
    },
    {
        "id": "IND-007",
        "name": "济南华润办公楼",
        "category": "办公",
        "location": "山东",
        "structure": "框架剪力墙结构",
        "floor_above": 18,
        "floor_below": 2,
        "area_total": 45000,
        "height": 76,
        "unit_cost": 3900,
        "unit_structure": 2300,
        "unit_installation": 1000,
        "unit_decoration": 500,
        "unit_measure": 100,
        "steel": 62,
        "concrete": 0.47,
        "source": "示例数据"
    },
    {
        "id": "IND-008",
        "name": "青岛中海国际社区",
        "category": "住宅",
        "location": "山东",
        "structure": "剪力墙结构",
        "floor_above": 26,
        "floor_below": 2,
        "area_total": 95000,
        "height": 82,
        "unit_cost": 2750,
        "unit_structure": 1600,
        "unit_installation": 430,
        "unit_decoration": 620,
        "unit_measure": 100,
        "steel": 50,
        "concrete": 0.42,
        "source": "示例数据"
    },
    {
        "id": "IND-009",
        "name": "临沂万达广场",
        "category": "商业",
        "location": "山东",
        "structure": "框架结构",
        "floor_above": 4,
        "floor_below": 1,
        "area_total": 75000,
        "height": 22,
        "unit_cost": 3400,
        "unit_structure": 1950,
        "unit_installation": 780,
        "unit_decoration": 570,
        "unit_measure": 100,
        "steel": 52,
        "concrete": 0.42,
        "source": "示例数据"
    },
    {
        "id": "IND-010",
        "name": "烟台金域蓝湾",
        "category": "住宅",
        "location": "山东",
        "structure": "剪力墙结构",
        "floor_above": 22,
        "floor_below": 1,
        "area_total": 72000,
        "height": 70,
        "unit_cost": 2600,
        "unit_structure": 1520,
        "unit_installation": 410,
        "unit_decoration": 570,
        "unit_measure": 100,
        "steel": 49,
        "concrete": 0.40,
        "source": "示例数据"
    }
]


def main():
    """初始化指标库数据"""
    logger.info("=" * 60)
    logger.info("初始化指标库数据")
    logger.info("=" * 60)

    service = LocalIndicatorService()

    # 检查现有数据
    stats = service.get_stats()
    logger.info(f"\n当前指标库状态:")
    logger.info(f"  总项目数: {stats['total']}")
    logger.info(f"  按业态: {stats['by_category']}")
    logger.info(f"  按地区: {stats['by_location']}")

    if stats['total'] > 0:
        logger.info(f"\n指标库已有数据，跳过初始化")
        return

    # 导入示例数据
    logger.info(f"\n开始导入 {len(SAMPLE_PROJECTS)} 个示例项目...")

    result = service.import_indicator_projects(SAMPLE_PROJECTS)

    logger.info(f"\n导入结果:")
    logger.info(f"  成功: {result['imported']}")
    logger.info(f"  总数: {result['total']}")

    if result['errors']:
        logger.warning(f"  错误: {result['errors']}")

    # 验证导入结果
    stats = service.get_stats()
    logger.info(f"\n导入后指标库状态:")
    logger.info(f"  总项目数: {stats['total']}")
    logger.info(f"  按业态: {stats['by_category']}")
    logger.info(f"  按地区: {stats['by_location']}")

    logger.info("\n" + "=" * 60)
    logger.info("初始化完成!")
    logger.info("=" * 60)


if __name__ == '__main__':
    main()
