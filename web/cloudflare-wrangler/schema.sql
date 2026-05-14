-- TaskPlatform 数据库初始化
-- D1 数据库 Schema

-- 项目表
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    status TEXT DEFAULT 'active',
    contract_no TEXT,
    contract_date TEXT,
    base_date TEXT,
    completion_date TEXT,
    total_value REAL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- 材料表
CREATE TABLE IF NOT EXISTS materials (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT DEFAULT 'unknown',
    unit TEXT DEFAULT '吨',
    current_price REAL DEFAULT 0,
    specification TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- 价格历史表
CREATE TABLE IF NOT EXISTS price_history (
    id TEXT PRIMARY KEY,
    material_id TEXT NOT NULL,
    price REAL NOT NULL,
    source TEXT DEFAULT 'manual',
    recorded_at TEXT NOT NULL,
    FOREIGN KEY (material_id) REFERENCES materials(id)
);

-- 价格来源表
CREATE TABLE IF NOT EXISTS price_sources (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    url TEXT,
    type TEXT DEFAULT 'website',
    enabled INTEGER DEFAULT 1,
    created_at TEXT NOT NULL
);

-- 调差记录表
CREATE TABLE IF NOT EXISTS adjustments (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    material_id TEXT NOT NULL,
    base_price REAL NOT NULL,
    current_price REAL NOT NULL,
    quantity REAL NOT NULL,
    adjustment_amount REAL NOT NULL,
    calculated_at TEXT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id),
    FOREIGN KEY (material_id) REFERENCES materials(id)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
CREATE INDEX IF NOT EXISTS idx_materials_type ON materials(type);
CREATE INDEX IF NOT EXISTS idx_price_history_material ON price_history(material_id);
CREATE INDEX IF NOT EXISTS idx_price_history_date ON price_history(recorded_at);
CREATE INDEX IF NOT EXISTS idx_adjustments_project ON adjustments(project_id);