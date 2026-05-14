-- ============================================
-- TaskPlatform 工程调差计算系统
-- 数据库初始化脚本
-- 适用于 Supabase PostgreSQL
-- ============================================

-- ========== 1. 创建表 ==========

-- 材料分类表
CREATE TABLE IF NOT EXISTS material_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    icon TEXT,
    color TEXT,
    sort_order INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT now()
);

-- 材料明细表
CREATE TABLE IF NOT EXISTS materials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category_id UUID REFERENCES material_categories(id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    spec TEXT,
    unit TEXT,
    base_price DECIMAL(15,2),
    source_id UUID,
    is_adjusted BOOLEAN DEFAULT true,
    adjustment_threshold DECIMAL(5,2) DEFAULT 5.00,
    created_at TIMESTAMP DEFAULT now()
);

-- 价格来源表
CREATE TABLE IF NOT EXISTS price_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    website_name TEXT,
    website_url TEXT,
    material_category TEXT NOT NULL,
    price_url TEXT NOT NULL,
    selector TEXT,
    xpath TEXT,
    -- 认证信息（请提供合法账号）
    auth_username TEXT,  -- 网站登录用户名
    auth_password_encrypted TEXT,  -- 加密后的密码（生产环境请加密存储）
    auth_type TEXT DEFAULT 'form',  -- 认证类型: form, api, cookie
    auth_extra JSONB,  -- 其他认证参数（如 API key）
    -- 抓取配置
    is_active BOOLEAN DEFAULT true,
    interval_hours INT DEFAULT 24,  -- 抓取间隔，默认每天一次
    last_fetched_at TIMESTAMP,
    last_fetch_status TEXT,  -- success, failed, pending
    last_error_message TEXT,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);

-- 价格历史表
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

-- 项目表
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    contract_no TEXT,
    contract_date DATE,
    base_date DATE,
    completion_date DATE,
    total_value DECIMAL(15,2),
    created_by UUID,
    created_at TIMESTAMP DEFAULT now()
);

-- 项目材料表
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

-- 施工阶段表
CREATE TABLE IF NOT EXISTS construction_phases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    phase_name TEXT NOT NULL,
    start_date DATE,
    end_date DATE,
    days INT,
    sort_order INT DEFAULT 0
);

-- 调差记录表
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

-- 指标分类表
CREATE TABLE IF NOT EXISTS indicator_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    icon TEXT,
    color TEXT,
    sort_order INT DEFAULT 0
);

-- 指标表
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

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    role TEXT DEFAULT 'member',
    created_at TIMESTAMP DEFAULT now()
);

-- ========== 2. 创建索引 ==========

CREATE INDEX IF NOT EXISTS idx_materials_category ON materials(category_id);
CREATE INDEX IF NOT EXISTS idx_price_history_material ON price_history(material_id);
CREATE INDEX IF NOT EXISTS idx_price_history_date ON price_history(recorded_date);
CREATE INDEX IF NOT EXISTS idx_price_history_source ON price_history(source_id);
CREATE INDEX IF NOT EXISTS idx_project_materials_project ON project_materials(project_id);
CREATE INDEX IF NOT EXISTS idx_adjustment_records_project ON adjustment_records(project_id);
CREATE INDEX IF NOT EXISTS idx_adjustment_records_phase ON adjustment_records(phase_id);
CREATE INDEX IF NOT EXISTS idx_phases_project ON construction_phases(project_id);

-- ========== 3. 插入初始数据 ==========

-- 材料分类
INSERT INTO material_categories (id, name, icon, color, sort_order) VALUES
    ('11111111-1111-1111-1111-111111111111', '钢筋类', '🔩', '#3498db', 1),
    ('22222222-2222-2222-2222-222222222222', '混凝土类', '🧱', '#e74c3c', 2),
    ('33333333-3333-3333-3333-333333333333', '金属类', '🔧', '#f39c12', 3),
    ('44444444-4444-4444-4444-444444444444', '有色金属类', '🪙', '#9b59b6', 4);

-- 材料
INSERT INTO materials (id, category_id, name, spec, unit, base_price, is_adjusted) VALUES
    ('aaaa1111-1111-1111-1111-111111111111', '11111111-1111-1111-1111-111111111111', 'HRB400螺纹钢筋', '12-25mm', '吨', 4500, true),
    ('aaaa2222-2222-2222-2222-222222222222', '11111111-1111-1111-1111-111111111111', 'HPB300光圆钢筋', '8-10mm', '吨', 4600, true),
    ('aaaa3333-3333-3333-3333-333333333333', '11111111-1111-1111-1111-111111111111', '钢绞线', '15.2mm', '吨', 5200, true),
    ('aaaa4444-4444-4444-4444-444444444444', '11111111-1111-1111-1111-111111111111', '钢丝绳', '6x19', '吨', 6800, true),
    ('bbbb1111-1111-1111-1111-111111111111', '22222222-2222-2222-2222-222222222222', 'C15混凝土', '普通', 'm³', 520, true),
    ('bbbb2222-2222-2222-2222-222222222222', '22222222-2222-2222-2222-222222222222', 'C20混凝土', '普通', 'm³', 540, true),
    ('bbbb3333-3333-3333-3333-333333333333', '22222222-2222-2222-2222-222222222222', 'C25混凝土', '普通', 'm³', 560, true),
    ('bbbb4444-4444-4444-4444-444444444444', '22222222-2222-2222-2222-222222222222', 'C30混凝土', '普通', 'm³', 580, true),
    ('bbbb5555-5555-5555-5555-555555555555', '22222222-2222-2222-2222-222222222222', 'C35混凝土', '普通', 'm³', 610, true),
    ('bbbb6666-6666-6666-6666-666666666666', '22222222-2222-2222-2222-222222222222', 'C40混凝土', '普通', 'm³', 640, true),
    ('cccc1111-1111-1111-1111-111111111111', '33333333-3333-3333-3333-333333333333', '304不锈钢', '2B卷板', '吨', 18000, true),
    ('cccc2222-2222-2222-2222-222222222222', '33333333-3333-3333-3333-333333333333', '316不锈钢', '2B卷板', '吨', 24000, true),
    ('cccc3333-3333-3333-3333-333333333333', '44444444-4444-4444-4444-444444444444', '铝锭', 'A00', '吨', 18500, true),
    ('cccc4444-4444-4444-4444-444444444444', '44444444-4444-4444-4444-444444444444', '铜锭', '1#电解铜', '吨', 68000, true),
    ('cccc5555-5555-5555-5555-555555555555', '44444444-4444-4444-4444-444444444444', '锌锭', '0#', '吨', 21000, true);

-- 价格来源（请提供合法账号）
INSERT INTO price_sources (id, name, website_name, website_url, material_category, price_url, selector, auth_type, interval_hours, is_active) VALUES
    ('eeee1111-1111-1111-1111-111111111111', '我的钢铁网-钢筋', '我的钢铁网', 'https://www.mysteel.com.cn', '钢筋类', 'https://www.mysteel.com.cn/price/rebar', '.price-value', 'form', 24, true),
    ('eeee2222-2222-2222-2222-222222222222', '我的钢铁网-混凝土', '我的钢铁网', 'https://www.mysteel.com.cn', '混凝土类', 'https://www.mysteel.com.cn/price/concrete', '.price-value', 'form', 24, true),
    ('eeee3333-3333-3333-3333-333333333333', '我的钢铁网-不锈钢', '我的钢铁网', 'https://www.mysteel.com.cn', '金属类', 'https://www.mysteel.com.cn/price/stainless', '.price-value', 'form', 24, true),
    ('eeee4444-4444-4444-4444-444444444444', '有色金属网-铝', '有色金属网', 'https://www.ccmn.cn', '有色金属类', 'https://www.ccmn.cn/aluminum', '.latest-price', 'form', 24, true),
    ('eeee5555-5555-5555-5555-555555555555', '有色金属网-铜', '有色金属网', 'https://www.ccmn.cn', '有色金属类', 'https://www.ccmn.cn/copper', '.latest-price', 'form', 24, true),
    ('eeee6666-6666-6666-6666-666666666666', '有色金属网-锌', '有色金属网', 'https://www.ccmn.cn', '有色金属类', 'https://www.ccmn.cn/zinc', '.latest-price', 'form', 24, true);

-- 更新材料的 source_id
UPDATE materials SET source_id = 'eeee1111-1111-1111-1111-111111111111' WHERE category_id = '11111111-1111-1111-1111-111111111111';
UPDATE materials SET source_id = 'eeee2222-2222-2222-2222-222222222222' WHERE category_id = '22222222-2222-2222-2222-222222222222';
UPDATE materials SET source_id = 'eeee3333-3333-3333-3333-333333333333' WHERE category_id = '33333333-3333-3333-3333-333333333333';
UPDATE materials SET source_id = 'eeee4444-4444-4444-4444-444444444444' WHERE name LIKE '%铝%';
UPDATE materials SET source_id = 'eeee5555-5555-5555-5555-555555555555' WHERE name LIKE '%铜%';
UPDATE materials SET source_id = 'eeee6666-6666-6666-6666-666666666666' WHERE name LIKE '%锌%';

-- 示例项目
INSERT INTO projects (id, name, contract_no, contract_date, base_date, completion_date, total_value) VALUES
    ('proj0001-0001-0001-0001-000000000001', 'XX商业综合体项目', 'HT2024001', '2024-01-15', '2024-03-01', '2025-12-31', 58000000),
    ('proj0002-0002-0002-0002-000000000002', 'YY住宅小区项目', 'HT2024002', '2024-02-20', '2024-04-01', '2025-06-30', 32000000);

-- 示例施工阶段
INSERT INTO construction_phases (id, project_id, phase_name, start_date, end_date, days, sort_order) VALUES
    ('phas0001-0001-0001-0001-000000000001', 'proj0001-0001-0001-0001-000000000001', '基础施工阶段', '2024-03-01', '2024-06-30', 122, 1),
    ('phas0002-0002-0002-0002-000000000002', 'proj0001-0001-0001-0001-000000000001', '主体结构阶段', '2024-07-01', '2024-12-31', 184, 2),
    ('phas0003-0003-0003-0003-000000000003', 'proj0001-0001-0001-0001-000000000001', '装饰装修阶段', '2025-01-01', '2025-12-31', 365, 3);

-- 示例项目材料
INSERT INTO project_materials (id, project_id, material_id, material_name, spec, unit, quantity, contract_price, base_price, adjustment_type) VALUES
    ('pmat0001-0001-0001-0001-000000000001', 'proj0001-0001-0001-0001-000000000001', 'aaaa1111-1111-1111-1111-111111111111', 'HRB400螺纹钢筋', '12-25mm', '吨', 500, 4200, 4200, 'adjustable'),
    ('pmat0002-0002-0002-0002-000000000002', 'proj0001-0001-0001-0001-000000000001', 'aaaa2222-2222-2222-2222-222222222222', 'HPB300光圆钢筋', '8-10mm', '吨', 200, 4300, 4300, 'adjustable'),
    ('pmat0003-0003-0003-0003-000000000003', 'proj0001-0001-0001-0001-000000000001', 'bbbb4444-4444-4444-4444-444444444444', 'C30混凝土', '普通', 'm³', 2000, 550, 550, 'adjustable'),
    ('pmat0004-0004-0004-0004-000000000004', 'proj0002-0002-0002-0002-000000000002', 'aaaa1111-1111-1111-1111-111111111111', 'HRB400螺纹钢筋', '12-25mm', '吨', 300, 4150, 4150, 'adjustable'),
    ('pmat0005-0005-0005-0005-000000000005', 'proj0002-0002-0002-0002-000000000002', 'bbbb4444-4444-4444-4444-444444444444', 'C30混凝土', '普通', 'm³', 1500, 540, 540, 'adjustable');

-- 示例价格历史
INSERT INTO price_history (id, material_id, source_id, price, unit, recorded_date, fetch_status) VALUES
    ('phst0001-0001-0001-0001-000000000001', 'aaaa1111-1111-1111-1111-111111111111', 'eeee1111-1111-1111-1111-111111111111', 4200, '吨', '2024-03-01', 'success'),
    ('phst0002-0002-0002-0002-000000000002', 'aaaa1111-1111-1111-1111-111111111111', 'eeee1111-1111-1111-1111-111111111111', 4250, '吨', '2024-03-15', 'success'),
    ('phst0003-0003-0003-0003-000000000003', 'aaaa1111-1111-1111-1111-111111111111', 'eeee1111-1111-1111-1111-111111111111', 4350, '吨', '2024-04-01', 'success'),
    ('phst0004-0004-0004-0004-000000000004', 'aaaa1111-1111-1111-1111-111111111111', 'eeee1111-1111-1111-1111-111111111111', 4450, '吨', '2024-04-15', 'success'),
    ('phst0005-0005-0005-0005-000000000005', 'aaaa1111-1111-1111-1111-111111111111', 'eeee1111-1111-1111-1111-111111111111', 4500, '吨', '2024-05-01', 'success'),
    ('phst0006-0006-0006-0006-000000000006', 'bbbb4444-4444-4444-4444-444444444444', 'eeee2222-2222-2222-2222-222222222222', 550, 'm³', '2024-03-01', 'success'),
    ('phst0007-0007-0007-0007-000000000007', 'bbbb4444-4444-4444-4444-444444444444', 'eeee2222-2222-2222-2222-222222222222', 560, 'm³', '2024-03-15', 'success'),
    ('phst0008-0008-0008-0008-000000000008', 'bbbb4444-4444-4444-4444-444444444444', 'eeee2222-2222-2222-2222-222222222222', 570, 'm³', '2024-04-01', 'success'),
    ('phst0009-0009-0009-0009-000000000009', 'bbbb4444-4444-4444-4444-444444444444', 'eeee2222-2222-2222-2222-222222222222', 580, 'm³', '2024-04-15', 'success'),
    ('phst0010-0010-0010-0010-001000000010', 'bbbb4444-4444-4444-4444-444444444444', 'eeee2222-2222-2222-2222-222222222222', 585, 'm³', '2024-05-01', 'success');

-- 指标分类
INSERT INTO indicator_categories (id, project_id, name, icon, color, sort_order) VALUES
    ('icat0001-0001-0001-0001-000000000001', 'proj0001-0001-0001-0001-000000000001', '质量指标', '📊', '#1890ff', 1),
    ('icat0002-0002-0002-0002-000000000002', 'proj0001-0001-0001-0001-000000000001', '进度指标', '⏰', '#52c41a', 2),
    ('icat0003-0003-0003-0003-000000000003', 'proj0001-0001-0001-0001-000000000001', '成本指标', '💰', '#faad14', 3),
    ('icat0004-0004-0004-0004-000000000004', 'proj0001-0001-0001-0001-000000000001', '安全指标', '⚠️', '#f5222d', 4);

-- 指标
INSERT INTO indicators (id, category_id, project_id, name, unit, target_value, warning_threshold, current_value, status) VALUES
    ('indi0001-0001-0001-0001-000000000001', 'icat0001-0001-0001-0001-000000000001', 'proj0001-0001-0001-0001-000000000001', '钢筋损耗率', '%', 2.5, 5, 2.8, 'warning'),
    ('indi0002-0002-0002-0002-000000000002', 'icat0001-0001-0001-0001-000000000001', 'proj0001-0001-0001-0001-000000000001', '混凝土强度', 'MPa', 30, 10, 32, 'normal'),
    ('indi0003-0003-0003-0003-000000000003', 'icat0002-0002-0002-0002-000000000002', 'proj0001-0001-0001-0001-000000000001', '施工进度', '%', 60, 10, 55, 'warning'),
    ('indi0004-0004-0004-0004-000000000004', 'icat0003-0003-0003-0003-000000000003', 'proj0001-0001-0001-0001-000000000001', '成本控制', '万元', 500, 5, 480, 'normal'),
    ('indi0005-0005-0005-0005-000000000005', 'icat0004-0004-0004-0004-000000000004', 'proj0001-0001-0001-0001-000000000001', '安全事故数', '次', 0, 0, 0, 'normal');

-- ========== 4. 启用 RLS（可选） ==========

-- 为所有表启用行级安全策略（允许所有操作，生产环境应更严格）

ALTER TABLE material_categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE materials ENABLE ROW LEVEL SECURITY;
ALTER TABLE price_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE price_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_materials ENABLE ROW LEVEL SECURITY;
ALTER TABLE construction_phases ENABLE ROW LEVEL SECURITY;
ALTER TABLE adjustment_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE indicator_categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE indicators ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- 允许所有操作（开发环境）
-- 生产环境应使用更严格的策略

CREATE POLICY "Allow all" ON material_categories FOR ALL USING (true);
CREATE POLICY "Allow all" ON materials FOR ALL USING (true);
CREATE POLICY "Allow all" ON price_sources FOR ALL USING (true);
CREATE POLICY "Allow all" ON price_history FOR ALL USING (true);
CREATE POLICY "Allow all" ON projects FOR ALL USING (true);
CREATE POLICY "Allow all" ON project_materials FOR ALL USING (true);
CREATE POLICY "Allow all" ON construction_phases FOR ALL USING (true);
CREATE POLICY "Allow all" ON adjustment_records FOR ALL USING (true);
CREATE POLICY "Allow all" ON indicator_categories FOR ALL USING (true);
CREATE POLICY "Allow all" ON indicators FOR ALL USING (true);
CREATE POLICY "Allow all" ON users FOR ALL USING (true);

-- ========== 完成 ==========
-- 数据库初始化完成！
-- 现在可以启动前端查看数据