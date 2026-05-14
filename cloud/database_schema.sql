-- TaskPlatform 工程调差计算系统数据库

-- 1. 用户表（简化版）
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    created_at TIMESTAMP DEFAULT now()
);

-- 2. 材料分类表
CREATE TABLE IF NOT EXISTS material_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parent_id UUID,
    name TEXT NOT NULL,
    icon TEXT,
    color TEXT,
    sort_order INT DEFAULT 0
);

-- 3. 材料明细表
CREATE TABLE IF NOT EXISTS materials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category_id UUID REFERENCES material_categories(id),
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
CREATE TABLE IF NOT EXISTS price_sources (
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
CREATE TABLE IF NOT EXISTS price_history (
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
CREATE TABLE IF NOT EXISTS projects (
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
CREATE TABLE IF NOT EXISTS project_materials (
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
CREATE TABLE IF NOT EXISTS construction_phases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    phase_name TEXT NOT NULL,
    start_date DATE,
    end_date DATE,
    days INT,
    sort_order INT DEFAULT 0
);

-- 9. 调差记录表
CREATE TABLE IF NOT EXISTS adjustment_records (
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
CREATE TABLE IF NOT EXISTS indicator_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    icon TEXT,
    color TEXT,
    sort_order INT DEFAULT 0
);

-- 11. 指标表
CREATE TABLE IF NOT EXISTS indicators (
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
CREATE TABLE IF NOT EXISTS indicator_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    indicator_id UUID REFERENCES indicators(id) ON DELETE CASCADE,
    current_value DECIMAL(15,4),
    recorded_by UUID REFERENCES users(id),
    recorded_at TIMESTAMP DEFAULT now(),
    note TEXT
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_price_history_material ON price_history(material_id);
CREATE INDEX IF NOT EXISTS idx_price_history_date ON price_history(recorded_date);
CREATE INDEX IF NOT EXISTS idx_price_history_source ON price_history(source_id);
CREATE INDEX IF NOT EXISTS idx_project_materials_project ON project_materials(project_id);
CREATE INDEX IF NOT EXISTS idx_adjustment_records_project ON adjustment_records(project_id);
CREATE INDEX IF NOT EXISTS idx_adjustment_records_phase ON adjustment_records(phase_id);

-- 插入默认材料分类
INSERT INTO material_categories (id, name, icon, color, sort_order) VALUES
    ('11111111-1111-1111-1111-111111111111', '钢筋类', '🔩', '#3498db', 1),
    ('22222222-2222-2222-2222-222222222222', '混凝土类', '🧱', '#e74c3c', 2),
    ('33333333-3333-3333-3333-333333333333', '金属类', '🔧', '#f39c12', 3),
    ('44444444-4444-4444-4444-444444444444', '有色金属类', '🪙', '#9b59b6', 4);

-- 插入默认材料
INSERT INTO materials (id, category_id, name, spec, unit) VALUES
    ('aaaa1111-1111-1111-1111-111111111111', '11111111-1111-1111-1111-111111111111', 'HRB400螺纹钢筋', '12-25mm', '吨'),
    ('aaaa2222-2222-2222-2222-222222222222', '11111111-1111-1111-1111-111111111111', 'HPB300光圆钢筋', '8-10mm', '吨'),
    ('aaaa3333-3333-3333-3333-333333333333', '11111111-1111-1111-1111-111111111111', '钢绞线', '15.2mm', '吨'),
    ('aaaa4444-4444-4444-4444-444444444444', '11111111-1111-1111-1111-111111111111', '钢丝绳', '6x19', '吨'),
    ('bbbb1111-1111-1111-1111-111111111111', '22222222-2222-2222-2222-222222222222', 'C15混凝土', '普通', 'm³'),
    ('bbbb2222-2222-2222-2222-222222222222', '22222222-2222-2222-2222-222222222222', 'C20混凝土', '普通', 'm³'),
    ('bbbb3333-3333-3333-3333-333333333333', '22222222-2222-2222-2222-222222222222', 'C25混凝土', '普通', 'm³'),
    ('bbbb4444-4444-4444-4444-444444444444', '22222222-2222-2222-2222-222222222222', 'C30混凝土', '普通', 'm³'),
    ('bbbb5555-5555-5555-5555-555555555555', '22222222-2222-2222-2222-222222222222', 'C35混凝土', '普通', 'm³'),
    ('bbbb6666-6666-6666-6666-666666666666', '22222222-2222-2222-2222-222222222222', 'C40混凝土', '普通', 'm³'),
    ('cccc1111-1111-1111-1111-111111111111', '33333333-3333-3333-3333-333333333333', '304不锈钢', '2B卷板', '吨'),
    ('cccc2222-2222-2222-2222-222222222222', '33333333-3333-3333-3333-333333333333', '316不锈钢', '2B卷板', '吨'),
    ('cccc3333-3333-3333-3333-333333333333', '44444444-4444-4444-4444-444444444444', '铝锭', 'A00', '吨'),
    ('cccc4444-4444-4444-4444-444444444444', '44444444-4444-4444-4444-444444444444', '铜锭', '1#电解铜', '吨'),
    ('cccc5555-5555-5555-5555-555555555555', '44444444-4444-4444-4444-444444444444', '锌锭', '0#', '吨');

-- 插入价格来源配置
INSERT INTO price_sources (id, name, website_name, website_url, material_category, price_url, selector, is_active) VALUES
    ('dddd1111-1111-1111-1111-111111111111', '我的钢铁网-钢筋', '我的钢铁网', 'https://www.mysteel.com.cn', '钢筋类', 'https://www.mysteel.com.cn/steel-rebar-price', '.rebar-price', true),
    ('dddd2222-2222-2222-2222-222222222222', '我的钢铁网-混凝土', '我的钢铁网', 'https://www.mysteel.com.cn', '混凝土类', 'https://www.mysteel.com.cn/concrete-price', '.concrete-price', true),
    ('dddd3333-3333-3333-3333-333333333333', '我的钢铁网-不锈钢', '我的钢铁网', 'https://www.mysteel.com.cn', '金属类', 'https://www.mysteel.com.cn/stainless-price', '.stainless-price', true),
    ('dddd4444-4444-4444-4444-444444444444', '有色金属网-铝', '有色金属网', 'https://www.ccmn.cn', '有色金属类', 'https://www.ccmn.cn/aluminum-price', '.al-price', true),
    ('dddd5555-5555-5555-5555-555555555555', '有色金属网-铜', '有色金属网', 'https://www.ccmn.cn', '有色金属类', 'https://www.ccmn.cn/copper-price', '.cu-price', true),
    ('dddd6666-6666-6666-6666-666666666666', '有色金属网-锌', '有色金属网', 'https://www.ccmn.cn', '有色金属类', 'https://www.ccmn.cn/zinc-price', '.zn-price', true);

-- 更新材料的source_id
UPDATE materials SET source_id = 'dddd1111-1111-1111-1111-111111111111' WHERE category_id = '11111111-1111-1111-1111-111111111111';
UPDATE materials SET source_id = 'dddd2222-2222-2222-2222-222222222222' WHERE category_id = '22222222-2222-2222-2222-222222222222';
UPDATE materials SET source_id = 'dddd3333-3333-3333-3333-333333333333' WHERE category_id = '33333333-3333-3333-3333-333333333333';
UPDATE materials SET source_id = 'dddd4444-4444-4444-4444-444444444444' WHERE name LIKE '%铝%';
UPDATE materials SET source_id = 'dddd5555-5555-5555-5555-555555555555' WHERE name LIKE '%铜%';
UPDATE materials SET source_id = 'dddd6666-6666-6666-6666-666666666666' WHERE name LIKE '%锌%';
