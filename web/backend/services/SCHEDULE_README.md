# TaskPlatform 调差计算引擎 v3.0 文档

## 概述

v3 引擎是一套完整的材料调差计算解决方案，包含三个核心模块：

| 模块 | 文件 | 功能 |
|------|------|------|
| FormulaEngine | `services/formula_engine.py` | 5种调差公式模板 |
| PriceService | `services/price_service.py` | 价格数据处理与校验 |
| AdjustmentEngineV3 | `services/adjustment_engine_v3.py` | 统一计算引擎 |

遵循规范：《地产项目材料调差规则_AI可执行配置规范》v3.0

---

## 引擎架构

```
AdjustmentEngineV3 (统一计算引擎)
  ├── FormulaEngine (公式工厂)
  │     ├── standard_three_stage    标准三段式
  │     ├── longhu_vat_conversion   龙湖增值税率换算法
  │     ├── ratio_adjustment        豪森比例调差法
  │     ├── cost_info_adjustment    造价信息调整法
  │     └── no_risk                 无风险幅度
  │
  └── PriceService (价格服务)
        ├── get_period_average      获取施工期均价
        ├── get_base_price          获取基准日期价格
        ├── handle_missing_price    处理缺失价格
        ├── validate_prices         校验价格数据
        └── fill_missing_prices     填充缺失价格
```

### 7步计算流程

```
Step 1:  校验配置        _validate_config
Step 2:  取基准价        _fetch_base_prices
Step 3:  取施工期均价    _fetch_period_prices
Step 3.5: 价格数据校验   _validate_price_data
Step 4:  判断风险幅度    _check_risk_threshold
Step 5:  代入公式计算    _calculate_adjustment
Step 5.5: 分阶段汇总      _summarize_by_phase
Step 6:  输出结果        _format_output
```

---

## 公式模板详解

### 1. 标准三段式 (standard_three_stage)

适用于：钢筋、混凝土等常规材料

**公式逻辑**：
- 涨幅超出：`调整金额 = 工程量 × (施工期均价 - 基准价 × (1 + 风险幅度%))`
- 跌幅超出：`调整金额 = 工程量 × (施工期均价 - 基准价 × (1 - 风险幅度%))`
- 风险幅度内：不调差

**风险配置**：
- 钢筋（钢筋）：风险幅度 0%，全额调差
- 混凝土：风险幅度 ±3%

### 2. 龙湖增值税率换算法 (longhu_vat_conversion)

适用于：龙湖地产项目

**公式逻辑**：
- 钢筋（0%风险幅度）：`调整金额 = {工程量 × (指导价 - 基准价)} / (1 + 13%) × (1 + 9%)`
- 混凝土（±3%风险幅度）：`调整金额 = {工程量 × (指导价 - 基准价 × (1 ± 3%))} / 1.13 × 1.09`

**特点**：承包人采购钢材可取得13%增值税专用发票，发包人支付时应换算为合同税率9%

### 3. 豪森比例调差法 (ratio_adjustment)

适用于：豪森置业项目

**公式逻辑**：
- 涨幅：`调整金额 = 基准价 × (Pi/P0 - (1 + 风险幅度)) × 工程量`
- 跌幅：`调整金额 = 基准价 × (Pi/P0 - (1 - 风险幅度)) × 工程量`

**特殊规则**：
- 电缆：铜价波动 <= 2000元/吨 时不调差

### 4. 造价信息调整法 (cost_info_adjustment)

适用于：使用造价信息价调整的项目

**公式逻辑**：与标准三段式相同，区别仅在于公式名称不同

### 5. 无风险幅度 (no_risk)

适用于：全额调差材料

**公式逻辑**：`调整金额 = 工程量 × (施工期均价 - 基准价)`

---

## 数据模型

### FormulaInput (公式输入)

```python
material_name: str       # 材料名称
quantity: float          # 工程量 (>0)
unit: str               # 单位
base_price: float        # 基准价 (>=0)
period_avg_price: float  # 施工期均价 (>=0)
risk_config: dict        # 风险幅度配置 {"类型": "百分比"/"固定金额"/"无", "值": 3.0}
tax_rate: float          # 税率% (默认9)
vat_input_rate: float    # 采购发票增值税率% (默认13, 龙湖模式专用)
vat_output_rate: float   # 合同约定增值税率% (默认9, 龙湖模式专用)
```

### CalculationInput (计算输入)

```python
base_prices: Dict[str, float]              # 材料名 -> 基准价
period_prices: Dict[str, List[PriceData]] # 材料名 -> 价格列表
quantities: List[QuantityData]             # 工程量列表
```

### CalculationResult (计算结果 v3.0)

```python
项目名称: str
调差总金额: float         # 含税总金额
不含税总金额: float
税金: float
明细: List[AdjustmentDetail]
阶段汇总: List[Dict]
价格校验: Dict
使用规则版本: str = "v3.0"
计算时间: datetime
```

---

## 价格数据校验

### HolidayHandling (节假日处理)

| 枚举值 | 说明 |
|--------|------|
| SHIFT_DAY | 顺延1天，取下一个有数据的工作日价格 |
| AVERAGE_PREV_NEXT | 取前后日均价 |
| LAST_MONTH | 取上月最后一天价格 |

### PriceValidationResult (校验结果)

```python
material_name: str      # 材料名称
total_days: int        # 总天数
valid_days: int        # 有效天数
missing_days: int      # 缺失天数
missing_dates: List[str]  # 缺失日期列表
data_completeness: float  # 数据完整率 0.0-1.0
warnings: List[str]    # 警告列表
is_valid: bool         # 是否有效（完整率>=80%视为有效）
```

---

## API 端点

### 调差计算

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/adjustments/calculate` | 执行调差计算 |
| POST | `/api/adjustments/prices/batch-get` | 批量获取价格 |
| GET | `/api/adjustments/prices/batch` | 批量获取价格（GET） |
| GET | `/api/adjustments/prices/completeness` | 检查数据完整率 |
| GET | `/api/adjustments/rules` | 获取调差规则列表 |
| POST | `/api/adjustments/rules` | 创建调差规则 |
| PUT | `/api/adjustments/rules/{id}` | 更新调差规则 |
| DELETE | `/api/adjustments/rules/{id}` | 删除调差规则 |

### 价格管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/yantai-prices` | 获取烟台钢筋价格 |
| POST | `/api/yantai-prices/update-credentials` | 更新凭据 |
| GET | `/api/price-history` | 价格历史记录 |
| POST | `/api/price-history/import` | 导入历史价格 |

---

## 使用示例

### 简单计算

```python
from services.adjustment_engine_v3 import AdjustmentEngineV3

result = AdjustmentEngineV3.calculate_simple(
    base_price=4500,      # 基准价
    avg_price=4800,       # 施工期均价
    quantity=100,          # 工程量（吨）
    risk_percent=3,        # 风险幅度 3%
    tax_rate=9             # 税率 9%
)
# 返回: {"adjustment_amount": 291.24, "total_with_tax": 317.45, ...}
```

### 完整配置计算

```python
from services.adjustment_engine_v3 import (
    AdjustmentEngineV3,
    CalculationInput,
    PriceData,
    QuantityData
)
from models.adjustment_rules import AdjustmentRuleConfig, FormulaType

# 构建配置
config = AdjustmentRuleConfig(
    项目名称="某住宅项目",
    调差公式模板=FormulaType.STANDARD_THREE_STAGE,
    税率=9,
    风险幅度={"钢筋": RiskConfig(类型=RiskType.NONE, 值=0)},
    ...
)

# 构建输入数据
input_data = CalculationInput(
    base_prices={"钢筋": 4500},
    period_prices={"钢筋": [PriceData("2026-05-01", 4600)]},
    quantities=[QuantityData(material_name="钢筋", quantity=100, unit="t")]
)

# 执行计算
engine = AdjustmentEngineV3(config)
result = engine.calculate(input_data)
```

---

## 依赖关系

```
models/adjustment_rules.py
  ├── FormulaType          公式类型枚举
  ├── RiskType             风险类型枚举
  ├── RiskConfig           风险配置
  ├── AdjustmentRuleConfig 规则配置
  └── HolidayHandling      节假日处理枚举

services/formula_engine.py
  └── models.adjustment_rules (FormulaType, RiskType, RiskConfig)

services/price_service.py
  └── models.adjustment_rules (HolidayHandling)

services/adjustment_engine_v3.py
  ├── services.formula_engine (FormulaEngine, FormulaInput)
  ├── services.price_service (PriceService)
  └── models.adjustment_rules (所有枚举和配置)

api/adjustment_prices_batch.py
  └── api.adjustment_prices (load_yantai_prices, get_material_prices)
```

---

## 注意事项

1. **基准价获取**：基准日期必须精确匹配，无数据时返回0
2. **施工期均价**：按时间范围过滤后计算算术平均值
3. **缺失价格处理**：根据 HolidayHandling 配置选择处理方式
4. **数据完整率**：低于80%时标记为警告，低于50%时可能影响计算
5. **多部位分时段**：各部位使用自己的施工时段，互不通用

---

**文档版本**：v3.0
**更新日期**：2026-06-05