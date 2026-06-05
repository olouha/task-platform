// API 服务配置
// 连接后端服务器（烟台钢筋价格）

// 开发环境使用 /api 代理到后端，生产环境使用实际部署的地址
const API_BASE_URL = import.meta.env.VITE_API_URL || '';

// 辅助函数：构建API URL
// 如果 API_BASE_URL 是 '/api'（代理模式），直接拼接路径
// 如果是完整URL（如 'http://localhost:8000'），直接使用
const buildApiUrl = (path: string): string => {
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  if (API_BASE_URL === '/api') {
    // 代理模式：/api + /stats -> /api/stats
    return `${API_BASE_URL}${cleanPath}`;
  }
  if (API_BASE_URL) {
    // 完整URL模式：http://localhost:8000 + /api/stats -> http://localhost:8000/api/stats
    return API_BASE_URL.replace(/\/$/, '') + cleanPath;
  }
  // 无base URL：/stats -> /stats
  return cleanPath;
};

export const config = {
  apiUrl: API_BASE_URL,
  buildUrl: buildApiUrl,
};

// 类型定义
export interface YantaiPrice {
  date?: string;
  time?: string;
  material_name: string;
  spec: string;
  material_type?: string;
  brand: string;
  price: number;
  price_change?: string;
  remark?: string;
  region?: string;
}

// Stats API
export const statsApi = {
  get: async () => {
    const response = await fetch(`${config.apiUrl}/stats`);
    return response.json();
  }
};

// Projects API
export const projectsApi = {
  list: async () => {
    const response = await fetch(`${config.apiUrl}/projects`);
    return response.json();
  },
  create: async (data: any) => {
    const response = await fetch(`${config.apiUrl}/projects`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return response.json();
  },
  delete: async (id: string) => {
    const response = await fetch(`${config.apiUrl}/projects/${id}`, {
      method: 'DELETE',
    });
    return response.json();
  }
};

export interface Project {
  id: string;
  name: string;
  description: string;
  created_at: string;
  status: 'active' | 'completed';
}

// 调差规则 API
export const adjustmentRulesApi = {
  list: async () => {
    const response = await fetch(`${config.apiUrl}/adjustment-rules/`);
    return response.json();
  },
  get: async (id: string) => {
    const response = await fetch(`${config.apiUrl}/adjustment-rules/${id}`);
    return response.json();
  },
  create: async (data: any) => {
    const response = await fetch(`${config.apiUrl}/adjustment-rules/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return response.json();
  },
  update: async (id: string, data: any) => {
    const response = await fetch(`${config.apiUrl}/adjustment-rules/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return response.json();
  },
  delete: async (id: string) => {
    const response = await fetch(`${config.apiUrl}/adjustment-rules/${id}`, {
      method: 'DELETE',
    });
    return response.json();
  },
  getPresets: async () => {
    const response = await fetch(`${config.apiUrl}/adjustment-rules/presets`);
    return response.json();
  },
  applyPreset: async (_presetName: string, projectName: string) => {
    const response = await fetch(`${config.apiUrl}/adjustment-rules/apply-preset`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 项目名称: projectName }),
    });
    return response.json();
  },
  saveBidPrices: async (ruleId: string, bidPrices: any[]) => {
    const response = await fetch(`${config.apiUrl}/adjustment-rules/bid-prices`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ rule_id: ruleId, bid_prices: bidPrices }),
    });
    return response.json();
  },
  getBidPrices: async (ruleId: string) => {
    const response = await fetch(`${config.apiUrl}/adjustment-rules/${ruleId}/bid-prices`);
    return response.json();
  },
};

// 调差计算 API
export const adjustmentCalcApi = {
  calculate: async (request: any) => {
    const response = await fetch(`${config.apiUrl}/adjustments/calculate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });
    return response.json();
  },
  calculateByProject: async (projectId: string) => {
    const response = await fetch(`${config.apiUrl}/adjustments/calculate-by-project/${projectId}`, {
      method: 'POST',
    });
    return response.json();
  },
  calculateSimple: async (params: {
    base_price: number;
    avg_price: number;
    quantity: number;
    risk_percent?: number;
    risk_fixed?: number;
    tax_rate?: number;
  }) => {
    const query = new URLSearchParams({
      base_price: params.base_price.toString(),
      avg_price: params.avg_price.toString(),
      quantity: params.quantity.toString(),
      ...(params.risk_percent && { risk_percent: params.risk_percent.toString() }),
      ...(params.risk_fixed && { risk_fixed: params.risk_fixed.toString() }),
      ...(params.tax_rate && { tax_rate: params.tax_rate.toString() }),
    });
    const response = await fetch(`${config.apiUrl}/adjustments/calculate-simple?${query}`);
    return response.json();
  },
  validateConfig: async (config: any) => {
    const response = await fetch(`${config.apiUrl}/adjustments/validate-config`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    });
    return response.json();
  },
  batchGetPrices: async (params: {
    materials: string[];
    start_date: string;
    end_date: string;
    base_date?: string;
  }) => {
    const response = await fetch(`${config.apiUrl}/api/adjustments/prices/batch-get`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    });
    return response.json();
  },
};

// 调度器 API
export const schedulerApi = {
  getStatus: async () => {
    const response = await fetch(`${config.apiUrl}/scheduler/status`);
    return response.json();
  },
  getTaskStatus: async (sourceId: string) => {
    const response = await fetch(`${config.apiUrl}/scheduler/${sourceId}/status`);
    return response.json();
  },
  executeTask: async (sourceId: string, force: boolean = false) => {
    const response = await fetch(`${config.apiUrl}/scheduler/${sourceId}/execute?force=${force}`, {
      method: 'POST',
    });
    return response.json();
  },
  executeAllPending: async () => {
    const response = await fetch(`${config.apiUrl}/scheduler/execute-all`, {
      method: 'POST',
    });
    return response.json();
  },
  executeAllSites: async (force: boolean = false) => {
    const response = await fetch(`${config.apiUrl}/scheduler/execute-all-sites?force=${force}`, {
      method: 'POST',
    });
    return response.json();
  },
  forceFetchAll: async () => {
    const response = await fetch(`${config.apiUrl}/scheduler/force-fetch-all`, {
      method: 'POST',
    });
    return response.json();
  },
  getNextExecution: async () => {
    const response = await fetch(`${config.apiUrl}/scheduler/next-execution`);
    return response.json();
  },
  getSupportedMaterials: async () => {
    const response = await fetch(`${config.apiUrl}/scheduler/supported-materials`);
    return response.json();
  },
};

// 人工抓取 API
export const fetchApi = {
  getFetchStatus: async () => {
    const response = await fetch(`${config.apiUrl}/fetch/status`);
    return response.json();
  },
  triggerManualFetch: async (cookies: any[]) => {
    const response = await fetch(`${config.apiUrl}/fetch/manual`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cookies }),
    });
    return response.json();
  },
  triggerAutoFetch: async () => {
    const response = await fetch(`${config.apiUrl}/fetch/auto`, {
      method: 'POST',
    });
    return response.json();
  },
  getManualRequired: async () => {
    const response = await fetch(`${config.apiUrl}/fetch/manual-required`);
    return response.json();
  },
  getExcelData: async () => {
    const response = await fetch(`${config.apiUrl}/fetch/excel-data`);
    return response.json();
  },
  downloadExcel: () => {
    window.open(`${config.apiUrl}/fetch/download`, '_blank');
  },
  getCookieGuide: async () => {
    const response = await fetch(`${config.apiUrl}/fetch/export-cookie-guide`);
    return response.json();
  },
};

// 定时抓取 API (Cloudflare Workers cron 触发)
export const cronFetchApi = {
  fetchToday: async () => {
    const response = await fetch(`${config.apiUrl}/cron/fetch-today`);
    return response.json();
  },
  getStatus: async () => {
    const response = await fetch(`${config.apiUrl}/cron/status`);
    return response.json();
  },
  forceFetch: async () => {
    const response = await fetch(`${config.apiUrl}/cron/force-fetch`, {
      method: 'POST',
    });
    return response.json();
  },
  getLatest: async () => {
    const response = await fetch(`${config.apiUrl}/cron/latest`);
    return response.json();
  },
};

// 造价参考价 API
export const costReferenceApi = {
  getSources: async () => {
    const response = await fetch(`${config.apiUrl}/cost-reference/sources`);
    return response.json();
  },
  getCategories: async () => {
    const response = await fetch(`${config.apiUrl}/cost-reference/categories`);
    return response.json();
  },
  getSummary: async () => {
    const response = await fetch(`${config.apiUrl}/cost-reference/summary`);
    return response.json();
  },
  getSteelPrices: async (params?: { spec?: string; steel_type?: string }) => {
    const query = new URLSearchParams(params || {}).toString();
    const response = await fetch(`${config.apiUrl}/cost-reference/steel${query ? '?' + query : ''}`);
    return response.json();
  },
  getSteelTypes: async () => {
    const response = await fetch(`${config.apiUrl}/cost-reference/steel/types`);
    return response.json();
  },
  getSteelSpecs: async () => {
    const response = await fetch(`${config.apiUrl}/cost-reference/steel/specs`);
    return response.json();
  },
  getConcretePrices: async (params?: { min_grade?: string; max_grade?: string }) => {
    const query = new URLSearchParams(params || {}).toString();
    const response = await fetch(`${config.apiUrl}/cost-reference/concrete${query ? '?' + query : ''}`);
    return response.json();
  },
  getConcreteGrades: async () => {
    const response = await fetch(`${config.apiUrl}/cost-reference/concrete/grades`);
    return response.json();
  },
  getMortarPrices: async () => {
    const response = await fetch(`${config.apiUrl}/cost-reference/mortar`);
    return response.json();
  },
  search: async (keyword: string, category?: string) => {
    const query = new URLSearchParams({ keyword, ...(category && { category }) }).toString();
    const response = await fetch(`${config.apiUrl}/cost-reference/search?${query}`);
    return response.json();
  },
};

// 指标库管理 API
export const indicatorDatabaseApi = {
  // 获取指标列表
  list: async (params?: { project_id?: string; category_id?: string }) => {
    const query = new URLSearchParams(params || {}).toString();
    const response = await fetch(`${config.apiUrl}/indicators/${query ? '?' + query : ''}`);
    return response.json();
  },
  // 获取单个指标
  get: async (id: string) => {
    const response = await fetch(`${config.apiUrl}/indicators/${id}`);
    return response.json();
  },
  // 创建指标
  create: async (data: any) => {
    const response = await fetch(`${config.apiUrl}/indicators/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return response.json();
  },
  // 更新指标
  update: async (id: string, data: any) => {
    const response = await fetch(`${config.apiUrl}/indicators/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return response.json();
  },
  // 删除指标
  delete: async (id: string) => {
    const response = await fetch(`${config.apiUrl}/indicators/${id}`, { method: 'DELETE' });
    return response.json();
  },
  // 获取指标分类
  listCategories: async (project_id?: string) => {
    const query = project_id ? `?project_id=${project_id}` : '';
    const response = await fetch(`${config.apiUrl}/indicators/categories${query}`);
    return response.json();
  },
  // 创建指标分类
  createCategory: async (data: any) => {
    const response = await fetch(`${config.apiUrl}/indicators/categories`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return response.json();
  },
  // 评估指标状态
  evaluate: async (project_id?: string, current_values?: Record<string, number>) => {
    const response = await fetch(`${config.apiUrl}/indicators/evaluate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project_id, current_values }),
    });
    return response.json();
  },
};

// 调差项目管理 API
export const adjustmentProjectApi = {
  list: async () => {
    const response = await fetch(`${config.apiUrl}/adjustment-projects/`);
    return response.json();
  },
  get: async (id: string) => {
    const response = await fetch(`${config.apiUrl}/adjustment-projects/${id}`);
    return response.json();
  },
  create: async (data: {
    name: string;
    contract_no?: string;
    rule_id?: string;
    rule_name?: string;
    base_price_source?: string;
  }) => {
    const response = await fetch(`${config.apiUrl}/adjustment-projects/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return response.json();
  },
  update: async (id: string, data: any) => {
    const response = await fetch(`${config.apiUrl}/adjustment-projects/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return response.json();
  },
  delete: async (id: string) => {
    const response = await fetch(`${config.apiUrl}/adjustment-projects/${id}`, {
      method: 'DELETE',
    });
    return response.json();
  },
  getMaterials: async (id: string) => {
    const response = await fetch(`${config.apiUrl}/adjustment-projects/${id}/materials`);
    return response.json();
  },
  setMaterials: async (id: string, materials: any[]) => {
    const response = await fetch(`${config.apiUrl}/adjustment-projects/${id}/materials`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(materials),
    });
    return response.json();
  },
  addAttachment: async (id: string, attachment: any) => {
    const response = await fetch(`${config.apiUrl}/adjustment-projects/${id}/attachments`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(attachment),
    });
    return response.json();
  },
  deleteAttachment: async (id: string, attachmentId: string) => {
    const response = await fetch(`${config.apiUrl}/adjustment-projects/${id}/attachments/${attachmentId}`, {
      method: 'DELETE',
    });
    return response.json();
  },
};

// 文件解析 API
export const fileParserApi = {
  upload: async (file: File): Promise<any> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await fetch(`${config.apiUrl}/file-parser/upload`, {
      method: 'POST',
      body: formData,
    });
    return response.json();
  },
  preview: async (file: File): Promise<any> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await fetch(`${config.apiUrl}/file-parser/preview`, {
      method: 'POST',
      body: formData,
    });
    return response.json();
  },
  getTemplates: async () => {
    const response = await fetch(`${config.apiUrl}/file-parser/templates`);
    return response.json();
  },
};

// 造价历史参考价 API
export const costHistoryApi = {
  getPeriods: async () => {
    const response = await fetch(`${config.apiUrl}/cost-history/periods`);
    return response.json();
  },
  getYears: async () => {
    const response = await fetch(`${config.apiUrl}/cost-history/years`);
    return response.json();
  },
  getSummary: async () => {
    const response = await fetch(`${config.apiUrl}/cost-history/summary`);
    return response.json();
  },
  getConcreteByPeriod: async (year: string, quarter: string) => {
    const query = new URLSearchParams({ year, quarter }).toString();
    const response = await fetch(`${config.apiUrl}/cost-history/concrete/by-period?${query}`);
    return response.json();
  },
  getSteelByPeriod: async (year: string, quarter: string) => {
    const query = new URLSearchParams({ year, quarter }).toString();
    const response = await fetch(`${config.apiUrl}/cost-history/steel/by-period?${query}`);
    return response.json();
  },
  getLatestConcrete: async (year?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (year) params.set('year', year);
    if (limit) params.set('limit', limit.toString());
    const query = params.toString();
    const response = await fetch(`${config.apiUrl}/cost-history/concrete/latest${query ? '?' + query : ''}`);
    return response.json();
  },
  getLatestSteel: async (year?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (year) params.set('year', year);
    if (limit) params.set('limit', limit.toString());
    const query = params.toString();
    const response = await fetch(`${config.apiUrl}/cost-history/steel/latest${query ? '?' + query : ''}`);
    return response.json();
  },
  getConcreteGrades: async () => {
    const response = await fetch(`${config.apiUrl}/cost-history/concrete/grades`);
    return response.json();
  },
  getSteelSpecs: async () => {
    const response = await fetch(`${config.apiUrl}/cost-history/steel/specs`);
    return response.json();
  },
};

// 调差价格获取 API
export const adjustmentPricesApi = {
  query: async (params: {
    material: string;
    start_date: string;
    end_date: string;
    spec?: string;
    brands?: string;
  }) => {
    const query = new URLSearchParams(params).toString();
    const response = await fetch(`${config.apiUrl}/adjustment-prices/query?${query}`);
    return response.json();
  },
  getPeriodAverage: async (params: {
    material: string;
    start_date: string;
    end_date: string;
    brands?: string;
  }) => {
    const query = new URLSearchParams(params).toString();
    const response = await fetch(`${config.apiUrl}/adjustment-prices/period-average?${query}`);
    return response.json();
  },
  getBasePrice: async (params: {
    material: string;
    base_date: string;
    spec?: string;
    brands?: string;
  }) => {
    const query = new URLSearchParams(params).toString();
    const response = await fetch(`${config.apiUrl}/adjustment-prices/base-price?${query}`);
    return response.json();
  },
  getAdjustmentPrices: async (params: {
    material: string;
    base_date: string;
    period_start: string;
    period_end: string;
    brands?: string;
  }) => {
    const query = new URLSearchParams(params).toString();
    const response = await fetch(`${config.apiUrl}/adjustment-prices/adjustment-prices?${query}`);
    return response.json();
  },
  batchGet: async (params: {
    materials: string;
    base_date: string;
    period_start: string;
    period_end: string;
  }) => {
    const query = new URLSearchParams(params).toString();
    const response = await fetch(`${config.apiUrl}/adjustment-prices/batch?${query}`);
    return response.json();
  },
  getLatest: async (material: string, spec?: string) => {
    const query = new URLSearchParams({ material, ...(spec && { spec }) }).toString();
    const response = await fetch(`${config.apiUrl}/adjustment-prices/latest?${query}`);
    return response.json();
  },
};

// 数据管理 API
export const dataManagerApi = {
  // 获取数据统计
  getStats: async () => {
    const response = await fetch(`${config.apiUrl}/data-manager/stats`);
    return response.json();
  },

  // 导出数据
  exportData: async (params: {
    format?: 'xlsx' | 'csv';
    start_date?: string;
    end_date?: string;
    material?: string;
  } = {}) => {
    const query = new URLSearchParams();
    if (params.format) query.set('format', params.format);
    if (params.start_date) query.set('start_date', params.start_date);
    if (params.end_date) query.set('end_date', params.end_date);
    if (params.material) query.set('material', params.material);

    const response = await fetch(`${config.apiUrl}/data-manager/export?${query}`);
    return response.json();
  },

  // 下载导出文件
  downloadFile: (fileName: string) => {
    window.open(`${config.apiUrl}/data-manager/download/${fileName}`, '_blank');
  },

  // 备份数据库
  backupDatabase: async () => {
    const response = await fetch(`${config.apiUrl}/data-manager/backup`, { method: 'POST' });
    return response.json();
  },

  // 获取备份列表
  getBackups: async () => {
    const response = await fetch(`${config.apiUrl}/data-manager/backups`);
    return response.json();
  },

  // 清洗数据
  cleanData: async () => {
    const response = await fetch(`${config.apiUrl}/data-manager/clean`, { method: 'POST' });
    return response.json();
  },

  // 导入数据
  importData: async (filePath: string) => {
    const response = await fetch(`${config.apiUrl}/data-manager/import?file_path=${encodeURIComponent(filePath)}`, {
      method: 'POST'
    });
    return response.json();
  },
};

// 调差模板 API
export const adjustmentTemplateApi = {
  // 生成模板
  generateTemplate: async (params: {
    project_name?: string;
    rule_name?: string;
    material_type?: string;
    include_examples?: boolean;
  } = {}) => {
    const query = new URLSearchParams();
    if (params.project_name) query.set('project_name', params.project_name);
    if (params.rule_name) query.set('rule_name', params.rule_name);
    if (params.material_type) query.set('material_type', params.material_type);
    if (params.include_examples !== undefined) query.set('include_examples', String(params.include_examples));

    const response = await fetch(`${config.apiUrl}/adjustment-template/template?${query}`);
    return response.json();
  },

  // 生成带价格的模板（自动联动）
  generateTemplateWithPrices: async (params: {
    project_name?: string;
    rule_name?: string;
    material_type?: string;
    price_date?: string;
  } = {}) => {
    const query = new URLSearchParams();
    if (params.project_name) query.set('project_name', params.project_name);
    if (params.rule_name) query.set('rule_name', params.rule_name);
    if (params.material_type) query.set('material_type', params.material_type);
    if (params.price_date) query.set('price_date', params.price_date);

    const response = await fetch(`${config.apiUrl}/adjustment-template/template/with-prices?${query}`);
    return response.json();
  },

  // 下载模板
  downloadTemplate: (fileName: string) => {
    window.open(`${config.apiUrl}/adjustment-template/download/${encodeURIComponent(fileName)}`, '_blank');
  },

  // 获取模板列表
  listTemplates: async () => {
    const response = await fetch(`${config.apiUrl}/adjustment-template/list`);
    return response.json();
  },

  // 获取自动材料清单
  getAutoMaterials: async (params: {
    material_type?: string;
    include_all_specs?: boolean;
  } = {}) => {
    const query = new URLSearchParams();
    if (params.material_type) query.set('material_type', params.material_type);
    if (params.include_all_specs !== undefined) query.set('include_all_specs', String(params.include_all_specs));

    const response = await fetch(`${config.apiUrl}/adjustment-template/materials?${query}`);
    return response.json();
  },

  // 获取施工期均价
  getPeriodAverage: async (params: {
    material_name: string;
    start_date: string;
    end_date: string;
    spec?: string;
    brands?: string;
  }) => {
    const query = new URLSearchParams();
    query.set('material_name', params.material_name);
    query.set('start_date', params.start_date);
    query.set('end_date', params.end_date);
    if (params.spec) query.set('spec', params.spec);
    if (params.brands) query.set('brands', params.brands);

    const response = await fetch(`${config.apiUrl}/adjustment-template/prices/period-average?${query}`);
    return response.json();
  },

  // 批量获取施工期均价
  batchGetPeriodAverage: async (params: {
    materials: string;
    start_date: string;
    end_date: string;
    brands?: string;
  }) => {
    const query = new URLSearchParams();
    query.set('materials', params.materials);
    query.set('start_date', params.start_date);
    query.set('end_date', params.end_date);
    if (params.brands) query.set('brands', params.brands);

    const response = await fetch(`${config.apiUrl}/adjustment-template/prices/batch-period-average?${query}`);
    return response.json();
  },
};

// 指标库分析报告 API
export const indicatorReportApi = {
  // 生成分析报告
  generateReport: async (params: {
    project: {
      name: string;
      category: string;
      location: string;
      structure: string;
      floor_above: number;
      floor_below?: number;
      area_total: number;
      height: number;
    };
    indicators: {
      unit_cost: number;
      unit_structure?: number;
      unit_installation?: number;
      unit_decoration?: number;
      steel_content?: number;
      concrete_content?: number;
    };
  }) => {
    const response = await fetch(`${config.apiUrl}/indicator-report/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    });
    return response.json();
  },

  // 快速匹配指标
  matchIndicators: async (params: {
    category: string;
    location: string;
    structure: string;
    height: number;
  }) => {
    const query = new URLSearchParams(params).toString();
    const response = await fetch(`${config.apiUrl}/indicator-report/match?${query}`);
    return response.json();
  },

  // 获取指标库汇总
  getDatabaseSummary: async () => {
    const response = await fetch(`${config.apiUrl}/indicator-report/database/summary`);
    return response.json();
  },

  // 获取指标库项目列表
  listDatabaseProjects: async (params?: {
    category?: string;
    location?: string;
    limit?: number;
  }) => {
    const query = new URLSearchParams();
    if (params?.category) query.set('category', params.category);
    if (params?.location) query.set('location', params.location);
    if (params?.limit) query.set('limit', String(params.limit));
    const queryStr = query.toString();
    const response = await fetch(`${config.apiUrl}/indicator-report/database/list${queryStr ? '?' + queryStr : ''}`);
    return response.json();
  },
};