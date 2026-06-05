-- Supabase SQL: 创建 indicator_projects 表
-- 运行此脚本前请确保 Supabase 项目已创建
-- 在 Supabase SQL Editor 中执行

CREATE TABLE IF NOT EXISTS public.indicator_projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    category TEXT,
    location TEXT,
    structure TEXT,
    floor_above INTEGER DEFAULT 0,
    floor_below INTEGER DEFAULT 0,
    area_total DOUBLE PRECISION,
    area_above DOUBLE PRECISION,
    area_below DOUBLE PRECISION,
    height DOUBLE PRECISION,
    complete_date TEXT,
    source TEXT DEFAULT '结算文件',
    source_file TEXT,
    remarks TEXT,
    total_cost DOUBLE PRECISION,
    unit_cost DOUBLE PRECISION,
    unit_structure DOUBLE PRECISION,
    unit_installation DOUBLE PRECISION,
    unit_decoration DOUBLE PRECISION,
    unit_measure DOUBLE PRECISION,
    steel DOUBLE PRECISION,
    concrete DOUBLE PRECISION,
    formwork DOUBLE PRECISION,
    block DOUBLE PRECISION,
    cable DOUBLE PRECISION,
    pipe DOUBLE PRECISION,
    duct DOUBLE PRECISION,
    underground_structure DOUBLE PRECISION,
    above_structure DOUBLE PRECISION,
    roof DOUBLE PRECISION,
    exterior_wall DOUBLE PRECISION,
    interior_wall DOUBLE PRECISION,
    floor_area DOUBLE PRECISION,
    electrical DOUBLE PRECISION,
    plumbing DOUBLE PRECISION,
    hvac DOUBLE PRECISION,
    elevator DOUBLE PRECISION,
    fire DOUBLE PRECISION,
    measures DOUBLE PRECISION,
    verified BOOLEAN DEFAULT FALSE,
    verified_by TEXT,
    verified_at TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS 策略（可选）
ALTER TABLE public.indicator_projects ENABLE ROW LEVEL SECURITY;

-- 允许匿名读取和写入
CREATE POLICY "Allow anonymous access" ON public.indicator_projects
    FOR ALL USING (true) WITH CHECK (true);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_indicator_projects_category ON public.indicator_projects(category);
CREATE INDEX IF NOT EXISTS idx_indicator_projects_location ON public.indicator_projects(location);
CREATE INDEX IF NOT EXISTS idx_indicator_projects_created_at ON public.indicator_projects(created_at DESC);