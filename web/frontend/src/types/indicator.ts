/**
 * 指标库 TypeScript 类型定义
 */

/**
 * 验证警告
 */
export interface ValidationWarning {
  field: string;
  message: string;
  severity: 'warning' | 'error';
  value?: unknown;
  expected?: string;
}

/**
 * 导入错误明细（带行列定位与修改建议）
 */
export interface ImportFieldError {
  /** Excel 实际行号（1-based，含表头行） */
  row?: number;
  /** 字段代码，如 area_total */
  field?: string;
  /** 中文列名，如 总面积（m2） */
  field_label?: string;
  /** 当前错误值 */
  value?: unknown;
  /** 问题描述 */
  message: string;
  /** 修改建议 */
  suggestion?: string;
}

/**
 * 导入预览项
 */
export interface ImportPreviewItem {
  index: number;
  name: string;
  category?: string;
  location?: string;
  unit_cost?: number;
  /** Excel 实际行号 */
  row?: number;
  status: 'valid' | 'warning' | 'error';
  /** 警告信息（兼容旧字段，纯文本） */
  warnings: string[];
  /** 错误信息（兼容旧字段，纯文本） */
  errors: string[];
  /** 警告明细（带行列定位） */
  warning_details?: ImportFieldError[];
  /** 错误明细（带行列定位） */
  error_details?: ImportFieldError[];
}

/**
 * 汇总项模型 - 用于列表展示
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

/**
 * 完整明细模型 - 用于详情和编辑
 */
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
  // 建筑指标
  wall_floor_ratio?: number;
  window_wall_ratio?: number;
  window_content?: number;
  door_content?: number;
  interior_wall_content?: number;
  balcony_ratio?: number;
  assembly_rate?: number;
  assembly_content?: number;
  source?: string;
  source_file?: string;
  remarks?: string;
  entry_date?: string;
  created_at?: string;
  updated_at?: string;
}

/**
 * 验证结果
 */
export interface ValidationResult {
  passed: boolean;
  warnings: ValidationWarning[];
  errors: ValidationWarning[];
  checks: Record<string, string>;
}

/**
 * 导入预览结果
 */
export interface ImportPreviewResult {
  total: number;
  valid_count: number;
  warning_count: number;
  error_count: number;
  items: ImportPreviewItem[];
}

/**
 * 导入结果
 */
export interface ImportResult {
  success: boolean;
  imported: number;
  total: number;
  warnings: Record<string, unknown>[];
  errors: string[];
  /** 错误明细（带行列定位与修改建议） */
  error_details?: ImportFieldError[];
}

/**
 * 指标库统计概览
 */
export interface IndicatorLibraryStats {
  total: number;
  categories: Record<string, number>;
  locations: Record<string, number>;
}

/**
 * 创建指标库项目的请求参数
 */
export type IndicatorLibraryCreate = Partial<IndicatorLibraryDetail>;

/**
 * 指标库筛选参数
 */
export interface IndicatorLibraryFilter {
  category?: string;
  location?: string;
  delivery_type?: string;
  start_date_from?: string;
  start_date_to?: string;
  end_date_from?: string;
  end_date_to?: string;
  search_text?: string;
  limit?: number;
}
