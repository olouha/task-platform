# 调差计算模块优化设计方案

**版本**: v1.0
**日期**: 2026-06-05
**方案**: 方案B（一次性重构）
**状态**: 待审批

---

## 1. 问题诊断

| 模块 | 问题 |
|------|------|
| **计算引擎** | 两个引擎文件 `adjustment_engine.py` 和 `adjustment_engine_v2.py` 功能重叠，代码维护困难 |
| **公式实现** | 龙湖增值税率换算、豪森电缆公式等特殊公式实现不完整或有bug |
| **价格处理** | `_handle_missing_price` 多处返回0，无实际处理逻辑 |
| **API** | `total_adjustment` 与 `调差总金额` 字段名不统一，前后端集成问题 |
| **前端** | 价格获取只能单材料，分时段均价计算缺失，多部位施工时段无法分别设置 |
| **数据校验** | 价格数据缺失时的处理逻辑不完整 |

---

## 2. 优化目标

1. **统一计算引擎** — 整合两个引擎为一个 v3.0 引擎
2. **修复公式bug** — 确保5种公式模板（含龙湖增值税换算）正确实现
3. **完善价格处理** — 实现节假日/缺失价格的三种处理逻辑
4. **统一API字段** — 前后端使用统一的中文字段名
5. **增强前端向导** — 支持批量价格获取、多部位时段配置、实时预览

---

## 3. 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                     前端 (React)                          │
│  Adjustment.tsx  — 4步计算向导 + 结果展示                  │
└────────────────────────┬────────────────────────────────┘
                          │ HTTP/REST
┌────────────────────────▼────────────────────────────────┐
│                   API 层 (FastAPI)                        │
│  adjustments.py  — 统一入口，统一字段名                    │
│  adjustment_prices.py  — 价格查询                        │
│  adjustment_rules.py  — 规则CRUD                         │
└────────────────────────┬────────────────────────────────┘
                          │
┌────────────────────────▼────────────────────────────────┐
│               计算引擎层 (核心重构)                       │
│  ┌─────────────────────────────────────────────────┐    │
│  │         AdjustmentEngineV3 (统一引擎)            │    │
│  │  ├── _fetch_base_prices()  — 基准价获取           │    │
│  │  ├── _fetch_period_prices()  — 施工期均价         │    │
│  │  ├── _validate_prices()  — 价格数据校验          │    │
│  │  ├── _check_risk()  — 风险幅度判断               │    │
│  │  ├── _calculate()  — 分材料计算                  │    │
│  │  └── _format_output()  — 统一输出               │    │
│  └─────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────┐    │
│  │         FormulaEngine (公式工厂)                  │    │
│  │  ├── standard_three_stage()  — 标准三段式        │    │
│  │  ├── no_risk()  — 无风险幅度                    │    │
│  │  ├── ratio_adjustment()  — 豪森比例调差法       │    │
│  │  ├── cost_info_adjustment()  — 造价信息调整法    │    │
│  │  ├── longhu_vat_conversion()  — 龙湖增值税换算   │    │
│  │  └── custom()  — 自定义公式                     │    │
│  └─────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────┐    │
│  │         PriceService (价格服务)                   │    │
│  │  ├── get_base_price()  — 获取基准价              │    │
│  │  ├── get_period_avg()  — 施工期均价             │    │
│  │  ├── handle_missing()  — 缺失价格处理            │    │
│  │  └── validate()  — 数据校验                     │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
                          │
┌────────────────────────▼────────────────────────────────┐
│                  数据层 (SQLite + Supabase)               │
│  yantai_rebar.db  — 钢筋价格历史数据                      │
│  adjustment_rules  — 调差规则配置                        │
│  adjustment_projects  — 项目数据                        │
└─────────────────────────────────────────────────────────┘
```

---

## 4. 核心数据结构

### 4.1 调差规则配置（统一模型）

```python
class AdjustmentRuleConfig(BaseModel):
    """调差规则配置 - 统一版本 v3.0"""

    # ===== 元信息 =====
    id: Optional[str] = None
    项目名称: str
    使用规则版本: str = "v3.0"

    # ===== 调差材料 =====
    调差项目: List[MaterialItem] = []

    # ===== 价格规则 =====
    风险幅度: Dict[str, RiskConfig] = {}   # {材料名: RiskConfig}
    基准价来源: PriceSource
    基准价取价规则: str
    施工期价格采集规则: str = "按月算术平均"
    节假日无价处理规则: HolidayHandling = HolidayHandling.SHIFT_DAY
    价格取整规则: PriceRounding = PriceRounding.TWO_DECIMAL

    # ===== 阶段配置 =====
    是否分阶段调差: PhaseType = PhaseType.NO
    阶段划分: List[PhaseDefinition] = []

    # ===== 计算公式 =====
    调差公式模板: FormulaType
    税率: float = 9.0
    负数处理: NegativeHandling = NegativeHandling.DEDUCT
    增值税率: Optional[float] = None   # 龙湖专用：13%
    合同税率: Optional[float] = None   # 龙湖专用：9%

    # ===== 特殊材料规则 =====
    材料特殊规则: Dict[str, Dict[str, Any]] = {}  # 材料 -> 特殊规则
```

### 4.2 材料配置

```python
class MaterialItem(BaseModel):
    """单个材料配置"""
    名称: str                      # 如：钢筋、商品混凝土
    是否必调: AdjustmentType
    规格列表: List[str] = []       # 如：["HRB400", "Φ12"]
    单位: str = "t"                # 默认吨
    供货方式: SupplyType = SupplyType.B_TYPE
    风险幅度类型: RiskType = RiskType.PERCENTAGE
    风险幅度值: float = 3.0
    是否分阶段调差: bool = False
```

### 4.3 风险幅度配置

```python
class RiskConfig(BaseModel):
    """风险幅度配置"""
    类型: RiskType  # PERCENTAGE | FIXED | NONE
    值: float = 0.0
    说明: Optional[str] = None
```

### 4.4 计算输入

```python
@dataclass
class CalculationInput:
    """计算输入数据"""
    base_prices: Dict[str, float]              # {材料名: 基准价}
    period_prices: Dict[str, List[PriceData]]  # {材料名: [价格列表]}
    quantities: List[QuantityData]             # 工程量列表


@dataclass
class QuantityData:
    """工程量数据"""
    material_name: str
    spec: str = ""                    # 规格
    quantity: float
    unit: str = "t"
    phase: str = "整体"               # 阶段
    location: str = ""                # 部位/楼栋
    start_date: Optional[str] = None  # 施工开始
    end_date: Optional[str] = None    # 施工结束


@dataclass
class PriceData:
    """价格数据"""
    date: str
    price: float
    source: str = ""
```

### 4.5 计算输出（统一字段名）

```python
class CalculationResult(BaseModel):
    """调差计算结果 - 统一输出格式 v3.0"""
    项目名称: str
    调差总金额: float                    # 含税总金额
    不含税总金额: float                 # 新增
    税金: float                         # 新增
    明细: List[AdjustmentDetail]
    阶段汇总: List[PhaseSummary] = []  # 分阶段小计
    价格校验: PriceValidationSummary   # 价格数据完整性
    使用规则版本: str = "v3.0"
    计算时间: datetime

    class Config:
        use_enum_values = True


class AdjustmentDetail(BaseModel):
    """调差明细"""
    材料名称: str
    规格: str = ""
    阶段: str = "整体"
    部位: str = ""                     # 新增
    工程量: float
    工程量单位: str
    基准价: float
    施工均价: float
    风险幅度: str
    是否超幅: bool
    调整单价: float
    调整金额: float                     # 不含税
    含税调整金额: float                 # 含税
    税率: float
    计算公式: str
    计算依据: str


class PhaseSummary(BaseModel):
    """阶段汇总"""
    阶段名称: str
    材料种数: int
    小计金额（不含税）: float
    含税小计: float


class PriceValidationSummary(BaseModel):
    """价格数据校验汇总"""
    总材料数: int
    有效材料数: int
    无效材料数: int
    平均完整率: float                    # 0-100%
    详细结果: Dict[str, PriceValidationResult]
```

### 4.6 价格校验结果

```python
class PriceValidationResult(BaseModel):
    """单个材料的价格校验"""
    材料名称: str
    数据完整率: float                    # 0-100%
    有效天数: int
    缺失天数: int
    缺失日期: List[str]                 # 前10个
    异常日期: List[str]                 # 价格偏离>50%的日期
    是否有效: bool
    警告信息: List[str]
```

---

## 5. 公式实现细节

### 5.1 标准三段式（最常用）

适用场景：青特地产、朱家庄
触发条件：施工期均价超出基准价 ± 风险幅度

```
公式（涨幅超出）：
  调整金额 = 工程量 × (施工期均价 - 基准价 × (1 + 风险幅度%))

公式（跌幅超出）：
  调整金额 = 工程量 × (施工期均价 - 基准价 × (1 - 风险幅度%))

含税金额 = 调整金额 × (1 + 税率%)
```

### 5.2 龙湖增值税率换算法（重点修复）

适用场景：龙湖集团
核心逻辑：承包人采购钢材可取得13%增值税专用发票，发包人支付时应换算为合同税率9%

```
钢筋公式（0%风险幅度，全额调差）：
  调整金额 = {工程量 × (指导价 - 基准价)} / (1 + 13%) × (1 + 9%)

混凝土公式（±3%风险幅度）：
  涨幅 > 3%：
    调整金额 = {工程量 × (指导价 - 基准价 × 1.03)} / (1 + 13%) × (1 + 9%)
  跌幅 > 3%：
    调整金额 = {工程量 × (指导价 - 基准价 × 0.97)} / (1 + 13%) × (1 + 9%)
```

### 5.3 豪森比例调差法

适用场景：豪森海天映月
核心逻辑：按涨幅比例计算，而非绝对价差

```
涨幅（Pi/P0 > 1 + 风险幅度）：
  调整金额 = 基准价 × (Pi/P0 - (1 + 风险幅度)) × 工程量 × (1 + 税率)

跌幅（Pi/P0 < 1 - 风险幅度）：
  调整金额 = 基准价 × (Pi/P0 - (1 - 风险幅度)) × 工程量 × (1 + 税率)

电缆特殊规则（±2000元/吨阈值）：
  铜价波动 ≤ ±2000元/吨 → 不调差
  铜价波动 > ±2000元/吨：
    调整金额 = 电缆材料费占比 × (|铜价波动| - 2000) / 1000 × 1%
```

### 5.4 造价信息调整法

适用场景：朱家庄
核心逻辑：与标准三段式相同，但强调价格来源为造价信息

```
调整金额 = 工程量 × (信息价 - 基准价 × (1 ± 风险幅度%)) × (1 + 税率)
```

### 5.5 多部位分时段计算

```
核心规则：各部位独立计算自己的施工时段，互不通用

计算流程：
1. 按部位/楼栋分组工程量
2. 每个部位使用自己的 (施工开始日期 ~ 施工结束日期)
3. 各部位独立计算均价后再调差
4. 汇总所有部位的调差金额

注意：基准日期对所有部位统一，施工期均价按各自时段计算
```

### 5.6 价格缺失处理（新增实现）

```
当某日价格数据缺失时：

规则1：顺延1天 (SHIFT_DAY)
  → 取下一个有数据的工作日价格

规则2：取前后日均价 (AVERAGE_PREV_NEXT)
  → 取最近前一个有价日和后一个有价日的均价

规则3：取上月价 (LAST_MONTH)
  → 取上月同期价格（如5月1日缺失，取4月1日价格）
```

---

## 6. API与前端集成

### 6.1 统一API端点

```
POST   /api/adjustments/calculate
  请求：{ rule_id, base_prices, period_prices, quantities }
  响应：CalculationResponse { success, data: CalculationResult, error }

POST   /api/adjustments/calculate-simple
  请求：{ base_price, avg_price, quantity, risk_percent, tax_rate }
  响应：{ success, data: {调整金额, 含税金额, 公式}, formula: "说明" }

GET    /api/adjustments/presets
  响应：{ presets: [{name, description, materials}] }

POST   /api/adjustments/validate-config
  请求：AdjustmentRuleConfig
  响应：{ valid, errors: [] }

POST   /api/adjustments/calculate-by-project/{project_id}
  响应：{ success, data: CalculationResult, rule_name, message }

POST   /api/adjustments/prices/batch-get       (新增)
  请求：{ materials, start_date, end_date }
  响应：{ success, data: {材料名: {base, avg, completeness, prices}} }
```

### 6.2 统一响应字段名

```python
class CalculationResponse(BaseModel):
    success: bool
    data: Optional[Dict] = None   # 包含调差总金额、明细、阶段汇总等
    error: Optional[str] = None
    message: Optional[str] = None  # 提示信息
```

### 6.3 前端计算向导优化

```
步骤1：上传文件
  → 自动解析材料清单 + 部位时段（支持 .xlsx/.xls/.csv）
  → 支持多部位识别（如：1#楼地下室的开始/结束日期）

步骤2：选择规则
  → 显示规则说明（公式类型、风险幅度、适用场景）
  → 预览材料清单

步骤3：设置时间 + 获取价格
  → 设置基准日期（招标/签约日期）
  → 设置施工时间段（支持多部位分别设置）
  → 批量获取价格（一次请求获取所有材料）
  → 显示价格数据完整性（缺失率、异常日期）

步骤4：执行计算 + 查看结果
  → 显示调差总金额（含税/不含税分开）
  → 按部位/楼栋分组小计
  → 按阶段（地下室/楼栋/建筑）分组小计
  → 价格校验报告
  → 可导出Excel/PDF
```

---

## 7. 实施计划

### 7.1 文件变更清单

| 操作 | 文件路径 | 说明 |
|------|----------|------|
| **新增** | `services/adjustment_engine_v3.py` | 统一计算引擎 v3 |
| **新增** | `services/formula_engine.py` | 公式工厂（独立模块） |
| **新增** | `services/price_service.py` | 价格服务（缺失处理） |
| **修改** | `models/adjustment_rules.py` | 统一数据模型 |
| **修改** | `api/adjustments.py` | 统一API + 字段名 |
| **新增** | `api/adjustment_prices_batch.py` | 批量价格接口 |
| **修改** | `pages/Adjustment.tsx` | 前端向导优化 |
| **修改** | `services/api.ts` | 前端批量价格接口调用 |
| **删除** | `services/adjustment_engine_v2.py` | 移除重复代码 |
| **删除** | `services/adjustment_calculator.py` | 移除重复代码 |

### 7.2 实施步骤

```
阶段1：后端核心（预计 2-3 小时）
├── Step 1: 创建 formula_engine.py
│   └── 实现5种公式模板（含龙湖增值税换算修复）
├── Step 2: 创建 price_service.py
│   └── 实现价格获取 + 缺失处理逻辑
├── Step 3: 创建 adjustment_engine_v3.py
│   └── 整合公式引擎 + 价格服务 + 7步计算流程
├── Step 4: 更新 models/adjustment_rules.py
│   └── 添加 PriceValidationSummary、阶段汇总等模型
└── Step 5: 更新 api/adjustments.py
    └── 统一字段名 + 新增批量价格接口

阶段2：前端优化（预计 1-2 小时）
├── Step 6: 更新 Adjustment.tsx
│   ├── 支持多部位分别设置施工时段
│   ├── 批量价格获取（一次请求）
│   ├── 价格数据完整性显示
│   └── 优化结果展示（不含税/含税分开）
└── Step 7: 更新 api.ts
    └── 新增批量价格接口调用

阶段3：测试与清理（预计 1 小时）
├── Step 8: 测试5种公式模板计算结果
├── Step 9: 删除废弃文件
└── Step 10: 更新文档
```

### 7.3 关键风险与对策

| 风险 | 概率 | 对策 |
|------|------|------|
| 龙湖增值税换算公式理解有误 | 中 | 与用户确认公式逻辑后再实现 |
| 前端批量价格接口影响性能 | 低 | 限制单次最多20种材料，分批获取 |
| 删除旧引擎导致兼容问题 | 中 | 先新增 v3，确认可用后再删除旧文件 |

---

## 8. 预设规则配置

### 8.1 青特地产（标准三段式）

```json
{
  "项目名称": "青特地产（调差办法升级版）",
  "调差公式模板": "标准三段式",
  "风险幅度": {
    "商品混凝土": {"类型": "百分比", "值": 3},
    "加气砌块": {"类型": "百分比", "值": 3},
    "PC构件钢筋": {"类型": "无", "值": 0},
    "电缆": {"类型": "固定金额", "值": 1000}
  },
  "是否分阶段调差": "是",
  "阶段划分": [
    {"名称": "地下室", "起始点": "垫层开始", "结束点": "地库顶板完成"},
    {"名称": "单体结构", "起始点": "首层墙柱开始", "结束点": "结构封顶"},
    {"名称": "建筑", "起始点": "砌体开始", "结束点": "竣工"}
  ],
  "税率": 9
}
```

### 8.2 龙湖集团（含增值税换算）

```json
{
  "项目名称": "龙湖集团（专用条款附件13）",
  "调差公式模板": "龙湖增值税率换算法",
  "风险幅度": {
    "钢筋": {"类型": "无", "值": 0},
    "混凝土": {"类型": "百分比", "值": 3}
  },
  "是否分阶段调差": "是",
  "阶段划分": [
    {"名称": "地库", "起始点": "基础垫层", "结束点": "顶板完工"},
    {"名称": "楼栋", "起始点": "±0.00结构面", "结束点": "结构封顶"}
  ],
  "增值税率": 13,
  "合同税率": 9,
  "税率": 9
}
```

---

## 9. 验收标准

1. **公式正确性** — 使用已知案例验证5种公式模板的计算结果
2. **龙湖增值税换算** — 钢筋调差金额 = 工程量 × (指导价 - 基准价) / 1.13 × 1.09
3. **多部位计算** — 各部位独立计算自己的施工时段，汇总金额正确
4. **价格校验** — 缺失率 > 50% 时显示警告信息
5. **API统一** — 所有端点返回统一的中文字段名
6. **前端批量获取** — 一次请求获取多种材料价格
7. **无遗留代码** — 删除 `v2` 和 `calculator` 后系统正常运行