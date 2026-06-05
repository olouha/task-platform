-- Supabase SQL: 创建 cost_reference_prices 表
-- 在 Supabase SQL Editor 中执行此脚本

CREATE TABLE IF NOT EXISTS public.cost_reference_prices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category TEXT NOT NULL,
    code TEXT,
    name TEXT NOT NULL,
    spec TEXT,
    unit TEXT DEFAULT 't',
    unit_price DOUBLE PRECISION,
    tax_rate DOUBLE PRECISION DEFAULT 13.0,
    pump_price DOUBLE PRECISION,
    non_pump_price DOUBLE PRECISION,
    source TEXT DEFAULT '烟台工程建设标准造价管理',
    period TEXT NOT NULL,
    region TEXT DEFAULT '山东烟台',
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_cost_ref_uniq
    ON public.cost_reference_prices(category, name, period);
CREATE INDEX IF NOT EXISTS idx_cost_ref_category ON public.cost_reference_prices(category);
CREATE INDEX IF NOT EXISTS idx_cost_ref_period ON public.cost_reference_prices(period);
ALTER TABLE public.cost_reference_prices ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow anonymous access" ON public.cost_reference_prices
    FOR ALL USING (true) WITH CHECK (true);