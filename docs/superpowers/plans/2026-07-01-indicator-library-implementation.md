# 指标库Excel转换功能实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**目标:** 将Excel格式的指标数据转换为Web端指标库管理系统，支持查看、编辑、导入导出和三级数据验证

**架构:** 后端FastAPI + SQLite存储，前端React + Ant Design主从布局UI，通过RESTful API通信

**技术栈:** FastAPI, SQLite, openpyxl, Pydantic, React, TypeScript, Ant Design

## 全局约束

- 遵循项目代码规范（CLAUDE.md）：每个函数必须记录日志，使用类型注解，API端点必须输入验证
- 数据库文件: `data/yantai_rebar.db`
- 现有表: `indicator_projects` 需要扩展，不重建
- 前端构建: `npm run build` 生成 `frontend/dist`
- API路由前缀: `/api/indicator-library`

---

## 文件结构

```
web/backend/
├── services/
│   ├── local_indicator_service.py          [修改] 扩展表结构
│   ├── indicator_library_service.py         [新建] 业务逻辑
│   ├── excel_parser_service.py              [新建] Excel解析
│   └── indicator_validator.py               [新建] 数据验证
├── api/
│   └── indicator_library.py                 [新建] API路由
├── models/
│   └── indicator_library.py                 [新建] Pydantic模型
└── main.py                                  [修改] 注册路由

web/frontend/src/
├── pages/
│   └── IndicatorLibrary.tsx                 [新建] 主页面
├── components/
│   └── indicator-library/
│       ├── SummaryList.tsx                  [新建] 汇总列表
│       ├── DetailPanel.tsx                  [新建] 详情面板
│       ├── BasicInfoSection.tsx              [新建] 基本信息表单
│       ├── CostSection.tsx                  [新建] 造价指标
│       ├── SpecialCostSection.tsx           [新建] 专项工程
│       ├── MaterialSection.tsx              [新建] 材料用量
│       └── ImportPreview.tsx                [新建] 导入预览
└── services/
    └── api.ts                               [修改] 添加API方法

tests/
├── services/
│   ├── test_excel_parser.py                 [新建]
│   └── test_indicator_validator.py          [新建]
└── api/
    └── test_indicator_library.py            [新建]
```

---

## 第一阶段：后端 - 数据库扩展

### Task 1: 扩展 indicator_projects 表结构

**文件:**
- 修改: `web/backend/services/local_indicator_service.py:23-88`

**接口:**
- 消费: 无（基础任务）
- 生产: `LocalIndicatorService._init_table()` 扩展表结构，`LocalIndicatorService._migrate_old_table()` 迁移逻辑

- [ ] **Step 1: 备份现有数据库**

```bash
cd web/backend
cp data/yantai_rebar.db data/yantai_rebar.db.backup_$(date +%Y%m%d)
```

- [ ] **Step 2: 查看当前表结构**

```bash
sqlite3 data/yantai_rebar.db ".schema indicator_projects"
```

Expected output: 现有CREATE TABLE语句，用于对比

- [ ] **Step 3: 修改 _init_table 方法，添加新字段**

在 `web/backend/services/local_indicator_service.py` 的 `_init_table` 方法中，更新CREATE TABLE语句：

```python
# 创建主表（完整字段 - 扩展版本）
cursor.execute('''
    CREATE TABLE IF NOT EXISTS indicator_projects (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        category TEXT,
        location TEXT,
        structure TEXT,
        floor_above INTEGER,
        floor_below INTEGER,
        area_total REAL,
        area_above REAL,
        area_below REAL,
        height REAL,
        complete_date TEXT,
        unit_cost REAL,
        total_cost REAL,
        unit_structure REAL,
        unit_installation REAL,
        unit_decoration REAL,
        unit_measure REAL,
        -- 主要经济指标
        underground_structure REAL,
        above_structure REAL,
        roof REAL,
        exterior_wall REAL,
        interior_wall REAL,
        floor REAL,
        electrical REAL,
        plumbing REAL,
        hvac REAL,
        elevator REAL,
        fire REAL,
        measures REAL,
        -- 材料含量
        steel REAL,
        concrete REAL,
        formwork REAL,
        block REAL,
        cable REAL,
        pipe REAL,
        duct REAL,
        -- ================== 新增字段 ==================
        -- 项目时间信息
        start_date TEXT,
        end_date TEXT,
        entry_date TEXT,
        -- 交付与基础信息
        delivery_type TEXT,
        foundation_type TEXT,
        -- 地上/地下造价分解
        cost_underground_structure REAL,
        cost_underground_installation REAL,
        unit_cost_underground_structure REAL,
        unit_cost_underground_installation REAL,
        cost_above_structure REAL,
        cost_above_installation REAL,
        unit_cost_above_structure REAL,
        unit_cost_above_installation REAL,
        -- 措施费与室外
        cost_measures REAL,
        unit_cost_measures REAL,
        cost_outdoor REAL,
        unit_cost_outdoor REAL,
        -- 专项工程造价（8组）
        cost_pile REAL,
        unit_cost_pile REAL,
        cost_foundation_support REAL,
        unit_cost_foundation_support REAL,
        cost_curtain_wall REAL,
        unit_cost_curtain_wall REAL,
        cost_decoration REAL,
        unit_cost_decoration REAL,
        cost_exterior_insulation REAL,
        unit_cost_exterior_insulation REAL,
        cost_exterior_windows REAL,
        unit_cost_exterior_windows REAL,
        cost_water_drainage REAL,
        unit_cost_water_drainage REAL,
        cost_heating REAL,
        unit_cost_heating REAL,
        cost_electrical REAL,
        unit_cost_electrical REAL,
        cost_hvac REAL,
        unit_cost_hvac REAL,
        -- 地上主体材料
        above_concrete REAL,
        above_concrete_unit REAL,
        above_rebar REAL,
        above_rebar_unit REAL,
        above_formwork REAL,
        above_formwork_unit REAL,
        -- 地下主体材料
        underground_concrete REAL,
        underground_concrete_unit REAL,
        underground_rebar REAL,
        underground_rebar_unit REAL,
        underground_formwork REAL,
        underground_formwork_unit REAL,
        -- 来源信息
        source TEXT,
        source_file TEXT,
        remarks TEXT,
        verified INTEGER DEFAULT 0,
        verified_by TEXT,
        verified_at TEXT,
        -- 时间戳
        created_at TEXT,
        updated_at TEXT
    )
''')
```

- [ ] **Step 4: 更新 _migrate_old_table 方法**

在 `_migrate_old_table` 方法中，添加新字段的迁移列表：

```python
def _migrate_old_table(self, conn):
    """迁移旧表，添加缺失的字段"""
    cursor = conn.cursor()

    # 需要添加的字段及默认值
    new_columns = {
        # 时间信息
        'start_date': 'TEXT',
        'end_date': 'TEXT',
        'entry_date': 'TEXT',
        # 交付与基础
        'delivery_type': 'TEXT',
        'foundation_type': 'TEXT',
        # 造价分解
        'cost_underground_structure': 'REAL',
        'cost_underground_installation': 'REAL',
        'unit_cost_underground_structure': 'REAL',
        'unit_cost_underground_installation': 'REAL',
        'cost_above_structure': 'REAL',
        'cost_above_installation': 'REAL',
        'unit_cost_above_structure': 'REAL',
        'unit_cost_above_installation': 'REAL',
        # 措施费与室外
        'cost_measures': 'REAL',
        'unit_cost_measures': 'REAL',
        'cost_outdoor': 'REAL',
        'unit_cost_outdoor': 'REAL',
        # 专项工程（16个字段）
        'cost_pile': 'REAL',
        'unit_cost_pile': 'REAL',
        'cost_foundation_support': 'REAL',
        'unit_cost_foundation_support': 'REAL',
        'cost_curtain_wall': 'REAL',
        'unit_cost_curtain_wall': 'REAL',
        'cost_decoration': 'REAL',
        'unit_cost_decoration': 'REAL',
        'cost_exterior_insulation': 'REAL',
        'unit_cost_exterior_insulation': 'REAL',
        'cost_exterior_windows': 'REAL',
        'unit_cost_exterior_windows': 'REAL',
        'cost_water_drainage': 'REAL',
        'unit_cost_water_drainage': 'REAL',
        'cost_heating': 'REAL',
        'unit_cost_heating': 'REAL',
        'cost_electrical': 'REAL',
        'unit_cost_electrical': 'REAL',
        'cost_hvac': 'REAL',
        'unit_cost_hvac': 'REAL',
        # 地上主体材料
        'above_concrete': 'REAL',
        'above_concrete_unit': 'REAL',
        'above_rebar': 'REAL',
        'above_rebar_unit': 'REAL',
        'above_formwork': 'REAL',
        'above_formwork_unit': 'REAL',
        # 地下主体材料
        'underground_concrete': 'REAL',
        'underground_concrete_unit': 'REAL',
        'underground_rebar': 'REAL',
        'underground_rebar_unit': 'REAL',
        'underground_formwork': 'REAL',
        'underground_formwork_unit': 'REAL',
    }

    # 获取当前表的所有列
    cursor.execute("PRAGMA table_info(indicator_projects)")
    existing_columns = {row[1] for row in cursor.fetchall()}

    # 添加缺失的列
    for col, col_type in new_columns.items():
        if col not in existing_columns:
            try:
                cursor.execute(f"ALTER TABLE indicator_projects ADD COLUMN {col} {col_type}")
                logger.info(f"[LocalIndicatorService] 添加字段 {col}")
            except sqlite3.OperationalError as e:
                logger.warning(f"[LocalIndicatorService] 添加字段失败: {e}")
```

- [ ] **Step 5: 更新 create_indicator_project 方法的字段列表**

在 `create_indicator_project` 方法中，更新 `all_fields` 列表：

```python
# 所有字段列表
all_fields = [
    'id', 'name', 'category', 'location', 'structure',
    'floor_above', 'floor_below', 'area_total', 'area_above', 'area_below',
    'height', 'complete_date', 'unit_cost', 'total_cost',
    'unit_structure', 'unit_installation', 'unit_decoration', 'unit_measure',
    'underground_structure', 'above_structure', 'roof', 'exterior_wall',
    'interior_wall', 'floor', 'electrical', 'plumbing', 'hvac',
    'elevator', 'fire', 'measures',
    'steel', 'concrete', 'formwork', 'block', 'cable', 'pipe', 'duct',
    # 新增字段
    'start_date', 'end_date', 'entry_date',
    'delivery_type', 'foundation_type',
    'cost_underground_structure', 'cost_underground_installation',
    'unit_cost_underground_structure', 'unit_cost_underground_installation',
    'cost_above_structure', 'cost_above_installation',
    'unit_cost_above_structure', 'unit_cost_above_installation',
    'cost_measures', 'unit_cost_measures', 'cost_outdoor', 'unit_cost_outdoor',
    'cost_pile', 'unit_cost_pile',
    'cost_foundation_support', 'unit_cost_foundation_support',
    'cost_curtain_wall', 'unit_cost_curtain_wall',
    'cost_decoration', 'unit_cost_decoration',
    'cost_exterior_insulation', 'unit_cost_exterior_insulation',
    'cost_exterior_windows', 'unit_cost_exterior_windows',
    'cost_water_drainage', 'unit_cost_water_drainage',
    'cost_heating', 'unit_cost_heating',
    'cost_electrical', 'unit_cost_electrical',
    'cost_hvac', 'unit_cost_hvac',
    'above_concrete', 'above_concrete_unit',
    'above_rebar', 'above_rebar_unit',
    'above_formwork', 'above_formwork_unit',
    'underground_concrete', 'underground_concrete_unit',
    'underground_rebar', 'underground_rebar_unit',
    'underground_formwork', 'underground_formwork_unit',
    'source', 'source_file', 'remarks', 'verified', 'verified_by', 'verified_at',
    'created_at', 'updated_at'
]
```

- [ ] **Step 6: 更新 update_indicator_project 方法的字段列表**

在 `update_indicator_project` 方法中，更新 `all_fields` 列表（同上）

- [ ] **Step 7: 测试数据库迁移**

```bash
cd web/backend
python -c "
from services.local_indicator_service import LocalIndicatorService
service = LocalIndicatorService()
print('数据库迁移测试成功')
"
```

Expected output: "数据库迁移测试成功"，无错误

- [ ] **Step 8: 验证表结构**

```bash
sqlite3 data/yantai_rebar.db "PRAGMA table_info(indicator_projects);" | grep -E "start_date|delivery_type|cost_pile"
```

Expected output: 新增字段的列表

- [ ] **Step 9: 提交**

```bash
git add web/backend/services/local_indicator_service.py
git commit -m "feat: 扩展indicator_projects表结构，新增约50个字段"
```

---

## 第二阶段：后端 - 数据模型

### Task 2: 创建 Pydantic 数据模型

**文件:**
- 创建: `web/backend/models/indicator_library.py`

**接口:**
- 消费: 无
- 生产: `IndicatorLibrarySummary`, `IndicatorLibraryDetail`, `ValidationResult` 等模型

- [ ] **Step 1: 创建模型文件**

```bash
touch web/backend/models/indicator_library.py
```

- [ ] **Step 2: 编写基础导入和汇总模型**

```python
"""
指标库数据模型
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class IndicatorLibrarySummary(BaseModel):
    """汇总项模型 - 用于列表展示"""
    id: str
    name: str = Field(..., min_length=1, max_length=100, description="项目名称")
    category: str = Field(..., description="业态: 住宅/商业/办公/工业")
    location: str = Field(..., description="项目所在地")
    structure: str = Field(..., description="结构形式")
    start_date: Optional[str] = Field(None, description="开工时间(YYYY-MM)")
    end_date: Optional[str] = Field(None, description="竣工时间(YYYY-MM)")
    area_total: Optional[float] = Field(None, gt=0, description="总建筑面积(㎡)")
    unit_cost: Optional[float] = Field(None, gt=0, description="平米造价(元/㎡)")
    entry_date: Optional[str] = Field(None, description="录入时间")
    updated_at: str = Field(..., description="更新时间")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "IND-20240101001",
                "name": "XX住宅项目",
                "category": "住宅",
                "location": "山东烟台",
                "structure": "框架结构",
                "start_date": "2023-01",
                "end_date": "2024-06",
                "area_total": 25000.0,
                "unit_cost": 2350.0,
                "entry_date": "2026-07-01 10:30:00",
                "updated_at": "2026-07-01T10:30:00"
            }
        }


class IndicatorLibraryDetail(BaseModel):
    """完整明细模型 - 用于详情和编辑"""
    # 基本信息
    id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=100)
    category: str
    location: str
    structure: str
    delivery_type: Optional[str] = Field(None, description="交付形式")
    foundation_type: Optional[str] = Field(None, description="桩基形式")
    start_date: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}$", description="开工时间(YYYY-MM)")
    end_date: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}$", description="竣工时间(YYYY-MM)")
    floor_above: Optional[int] = Field(None, ge=0, description="地上层数")
    floor_below: Optional[int] = Field(None, ge=0, description="地下层数")
    height: Optional[float] = Field(None, gt=0, description="檐高(m)")
    area_total: Optional[float] = Field(None, gt=0, description="总建筑面积(㎡)")
    area_above: Optional[float] = Field(None, ge=0, description="地上建筑面积(㎡)")
    area_below: Optional[float] = Field(None, ge=0, description="地下建筑面积(㎡)")

    # 造价指标
    unit_cost: Optional[float] = Field(None, gt=0, description="平米造价(元/㎡)")
    total_cost: Optional[float] = Field(None, gt=0, description="总造价(元)")
    unit_structure: Optional[float] = Field(None, ge=0, description="结构平米造价")
    unit_installation: Optional[float] = Field(None, ge=0, description="安装平米造价")

    # 地上/地下造价分解
    cost_above_structure: Optional[float] = Field(None, ge=0)
    cost_above_installation: Optional[float] = Field(None, ge=0)
    unit_cost_above_structure: Optional[float] = Field(None, ge=0)
    unit_cost_above_installation: Optional[float] = Field(None, ge=0)
    cost_underground_structure: Optional[float] = Field(None, ge=0)
    cost_underground_installation: Optional[float] = Field(None, ge=0)
    unit_cost_underground_structure: Optional[float] = Field(None, ge=0)
    unit_cost_underground_installation: Optional[float] = Field(None, ge=0)

    # 措施费与室外
    cost_measures: Optional[float] = Field(None, ge=0)
    unit_cost_measures: Optional[float] = Field(None, ge=0)
    cost_outdoor: Optional[float] = Field(None, ge=0)
    unit_cost_outdoor: Optional[float] = Field(None, ge=0)

    # 专项工程（8组）
    cost_pile: Optional[float] = Field(None, ge=0)
    unit_cost_pile: Optional[float] = Field(None, ge=0)
    cost_foundation_support: Optional[float] = Field(None, ge=0)
    unit_cost_foundation_support: Optional[float] = Field(None, ge=0)
    cost_curtain_wall: Optional[float] = Field(None, ge=0)
    unit_cost_curtain_wall: Optional[float] = Field(None, ge=0)
    cost_decoration: Optional[float] = Field(None, ge=0)
    unit_cost_decoration: Optional[float] = Field(None, ge=0)
    cost_exterior_insulation: Optional[float] = Field(None, ge=0)
    unit_cost_exterior_insulation: Optional[float] = Field(None, ge=0)
    cost_exterior_windows: Optional[float] = Field(None, ge=0)
    unit_cost_exterior_windows: Optional[float] = Field(None, ge=0)
    cost_water_drainage: Optional[float] = Field(None, ge=0)
    unit_cost_water_drainage: Optional[float] = Field(None, ge=0)
    cost_heating: Optional[float] = Field(None, ge=0)
    unit_cost_heating: Optional[float] = Field(None, ge=0)
    cost_electrical: Optional[float] = Field(None, ge=0)
    unit_cost_electrical: Optional[float] = Field(None, ge=0)
    cost_hvac: Optional[float] = Field(None, ge=0)
    unit_cost_hvac: Optional[float] = Field(None, ge=0)

    # 地上主体材料
    above_concrete: Optional[float] = Field(None, ge=0, description="地上砼用量(m³)")
    above_concrete_unit: Optional[float] = Field(None, ge=0, description="地上砼平米含量(m³/㎡)")
    above_rebar: Optional[float] = Field(None, ge=0, description="地上钢筋用量(t)")
    above_rebar_unit: Optional[float] = Field(None, ge=0, description="地上钢筋平米含量(t/㎡)")
    above_formwork: Optional[float] = Field(None, ge=0, description="地上模板用量(m²)")
    above_formwork_unit: Optional[float] = Field(None, ge=0, description="地上模板平米含量(m²/㎡)")

    # 地下主体材料
    underground_concrete: Optional[float] = Field(None, ge=0, description="地下砼用量(m³)")
    underground_concrete_unit: Optional[float] = Field(None, ge=0, description="地下砼平米含量(m³/㎡)")
    underground_rebar: Optional[float] = Field(None, ge=0, description="地下钢筋用量(t)")
    underground_rebar_unit: Optional[float] = Field(None, ge=0, description="地下钢筋平米含量(t/㎡)")
    underground_formwork: Optional[float] = Field(None, ge=0, description="地下模板用量(m²)")
    underground_formwork_unit: Optional[float] = Field(None, ge=0, description="地下模板平米含量(m²/㎡)")

    # 元数据
    source: Optional[str] = Field(None, description="数据来源")
    source_file: Optional[str] = Field(None, description="来源文件名")
    remarks: Optional[str] = Field(None, max_length=500, description="备注")
    entry_date: Optional[str] = Field(None, description="录入时间")
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "name": "XX住宅项目",
                "category": "住宅",
                "location": "山东烟台",
                "structure": "框架结构",
                "delivery_type": "毛坯交付",
                "foundation_type": "钢板桩",
                "start_date": "2023-01",
                "end_date": "2024-06",
                "floor_above": 12,
                "floor_below": 2,
                "height": 36.0,
                "area_total": 25000.0,
                "unit_cost": 2350.0
            }
        }


class IndicatorLibraryCreate(BaseModel):
    """创建指标库项目请求"""
    name: str = Field(..., min_length=1, max_length=100)
    category: str = Field(..., description="业态: 住宅/商业/办公/工业")
    location: str
    structure: str
    delivery_type: Optional[str] = None
    foundation_type: Optional[str] = None
    start_date: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}$")
    end_date: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}$")
    floor_above: Optional[int] = Field(None, ge=0)
    floor_below: Optional[int] = Field(None, ge=0)
    height: Optional[float] = Field(None, gt=0)
    area_total: Optional[float] = Field(None, gt=0)
    area_above: Optional[float] = Field(None, ge=0)
    area_below: Optional[float] = Field(None, ge=0)
    unit_cost: Optional[float] = Field(None, gt=0)
    total_cost: Optional[float] = Field(None, gt=0)
    # ... 其他字段同 IndicatorLibraryDetail

    class Config:
        extra = "allow"  # 允许额外字段


class ValidationWarning(BaseModel):
    """验证警告"""
    field: str = Field(..., description="字段名")
    message: str = Field(..., description="警告信息")
    severity: str = Field(..., description="严重程度: warning/error")
    value: Optional[Any] = Field(None, description="当前值")
    expected: Optional[str] = Field(None, description="期望值或范围")


class ValidationResult(BaseModel):
    """验证结果"""
    passed: bool = Field(..., description="是否通过验证")
    warnings: List[ValidationWarning] = Field(default_factory=list, description="警告列表")
    errors: List[ValidationWarning] = Field(default_factory=list, description="错误列表")
    checks: Dict[str, str] = Field(default_factory=dict, description="各检查项结果")


class ImportPreviewItem(BaseModel):
    """导入预览项"""
    index: int = Field(..., description="序号")
    name: str = Field(..., description="项目名称")
    category: Optional[str] = None
    location: Optional[str] = None
    unit_cost: Optional[float] = None
    status: str = Field(..., description="状态: valid/warning/error")
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


class ImportPreviewResult(BaseModel):
    """导入预览结果"""
    total: int = Field(..., description="总项目数")
    valid_count: int = Field(..., description="有效项目数")
    warning_count: int = Field(..., description="警告项目数")
    error_count: int = Field(..., description="错误项目数")
    items: List[ImportPreviewItem] = Field(..., description="项目列表")


class ImportResult(BaseModel):
    """导入结果"""
    success: bool = Field(..., description="是否成功")
    imported: int = Field(..., description="成功导入数")
    total: int = Field(..., description="总数")
    warnings: List[Dict[str, Any]] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
```

- [ ] **Step 3: 测试模型导入**

```bash
cd web/backend
python -c "from models.indicator_library import IndicatorLibrarySummary; print('模型导入成功')"
```

Expected output: "模型导入成功"

- [ ] **Step 4: 提交**

```bash
git add web/backend/models/indicator_library.py
git commit -m "feat: 添加指标库Pydantic数据模型"
```

---

## 第三阶段：后端 - 数据验证服务

### Task 3: 创建数据验证服务

**文件:**
- 创建: `web/backend/services/indicator_validator.py`

**接口:**
- 消费: `models.indicator_library.IndicatorLibraryDetail`
- 生产: `IndicatorValidator.validate()` 返回 `ValidationResult`

- [ ] **Step 1: 创建验证服务文件**

```bash
touch web/backend/services/indicator_validator.py
```

- [ ] **Step 2: 编写验证服务**

```python
"""
指标数据验证服务
三级验证：基础验证、逻辑验证、参考范围验证
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import re

from models.indicator_library import IndicatorLibraryDetail, ValidationResult, ValidationWarning

logger = logging.getLogger(__name__)


class IndicatorValidator:
    """指标数据验证器"""

    # 业态枚举值
    VALID_CATEGORIES = ["住宅", "商业", "办公", "工业", "其他"]

    # 参考范围（按业态分组）
    REFERENCE_RANGES = {
        "住宅": {
            "unit_cost": (1800, 3500),  # 元/㎡
            "steel": (35, 65),          # kg/㎡
            "concrete": (0.35, 0.55),   # m³/㎡
        },
        "商业": {
            "unit_cost": (2500, 5000),
            "steel": (50, 80),
            "concrete": (0.40, 0.60),
        },
        "办公": {
            "unit_cost": (2800, 5500),
            "steel": (55, 85),
            "concrete": (0.45, 0.65),
        },
        "工业": {
            "unit_cost": (1500, 3500),
            "steel": (30, 60),
            "concrete": (0.25, 0.50),
        },
    }

    @classmethod
    def validate(cls, data: Dict[str, Any], database_stats: Optional[Dict] = None) -> ValidationResult:
        """
        执行三级验证

        Args:
            data: 项目数据
            database_stats: 数据库统计信息（用于参考范围验证）

        Returns:
            ValidationResult: 验证结果
        """
        logger.info(f"[IndicatorValidator] 开始验证 | 项目={data.get('name')}")

        warnings = []
        errors = []
        checks = {}

        # 一级验证：基础验证（必填+范围）
        basic_warnings, basic_errors = cls._validate_basic(data)
        warnings.extend(basic_warnings)
        errors.extend(basic_errors)
        checks["required_fields"] = "passed" if not basic_errors else "failed"

        # 二级验证：逻辑验证（关联校验）
        logical_warnings, logical_errors = cls._validate_logical(data)
        warnings.extend(logical_warnings)
        errors.extend(logical_errors)
        checks["logical_consistency"] = "passed" if not logical_errors else "failed"

        # 三级验证：参考范围验证（异常检测）
        reference_warnings = cls._validate_reference_range(data, database_stats)
        warnings.extend(reference_warnings)
        checks["reference_ranges"] = "passed" if not reference_warnings else "warning"

        passed = len(errors) == 0
        logger.info(f"[IndicatorValidator] 验证完成 | passed={passed}, warnings={len(warnings)}, errors={len(errors)}")

        return ValidationResult(
            passed=passed,
            warnings=[ValidationWarning(**w) for w in warnings],
            errors=[ValidationWarning(**e) for e in errors],
            checks=checks
        )

    @classmethod
    def _validate_basic(cls, data: Dict[str, Any]) -> tuple[List[Dict], List[Dict]]:
        """基础验证：必填字段和数值范围"""
        warnings = []
        errors = []

        # 必填字段检查
        required_fields = ["name", "category"]
        for field in required_fields:
            if not data.get(field):
                errors.append({
                    "field": field,
                    "message": f"{field}为必填字段",
                    "severity": "error"
                })

        # 名称长度
        name = data.get("name", "")
        if len(name) > 100:
            errors.append({
                "field": "name",
                "message": "项目名称不能超过100字符",
                "severity": "error",
                "value": len(name)
            })

        # 业态枚举值
        category = data.get("category")
        if category and category not in cls.VALID_CATEGORIES:
            warnings.append({
                "field": "category",
                "message": f"业态应为以下之一: {', '.join(cls.VALID_CATEGORIES)}",
                "severity": "warning",
                "value": category
            })

        # 数值范围检查
        if data.get("area_total") is not None and data["area_total"] <= 0:
            errors.append({
                "field": "area_total",
                "message": "总建筑面积必须大于0",
                "severity": "error"
            })

        if data.get("unit_cost") is not None and data["unit_cost"] <= 0:
            errors.append({
                "field": "unit_cost",
                "message": "平米造价必须大于0",
                "severity": "error"
            })

        # 日期格式检查
        date_fields = ["start_date", "end_date"]
        for field in date_fields:
            value = data.get(field)
            if value and not re.match(r"^\d{4}-\d{2}$", value):
                errors.append({
                    "field": field,
                    "message": f"{field}格式应为YYYY-MM",
                    "severity": "error",
                    "value": value
                })

        return warnings, errors

    @classmethod
    def _validate_logical(cls, data: Dict[str, Any]) -> tuple[List[Dict], List[Dict]]:
        """逻辑验证：关联字段一致性"""
        warnings = []
        errors = []

        # 总造价一致性: total_cost ≈ cost_above + cost_underground
        total_cost = data.get("total_cost")
        cost_above = (data.get("cost_above_structure") or 0) + (data.get("cost_above_installation") or 0)
        cost_underground = (data.get("cost_underground_structure") or 0) + (data.get("cost_underground_installation") or 0)

        if total_cost and cost_above and cost_underground:
            calculated_total = cost_above + cost_underground
            tolerance = total_cost * 0.05  # 5%容差
            if abs(total_cost - calculated_total) > tolerance:
                warnings.append({
                    "field": "total_cost",
                    "message": f"总造价与分项造价不一致: total={total_cost}, above+underground={calculated_total}",
                    "severity": "warning",
                    "value": total_cost,
                    "expected": f"{calculated_total} ± 5%"
                })

        # 面积一致性: area_total ≈ area_above + area_below
        area_total = data.get("area_total")
        area_above = data.get("area_above")
        area_below = data.get("area_below")

        if area_total and area_above and area_below:
            calculated_area = area_above + area_below
            area_tolerance = area_total * 0.05  # 5%容差
            if abs(area_total - calculated_area) > area_tolerance:
                warnings.append({
                    "field": "area_total",
                    "message": f"建筑面积不一致: total={area_total}, above+below={calculated_area}",
                    "severity": "warning",
                    "value": area_total,
                    "expected": f"{calculated_area} ± 5%"
                })

        # 单价×面积一致性: unit_cost × area_total ≈ total_cost
        unit_cost = data.get("unit_cost")
        if total_cost and unit_cost and area_total:
            calculated_total = unit_cost * area_total
            cost_tolerance = total_cost * 0.10  # 10%容差
            if abs(total_cost - calculated_total) > cost_tolerance:
                warnings.append({
                    "field": "unit_cost",
                    "message": f"平米造价×面积与总造价不一致",
                    "severity": "warning",
                    "value": f"{unit_cost} × {area_total} = {calculated_total}",
                    "expected": f"{total_cost} ± 10%"
                })

        # 平米含量一致性: above_concrete_unit ≈ above_concrete / area_above
        above_concrete = data.get("above_concrete")
        above_concrete_unit = data.get("above_concrete_unit")
        if above_concrete and above_concrete_unit and area_above:
            calculated_unit = above_concrete / area_above
            unit_tolerance = above_concrete_unit * 0.10  # 10%容差
            if abs(above_concrete_unit - calculated_unit) > unit_tolerance:
                warnings.append({
                    "field": "above_concrete_unit",
                    "message": f"地上砼平米含量不一致",
                    "severity": "warning",
                    "value": above_concrete_unit,
                    "expected": f"{calculated_unit:.4f} ± 10%"
                })

        return warnings, errors

    @classmethod
    def _validate_reference_range(cls, data: Dict[str, Any], database_stats: Optional[Dict] = None) -> List[Dict]:
        """参考范围验证：与历史数据对比"""
        warnings = []

        category = data.get("category")
        if not category or category not in cls.REFERENCE_RANGES:
            return warnings

        ranges = cls.REFERENCE_RANGES[category]

        # 检查平米造价
        unit_cost = data.get("unit_cost")
        if unit_cost:
            min_cost, max_cost = ranges["unit_cost"]
            if unit_cost < min_cost or unit_cost > max_cost:
                warnings.append({
                    "field": "unit_cost",
                    "message": f"平米造价超出{category}项目常见范围({min_cost}-{max_cost})",
                    "severity": "warning",
                    "value": unit_cost,
                    "expected": f"{min_cost} - {max_cost}"
                })

        # 检查钢筋含量
        steel = data.get("steel")
        if steel:
            min_steel, max_steel = ranges["steel"]
            if steel < min_steel or steel > max_steel:
                warnings.append({
                    "field": "steel",
                    "message": f"钢筋含量超出{category}项目常见范围({min_steel}-{max_steel} kg/㎡)",
                    "severity": "warning",
                    "value": steel,
                    "expected": f"{min_steel} - {max_steel}"
                })

        # 检查砼含量
        concrete = data.get("concrete")
        if concrete:
            min_concrete, max_concrete = ranges["concrete"]
            if concrete < min_concrete or concrete > max_concrete:
                warnings.append({
                    "field": "concrete",
                    "message": f"砼含量超出{category}项目常见范围({min_concrete}-{max_concrete} m³/㎡)",
                    "severity": "warning",
                    "value": concrete,
                    "expected": f"{min_concrete} - {max_concrete}"
                })

        return warnings


def get_validator() -> IndicatorValidator:
    """获取验证器实例"""
    return IndicatorValidator()
```

- [ ] **Step 3: 创建测试文件**

```bash
touch tests/services/test_indicator_validator.py
```

- [ ] **Step 4: 编写基础验证测试**

```python
"""测试指标数据验证服务"""
import pytest
from services.indicator_validator import IndicatorValidator
from models.indicator_library import ValidationResult


class TestIndicatorValidator:
    """测试指标数据验证器"""

    def test_validate_valid_data(self):
        """测试有效数据验证"""
        data = {
            "name": "测试项目",
            "category": "住宅",
            "location": "山东",
            "structure": "框架结构",
            "area_total": 10000.0,
            "unit_cost": 2500.0,
        }
        result = IndicatorValidator.validate(data)
        assert result.passed is True
        assert len(result.errors) == 0

    def test_validate_missing_required_field(self):
        """测试缺少必填字段"""
        data = {
            "name": "测试项目",
            # 缺少category
        }
        result = IndicatorValidator.validate(data)
        assert result.passed is False
        assert any(e.field == "category" for e in result.errors)

    def test_validate_invalid_date_format(self):
        """测试无效日期格式"""
        data = {
            "name": "测试项目",
            "category": "住宅",
            "location": "山东",
            "structure": "框架结构",
            "start_date": "2023/01",  # 错误格式
        }
        result = IndicatorValidator.validate(data)
        assert result.passed is False
        assert any(e.field == "start_date" for e in result.errors)

    def test_validate_logical_inconsistency(self):
        """测试逻辑不一致"""
        data = {
            "name": "测试项目",
            "category": "住宅",
            "location": "山东",
            "structure": "框架结构",
            "area_total": 10000.0,
            "area_above": 6000.0,
            "area_below": 3000.0,  # 不等于area_total
            "unit_cost": 2500.0,
            "total_cost": 25000000.0,
        }
        result = IndicatorValidator.validate(data)
        # 应该有警告但不阻止
        assert len(result.warnings) > 0
        assert any("面积不一致" in w.message for w in result.warnings)

    def test_validate_reference_range_warning(self):
        """测试参考范围警告"""
        data = {
            "name": "测试项目",
            "category": "住宅",
            "location": "山东",
            "structure": "框架结构",
            "area_total": 10000.0,
            "unit_cost": 5000.0,  # 超出住宅常见范围
            "steel": 100.0,  # 超出住宅常见范围
        }
        result = IndicatorValidator.validate(data)
        # 应该有警告
        assert len(result.warnings) > 0
        assert any(w.field == "unit_cost" for w in result.warnings)
```

- [ ] **Step 5: 运行测试**

```bash
cd web/backend
pytest tests/services/test_indicator_validator.py -v
```

Expected output: 所有测试通过

- [ ] **Step 6: 提交**

```bash
git add web/backend/services/indicator_validator.py tests/services/test_indicator_validator.py
git commit -m "feat: 添加指标数据验证服务（三级验证）"
```

---

## 第四阶段：后端 - Excel解析服务

### Task 4: 创建Excel解析服务

**文件:**
- 创建: `web/backend/services/excel_parser_service.py`

**接口:**
- 消费: `openpyxl`, 上传的Excel文件
- 生产: `ExcelParserService.parse()` 返回合并后的项目数据列表

- [ ] **Step 1: 创建Excel解析服务文件**

```bash
touch web/backend/services/excel_parser_service.py
```

- [ ] **Step 2: 编写Excel解析服务**

```python
"""
Excel解析服务
解析指标库Excel文件（汇总表+明细表）
"""
import logging
import io
from typing import List, Dict, Any, Optional
from datetime import datetime

import openpyxl

logger = logging.getLogger(__name__)


class ExcelParserService:
    """Excel解析器 - 解析指标库Excel文件"""

    # 汇总表列名映射（中文列名 -> 数据库字段名）
    SUMMARY_COLUMN_MAP = {
        "序号": "index",
        "项目名称": "name",
        "业态": "category",
        "项目所在地": "location",
        "结构形式": "structure",
        "交付形式": "delivery_type",
        "层数（地上/下）": "floor_info",
        "总面积（m2）": "area_total",
        "檐高（m）": "height",
        "总造价": "total_cost",
        "开工时间": "start_date",
        "竣工时间": "end_date",
    }

    # 明细表列名映射（多级表头合并后的列名 -> 数据库字段名）
    DETAIL_COLUMN_MAP = {
        # 基本信息
        "项目名称": "name",
        "项目所在地": "location",
        "结构": "structure",
        "交付形式": "delivery_type",
        "建筑高度（m）": "height",
        "建筑层数（地上）": "floor_above",
        "建筑层数（地下）": "floor_below",
        "有无桩基，桩基形式": "foundation_type",
        "其中地下建筑面积（m2）": "area_below",
        "其中地上建筑面积（m2）": "area_above",
        "总建筑面积（m2）": "area_total",

        # 造价分解
        "地下土建造价": "cost_underground_structure",
        "地下安装造价": "cost_underground_installation",
        "地上土建造价": "cost_above_structure",
        "地上安装造价": "cost_above_installation",
        "合计总造价（元）": "total_cost",
        "地下土建造价": "cost_underground_structure",
        "地下安装造价": "cost_underground_installation",
        "地上土建造价": "cost_above_structure",
        "地上安装造价": "cost_above_installation",
        "合计平米造价（元/m2）": "unit_cost",
        "金额（元）": "cost_measures",
        "平米造价（元/m2）": "unit_cost_measures",
        "其中：室外造价（元）": "cost_outdoor",
        "室外平米造价（元/m2）": "unit_cost_outdoor",

        # 专项工程
        "造价（元）": "cost_pile",
        "平米造价（m2/元）": "unit_cost_pile",
        "造价（元）": "cost_foundation_support",
        "平米造价（m2/元）": "unit_cost_foundation_support",
        "造价（元）": "cost_curtain_wall",
        "平米造价（m2/元）": "unit_cost_curtain_wall",
        "造价（元）": "cost_decoration",
        "平米造价（m2/元）": "unit_cost_decoration",
        "造价（元）": "cost_exterior_insulation",
        "平米造价（m2/元）": "unit_cost_exterior_insulation",
        "造价（元）": "cost_exterior_windows",
        "平米造价（m2/元）": "unit_cost_exterior_windows",
        "造价（元）": "cost_water_drainage",
        "平米造价（m2/元）": "unit_cost_water_drainage",
        "造价（元）": "cost_heating",
        "平米造价（m2/元）": "unit_cost_heating",
        "造价（元）": "cost_electrical",
        "平米造价（m2/元）": "unit_cost_electrical",
        "造价（元）": "cost_hvac",
        "平米造价（m2/元）": "unit_cost_hvac",

        # 材料用量
        "砼（m3）": "underground_concrete",
        "平米含量（m3/m2）": "underground_concrete_unit",
        "钢筋（t）": "underground_rebar",
        "平米含量（t/m2）": "underground_rebar_unit",
        "模板（m2）": "underground_formwork",
        "平米含量（m2/m2）": "underground_formwork_unit",
        "砼（m3）": "above_concrete",
        "平米含量（m3/m2）": "above_concrete_unit",
        "钢筋（t）": "above_rebar",
        "平米含量（t/m2）": "above_rebar_unit",
        "模板（m2）": "above_formwork",
        "平米含量（m2/m2）": "above_formwork_unit",
    }

    def __init__(self):
        self.logger = logger

    def parse(self, file_content: bytes, filename: str = "") -> Dict[str, Any]:
        """
        解析Excel文件

        Args:
            file_content: Excel文件内容（bytes）
            filename: 原始文件名

        Returns:
            解析结果: {"projects": [...], "summary_count": n, "detail_count": m}
        """
        logger.info(f"[ExcelParserService] 开始解析 | 文件={filename}")

        try:
            wb = openpyxl.load_workbook(io.BytesIO(file_content))

            # 检查工作表
            if "汇总" not in wb.sheetnames or "明细" not in wb.sheetnames:
                logger.error("[ExcelParserService] 缺少必要的工作表")
                return {
                    "success": False,
                    "error": "Excel文件必须包含'汇总'和'明细'两个工作表",
                    "projects": []
                }

            # 解析汇总表
            summary_data = self._parse_summary_sheet(wb["汇总"])
            logger.info(f"[ExcelParserService] 汇总表解析完成 | {len(summary_data)} 条")

            # 解析明细表
            detail_data = self._parse_detail_sheet(wb["明细"])
            logger.info(f"[ExcelParserService] 明细表解析完成 | {len(detail_data)} 条")

            # 按序号合并数据
            merged_projects = self._merge_data(summary_data, detail_data)

            # 添加录入时间和来源文件
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for project in merged_projects:
                project["entry_date"] = now
                project["source_file"] = filename
                project["source"] = "excel_import"

            logger.info(f"[ExcelParserService] 解析完成 | 合并后={len(merged_projects)} 条")

            return {
                "success": True,
                "projects": merged_projects,
                "summary_count": len(summary_data),
                "detail_count": len(detail_data)
            }

        except Exception as e:
            logger.error(f"[ExcelParserService] 解析失败 | {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "projects": []
            }

    def _parse_summary_sheet(self, ws) -> List[Dict[str, Any]]:
        """解析汇总表"""
        data = []

        # 第1行是表头
        headers = [cell.value for cell in ws[1]]

        # 从第2行开始读取数据
        for row_idx in range(2, ws.max_row + 1):
            row_data = {}
            has_data = False

            for col_idx, header in enumerate(headers):
                if header and header in self.SUMMARY_COLUMN_MAP:
                    cell_value = ws.cell(row=row_idx, column=col_idx + 1).value
                    if cell_value is not None:
                        field_name = self.SUMMARY_COLUMN_MAP[header]
                        row_data[field_name] = cell_value
                        has_data = True

            if has_data and row_data.get("name"):
                data.append(row_data)

        return data

    def _parse_detail_sheet(self, ws) -> List[Dict[str, Any]]:
        """
        解析明细表
        明细表有多级表头（第2-4行），需要合并处理
        """
        data = []

        # 构建完整列名（合并多级表头）
        merged_headers = self._build_merged_headers(ws)

        # 从第5行开始读取数据
        for row_idx in range(5, ws.max_row + 1):
            row_data = {}
            has_data = False

            for col_idx, header in enumerate(merged_headers):
                if header:
                    cell_value = ws.cell(row=row_idx, column=col_idx + 1).value
                    if cell_value is not None:
                        # 尝试转换数字类型
                        if isinstance(cell_value, str) and cell_value.startswith("="):
                            # 公式，跳过或尝试计算
                            continue
                        row_data[header] = cell_value
                        has_data = True

            if has_data:
                # 添加序号（行号-4，因为前4行是表头）
                row_data["index"] = row_idx - 4
                data.append(row_data)

        return data

    def _build_merged_headers(self, ws) -> List[str]:
        """
        构建合并后的表头
        将第2-4行的多级表头合并成单层
        """
        # 第2行：主要分类
        row2 = [str(cell.value or "") for cell in ws[2]]
        # 第3行：次要分类
        row3 = [str(cell.value or "") for cell in ws[3]]
        # 第4行：字段名
        row4 = [str(cell.value or "") for cell in ws[4]]

        merged_headers = []
        for i in range(len(row4)):
            # 优先使用第4行的字段名
            if row4[i] and row4[i] != "None":
                merged_headers.append(row4[i])
            elif row3[i] and row3[i] != "None":
                merged_headers.append(row3[i])
            elif row2[i] and row2[i] != "None":
                merged_headers.append(row2[i])
            else:
                merged_headers.append("")

        return merged_headers

    def _merge_data(self, summary_data: List[Dict], detail_data: List[Dict]) -> List[Dict[str, Any]]:
        """
        按序号合并汇总数据和明细数据
        """
        # 创建序号到明细的映射
        detail_map = {d.get("index"): d for d in detail_data}

        merged = []
        for summary_item in summary_data:
            index = summary_item.get("index")
            if index is None:
                continue

            # 查找对应明细
            detail_item = detail_map.get(index)
            if detail_item:
                # 合并数据
                merged_item = {**summary_item, **detail_item}
            else:
                # 没有明细，只用汇总数据
                merged_item = summary_item

            merged.append(merged_item)

        return merged


def get_excel_parser() -> ExcelParserService:
    """获取Excel解析器实例"""
    return ExcelParserService()
```

- [ ] **Step 3: 创建测试文件和示例Excel**

```bash
touch tests/services/test_excel_parser.py
```

- [ ] **Step 4: 编写Excel解析测试**

```python
"""测试Excel解析服务"""
import pytest
import openpyxl
from io import BytesIO
from services.excel_parser_service import ExcelParserService


class TestExcelParserService:
    """测试Excel解析器"""

    def create_test_excel(self):
        """创建测试用的Excel文件"""
        wb = openpyxl.Workbook()

        # 创建汇总表
        ws_summary = wb.active
        ws_summary.title = "汇总"
        ws_summary.append(["序号", "项目名称", "业态", "项目所在地", "结构形式", "交付形式", "总面积（m2）", "檐高（m）", "总造价"])
        ws_summary.append([1, "测试项目A", "住宅", "山东烟台", "框架结构", "毛坯交付", 10000.0, 36.0, 25000000.0])
        ws_summary.append([2, "测试项目B", "商业", "山东青岛", "剪力墙结构", "精装修", 15000.0, 48.0, 45000000.0])

        # 创建明细表
        ws_detail = wb.create_sheet("明细")
        # 多级表头（简化版）
        ws_detail.append([""] * 10)
        ws_detail.append(["序号", "项目名称", "建筑高度（m）", "建筑层数（地上）", "建筑层数（地下）", "砼（m3）", "平米含量（m3/m2）", "钢筋（t）", "平米含量（t/m2）", "合计平米造价（元/m2）"])
        ws_detail.append([1, "测试项目A", 36.0, 12, 2, 3500.0, 0.35, 420.0, 0.042, 2500.0])
        ws_detail.append([2, "测试项目B", 48.0, 16, 2, 6000.0, 0.40, 750.0, 0.050, 3000.0])

        # 保存到内存
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        return output.read()

    def test_parse_success(self):
        """测试成功解析"""
        parser = ExcelParserService()
        file_content = self.create_test_excel()

        result = parser.parse(file_content, "test.xlsx")

        assert result["success"] is True
        assert len(result["projects"]) == 2
        assert result["projects"][0]["name"] == "测试项目A"
        assert result["projects"][0]["category"] == "住宅"

    def test_parse_missing_sheets(self):
        """测试缺少工作表"""
        parser = ExcelParserService()
        wb = openpyxl.Workbook()
        output = BytesIO()
        wb.save(output)
        output.seek(0)

        result = parser.parse(output.read(), "test.xlsx")

        assert result["success"] is False
        assert "缺少必要的工作表" in result["error"]

    def test_merge_data(self):
        """测试数据合并"""
        parser = ExcelParserService()
        file_content = self.create_test_excel()

        result = parser.parse(file_content, "test.xlsx")

        # 检查合并后的数据
        project = result["projects"][0]
        assert project["name"] == "测试项目A"
        assert project["area_total"] == 10000.0
        assert project["height"] == 36.0
        assert project["above_concrete"] == 3500.0
```

- [ ] **Step 5: 运行测试**

```bash
cd web/backend
pytest tests/services/test_excel_parser.py -v
```

Expected output: 所有测试通过

- [ ] **Step 6: 提交**

```bash
git add web/backend/services/excel_parser_service.py tests/services/test_excel_parser.py
git commit -m "feat: 添加Excel解析服务（汇总表+明细表）"
```

---

## 第五阶段：后端 - 指标库业务服务

### Task 5: 创建指标库业务服务

**文件:**
- 创建: `web/backend/services/indicator_library_service.py`

**接口:**
- 消费: `LocalIndicatorService`, `ExcelParserService`, `IndicatorValidator`
- 生产: `IndicatorLibraryService.get_summary()`, `create_project()`, `import_from_excel()` 等

- [ ] **Step 1: 创建业务服务文件**

```bash
touch web/backend/services/indicator_library_service.py
```

- [ ] **Step 2: 编写业务服务**

```python
"""
指标库业务服务
整合数据存储、解析和验证
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from services.local_indicator_service import LocalIndicatorService
from services.excel_parser_service import ExcelParserService, get_excel_parser
from services.indicator_validator import IndicatorValidator
from models.indicator_library import (
    IndicatorLibrarySummary,
    IndicatorLibraryDetail,
    IndicatorLibraryCreate,
    ValidationResult,
    ImportPreviewResult,
    ImportResult
)

logger = logging.getLogger(__name__)


class IndicatorLibraryService:
    """指标库业务服务"""

    def __init__(self):
        self.storage = LocalIndicatorService()
        self.parser = get_excel_parser()
        self.validator = IndicatorValidator()

    def get_summary_list(
        self,
        category: Optional[str] = None,
        location: Optional[str] = None,
        limit: int = 100
    ) -> List[IndicatorLibrarySummary]:
        """
        获取汇总列表

        Args:
            category: 业态筛选
            location: 地区筛选
            limit: 返回数量限制

        Returns:
            汇总项列表
        """
        logger.info(f"[IndicatorLibraryService] 获取汇总列表 | category={category}, location={location}")

        projects = self.storage.get_indicator_projects(
            limit=limit,
            category=category,
            location=location
        )

        # 转换为汇总模型
        summaries = []
        for p in projects:
            summaries.append(IndicatorLibrarySummary(
                id=p.get("id", ""),
                name=p.get("name", ""),
                category=p.get("category", ""),
                location=p.get("location", ""),
                structure=p.get("structure", ""),
                start_date=p.get("start_date"),
                end_date=p.get("end_date"),
                area_total=p.get("area_total"),
                unit_cost=p.get("unit_cost"),
                entry_date=p.get("entry_date"),
                updated_at=p.get("updated_at", "")
            ))

        logger.info(f"[IndicatorLibraryService] 返回 {len(summaries)} 条汇总")
        return summaries

    def get_detail(self, project_id: str) -> Optional[IndicatorLibraryDetail]:
        """
        获取项目详情

        Args:
            project_id: 项目ID

        Returns:
            项目详情，不存在返回None
        """
        logger.info(f"[IndicatorLibraryService] 获取详情 | id={project_id}")

        project = self.storage.get_indicator_project(project_id)
        if not project:
            logger.warning(f"[IndicatorLibraryService] 项目不存在 | id={project_id}")
            return None

        return IndicatorLibraryDetail(**project)

    def create_project(self, data: IndicatorLibraryCreate) -> Optional[IndicatorLibraryDetail]:
        """
        创建项目

        Args:
            data: 创建数据

        Returns:
            创建的项目详情，失败返回None
        """
        logger.info(f"[IndicatorLibraryService] 创建项目 | name={data.name}")

        # 先验证
        validation = self.validator.validate(data.dict())
        if not validation.passed:
            logger.warning(f"[IndicatorLibraryService] 验证失败 | errors={len(validation.errors)}")
            return None

        # 添加录入时间
        project_data = data.dict()
        project_data["entry_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        result = self.storage.create_indicator_project(project_data)
        if result:
            logger.info(f"[IndicatorLibraryService] 创建成功 | id={result.get('id')}")
            return IndicatorLibraryDetail(**result)

        return None

    def update_project(self, project_id: str, data: Dict[str, Any]) -> Optional[IndicatorLibraryDetail]:
        """
        更新项目

        Args:
            project_id: 项目ID
            data: 更新数据

        Returns:
            更新后的项目详情
        """
        logger.info(f"[IndicatorLibraryService] 更新项目 | id={project_id}")

        # 验证
        validation = self.validator.validate(data)
        if not validation.passed:
            logger.warning(f"[IndicatorLibraryService] 验证失败 | errors={len(validation.errors)}")
            return None

        success = self.storage.update_indicator_project(project_id, data)
        if success:
            updated = self.storage.get_indicator_project(project_id)
            logger.info(f"[IndicatorLibraryService] 更新成功 | id={project_id}")
            return IndicatorLibraryDetail(**updated)

        return None

    def delete_project(self, project_id: str) -> bool:
        """
        删除项目

        Args:
            project_id: 项目ID

        Returns:
            是否成功
        """
        logger.info(f"[IndicatorLibraryService] 删除项目 | id={project_id}")

        success = self.storage.delete_indicator_project(project_id)
        if success:
            logger.info(f"[IndicatorLibraryService] 删除成功 | id={project_id}")
        else:
            logger.warning(f"[IndicatorLibraryService] 删除失败 | id={project_id}")

        return success

    def validate_data(self, data: Dict[str, Any]) -> ValidationResult:
        """
        验证数据

        Args:
            data: 待验证数据

        Returns:
            验证结果
        """
        logger.info(f"[IndicatorLibraryService] 验证数据")

        # 获取数据库统计信息用于参考范围验证
        stats = self.storage.get_stats()
        return self.validator.validate(data, database_stats=stats)

    def import_from_excel(self, file_content: bytes, filename: str) -> ImportResult:
        """
        从Excel导入

        Args:
            file_content: Excel文件内容
            filename: 文件名

        Returns:
            导入结果
        """
        logger.info(f"[IndicatorLibraryService] Excel导入 | file={filename}")

        # 解析Excel
        parse_result = self.parser.parse(file_content, filename)
        if not parse_result["success"]:
            return ImportResult(
                success=False,
                imported=0,
                total=0,
                errors=[parse_result.get("error", "解析失败")]
            )

        projects = parse_result["projects"]
        warnings = []
        errors = []
        imported = 0

        # 逐个验证和导入
        for idx, project_data in enumerate(projects):
            project_name = project_data.get("name", f"项目{idx+1}")

            # 验证
            validation = self.validator.validate(project_data)
            if validation.errors:
                errors.append(f"{project_name}: {len(validation.errors)}个错误")
                continue

            # 记录警告
            if validation.warnings:
                for w in validation.warnings:
                    warnings.append({
                        "project": project_name,
                        "field": w.field,
                        "message": w.message
                    })

            # 创建项目
            result = self.storage.create_indicator_project(project_data)
            if result:
                imported += 1
            else:
                errors.append(f"{project_name}: 创建失败")

        logger.info(f"[IndicatorLibraryService] 导入完成 | 成功={imported}/{len(projects)}")

        return ImportResult(
            success=imported > 0,
            imported=imported,
            total=len(projects),
            warnings=warnings,
            errors=errors
        )

    def preview_import(self, file_content: bytes, filename: str) -> ImportPreviewResult:
        """
        预览导入（不实际写入数据库）

        Args:
            file_content: Excel文件内容
            filename: 文件名

        Returns:
            预览结果
        """
        logger.info(f"[IndicatorLibraryService] 预览导入 | file={filename}")

        # 解析Excel
        parse_result = self.parser.parse(file_content, filename)
        if not parse_result["success"]:
            return ImportPreviewResult(
                total=0,
                valid_count=0,
                warning_count=0,
                error_count=0,
                items=[]
            )

        projects = parse_result["projects"]
        items = []
        valid_count = 0
        warning_count = 0
        error_count = 0

        for idx, project_data in enumerate(projects):
            # 验证
            validation = self.validator.validate(project_data)

            item_warnings = [w.message for w in validation.warnings]
            item_errors = [e.message for e in validation.errors]

            if item_errors:
                status = "error"
                error_count += 1
            elif item_warnings:
                status = "warning"
                warning_count += 1
            else:
                status = "valid"
                valid_count += 1

            items.append({
                "index": idx + 1,
                "name": project_data.get("name", ""),
                "category": project_data.get("category"),
                "location": project_data.get("location"),
                "unit_cost": project_data.get("unit_cost"),
                "status": status,
                "warnings": item_warnings,
                "errors": item_errors
            })

        return ImportPreviewResult(
            total=len(projects),
            valid_count=valid_count,
            warning_count=warning_count,
            error_count=error_count,
            items=items
        )

    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息

        Returns:
            统计数据
        """
        logger.info("[IndicatorLibraryService] 获取统计信息")
        return self.storage.get_stats()


def get_indicator_library_service() -> IndicatorLibraryService:
    """获取指标库服务实例"""
    return IndicatorLibraryService()
```

- [ ] **Step 3: 创建测试文件**

```bash
touch tests/services/test_indicator_library_service.py
```

- [ ] **Step 4: 编写业务服务测试**

```python
"""测试指标库业务服务"""
import pytest
from services.indicator_library_service import IndicatorLibraryService, get_indicator_library_service
from models.indicator_library import IndicatorLibraryCreate


class TestIndicatorLibraryService:
    """测试指标库业务服务"""

    def test_get_summary_list(self):
        """测试获取汇总列表"""
        service = get_indicator_library_service()
        summaries = service.get_summary_list(limit=10)

        assert isinstance(summaries, list)

    def test_create_valid_project(self):
        """测试创建有效项目"""
        service = get_indicator_library_service()
        data = IndicatorLibraryCreate(
            name="测试项目",
            category="住宅",
            location="山东",
            structure="框架结构",
            area_total=10000.0,
            unit_cost=2500.0
        )

        result = service.create_project(data)
        assert result is not None
        assert result.name == "测试项目"

        # 清理
        if result and result.id:
            service.delete_project(result.id)

    def test_create_invalid_project(self):
        """测试创建无效项目（缺少必填）"""
        service = get_indicator_library_service()
        data = IndicatorLibraryCreate(
            name="",  # 无效：空名称
            category="住宅",
            location="山东",
            structure="框架结构"
        )

        result = service.create_project(data)
        assert result is None  # 验证失败应返回None

    def test_validate_data(self):
        """测试数据验证"""
        service = get_indicator_library_service()
        data = {
            "name": "测试项目",
            "category": "住宅",
            "location": "山东",
            "structure": "框架结构",
            "area_total": 10000.0,
            "unit_cost": 2500.0
        }

        result = service.validate_data(data)
        assert result.passed is True
```

- [ ] **Step 5: 运行测试**

```bash
cd web/backend
pytest tests/services/test_indicator_library_service.py -v
```

Expected output: 所有测试通过

- [ ] **Step 6: 提交**

```bash
git add web/backend/services/indicator_library_service.py tests/services/test_indicator_library_service.py
git commit -m "feat: 添加指标库业务服务"
```

---

## 第六阶段：后端 - API路由

### Task 6: 创建API路由

**文件:**
- 创建: `web/backend/api/indicator_library.py`
- 修改: `web/backend/main.py:114` (注册路由)

**接口:**
- 消费: `IndicatorLibraryService`, `IndicatorLibraryDetail`, `IndicatorLibraryCreate`
- 生产: RESTful API端点

- [ ] **Step 1: 创建API路由文件**

```bash
touch web/backend/api/indicator_library.py
```

- [ ] **Step 2: 编写API路由**

```python
"""
指标库API路由
提供CRUD、导入导出、验证等端点
"""
import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, UploadFile, File, Query, Depends
from fastapi.responses import StreamingResponse
from io import BytesIO
import openpyxl
from datetime import datetime

from services.indicator_library_service import get_indicator_library_service, IndicatorLibraryService
from models.indicator_library import (
    IndicatorLibrarySummary,
    IndicatorLibraryDetail,
    IndicatorLibraryCreate,
    ValidationResult,
    ImportResult,
    ImportPreviewResult
)

logger = logging.getLogger(__name__)
router = APIRouter()


def get_service() -> IndicatorLibraryService:
    """获取服务实例"""
    return get_indicator_library_service()


# ==================== 汇总列表 ====================

@router.get("/summary", response_model=List[IndicatorLibrarySummary])
async def get_summary_list(
    category: Optional[str] = Query(None, description="业态筛选"),
    location: Optional[str] = Query(None, description="地区筛选"),
    limit: int = Query(100, ge=1, le=500, description="返回数量限制"),
    service: IndicatorLibraryService = Depends(get_service)
):
    """
    获取汇总列表

    返回指标库项目的汇总信息，支持按业态和地区筛选
    """
    logger.info(f"[get_summary_list] 查询汇总列表 | category={category}, location={location}")
    try:
        result = service.get_summary_list(category=category, location=location, limit=limit)
        logger.info(f"[get_summary_list] 返回 {len(result)} 条")
        return result
    except Exception as e:
        logger.error(f"[get_summary_list] 查询失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="查询失败")


# ==================== 项目详情 ====================

@router.get("/{project_id}", response_model=IndicatorLibraryDetail)
async def get_project_detail(
    project_id: str,
    service: IndicatorLibraryService = Depends(get_service)
):
    """
    获取项目详情

    返回指定项目的完整明细信息
    """
    logger.info(f"[get_project_detail] 获取详情 | id={project_id}")
    try:
        result = service.get_detail(project_id)
        if not result:
            raise HTTPException(status_code=404, detail="项目不存在")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[get_project_detail] 查询失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="查询失败")


@router.post("/", response_model=IndicatorLibraryDetail, status_code=201)
async def create_project(
    data: IndicatorLibraryCreate,
    service: IndicatorLibraryService = Depends(get_service)
):
    """
    创建项目

    创建新的指标库项目
    """
    logger.info(f"[create_project] 创建项目 | name={data.name}")
    try:
        result = service.create_project(data)
        if not result:
            raise HTTPException(status_code=400, detail="数据验证失败或创建失败")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[create_project] 创建失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="创建失败")


@router.put("/{project_id}", response_model=IndicatorLibraryDetail)
async def update_project(
    project_id: str,
    data: IndicatorLibraryDetail,
    service: IndicatorLibraryService = Depends(get_service)
):
    """
    更新项目

    更新指定项目的信息
    """
    logger.info(f"[update_project] 更新项目 | id={project_id}")
    try:
        result = service.update_project(project_id, data.dict(exclude_unset=True))
        if not result:
            raise HTTPException(status_code=400, detail="更新失败")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[update_project] 更新失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="更新失败")


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    service: IndicatorLibraryService = Depends(get_service)
):
    """
    删除项目

    删除指定的指标库项目
    """
    logger.info(f"[delete_project] 删除项目 | id={project_id}")
    try:
        success = service.delete_project(project_id)
        return {"success": success}
    except Exception as e:
        logger.error(f"[delete_project] 删除失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="删除失败")


# ==================== 数据验证 ====================

@router.post("/validate", response_model=ValidationResult)
async def validate_data(
    data: IndicatorLibraryDetail,
    service: IndicatorLibraryService = Depends(get_service)
):
    """
    数据验证

    对项目数据进行三级验证：基础、逻辑、参考范围
    """
    logger.info(f"[validate_data] 验证数据 | name={data.name}")
    try:
        return service.validate_data(data.dict())
    except Exception as e:
        logger.error(f"[validate_data] 验证失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="验证失败")


# ==================== Excel导入 ====================

@router.post("/import", response_model=ImportResult)
async def import_from_excel(
    file: UploadFile = File(...),
    service: IndicatorLibraryService = Depends(get_service)
):
    """
    Excel导入

    从Excel文件批量导入指标数据
    """
    logger.info(f"[import_from_excel] Excel导入 | file={file.filename}")

    # 验证文件类型
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="仅支持Excel文件格式(.xlsx, .xls)")

    try:
        content = await file.read()
        result = service.import_from_excel(content, file.filename)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[import_from_excel] 导入失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")


@router.post("/preview", response_model=ImportPreviewResult)
async def preview_import(
    file: UploadFile = File(...),
    service: IndicatorLibraryService = Depends(get_service)
):
    """
    导入预览

    预览Excel导入结果，不实际写入数据库
    """
    logger.info(f"[preview_import] 导入预览 | file={file.filename}")

    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="仅支持Excel文件格式")

    try:
        content = await file.read()
        result = service.preview_import(content, file.filename)
        return result
    except Exception as e:
        logger.error(f"[preview_import] 预览失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"预览失败: {str(e)}")


# ==================== Excel导出 ====================

@router.get("/export")
async def export_to_excel(
    category: Optional[str] = Query(None, description="业态筛选"),
    service: IndicatorLibraryService = Depends(get_service)
):
    """
    导出Excel

    将指标库数据导出为Excel文件
    """
    logger.info(f"[export_to_excel] 导出Excel | category={category}")

    try:
        # 获取数据
        projects = service.storage.get_indicator_projects(limit=1000, category=category)

        # 创建Excel
        wb = openpyxl.Workbook()

        # 汇总表
        ws_summary = wb.active
        ws_summary.title = "汇总"
        ws_summary.append(["序号", "项目名称", "业态", "项目所在地", "结构形式", "开工时间", "竣工时间", "总面积（m2）", "平米造价"])
        for idx, p in enumerate(projects, 1):
            ws_summary.append([
                idx,
                p.get("name"),
                p.get("category"),
                p.get("location"),
                p.get("structure"),
                p.get("start_date"),
                p.get("end_date"),
                p.get("area_total"),
                p.get("unit_cost")
            ])

        # 输出到内存
        output = BytesIO()
        wb.save(output)
        output.seek(0)

        filename = f"indicator_library_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

        logger.info(f"[export_to_excel] 导出完成 | {len(projects)} 条记录")

        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"}
        )

    except Exception as e:
        logger.error(f"[export_to_excel] 导出失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")


# ==================== 统计信息 ====================

@router.get("/stats/overview")
async def get_stats(
    service: IndicatorLibraryService = Depends(get_service)
):
    """
    获取统计信息

    返回指标库的统计数据
    """
    logger.info("[get_stats] 获取统计信息")
    try:
        return service.get_stats()
    except Exception as e:
        logger.error(f"[get_stats] 获取失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取失败")
```

- [ ] **Step 3: 在main.py中注册路由**

在 `web/backend/main.py` 中添加导入和路由注册：

```python
# 在文件开头的导入部分添加
from api import indicator_library

# 在路由注册部分（约第110行之后）添加
app.include_router(indicator_library.router, prefix="/api/indicator-library", tags=["指标库管理"])
```

具体修改位置：

```python
# 在第14行附近添加导入
from api import projects, materials, price_sources, price_history, adjustments, indicators, sync, adjustment_rules, scheduler_api, fetch as fetch_api, cron_fetch, cost_reference, adjustment_project, history_fetch, price_history_db, file_parser, adjustment_prices, adjustment_prices_batch, building_schedule, building_adjustment, cost_history, data_manager, adjustment_template, indicator_report, fetch_history, indicator_library

# 在第111行之后添加路由注册
app.include_router(indicator_library.router, prefix="/api/indicator-library", tags=["指标库管理"])
```

- [ ] **Step 4: 测试API端点**

```bash
cd web/backend
python -c "
from main import app
from fastapi.testclient import TestClient

client = TestClient(app)
response = client.get('/api/indicator-library/summary?limit=10')
print('Status:', response.status_code)
print('Response:', response.json())
"
```

Expected output: 200状态码，返回汇总列表

- [ ] **Step 5: 创建API测试**

```bash
touch tests/api/test_indicator_library.py
```

```python
"""测试指标库API"""
import pytest
from fastapi.testclient import TestClient
from main import app


class TestIndicatorLibraryAPI:
    """测试指标库API"""

    def test_get_summary_list(self):
        """测试获取汇总列表"""
        client = TestClient(app)
        response = client.get("/api/indicator-library/summary?limit=10")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_create_project(self):
        """测试创建项目"""
        client = TestClient(app)
        project_data = {
            "name": "API测试项目",
            "category": "住宅",
            "location": "山东",
            "structure": "框架结构",
            "area_total": 10000.0,
            "unit_cost": 2500.0
        }
        response = client.post("/api/indicator-library/", json=project_data)
        assert response.status_code == 201 or response.status_code == 400  # 400可能是已存在

    def test_validate_data(self):
        """测试数据验证"""
        client = TestClient(app)
        data = {
            "name": "验证测试",
            "category": "住宅",
            "location": "山东",
            "structure": "框架结构"
        }
        response = client.post("/api/indicator-library/validate", json=data)
        assert response.status_code == 200
        result = response.json()
        assert "passed" in result
```

- [ ] **Step 6: 运行测试**

```bash
cd web/backend
pytest tests/api/test_indicator_library.py -v
```

Expected output: 所有测试通过

- [ ] **Step 7: 提交**

```bash
git add web/backend/api/indicator_library.py web/backend/main.py tests/api/test_indicator_library.py
git commit -m "feat: 添加指标库API路由"
```

---

## 第七阶段：前端 - 页面组件

### Task 7: 创建前端主页面

**文件:**
- 创建: `web/frontend/src/pages/IndicatorLibrary.tsx`

**接口:**
- 消费: `SummaryList`, `DetailPanel` 组件
- 生产: 主页面组件

- [ ] **Step 1: 创建主页面文件**

```bash
mkdir -p web/frontend/src/pages
touch web/frontend/src/pages/IndicatorLibrary.tsx
```

- [ ] **Step 2: 编写主页面组件**

```typescript
/**
 * 指标库管理页面
 * 主从布局：左侧汇总列表，右侧详情面板
 */
import React, { useState, useEffect } from 'react';
import { Layout, Button, message, Spin } from 'antd';
import { PlusOutlined, ImportOutlined, ExportOutlined } from '@ant-design/icons';
import SummaryList from '../components/indicator-library/SummaryList';
import DetailPanel from '../components/indicator-library/DetailPanel';
import ImportPreview from '../components/indicator-library/ImportPreview';
import { indicatorLibraryAPI } from '../services/api';
import { IndicatorLibrarySummary } from '../types';

import './IndicatorLibrary.css';

const { Header, Content, Sider } = Layout;

const IndicatorLibrary: React.FC = () => {
  const [summaries, setSummaries] = useState<IndicatorLibrarySummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [importVisible, setImportVisible] = useState(false);
  const [filters, setFilters] = useState({
    category: undefined as string | undefined,
    location: undefined as string | undefined,
    delivery_type: undefined as string | undefined,
    start_date_from: undefined as string | undefined,
    start_date_to: undefined as string | undefined,
    end_date_from: undefined as string | undefined,
    end_date_to: undefined as string | undefined,
    search_text: undefined as string | undefined,
  });

  // 加载汇总列表
  const loadSummaries = async () => {
    setLoading(true);
    try {
      const data = await indicatorLibraryAPI.getSummary({
        category: filters.category,
        location: filters.location,
        limit: 100,
      });
      setSummaries(data);
    } catch (error) {
      message.error('加载失败');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  // 初始化加载
  useEffect(() => {
    loadSummaries();
  }, [filters]);

  // 选择项目
  const handleSelect = (id: string) => {
    setSelectedId(id);
  };

  // 新建项目
  const handleCreate = () => {
    setSelectedId('new');
  };

  // 导入成功后刷新
  const handleImportSuccess = () => {
    setImportVisible(false);
    loadSummaries();
    message.success('导入成功');
  };

  // 导出
  const handleExport = async () => {
    try {
      await indicatorLibraryAPI.exportExcel(filters.category);
      message.success('导出成功');
    } catch (error) {
      message.error('导出失败');
    }
  };

  // 详情保存后刷新
  const handleSave = () => {
    loadSummaries();
  };

  return (
    <Layout className="indicator-library-page">
      <Header className="page-header">
        <div className="header-title">指标库管理</div>
        <div className="header-actions">
          <Button icon={<PlusOutlined />} onClick={handleCreate}>
            新建
          </Button>
          <Button icon={<ImportOutlined />} onClick={() => setImportVisible(true)}>
            导入
          </Button>
          <Button icon={<ExportOutlined />} onClick={handleExport}>
            导出
          </Button>
        </div>
      </Header>
      <Layout>
        <Sider width="35%" className="summary-sider">
          {loading ? (
            <div className="loading-wrapper">
              <Spin />
            </div>
          ) : (
            <SummaryList
              data={summaries}
              selectedId={selectedId}
              onSelect={handleSelect}
              filters={filters}
              onFilterChange={setFilters}
            />
          )}
        </Sider>
        <Content className="detail-content">
          <DetailPanel
            projectId={selectedId}
            onSave={handleSave}
            onCancel={() => setSelectedId(null)}
          />
        </Content>
      </Layout>
      {importVisible && (
        <ImportPreview
          visible={importVisible}
          onSuccess={handleImportSuccess}
          onCancel={() => setImportVisible(false)}
        />
      )}
    </Layout>
  );
};

export default IndicatorLibrary;
```

- [ ] **Step 3: 创建样式文件**

```bash
touch web/frontend/src/pages/IndicatorLibrary.css
```

```css
.indicator-library-page {
  height: 100vh;
  background: #f0f2f5;
}

.indicator-library-page .page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #fff;
  padding: 0 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  z-index: 10;
}

.indicator-library-page .header-title {
  font-size: 18px;
  font-weight: 600;
}

.indicator-library-page .header-actions {
  display: flex;
  gap: 8px;
}

.indicator-library-page .summary-sider {
  background: #fff;
  border-right: 1px solid #f0f0f0;
  overflow-y: auto;
}

.indicator-library-page .detail-content {
  background: #fff;
  overflow-y: auto;
}

.indicator-library-page .loading-wrapper {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
}
```

- [ ] **Step 4: 提交**

```bash
git add web/frontend/src/pages/IndicatorLibrary.tsx web/frontend/src/pages/IndicatorLibrary.css
git commit -m "feat: 添加指标库主页面"
```

---

### Task 8: 创建汇总列表组件

**文件:**
- 创建: `web/frontend/src/components/indicator-library/SummaryList.tsx`

**接口:**
- 消费: `IndicatorLibrarySummary[]`
- 生产: 选择事件、筛选事件

- [ ] **Step 1: 创建组件目录和文件**

```bash
mkdir -p web/frontend/src/components/indicator-library
touch web/frontend/src/components/indicator-library/SummaryList.tsx
```

- [ ] **Step 2: 编写汇总列表组件（支持多维度筛选）**

```typescript
/**
 * 汇总列表组件
 * 左侧显示项目汇总信息，支持筛选和搜索
 * 筛选条件：业态、地区、交付形式、开竣工时间范围、项目名称搜索
 */
import React from 'react';
import { Input, Select, List, Tag, Empty, Space, DatePicker, Button } from 'antd';
import { SearchOutlined, FilterOutlined, ClearOutlined } from '@ant-design/icons';
import { IndicatorLibrarySummary } from '../../types';
import './SummaryList.css';

interface SummaryListProps {
  data: IndicatorLibrarySummary[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  filters: {
    category?: string;
    location?: string;
    delivery_type?: string;
    start_date_from?: string;
    start_date_to?: string;
    end_date_from?: string;
    end_date_to?: string;
    search_text?: string;
  };
  onFilterChange: (filters: {
    category?: string;
    location?: string;
    delivery_type?: string;
    start_date_from?: string;
    start_date_to?: string;
    end_date_from?: string;
    end_date_to?: string;
    search_text?: string;
  }) => void;
}

const CATEGORY_OPTIONS = [
  { label: '全部业态', value: undefined },
  { label: '住宅', value: '住宅' },
  { label: '商业', value: '商业' },
  { label: '办公', value: '办公' },
  { label: '工业', value: '工业' },
];

const DELIVERY_TYPE_OPTIONS = [
  { label: '全部交付形式', value: undefined },
  { label: '毛坯交付', value: '毛坯交付' },
  { label: '精装修', value: '精装修' },
  { label: '带装修', value: '带装修' },
  { label: '其他', value: '其他' },
];

const SummaryList: React.FC<SummaryListProps> = ({
  data,
  selectedId,
  onSelect,
  filters,
  onFilterChange,
}) => {
  const [searchText, setSearchText] = React.useState(filters.search_text || '');
  const [showFilters, setShowFilters] = React.useState(false);

  // 过滤数据（客户端二次过滤）
  const filteredData = data.filter((item) => {
    // 项目名称搜索
    if (searchText && !item.name.toLowerCase().includes(searchText.toLowerCase())) {
      return false;
    }
    // 业态过滤
    if (filters.category && item.category !== filters.category) {
      return false;
    }
    // 地区过滤
    if (filters.location && item.location !== filters.location) {
      return false;
    }
    // 开工时间范围过滤
    if (filters.start_date_from && item.start_date) {
      if (item.start_date < filters.start_date_from) return false;
    }
    if (filters.start_date_to && item.start_date) {
      if (item.start_date > filters.start_date_to) return false;
    }
    // 竣工时间范围过滤
    if (filters.end_date_from && item.end_date) {
      if (item.end_date < filters.end_date_from) return false;
    }
    if (filters.end_date_to && item.end_date) {
      if (item.end_date > filters.end_date_to) return false;
    }
    return true;
  });

  // 渲染项目项
  const renderItem = (item: IndicatorLibrarySummary) => (
    <List.Item
      key={item.id}
      className={selectedId === item.id ? 'selected' : ''}
      onClick={() => onSelect(item.id)}
    >
      <div className="summary-item">
        <div className="item-header">
          <span className="item-name">{item.name}</span>
          <Tag color="blue">{item.category}</Tag>
        </div>
        <Space className="item-meta" size="small">
          <span>{item.location}</span>
          <span>{item.structure}</span>
        </Space>
        {item.start_date && item.end_date && (
          <div className="item-period">
            {item.start_date} ~ {item.end_date}
          </div>
        )}
        <div className="item-stats">
          <span>面积: {item.area_total?.toLocaleString()}㎡</span>
          <span>造价: ¥{item.unit_cost?.toLocaleString()}/㎡</span>
        </div>
        {item.entry_date && (
          <div className="item-entry">录入: {item.entry_date}</div>
        )}
      </div>
    </List.Item>
  );

  // 应用筛选
  const handleFilterChange = (key: string, value: any) => {
    onFilterChange({ ...filters, [key]: value });
  };

  // 清空筛选
  const handleClearFilters = () => {
    setSearchText('');
    onFilterChange({
      category: undefined,
      location: undefined,
      delivery_type: undefined,
      start_date_from: undefined,
      start_date_to: undefined,
      end_date_from: undefined,
      end_date_to: undefined,
      search_text: undefined,
    });
    setShowFilters(false);
  };

  // 有筛选条件
  const hasFilters = Object.values(filters).some(v => v !== undefined && v !== '');

  return (
    <div className="summary-list">
      <div className="list-filters">
        <div className="filter-row">
          <Input
            placeholder="搜索项目名称"
            prefix={<SearchOutlined />}
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            onPressEnter={() => handleFilterChange('search_text', searchText)}
            allowClear
            onClear={() => handleFilterChange('search_text', undefined)}
          />
          <Button
            icon={showFilters ? <ClearOutlined /> : <FilterOutlined />}
            onClick={() => setShowFilters(!showFilters)}
            type={hasFilters ? 'primary' : 'default'}
          >
            {showFilters ? '收起' : '筛选'}
          </Button>
        </div>
        
        {showFilters && (
          <div className="filter-advanced">
            <div className="filter-item">
              <label>业态</label>
              <Select
                placeholder="全部业态"
                value={filters.category}
                onChange={(value) => handleFilterChange('category', value)}
                options={CATEGORY_OPTIONS}
                allowClear
                style={{ width: '100%' }}
              />
            </div>
            
            <div className="filter-item">
              <label>交付形式</label>
              <Select
                placeholder="全部交付形式"
                value={filters.delivery_type}
                onChange={(value) => handleFilterChange('delivery_type', value)}
                options={DELIVERY_TYPE_OPTIONS}
                allowClear
                style={{ width: '100%' }}
              />
            </div>
            
            <div className="filter-item">
              <label>开工时间</label>
              <Space.Compact style={{ width: '100%' }}>
                <DatePicker
                  placeholder="开始"
                  picker="month"
                  format="YYYY-MM"
                  onChange={(date) => handleFilterChange('start_date_from', date ? date.format('YYYY-MM') : undefined)}
                  allowClear
                />
                <DatePicker
                  placeholder="结束"
                  picker="month"
                  format="YYYY-MM"
                  onChange={(date) => handleFilterChange('start_date_to', date ? date.format('YYYY-MM') : undefined)}
                  allowClear
                />
              </Space.Compact>
            </div>
            
            <div className="filter-item">
              <label>竣工时间</label>
              <Space.Compact style={{ width: '100%' }}>
                <DatePicker
                  placeholder="开始"
                  picker="month"
                  format="YYYY-MM"
                  onChange={(date) => handleFilterChange('end_date_from', date ? date.format('YYYY-MM') : undefined)}
                  allowClear
                />
                <DatePicker
                  placeholder="结束"
                  picker="month"
                  format="YYYY-MM"
                  onChange={(date) => handleFilterChange('end_date_to', date ? date.format('YYYY-MM') : undefined)}
                  allowClear
                />
              </Space.Compact>
            </div>
            
            <Button size="small" onClick={handleClearFilters}>
              清空筛选
            </Button>
          </div>
        )}
        
        {hasFilters && !showFilters && (
          <div className="filter-tags">
            {filters.category && <Tag>{filters.category}</Tag>}
            {filters.delivery_type && <Tag>{filters.delivery_type}</Tag>}
            {(filters.start_date_from || filters.start_date_to) && (
              <Tag>开工: {filters.start_date_from || '-'} ~ {filters.start_date_to || '-'}</Tag>
            )}
            {(filters.end_date_from || filters.end_date_to) && (
              <Tag>竣工: {filters.end_date_from || '-'} ~ {filters.end_date_to || '-'}</Tag>
            )}
          </div>
        )}
      </div>
      
      <div className="list-count">
        共 {filteredData.length} 条数据
      </div>
      
      <List
        dataSource={filteredData}
        renderItem={renderItem}
        locale={{
          emptyText: <Empty description="暂无数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />,
        }}
      />
    </div>
  );
};

export default SummaryList;
```

- [ ] **Step 3: 创建样式文件**

```bash
touch web/frontend/src/components/indicator-library/SummaryList.css
```

```css
.summary-list {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.summary-list .list-filters {
  padding: 12px;
  border-bottom: 1px solid #f0f0f0;
  background: #fafafa;
}

.summary-list .filter-row {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}

.summary-list .filter-row .ant-input {
  flex: 1;
}

.summary-list .filter-advanced {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 12px;
  background: #fff;
  border-radius: 4px;
  border: 1px solid #f0f0f0;
}

.summary-list .filter-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.summary-list .filter-item label {
  font-size: 12px;
  color: #666;
  font-weight: 500;
}

.summary-list .filter-tags {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.summary-list .list-count {
  padding: 8px 12px;
  font-size: 12px;
  color: #999;
  text-align: center;
  border-bottom: 1px solid #f0f0f0;
}

.summary-list .ant-list {
  flex: 1;
  overflow-y: auto;
}

.summary-list .ant-list-item {
  padding: 12px 16px;
  cursor: pointer;
  border-bottom: 1px solid #f0f0f0;
  transition: background 0.2s;
}

.summary-list .ant-list-item:hover {
  background: #f5f5f5;
}

.summary-list .ant-list-item.selected {
  background: #e6f7ff;
}

.summary-item {
  width: 100%;
}

.summary-item .item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.summary-item .item-name {
  font-weight: 600;
  font-size: 14px;
}

.summary-item .item-meta {
  color: #666;
  font-size: 12px;
  margin-bottom: 4px;
}

.summary-item .item-period {
  color: #1890ff;
  font-size: 12px;
  margin-bottom: 4px;
}

.summary-item .item-stats {
  color: #666;
  font-size: 12px;
  display: flex;
  gap: 12px;
  margin-bottom: 4px;
}

.summary-item .item-entry {
  color: #999;
  font-size: 11px;
}
```

- [ ] **Step 4: 提交**

```bash
git add web/frontend/src/components/indicator-library/SummaryList.tsx web/frontend/src/components/indicator-library/SummaryList.css
git commit -m "feat: 添加指标库汇总列表组件"
```

---

### Task 9: 创建详情面板组件

**文件:**
- 创建: `web/frontend/src/components/indicator-library/DetailPanel.tsx`
- 创建: `web/frontend/src/components/indicator-library/BasicInfoSection.tsx`
- 创建: `web/frontend/src/components/indicator-library/CostSection.tsx`

**接口:**
- 消费: `indicatorLibraryAPI`, 各Section组件
- 生产: 编辑状态、保存事件

- [ ] **Step 1: 创建详情面板主文件**

```bash
touch web/frontend/src/components/indicator-library/DetailPanel.tsx
```

- [ ] **Step 2: 编写详情面板组件**

```typescript
/**
 * 详情面板组件
 * 右侧显示项目完整详情，支持查看和编辑
 */
import React, { useState, useEffect } from 'react';
import { Spin, Result, Button } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import BasicInfoSection from './BasicInfoSection';
import CostSection from './CostSection';
import SpecialCostSection from './SpecialCostSection';
import MaterialSection from './MaterialSection';
import { indicatorLibraryAPI } from '../../services/api';
import { IndicatorLibraryDetail } from '../../types';
import './DetailPanel.css';

interface DetailPanelProps {
  projectId: string | null;
  onSave: () => void;
  onCancel: () => void;
}

const DetailPanel: React.FC<DetailPanelProps> = ({ projectId, onSave, onCancel }) => {
  const [loading, setLoading] = useState(false);
  const [detail, setDetail] = useState<IndicatorLibraryDetail | null>(null);
  const [editing, setEditing] = useState(false);
  const [editData, setEditData] = useState<IndicatorLibraryDetail | null>(null);

  // 加载详情
  const loadDetail = async () => {
    if (!projectId || projectId === 'new') {
      setDetail(null);
      setEditData(null);
      setEditing(true);
      return;
    }

    setLoading(true);
    try {
      const data = await indicatorLibraryAPI.getDetail(projectId);
      setDetail(data);
      setEditData(data);
      setEditing(false);
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDetail();
  }, [projectId]);

  // 开始编辑
  const handleEdit = () => {
    setEditData(detail);
    setEditing(true);
  };

  // 取消编辑
  const handleCancel = () => {
    if (projectId === 'new') {
      onCancel();
    } else {
      setEditData(detail);
      setEditing(false);
    }
  };

  // 保存
  const handleSave = async () => {
    if (!editData) return;

    setLoading(true);
    try {
      if (projectId === 'new') {
        await indicatorLibraryAPI.create(editData);
      } else {
        await indicatorLibraryAPI.update(projectId, editData);
      }
      await loadDetail();
      setEditing(false);
      onSave();
      // message.success('保存成功');
    } catch (error) {
      // message.error('保存失败');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  // 更新编辑数据
  const handleFieldChange = (field: string, value: any) => {
    setEditData((prev) => ({ ...prev, [field]: value }));
  };

  // 空状态
  if (!projectId) {
    return (
      <div className="detail-panel-empty">
        <Result
          icon={<ReloadOutlined />}
          title="请选择项目"
          subTitle="从左侧列表选择一个项目查看详情，或新建项目"
        />
      </div>
    );
  }

  if (loading && !detail) {
    return (
      <div className="detail-panel-loading">
        <Spin />
      </div>
    );
  }

  const content = editData || detail;

  return (
    <div className="detail-panel">
      {editing ? (
        <>
          <BasicInfoSection
            data={content}
            onChange={handleFieldChange}
            editable
          />
          <CostSection data={content} onChange={handleFieldChange} editable />
          <SpecialCostSection data={content} onChange={handleFieldChange} editable />
          <MaterialSection data={content} onChange={handleFieldChange} editable />
          <div className="detail-actions">
            <Button onClick={handleCancel}>取消</Button>
            <Button type="primary" onClick={handleSave} loading={loading}>
              保存
            </Button>
          </div>
        </>
      ) : (
        <>
          <BasicInfoSection data={detail} onChange={() => {}} editable={false} />
          <CostSection data={detail} onChange={() => {}} editable={false} />
          <SpecialCostSection data={detail} onChange={() => {}} editable={false} />
          <MaterialSection data={detail} onChange={() => {}} editable={false} />
          <div className="detail-actions">
            <Button type="primary" onClick={handleEdit}>
              编辑
            </Button>
          </div>
        </>
      )}
    </div>
  );
};

export default DetailPanel;
```

- [ ] **Step 3: 创建样式文件**

```bash
touch web/frontend/src/components/indicator-library/DetailPanel.css
```

```css
.detail-panel {
  height: 100%;
  overflow-y: auto;
  padding: 24px;
}

.detail-panel-empty,
.detail-panel-loading {
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
}

.detail-actions {
  margin-top: 24px;
  padding-top: 24px;
  border-top: 1px solid #f0f0f0;
  text-align: right;
}

.detail-actions .ant-btn {
  margin-left: 8px;
}
```

- [ ] **Step 4: 创建基本信息组件**

```bash
touch web/frontend/src/components/indicator-library/BasicInfoSection.tsx
```

```typescript
/**
 * 基本信息组件
 */
import React from 'react';
import { Form, Input, Select, DatePicker, Row, Col } from 'antd';
import { IndicatorLibraryDetail } from '../../types';
import dayjs from 'dayjs';

const { Option } = Select;

interface BasicInfoSectionProps {
  data: IndicatorLibraryDetail | null;
  onChange: (field: string, value: any) => void;
  editable: boolean;
}

const CATEGORY_OPTIONS = ['住宅', '商业', '办公', '工业'];

const BasicInfoSection: React.FC<BasicInfoSectionProps> = ({ data, onChange, editable }) => {
  if (!data) return null;

  return (
    <div className="detail-section">
      <h3 className="section-title">基本信息</h3>
      <Form layout="vertical">
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item label="项目名称">
              <Input
                value={data.name}
                onChange={(e) => onChange('name', e.target.value)}
                disabled={!editable}
                placeholder="请输入项目名称"
              />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item label="业态">
              <Select
                value={data.category}
                onChange={(value) => onChange('category', value)}
                disabled={!editable}
                placeholder="请选择业态"
              >
                {CATEGORY_OPTIONS.map((cat) => (
                  <Option key={cat} value={cat}>
                    {cat}
                  </Option>
                ))}
              </Select>
            </Form.Item>
          </Col>
        </Row>
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item label="项目所在地">
              <Input
                value={data.location}
                onChange={(e) => onChange('location', e.target.value)}
                disabled={!editable}
                placeholder="请输入项目所在地"
              />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item label="结构形式">
              <Input
                value={data.structure}
                onChange={(e) => onChange('structure', e.target.value)}
                disabled={!editable}
                placeholder="请输入结构形式"
              />
            </Form.Item>
          </Col>
        </Row>
        <Row gutter={16}>
          <Col span={8}>
            <Form.Item label="开工时间">
              <Input
                value={data.start_date || ''}
                onChange={(e) => onChange('start_date', e.target.value)}
                disabled={!editable}
                placeholder="YYYY-MM"
              />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item label="竣工时间">
              <Input
                value={data.end_date || ''}
                onChange={(e) => onChange('end_date', e.target.value)}
                disabled={!editable}
                placeholder="YYYY-MM"
              />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item label="交付形式">
              <Input
                value={data.delivery_type || ''}
                onChange={(e) => onChange('delivery_type', e.target.value)}
                disabled={!editable}
                placeholder="请输入交付形式"
              />
            </Form.Item>
          </Col>
        </Row>
        <Row gutter={16}>
          <Col span={8}>
            <Form.Item label="地上层数">
              <Input
                type="number"
                value={data.floor_above}
                onChange={(e) => onChange('floor_above', Number(e.target.value))}
                disabled={!editable}
              />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item label="地下层数">
              <Input
                type="number"
                value={data.floor_below}
                onChange={(e) => onChange('floor_below', Number(e.target.value))}
                disabled={!editable}
              />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item label="檐高(m)">
              <Input
                type="number"
                value={data.height}
                onChange={(e) => onChange('height', Number(e.target.value))}
                disabled={!editable}
              />
            </Form.Item>
          </Col>
        </Row>
        <Row gutter={16}>
          <Col span={8}>
            <Form.Item label="总建筑面积(㎡)">
              <Input
                type="number"
                value={data.area_total}
                onChange={(e) => onChange('area_total', Number(e.target.value))}
                disabled={!editable}
              />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item label="地上建筑面积(㎡)">
              <Input
                type="number"
                value={data.area_above}
                onChange={(e) => onChange('area_above', Number(e.target.value))}
                disabled={!editable}
              />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item label="地下建筑面积(㎡)">
              <Input
                type="number"
                value={data.area_below}
                onChange={(e) => onChange('area_below', Number(e.target.value))}
                disabled={!editable}
              />
            </Form.Item>
          </Col>
        </Row>
      </Form>
    </div>
  );
};

export default BasicInfoSection;
```

- [ ] **Step 5: 创建造价组件**

```bash
touch web/frontend/src/components/indicator-library/CostSection.tsx
```

```typescript
/**
 * 造价指标组件
 */
import React from 'react';
import { Form, InputNumber, Collapse, Row, Col } from 'antd';
import { IndicatorLibraryDetail } from '../../types';

const { Panel } = Collapse;

interface CostSectionProps {
  data: IndicatorLibraryDetail | null;
  onChange: (field: string, value: any) => void;
  editable: boolean;
}

const CostSection: React.FC<CostSectionProps> = ({ data, onChange, editable }) => {
  if (!data) return null;

  return (
    <div className="detail-section">
      <Collapse defaultActiveKey={['1']}>
        <Panel header="造价指标" key="1">
          <Form layout="vertical">
            <Row gutter={16}>
              <Col span={8}>
                <Form.Item label="平米造价(元/㎡)">
                  <InputNumber
                    value={data.unit_cost}
                    onChange={(value) => onChange('unit_cost', value)}
                    disabled={!editable}
                    style={{ width: '100%' }}
                  />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item label="总造价(元)">
                  <InputNumber
                    value={data.total_cost}
                    onChange={(value) => onChange('total_cost', value)}
                    disabled={!editable}
                    style={{ width: '100%' }}
                  />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item label="结构平米造价">
                  <InputNumber
                    value={data.unit_structure}
                    onChange={(value) => onChange('unit_structure', value)}
                    disabled={!editable}
                    style={{ width: '100%' }}
                  />
                </Form.Item>
              </Col>
            </Row>
          </Form>
        </Panel>
        <Panel header="地上/地下造价分解" key="2">
          <Form layout="vertical">
            <Row gutter={16}>
              <Col span={6}>
                <Form.Item label="地上土建造价">
                  <InputNumber
                    value={data.cost_above_structure}
                    onChange={(value) => onChange('cost_above_structure', value)}
                    disabled={!editable}
                    style={{ width: '100%' }}
                  />
                </Form.Item>
              </Col>
              <Col span={6}>
                <Form.Item label="地上安装造价">
                  <InputNumber
                    value={data.cost_above_installation}
                    onChange={(value) => onChange('cost_above_installation', value)}
                    disabled={!editable}
                    style={{ width: '100%' }}
                  />
                </Form.Item>
              </Col>
              <Col span={6}>
                <Form.Item label="地下土建造价">
                  <InputNumber
                    value={data.cost_underground_structure}
                    onChange={(value) => onChange('cost_underground_structure', value)}
                    disabled={!editable}
                    style={{ width: '100%' }}
                  />
                </Form.Item>
              </Col>
              <Col span={6}>
                <Form.Item label="地下安装造价">
                  <InputNumber
                    value={data.cost_underground_installation}
                    onChange={(value) => onChange('cost_underground_installation', value)}
                    disabled={!editable}
                    style={{ width: '100%' }}
                  />
                </Form.Item>
              </Col>
            </Row>
          </Form>
        </Panel>
      </Collapse>
    </div>
  );
};

export default CostSection;
```

- [ ] **Step 6: 创建专项工程组件**

```bash
touch web/frontend/src/components/indicator-library/SpecialCostSection.tsx
```

```typescript
/**
 * 专项工程造价组件
 */
import React from 'react';
import { Form, InputNumber, Collapse, Row, Col } from 'antd';
import { IndicatorLibraryDetail } from '../../types';

const { Panel } = Collapse;

interface SpecialCostSectionProps {
  data: IndicatorLibraryDetail | null;
  onChange: (field: string, value: any) => void;
  editable: boolean;
}

const SPECIAL_ITEMS = [
  { key: 'pile', name: '桩基' },
  { key: 'foundation_support', name: '基坑支护' },
  { key: 'curtain_wall', name: '幕墙' },
  { key: 'decoration', name: '精装修' },
  { key: 'exterior_insulation', name: '外保温+涂料' },
  { key: 'exterior_windows', name: '外门窗' },
  { key: 'water_drainage', name: '室内给排水' },
  { key: 'heating', name: '采暖' },
];

const SpecialCostSection: React.FC<SpecialCostSectionProps> = ({ data, onChange, editable }) => {
  if (!data) return null;

  return (
    <div className="detail-section">
      <Collapse defaultActiveKey={[]}>
        <Panel header="专项工程造价" key="1">
          <Form layout="vertical">
            {SPECIAL_ITEMS.map((item) => (
              <Row gutter={16} key={item.key}>
                <Col span={12}>
                  <Form.Item label={`${item.name}造价(元)`}>
                    <InputNumber
                      value={data[`cost_${item.key}` as keyof IndicatorLibraryDetail]}
                      onChange={(value) => onChange(`cost_${item.key}`, value)}
                      disabled={!editable}
                      style={{ width: '100%' }}
                    />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item label={`${item.name}平米造价(元/㎡)`}>
                    <InputNumber
                      value={data[`unit_cost_${item.key}` as keyof IndicatorLibraryDetail]}
                      onChange={(value) => onChange(`unit_cost_${item.key}`, value)}
                      disabled={!editable}
                      style={{ width: '100%' }}
                    />
                  </Form.Item>
                </Col>
              </Row>
            ))}
          </Form>
        </Panel>
      </Collapse>
    </div>
  );
};

export default SpecialCostSection;
```

- [ ] **Step 7: 创建材料用量组件**

```bash
touch web/frontend/src/components/indicator-library/MaterialSection.tsx
```

```typescript
/**
 * 材料用量组件
 */
import React from 'react';
import { Form, InputNumber, Collapse, Row, Col } from 'antd';
import { IndicatorLibraryDetail } from '../../types';

const { Panel } = Collapse;

interface MaterialSectionProps {
  data: IndicatorLibraryDetail | null;
  onChange: (field: string, value: any) => void;
  editable: boolean;
}

const MaterialSection: React.FC<MaterialSectionProps> = ({ data, onChange, editable }) => {
  if (!data) return null;

  return (
    <div className="detail-section">
      <Collapse defaultActiveKey={[]}>
        <Panel header="材料用量指标" key="1">
          <Form layout="vertical">
            {/* 地上主体材料 */}
            <Row gutter={16}>
              <Col span={8}>
                <Form.Item label="地上砼用量(m³)">
                  <InputNumber
                    value={data.above_concrete}
                    onChange={(value) => onChange('above_concrete', value)}
                    disabled={!editable}
                    style={{ width: '100%' }}
                  />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item label="地上砼平米含量(m³/㎡)">
                  <InputNumber
                    value={data.above_concrete_unit}
                    onChange={(value) => onChange('above_concrete_unit', value)}
                    disabled={!editable}
                    style={{ width: '100%' }}
                  />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item label="地上钢筋用量(t)">
                  <InputNumber
                    value={data.above_rebar}
                    onChange={(value) => onChange('above_rebar', value)}
                    disabled={!editable}
                    style={{ width: '100%' }}
                  />
                </Form.Item>
              </Col>
            </Row>
            {/* 地下主体材料 */}
            <Row gutter={16}>
              <Col span={8}>
                <Form.Item label="地下砼用量(m³)">
                  <InputNumber
                    value={data.underground_concrete}
                    onChange={(value) => onChange('underground_concrete', value)}
                    disabled={!editable}
                    style={{ width: '100%' }}
                  />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item label="地下砼平米含量(m³/㎡)">
                  <InputNumber
                    value={data.underground_concrete_unit}
                    onChange={(value) => onChange('underground_concrete_unit', value)}
                    disabled={!editable}
                    style={{ width: '100%' }}
                  />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item label="地下钢筋用量(t)">
                  <InputNumber
                    value={data.underground_rebar}
                    onChange={(value) => onChange('underground_rebar', value)}
                    disabled={!editable}
                    style={{ width: '100%' }}
                  />
                </Form.Item>
              </Col>
            </Row>
          </Form>
        </Panel>
      </Collapse>
    </div>
  );
};

export default MaterialSection;
```

- [ ] **Step 8: 添加详情面板样式**

更新 `DetailPanel.css`:

```css
.detail-section {
  margin-bottom: 24px;
  padding-bottom: 24px;
  border-bottom: 1px solid #f0f0f0;
}

.detail-section:last-child {
  border-bottom: none;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 16px;
  color: #333;
}

.detail-section .ant-form {
  margin-bottom: 0;
}

.detail-section .ant-form-item {
  margin-bottom: 12px;
}

.detail-section .ant-collapse {
  background: transparent;
}

.detail-section .ant-collapse-header {
  font-weight: 600;
}
```

- [ ] **Step 9: 提交**

```bash
git add web/frontend/src/components/indicator-library/
git commit -m "feat: 添加指标库详情面板及相关Section组件"
```

---

### Task 10: 创建导入预览组件

**文件:**
- 创建: `web/frontend/src/components/indicator-library/ImportPreview.tsx`

**接口:**
- 消费: `Upload`, `indicatorLibraryAPI`
- 生产: 导入成功事件

- [ ] **Step 1: 创建导入预览组件**

```bash
touch web/frontend/src/components/indicator-library/ImportPreview.tsx
```

- [ ] **Step 2: 编写导入预览组件**

```typescript
/**
 * 导入预览组件
 * 上传Excel文件，预览解析结果，确认后导入
 */
import React, { useState } from 'react';
import {
  Modal,
  Upload,
  Button,
  Table,
  Tag,
  message,
  Alert,
  Space,
  Progress,
} from 'antd';
import { UploadOutlined, CheckCircleOutlined, WarningOutlined, CloseCircleOutlined } from '@ant-design/icons';
import type { UploadFile } from 'antd';
import { indicatorLibraryAPI } from '../../services/api';
import './ImportPreview.css';

interface ImportPreviewProps {
  visible: boolean;
  onSuccess: () => void;
  onCancel: () => void;
}

const ImportPreview: React.FC<ImportPreviewProps> = ({ visible, onSuccess, onCancel }) => {
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [previewData, setPreviewData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [importing, setImporting] = useState(false);

  // 上传并预览
  const handlePreview = async () => {
    if (fileList.length === 0) {
      message.warning('请先选择文件');
      return;
    }

    const file = fileList[0];
    setLoading(true);

    try {
      const formData = new FormData();
      formData.append('file', file.originFileObj as File);

      const response = await fetch('/api/indicator-library/preview', {
        method: 'POST',
        body: formData,
      });
      const data = await response.json();

      setPreviewData(data);
    } catch (error) {
      message.error('解析失败，请检查文件格式');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  // 确认导入
  const handleImport = async () => {
    if (!previewData || previewData.error_count > 0) {
      message.warning('存在错误数据，请修正后再导入');
      return;
    }

    setImporting(true);

    try {
      const file = fileList[0];
      const formData = new FormData();
      formData.append('file', file.originFileObj as File);

      const response = await fetch('/api/indicator-library/import', {
        method: 'POST',
        body: formData,
      });
      const data = await response.json();

      if (data.success) {
        message.success(`成功导入 ${data.imported} 条数据`);
        onSuccess();
      } else {
        message.error('导入失败');
      }
    } catch (error) {
      message.error('导入失败');
      console.error(error);
    } finally {
      setImporting(false);
    }
  };

  // 重置
  const handleReset = () => {
    setFileList([]);
    setPreviewData(null);
  };

  // 关闭
  const handleClose = () => {
    handleReset();
    onCancel();
  };

  const columns = [
    {
      title: '序号',
      dataIndex: 'index',
      width: 60,
    },
    {
      title: '项目名称',
      dataIndex: 'name',
      width: 150,
    },
    {
      title: '业态',
      dataIndex: 'category',
      width: 80,
    },
    {
      title: '地区',
      dataIndex: 'location',
      width: 100,
    },
    {
      title: '平米造价',
      dataIndex: 'unit_cost',
      width: 100,
      render: (value: number) => value?.toLocaleString(),
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 80,
      render: (status: string) => {
        if (status === 'valid') {
          return <Tag color="success" icon={<CheckCircleOutlined />}>正常</Tag>;
        } else if (status === 'warning') {
          return <Tag color="warning" icon={<WarningOutlined />}>警告</Tag>;
        } else {
          return <Tag color="error" icon={<CloseCircleOutlined />}>错误</Tag>;
        }
      },
    },
    {
      title: '问题',
      key: 'issues',
      render: (_: any, record: any) => (
        <Space direction="vertical" size="small">
          {record.warnings?.map((w: string, i: number) => (
            <span key={`w-${i}`} style={{ color: '#faad14' }}>
              警告: {w}
            </span>
          ))}
          {record.errors?.map((e: string, i: number) => (
            <span key={`e-${i}`} style={{ color: '#ff4d4f' }}>
              错误: {e}
            </span>
          ))}
        </Space>
      ),
    },
  ];

  return (
    <Modal
      title="Excel导入"
      open={visible}
      onCancel={handleClose}
      width={900}
      footer={[
        <Button key="cancel" onClick={handleClose}>
          取消
        </Button>,
        <Button
          key="import"
          type="primary"
          onClick={handleImport}
          loading={importing}
          disabled={!previewData || previewData.error_count > 0}
        >
          确认导入
        </Button>,
      ]}
    >
      <div className="import-preview">
        {!previewData ? (
          <div className="upload-section">
            <Upload
              fileList={fileList}
              onChange={({ fileList }) => setFileList(fileList)}
              beforeUpload={() => false}
              accept=".xlsx,.xls"
              maxCount={1}
            >
              <Button icon={<UploadOutlined />}>选择Excel文件</Button>
            </Upload>
            <Button
              type="primary"
              onClick={handlePreview}
              loading={loading}
              disabled={fileList.length === 0}
              style={{ marginLeft: 8 }}
            >
              解析预览
            </Button>
            <Alert
              message="Excel文件说明"
              description="文件需包含'汇总'和'明细'两个工作表"
              type="info"
              showIcon
              style={{ marginTop: 16 }}
            />
          </div>
        ) : (
          <div className="preview-section">
            <div className="preview-stats">
              <Space size="large">
                <span>
                  共识别 <strong>{previewData.total}</strong> 个项目
                </span>
                <Tag color="success">正常: {previewData.valid_count}</Tag>
                <Tag color="warning">警告: {previewData.warning_count}</Tag>
                <Tag color="error">错误: {previewData.error_count}</Tag>
              </Space>
              <Button size="small" onClick={handleReset}>
                重新上传
              </Button>
            </div>

            {previewData.error_count > 0 && (
              <Alert
                message={`存在 ${previewData.error_count} 个错误项目，无法导入`}
                type="error"
                showIcon
                style={{ marginBottom: 16 }}
              />
            )}

            <Table
              columns={columns}
              dataSource={previewData.items}
              rowKey="index"
              size="small"
              pagination={{ pageSize: 10 }}
              scroll={{ y: 400 }}
            />
          </div>
        )}
      </div>
    </Modal>
  );
};

export default ImportPreview;
```

- [ ] **Step 3: 创建样式文件**

```bash
touch web/frontend/src/components/indicator-library/ImportPreview.css
```

```css
.import-preview {
  padding: 8px 0;
}

.import-preview .upload-section {
  text-align: center;
  padding: 32px 0;
}

.import-preview .preview-section {
  margin-top: 16px;
}

.import-preview .preview-stats {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding: 12px;
  background: #f5f5f5;
  border-radius: 4px;
}
```

- [ ] **Step 4: 提交**

```bash
git add web/frontend/src/components/indicator-library/ImportPreview.tsx web/frontend/src/components/indicator-library/ImportPreview.css
git commit -m "feat: 添加Excel导入预览组件"
```

---

### Task 11: 添加API服务和类型定义

**文件:**
- 修改: `web/frontend/src/services/api.ts`
- 创建: `web/frontend/src/types/indicator.ts`

**接口:**
- 消费: 无
- 生产: `indicatorLibraryAPI` 对象

- [ ] **Step 1: 创建类型定义文件**

```bash
mkdir -p web/frontend/src/types
touch web/frontend/src/types/indicator.ts
```

```typescript
/**
 * 指标库类型定义
 */
export interface IndicatorLibrarySummary {
  id: string;
  name: string;
  category: string;
  location: string;
  structure: string;
  start_date?: string;
  end_date?: string;
  area_total?: number;
  unit_cost?: number;
  entry_date?: string;
  updated_at: string;
}

export interface IndicatorLibraryDetail {
  id?: string;
  name: string;
  category: string;
  location: string;
  structure: string;
  delivery_type?: string;
  foundation_type?: string;
  start_date?: string;
  end_date?: string;
  floor_above?: number;
  floor_below?: number;
  height?: number;
  area_total?: number;
  area_above?: number;
  area_below?: number;
  unit_cost?: number;
  total_cost?: number;
  unit_structure?: number;
  unit_installation?: number;
  cost_above_structure?: number;
  cost_above_installation?: number;
  unit_cost_above_structure?: number;
  unit_cost_above_installation?: number;
  cost_underground_structure?: number;
  cost_underground_installation?: number;
  unit_cost_underground_structure?: number;
  unit_cost_underground_installation?: number;
  cost_measures?: number;
  unit_cost_measures?: number;
  cost_outdoor?: number;
  unit_cost_outdoor?: number;
  cost_pile?: number;
  unit_cost_pile?: number;
  cost_foundation_support?: number;
  unit_cost_foundation_support?: number;
  cost_curtain_wall?: number;
  unit_cost_curtain_wall?: number;
  cost_decoration?: number;
  unit_cost_decoration?: number;
  cost_exterior_insulation?: number;
  unit_cost_exterior_insulation?: number;
  cost_exterior_windows?: number;
  unit_cost_exterior_windows?: number;
  cost_water_drainage?: number;
  unit_cost_water_drainage?: number;
  cost_heating?: number;
  unit_cost_heating?: number;
  cost_electrical?: number;
  unit_cost_electrical?: number;
  cost_hvac?: number;
  unit_cost_hvac?: number;
  above_concrete?: number;
  above_concrete_unit?: number;
  above_rebar?: number;
  above_rebar_unit?: number;
  above_formwork?: number;
  above_formwork_unit?: number;
  underground_concrete?: number;
  underground_concrete_unit?: number;
  underground_rebar?: number;
  underground_rebar_unit?: number;
  underground_formwork?: number;
  underground_formwork_unit?: number;
  source?: string;
  source_file?: string;
  remarks?: string;
  entry_date?: string;
  created_at?: string;
  updated_at?: string;
}

export interface ImportPreviewResult {
  total: number;
  valid_count: number;
  warning_count: number;
  error_count: number;
  items: ImportPreviewItem[];
}

export interface ImportPreviewItem {
  index: number;
  name: string;
  category?: string;
  location?: string;
  unit_cost?: number;
  status: 'valid' | 'warning' | 'error';
  warnings: string[];
  errors: string[];
}

export interface ImportResult {
  success: boolean;
  imported: number;
  total: number;
  warnings: Array<{
    project: string;
    field: string;
    message: string;
  }>;
  errors: string[];
}

export interface ValidationResult {
  passed: boolean;
  warnings: Array<{
    field: string;
    message: string;
    severity: string;
  }>;
  errors: Array<{
    field: string;
    message: string;
    severity: string;
  }>;
  checks: Record<string, string>;
}
```

- [ ] **Step 2: 查看并修改api.ts文件**

```bash
head -50 web/frontend/src/services/api.ts
```

- [ ] **Step 3: 在api.ts中添加指标库API**

在 `web/frontend/src/services/api.ts` 中添加以下内容：

```typescript
// 在文件顶部添加类型导入
import type {
  IndicatorLibrarySummary,
  IndicatorLibraryDetail,
  ImportPreviewResult,
  ImportResult,
  ValidationResult,
} from '../types/indicator';

// 在API对象中添加指标库API方法
export const indicatorLibraryAPI = {
  // 获取汇总列表
  getSummary: async (params: {
    category?: string;
    location?: string;
    limit?: number;
  }): Promise<IndicatorLibrarySummary[]> => {
    const searchParams = new URLSearchParams();
    if (params.category) searchParams.append('category', params.category);
    if (params.location) searchParams.append('location', params.location);
    searchParams.append('limit', String(params.limit || 100));

    const response = await fetch(`/api/indicator-library/summary?${searchParams}`);
    if (!response.ok) throw new Error('获取汇总列表失败');
    return response.json();
  },

  // 获取项目详情
  getDetail: async (id: string): Promise<IndicatorLibraryDetail> => {
    const response = await fetch(`/api/indicator-library/${id}`);
    if (!response.ok) throw new Error('获取项目详情失败');
    return response.json();
  },

  // 创建项目
  create: async (data: Partial<IndicatorLibraryDetail>): Promise<IndicatorLibraryDetail> => {
    const response = await fetch('/api/indicator-library/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error('创建项目失败');
    return response.json();
  },

  // 更新项目
  update: async (id: string, data: Partial<IndicatorLibraryDetail>): Promise<IndicatorLibraryDetail> => {
    const response = await fetch(`/api/indicator-library/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error('更新项目失败');
    return response.json();
  },

  // 删除项目
  delete: async (id: string): Promise<{ success: boolean }> => {
    const response = await fetch(`/api/indicator-library/${id}`, {
      method: 'DELETE',
    });
    if (!response.ok) throw new Error('删除项目失败');
    return response.json();
  },

  // 数据验证
  validate: async (data: Partial<IndicatorLibraryDetail>): Promise<ValidationResult> => {
    const response = await fetch('/api/indicator-library/validate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error('验证失败');
    return response.json();
  },

  // 导出Excel
  exportExcel: async (category?: string): Promise<void> => {
    const params = category ? `?category=${category}` : '';
    const response = await fetch(`/api/indicator-library/export${params}`);
    if (!response.ok) throw new Error('导出失败');

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `indicator_library_${new Date().getTime()}.xlsx`;
    a.click();
    window.URL.revokeObjectURL(url);
  },

  // 获取统计信息
  getStats: async (): Promise<Record<string, any>> => {
    const response = await fetch('/api/indicator-library/stats/overview');
    if (!response.ok) throw new Error('获取统计信息失败');
    return response.json();
  },
};
```

- [ ] **Step 4: 提交**

```bash
git add web/frontend/src/types/indicator.ts web/frontend/src/services/api.ts
git commit -m "feat: 添加指标库API服务和类型定义"
```

---

### Task 12: 添加路由配置

**文件:**
- 修改: 路由配置文件（查找App.tsx或路由文件）

- [ ] **Step 1: 查找路由配置文件**

```bash
find web/frontend/src -name "*route*" -o -name "App.tsx" -o -name "main.tsx" 2>/dev/null | head -10
```

- [ ] **Step 2: 添加路由配置**

在找到的路由配置文件中添加指标库页面路由：

```typescript
import IndicatorLibrary from './pages/IndicatorLibrary';

// 在路由配置中添加
{
  path: '/indicator-library',
  element: <IndicatorLibrary />,
},
```

- [ ] **Step 3: 提交**

```bash
git add web/frontend/src/App.tsx  # 或实际的路由配置文件
git commit -m "feat: 添加指标库页面路由"
```

---

## 第八阶段：测试和部署

### Task 13: 端到端测试

- [ ] **Step 1: 启动后端服务**

```bash
cd web/backend
python main.py
```

- [ ] **Step 2: 启动前端开发服务器**

```bash
cd web/frontend
npm run dev
```

- [ ] **Step 3: 手动测试功能**

1. 访问指标库页面
2. 测试新建项目
3. 测试编辑保存
4. 测试Excel导入（使用原始Excel文件）
5. 测试筛选和搜索
6. 测试导出功能

- [ ] **Step 4: 检查API文档**

访问 http://localhost:8000/docs 查看API文档

- [ ] **Step 5: 运行所有测试**

```bash
cd web/backend
pytest tests/ -v
```

---

### Task 14: 构建前端

- [ ] **Step 1: 构建前端**

```bash
cd web/frontend
npm run build
```

- [ ] **Step 2: 检查构建输出**

```bash
ls -la web/frontend/dist/
```

Expected: dist目录包含index.html和assets目录

- [ ] **Step 3: 测试生产版本**

```bash
cd web/backend
python main.py
# 访问 http://localhost:8000
```

---

## 完成检查清单

在实现完成后，确认以下事项：

- [ ] 数据库表结构已扩展，新字段已添加
- [ ] 所有API端点可正常访问（/docs页面验证）
- [ ] Excel解析功能正常，能正确读取汇总表和明细表
- [ ] 三级验证功能正常（基础、逻辑、参考范围）
- [ ] 前端页面正常显示，主从布局正确
- [ ] 新建、编辑、保存功能正常
- [ ] Excel导入预览和确认导入功能正常
- [ ] 导出功能正常
- [ ] 所有测试通过
- [ ] 前端构建成功
- [ ] 生产环境测试通过

---

## 预估工作量

- Task 1: 数据库扩展 - 30分钟
- Task 2: 数据模型 - 20分钟
- Task 3: 数据验证服务 - 45分钟
- Task 4: Excel解析服务 - 60分钟
- Task 5: 业务服务 - 30分钟
- Task 6: API路由 - 45分钟
- Task 7-12: 前端组件 - 180分钟（3小时）
- Task 13-14: 测试构建 - 30分钟

**总计: 约7-8小时**
