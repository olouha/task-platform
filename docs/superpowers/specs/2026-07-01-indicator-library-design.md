# 指标库Excel转换功能设计文档

**日期**: 2026-07-01
**版本**: 1.0
**状态**: 待实现

---

## 一、需求概述

将Excel文件（数据指标填写1.0.xlsx）转换为Web端的指标库管理系统，实现：

1. **数据结构**：汇总表与明细表一对一关系
2. **UI布局**：左侧汇总列表 + 右侧明细详情（主从布局）
3. **功能**：查看、编辑、导入（支持员工协作）
4. **验证**：基础验证 + 逻辑验证 + 参考范围验证

---

## 二、数据库结构扩展

### 2.1 现有 `indicator_projects` 表

现有表位于 `data/yantai_rebar.db`，已包含约40个字段：
- 基本信息（项目名称、业态、地区、结构等）
- 造价指标（平米造价、分部分项造价）
- 材料含量（钢筋、砼、模板等）

### 2.2 新增字段

```sql
-- 交付与基础信息
ALTER TABLE indicator_projects ADD COLUMN delivery_type TEXT;
ALTER TABLE indicator_projects ADD COLUMN foundation_type TEXT;

-- 地上/地下造价分解
ALTER TABLE indicator_projects ADD COLUMN cost_underground_structure REAL;
ALTER TABLE indicator_projects ADD COLUMN cost_underground_installation REAL;
ALTER TABLE indicator_projects ADD COLUMN unit_cost_underground_structure REAL;
ALTER TABLE indicator_projects ADD COLUMN unit_cost_underground_installation REAL;
ALTER TABLE indicator_projects ADD COLUMN cost_above_structure REAL;
ALTER TABLE indicator_projects ADD COLUMN cost_above_installation REAL;
ALTER TABLE indicator_projects ADD COLUMN unit_cost_above_structure REAL;
ALTER TABLE indicator_projects ADD COLUMN unit_cost_above_installation REAL;

-- 措施费与室外
ALTER TABLE indicator_projects ADD COLUMN cost_measures REAL;
ALTER TABLE indicator_projects ADD COLUMN unit_cost_measures REAL;
ALTER TABLE indicator_projects ADD COLUMN cost_outdoor REAL;
ALTER TABLE indicator_projects ADD COLUMN unit_cost_outdoor REAL;

-- 专项工程造价（8组，16个字段）
ALTER TABLE indicator_projects ADD COLUMN cost_pile REAL;
ALTER TABLE indicator_projects ADD COLUMN unit_cost_pile REAL;
ALTER TABLE indicator_projects ADD COLUMN cost_foundation_support REAL;
ALTER TABLE indicator_projects ADD COLUMN unit_cost_foundation_support REAL;
ALTER TABLE indicator_projects ADD COLUMN cost_curtain_wall REAL;
ALTER TABLE indicator_projects ADD COLUMN unit_cost_curtain_wall REAL;
ALTER TABLE indicator_projects ADD COLUMN cost_decoration REAL;
ALTER TABLE indicator_projects ADD COLUMN unit_cost_decoration REAL;
ALTER TABLE indicator_projects ADD COLUMN cost_exterior_insulation REAL;
ALTER TABLE indicator_projects ADD COLUMN unit_cost_exterior_insulation REAL;
ALTER TABLE indicator_projects ADD COLUMN cost_exterior_windows REAL;
ALTER TABLE indicator_projects ADD COLUMN unit_cost_exterior_windows REAL;
ALTER TABLE indicator_projects ADD COLUMN cost_water_drainage REAL;
ALTER TABLE indicator_projects ADD COLUMN unit_cost_water_drainage REAL;
ALTER TABLE indicator_projects ADD COLUMN cost_heating REAL;
ALTER TABLE indicator_projects ADD COLUMN unit_cost_heating REAL;
ALTER TABLE indicator_projects ADD COLUMN cost_electrical REAL;
ALTER TABLE indicator_projects ADD COLUMN unit_cost_electrical REAL;
ALTER TABLE indicator_projects ADD COLUMN cost_hvac REAL;
ALTER TABLE indicator_projects ADD COLUMN unit_cost_hvac REAL;

-- 地上主体材料（6个字段）
ALTER TABLE indicator_projects ADD COLUMN above_concrete REAL;
ALTER TABLE indicator_projects ADD COLUMN above_concrete_unit REAL;
ALTER TABLE indicator_projects ADD COLUMN above_rebar REAL;
ALTER TABLE indicator_projects ADD COLUMN above_rebar_unit REAL;
ALTER TABLE indicator_projects ADD COLUMN above_formwork REAL;
ALTER TABLE indicator_projects ADD COLUMN above_formwork_unit REAL;

-- 地下主体材料（6个字段）
ALTER TABLE indicator_projects ADD COLUMN underground_concrete REAL;
ALTER TABLE indicator_projects ADD COLUMN underground_concrete_unit REAL;
ALTER TABLE indicator_projects ADD COLUMN underground_rebar REAL;
ALTER TABLE indicator_projects ADD COLUMN underground_rebar_unit REAL;
ALTER TABLE indicator_projects ADD COLUMN underground_formwork REAL;
ALTER TABLE indicator_projects ADD COLUMN underground_formwork_unit REAL;
```

---

## 三、API设计

### 3.1 新增端点

```
GET    /api/indicator-library/summary           # 获取汇总列表
GET    /api/indicator-library/{id}             # 获取项目详情
POST   /api/indicator-library                   # 创建项目
PUT    /api/indicator-library/{id}              # 更新项目
POST   /api/indicator-library/import            # Excel导入
POST   /api/indicator-library/validate          # 数据验证
GET    /api/indicator-library/export            # 导出Excel
GET    /api/indicator-library/template          # 下载导入模板
```

### 3.2 数据模型

```python
class IndicatorLibrarySummary(BaseModel):
    """汇总项模型"""
    id: str
    name: str = Field(..., min_length=1, max_length=100)
    category: str  # 业态: 住宅/商业/办公/工业
    location: str
    structure: str
    area_total: Optional[float] = Field(None, gt=0)
    unit_cost: Optional[float] = Field(None, gt=0)
    updated_at: str

class IndicatorLibraryDetail(BaseModel):
    """完整明细模型"""
    # 基本信息
    id: Optional[str]
    name: str = Field(..., min_length=1, max_length=100)
    category: str
    location: str
    structure: str
    delivery_type: Optional[str]  # 交付形式
    foundation_type: Optional[str]  # 桩基形式
    floor_above: Optional[int]
    floor_below: Optional[int]
    height: Optional[float]
    area_total: Optional[float]
    area_above: Optional[float]
    area_below: Optional[float]

    # 造价指标
    unit_cost: Optional[float]
    total_cost: Optional[float]
    unit_structure: Optional[float]
    unit_installation: Optional[float]

    # 地上/地下造价分解
    cost_above_structure: Optional[float]
    cost_above_installation: Optional[float]
    unit_cost_above_structure: Optional[float]
    unit_cost_above_installation: Optional[float]
    cost_underground_structure: Optional[float]
    cost_underground_installation: Optional[float]
    unit_cost_underground_structure: Optional[float]
    unit_cost_underground_installation: Optional[float]

    # 措施费与室外
    cost_measures: Optional[float]
    unit_cost_measures: Optional[float]
    cost_outdoor: Optional[float]
    unit_cost_outdoor: Optional[float]

    # 专项工程（8组）
    cost_pile: Optional[float]
    unit_cost_pile: Optional[float]
    cost_foundation_support: Optional[float]
    unit_cost_foundation_support: Optional[float]
    cost_curtain_wall: Optional[float]
    unit_cost_curtain_wall: Optional[float]
    cost_decoration: Optional[float]
    unit_cost_decoration: Optional[float]
    cost_exterior_insulation: Optional[float]
    unit_cost_exterior_insulation: Optional[float]
    cost_exterior_windows: Optional[float]
    unit_cost_exterior_windows: Optional[float]
    cost_water_drainage: Optional[float]
    unit_cost_water_drainage: Optional[float]
    cost_heating: Optional[float]
    unit_cost_heating: Optional[float]
    cost_electrical: Optional[float]
    unit_cost_electrical: Optional[float]
    cost_hvac: Optional[float]
    unit_cost_hvac: Optional[float]

    # 地上主体材料
    above_concrete: Optional[float]
    above_concrete_unit: Optional[float]
    above_rebar: Optional[float]
    above_rebar_unit: Optional[float]
    above_formwork: Optional[float]
    above_formwork_unit: Optional[float]

    # 地下主体材料
    underground_concrete: Optional[float]
    underground_concrete_unit: Optional[float]
    underground_rebar: Optional[float]
    underground_rebar_unit: Optional[float]
    underground_formwork: Optional[float]
    underground_formwork_unit: Optional[float]

    # 元数据
    source: Optional[str]
    source_file: Optional[str]
    remarks: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]
```

---

## 四、前端UI设计

### 4.1 页面结构

```
┌─────────────────────────────────────────────────────────────────┐
│  指标库管理                                    [+新建] [导入] [导出]│
├─────────────────────┬───────────────────────────────────────────┤
│                     │                                           │
│  汇总列表（30%）    │           明细详情（70%）                 │
│                     │                                           │
│  ┌───────────────┐ │  ┌─────────────────────────────────────┐ │
│  │ XX项目        │ │  │ 基本信息                             │ │
│  │ YY项目        │ │  │ 项目名称: [_____________]             │ │
│  │ ZZ项目        │ │  │ 业态: [下拉选择▼]   结构: [_____]    │ │
│  │ ...           │ │  │                                       │ │
│  └───────────────┘ │  │ 造价指标（可折叠面板）                │ │
│                     │  │ ▼ 地上/地下造价分解                  │ │
│  筛选条件：         │  │ ▼ 专项工程造价（8项）                 │ │
│  业态: [全部▼]     │  │ ▼ 材料用量指标                        │ │
│  地区: [全部▼]     │  │                                       │ │
│  搜索: [_______]   │  │ [保存] [取消]                         │ │
└─────────────────────┴───────────────────────────────────────────┘
```

### 4.2 组件结构

```
IndicatorLibrary.tsx (主页面)
├── SummaryList.tsx (左侧汇总列表)
│   ├── FilterBar (筛选条件)
│   └── ProjectItem (项目项)
└── DetailPanel.tsx (右侧详情面板)
    ├── BasicInfoSection (基本信息)
    ├── CostSection (造价指标 - 可折叠)
    ├── SpecialCostSection (专项工程 - 可折叠)
    └── MaterialSection (材料用量 - 可折叠)
```

---

## 五、数据验证规则

### 5.1 基础验证（必填+范围）

| 字段 | 规则 |
|------|------|
| name | 必填，1-100字符 |
| category | 必填，枚举: 住宅/商业/办公/工业 |
| area_total | 必须>0 |
| unit_cost | 必须>0，参考范围: 1000-10000 |
| steel | 必须>=0，参考范围: 20-100 kg/m² |
| concrete | 必须>=0，参考范围: 0.3-0.8 m³/m² |

### 5.2 逻辑验证（关联校验）

| 规则 | 公式 | 容差 |
|------|------|------|
| 总造价一致性 | total_cost ≈ cost_above + cost_underground | 5% |
| 面积一致性 | area_total ≈ area_above + area_below | 5% |
| 单价×面积 | unit_cost × area_total ≈ total_cost | 10% |
| 平米含量 | above_concrete_unit ≈ above_concrete / area_above | 10% |

### 5.3 参考范围验证（异常检测）

- 按业态分组统计，计算均值±2倍标准差
- 超出范围的数据标记为"异常"
- 不阻止导入，但高亮提醒

---

## 六、Excel导入功能

### 6.1 Excel结构

**汇总表**：
- 列：序号、项目名称、业态、项目所在地、结构形式、交付形式、层数、总面积、檐高、总造价

**明细表**：
- 多级表头（第1-4行为表头）
- 第5行开始为数据
- 59列详细数据

### 6.2 导入流程

```
用户上传 → 解析Excel → 数据合并 → 预览 → 验证 → 确认导入 → 结果反馈
```

### 6.3 解析逻辑

1. 读取汇总表获取项目基本信息
2. 读取明细表（处理多级表头，第2-4行合并为单层表头）
3. 按序号匹配汇总与明细
4. 合并数据并执行三级验证
5. 返回预览结果

---

## 七、实现计划

### 7.1 后端任务

1. **扩展数据库表结构**
   - 更新 `LocalIndicatorService._init_table()`
   - 添加数据迁移逻辑

2. **创建指标库服务**
   - `IndicatorLibraryService` - 业务逻辑
   - `ExcelParserService` - Excel解析
   - `IndicatorValidator` - 数据验证

3. **创建API路由**
   - `/api/indicator-library/` - 主路由
   - 实现CRUD端点
   - 实现导入/导出端点

### 7.2 前端任务

1. **创建页面组件**
   - `IndicatorLibrary.tsx` - 主页面
   - `SummaryList.tsx` - 汇总列表
   - `DetailPanel.tsx` - 详情面板

2. **实现交互功能**
   - 列表点击切换
   - 表单编辑
   - Excel上传预览

3. **集成API**
   - 连接后端端点
   - 错误处理
   - 加载状态

### 7.3 测试任务

1. 数据库迁移测试
2. API端点测试
3. Excel导入测试
4. 数据验证测试
5. 前端交互测试

---

## 八、技术栈

- **后端**: FastAPI + SQLite + openpyxl
- **前端**: React + TypeScript + Ant Design
- **验证**: Pydantic + 自定义验证逻辑
