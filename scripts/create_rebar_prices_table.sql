-- Supabase SQL: 创建 rebar_prices 表
-- 在 Supabase SQL Editor 中执行此脚本

CREATE TABLE IF NOT EXISTS public.rebar_prices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date TEXT NOT NULL,
    fetch_time TEXT,
    material_name TEXT NOT NULL,
    spec TEXT,
    material_type TEXT,
    brand TEXT,
    price INTEGER NOT NULL,
    region TEXT DEFAULT '山东烟台',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 防重复唯一索引
CREATE UNIQUE INDEX IF NOT EXISTS idx_rebar_uniq
    ON public.rebar_prices(date, material_name, spec, brand, price);

-- 查询索引
CREATE INDEX IF NOT EXISTS idx_rebar_date ON public.rebar_prices(date);
CREATE INDEX IF NOT EXISTS idx_rebar_material ON public.rebar_prices(material_name);
CREATE INDEX IF NOT EXISTS idx_rebar_spec ON public.rebar_prices(spec);

-- RLS 策略
ALTER TABLE public.rebar_prices ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow anonymous access" ON public.rebar_prices
    FOR ALL USING (true) WITH CHECK (true);