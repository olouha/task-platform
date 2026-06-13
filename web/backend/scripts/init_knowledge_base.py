"""
知识库初始化数据脚本
用于初始化系统的知识库内容
"""

import logging
from services.supabase_service import SupabaseService

logger = logging.getLogger(__name__)


# 初始知识库内容
INITIAL_KNOWLEDGE = [
    {
        "title": "调差计算方法",
        "category": "调差计算",
        "content": """【调差计算方法】

调差（价格调整）是指当工程材料价格波动超过合同约定幅度时，对合同价格进行调整的机制。

常见的调差方法：

1. 简单比例法
   调差额 = Σ(材料用量 × 调差单价)
   调差单价 = (本期价格 - 基准价格) × 调整系数

2. 造价信息调整法
   依据当地造价管理部门发布的信息价计算
   调差额 = (信息价 - 合同价) × 用量 × 调整系数

3. 钢筋节点法
   按节点价格计算调差
   适用于钢筋材料的调差计算

4. 票证法
   根据实际采购发票计算调差
   需要提供完整的采购凭证"""
    },
    {
        "title": "材料价格查询说明",
        "category": "价格查询",
        "content": """【材料价格查询说明】

本系统支持查询以下材料价格：

1. 钢筋价格
   - 螺纹钢 (HRB400, HRB400E, HRB500)
   - 光圆钢筋 (HPB300)
   - 数据来源：我的钢铁网
   - 更新频率：每日

2. 混凝土价格
   - 商品混凝土 (C30, C35, C40等)
   - 分为泵送和非泵送两种
   - 数据来源：当地造价信息

3. 水泥价格
   - P.O 42.5 普通硅酸盐水泥
   - P.S 32.5 矿渣硅酸盐水泥

4. 砂石价格
   - 中砂、细砂、粗砂
   - 碎石、石屑

查询方式：
- 按日期查询："查询2024-05-15的螺纹钢价格"
- 查询最新价格："最新钢筋价格"
- 查询趋势："最近一周价格趋势"
"""
    },
    {
        "title": "螺纹钢规格说明",
        "category": "材料信息",
        "content": """【螺纹钢规格说明】

螺纹钢是建筑工程中常用的钢材，表面有螺旋形横肋。

常用牌号：
- HRB400: 屈服强度400MPa，普通建筑用钢
- HRB400E: 抗震钢筋，适用于抗震设防区域
- HRB500: 高强度钢筋，适用于重要结构

常见规格（直径）：
- Φ12: 12mm，用于小型构件
- Φ14: 14mm
- Φ16: 16mm，常用规格
- Φ18: 18mm
- Φ20: 20mm，常用规格
- Φ22: 22mm
- Φ25: 25mm，用于大型构件

长度：
- 定尺：9米、12米
- 理论重量：0.00617 × 直径² (kg/m)

单位：吨（t）
"""
    },
    {
        "title": "混凝土分类与用途",
        "category": "材料信息",
        "content": """【混凝土分类与用途】

混凝土是由胶凝材料、骨料和水按一定比例配制而成。

强度等级：
- C15: 垫层、基础
- C20: 一般构件
- C25: 梁板柱
- C30: 高层建筑主体结构
- C35: 重要结构
- C40: 大跨度结构
- C45及以上：特殊结构

按浇筑方式：
- 商品混凝土（泵送）：适用于高层建筑
- 商品混凝土（非泵送）：适用于一般建筑
- 现场搅拌：小型工程

按用途：
- 结构混凝土：承重结构
- 防水混凝土：地下工程
- 耐腐蚀混凝土：特殊环境

单位：立方米（m³）
"""
    },
    {
        "title": "工程造价调整规则",
        "category": "调差计算",
        "content": """【工程造价调整规则】

根据《建设工程工程量清单计价规范》，材料价格调整需满足以下条件：

1. 调整条件
   - 材料价格波动超过合同约定幅度（通常为±5%）
   - 合同中有明确的调差条款
   - 有合法的价格依据（造价信息、发票等）

2. 调整范围
   - 主要材料：钢筋、水泥、混凝土、砂石等
   - 甲方指定材料
   - 合同约定的其他材料

3. 计算公式
   调差金额 = Σ[(材料实际价格 - 材料基准价格) × 材料用量 × 调整系数]

   其中：
   - 材料实际价格：采购期信息价或发票价
   - 材料基准价格：投标期信息价或合同价
   - 调整系数：合同约定（通常为1或0.9）

4. 申报流程
   - 收集价格证明材料
   - 编制调差计算表
   - 提交监理审核
   - 甲方审批确认
"""
    },
    {
        "title": "钢筋价格影响因素",
        "category": "价格分析",
        "content": """【钢筋价格影响因素】

钢筋价格受多种因素影响：

1. 原材料成本
   - 铁矿石价格
   - 焦炭价格
   - 废钢价格

2. 市场供需
   - 房地产开工情况
   - 基础设施投资
   - 季节性因素（春季开工旺季）

3. 政策因素
   - 环保限产
   - 产能控制
   - 进口关税

4. 区域差异
   - 运输成本
   - 当地供需情况
   - 主流品牌价格

价格趋势观察：
- 每年3-5月：春季开工，价格通常上涨
- 每年11-12月：冬季停工，价格回落
- 重大事件（疫情、政策等）会显著影响价格
"""
    },
    {
        "title": "系统使用指南",
        "category": "系统帮助",
        "content": """【系统使用指南】

工程材料管理系统提供以下功能：

1. 价格查询
   - 支持按日期、材料类型查询价格
   - 显示详细的价格信息（规格、品牌、价格）
   - 支持查看价格趋势图

2. 调差计算
   - 输入项目信息和使用量
   - 自动计算调差金额
   - 生成调差计算报告

3. 数据管理
   - 项目信息管理
   - 材料库管理
   - 价格历史查询

4. AI助手
   - 自然语言查询价格
   - 解答调差计算问题
   - 提供材料信息咨询

使用示例：
- "查询螺纹钢价格"
- "最近一周钢筋价格趋势"
- "什么是调差计算？"
- "HRB400E Φ16 最新价格"
"""
    },
    {
        "title": "水泥品种与用途",
        "category": "材料信息",
        "content": """【水泥品种与用途】

水泥是建筑工程最重要的胶凝材料。

常用品种：

1. 硅酸盐水泥（P.I）
   - 强度高，硬化快
   - 适用于重要结构

2. 普通硅酸盐水泥（P.O）
   - 最常用的品种
   - 适用于一般建筑
   - P.O 42.5：强度42.5MPa
   - P.O 52.5：强度52.5MPa

3. 矿渣硅酸盐水泥（P.S）
   - 耐水性好
   - 适用于地下工程

4. 粉煤灰水泥（P.F）
   - 水化热低
   - 适用于大体积混凝土

标号含义：
- 32.5: 28天抗压强度≥32.5MPa
- 42.5: 28天抗压强度≥42.5MPa
- 52.5: 28天抗压强度≥52.5MPa

单位：吨（t）
"""
    },
    {
        "title": "烟台地区价格信息来源",
        "category": "价格信息",
        "content": """【烟台地区价格信息来源】

烟台地区工程材料价格主要来源：

1. 官方造价信息
   - 烟台市工程建设标准造价管理站
   - 发布周期：每月
   - 内容：当地常用材料信息价

2. 市场价格
   - 我的钢铁网（steelwise.com）
   - 百度建材网
   - 当地建材市场

3. 供应商报价
   - 材料供应商直接报价
   - 需要考虑运费和付款条件

价格使用建议：
- 合同约定优先
- 信息价作为参考
- 实际采购价作为调差依据
- 注意价格的有效期和地域性
"""
    },
    {
        "title": "砂浆分类与用途",
        "category": "材料信息",
        "content": """【砂浆分类与用途】

砂浆是由胶凝材料、细骨料和水按一定比例配制而成。

按用途分类：

1. 砌筑砂浆
   - 用于砌筑墙体
   - 常用强度：M5、M7.5、M10
   - 材料：水泥、砂、水

2. 抹灰砂浆
   - 用于墙面抹灰
   - 常用强度：M5、M7.5
   - 分为内墙和外墙

3. 地面砂浆
   - 用于地面找平
   - 常用强度：M10、M15

按胶凝材料分类：
- 水泥砂浆：强度高，适用于潮湿环境
- 混合砂浆：水泥+石灰，和易性好
- 石灰砂浆：强度低，适用于临时建筑

单位：立方米（m³）
"""
    }
]


def init_knowledge_base():
    """初始化知识库数据"""
    logger.info("[init_knowledge_base] 开始初始化知识库")

    supabase = SupabaseService()

    # 检查是否已有数据
    existing_docs = supabase.list_kb_documents(limit=1)
    if existing_docs:
        logger.info(f"[init_knowledge_base] 知识库已有 {len(existing_docs)} 条数据，跳过初始化")
        return {"status": "skipped", "reason": "知识库已存在数据"}

    # 批量插入
    imported = 0
    errors = []

    for doc_data in INITIAL_KNOWLEDGE:
        try:
            result = supabase.create_kb_document(
                title=doc_data["title"],
                content=doc_data["content"],
                category=doc_data["category"],
                created_by="system"
            )
            if result:
                imported += 1
                logger.info(f"[init_knowledge_base] 导入成功 | title={doc_data['title']}")
            else:
                errors.append({"title": doc_data["title"], "error": "插入失败"})
        except Exception as e:
            errors.append({"title": doc_data["title"], "error": str(e)})
            logger.error(f"[init_knowledge_base] 导入失败 | title={doc_data['title']}, error={e}")

    logger.info(f"[init_knowledge_base] 初始化完成 | imported={imported}, errors={len(errors)}")

    return {
        "status": "completed",
        "imported": imported,
        "total": len(INITIAL_KNOWLEDGE),
        "errors": errors
    }


if __name__ == "__main__":
    # 直接运行此脚本来初始化知识库
    result = init_knowledge_base()
    print(f"\n{'='*50}")
    print(f"知识库初始化结果：")
    print(f"状态: {result['status']}")
    if result['status'] == 'completed':
        print(f"导入: {result['imported']}/{result['total']} 条")
        if result['errors']:
            print(f"错误: {len(result['errors'])} 条")
            for err in result['errors']:
                print(f"  - {err['title']}: {err['error']}")
    print(f"{'='*50}\n")
