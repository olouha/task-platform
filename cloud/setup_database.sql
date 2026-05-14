-- TaskPlatform 工程调差计算系统数据库

-- 1. 用户表
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    created_at TIMESTAMP DEFAULT now()
);

-- 2. 材料分类表
CREATE TABLE material_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parent_id UUID,
    name TEXT NOT NULL,
    icon TEXT,
    color TEXT,
    sort_order INT DEFAULT 0
);

-- 3. 材料明细表
CREATE TABLE materials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category_id UUID,
    name TEXT NOT NULL,
    spec TEXT,
    unit TEXT,
    base_price DECIMAL(15,2),
    source_id UUID,
    is_adjusted BOOLEAN DEFAULT true,
    adjustment_threshold DECIMAL(5,2) DEFAULT 5.00,
    created_at TIMESTAMP DEFAULT now()
);

-- 4. 价格来源配置表
CREATE TABLE price_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    website_name TEXT,
    website_url TEXT,
    material_category TEXT NOT NULL,
    price_url TEXT NOT NULL,
    selector TEXT,
    xpath TEXT,
    is_active BOOLEAN DEFAULT true,
    interval_minutes INT DEFAULT 1440,
    last_fetched_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT now()
);

-- 5. 价格历史记录表
CREATE TABLE price_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    material_id UUID,
    source_id UUID,
    price DECIMAL(15,4) NOT NULL,
    unit TEXT,
    recorded_date DATE NOT NULL,
    raw_data JSONB,
    fetch_status TEXT,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT now()
);

-- 6. 项目表
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    contract_no TEXT,
    contract_date DATE,
    base_date DATE,
    completion_date DATE,
    total_value DECIMAL(15,2),
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT now()
);

-- 7. 项目材料表
CREATE TABLE project_materials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    material_id UUID,
    material_name TEXT,
    spec TEXT,
    unit TEXT,
    quantity DECIMAL(15,4),
    contract_price DECIMAL(15,2),
    base_price DECIMAL(15,2),
    adjustment_type TEXT DEFAULT 'adjustable',
    threshold DECIMAL(5,2) DEFAULT 5.00,
    source_id UUID,
    sort_order INT DEFAULT 0
);

-- 8. 施工阶段表
CREATE TABLE construction_phases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    phase_name TEXT NOT NULL,
    start_date DATE,
    end_date DATE,
    days INT,
    sort_order INT DEFAULT 0
);

-- 9. 调差记录表
CREATE TABLE adjustment_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    material_id UUID,
    phase_id UUID,
    phase_name TEXT,
    base_price DECIMAL(15,4),
    current_price DECIMAL(15,4),
    change_rate DECIMAL(10,4),
    adjustment_amount DECIMAL(15,2),
    calculated_at TIMESTAMP DEFAULT now()
);

-- 10. 指标分类表
CREATE TABLE indicator_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    icon TEXT,
    color TEXT,
    sort_order INT DEFAULT 0
);

-- 11. 指标表
CREATE TABLE indicators (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category_id UUID REFERENCES indicator_categories(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    unit TEXT,
    target_value DECIMAL(15,4),
    target_type TEXT,
    warning_threshold DECIMAL(15,4),
    current_value DECIMAL(15,4),
    data_type TEXT DEFAULT 'number',
    status TEXT DEFAULT 'normal',
    updated_at TIMESTAMP DEFAULT now()
);

-- 12. 指标记录表
CREATE TABLE indicator_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    indicator_id UUID REFERENCES indicators(id) ON DELETE CASCADE,
    current_value DECIMAL(15,4),
    recorded_by UUID REFERENCES users(id),
    recorded_at TIMESTAMP DEFAULT now(),
    note TEXT
);

-- 创建索引
CREATE INDEX idx_price_history_material ON price_history(material_id);
CREATE INDEX idx_price_history_date ON price_history(recorded_date);
CREATE INDEX idx_price_history_source ON price_history(source_id);
CREATE INDEX idx_project_materials_project ON project_materials(project_id);
CREATE INDEX idx_adjustment_records_project ON adjustment_records(project_id);
CREATE INDEX idx_adjustment_records_phase ON adjustment_records(phase_id);
