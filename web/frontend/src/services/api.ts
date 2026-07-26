import { getSessionId } from '../auth'

// API 服务配置
// 连接后端服务器（烟台钢筋价格）

// 开发环境使用 /api 代理到后端，生产环境使用实际部署的地址
const API_BASE_URL = import.meta.env.VITE_API_URL || '';

// 辅助函数：构建API URL
// 如果 API_BASE_URL 是 '/api'（代理模式），直接拼接路径
// 如果是完整URL（如 'http://localhost:8000'），直接使用
function buildApiUrl(path: string): string {
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  if (API_BASE_URL === '/api') {
    // 代理模式：若调用方已带 /api 前缀（如 yantaiRebarApi 的 '/api/rebar/...'），直接用，
    // 避免与 API_BASE_URL='/api' 叠加成 '/api/api/...'
    if (cleanPath.startsWith('/api')) return cleanPath;
    // 否则拼上 /api：/stats -> /api/stats
    return `${API_BASE_URL}${cleanPath}`;
  }
  if (API_BASE_URL) {
    // 完整URL模式：http://localhost:8000 + /api/stats -> http://localhost:8000/api/stats
    return API_BASE_URL.replace(/\/$/, '') + cleanPath;
  }
  // 无base URL：/stats -> /stats
  return cleanPath;
}

/** 带 X-Session-ID 的 fetch 封装：用于上传/导入等需要留痕（uploaded_by）的接口 */
async function authFetch(input: RequestInfo, init: RequestInit = {}): Promise<Response> {
  const sid = getSessionId()
  const headers = new Headers(init.headers || {})
  if (sid) headers.set('X-Session-ID', sid)
  return fetch(input, { ...init, headers })
}

export const config = {
  apiUrl: API_BASE_URL,
  buildUrl: buildApiUrl,
};

export { buildApiUrl as buildUrl };

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
    const response = await fetch(`${config.apiUrl}/adjustments/prices/batch-get`, {
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
// 指标库（基础管理）API - 对应 /indicators/* 端点
export const indicatorApi = {
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
    const response = await authFetch(`${config.apiUrl}/data-manager/import?file_path=${encodeURIComponent(filePath)}`, {
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
    const query = new URLSearchParams({
      category: params.category,
      location: params.location,
      structure: params.structure,
      height: params.height.toString()
    }).toString();
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

// 烟台钢筋价格 API (统一端点)
export const yantaiRebarApi = {
  getStats: async () => {
    const response = await fetch(buildApiUrl('/api/rebar/stats'));
    return response.json();
  },
  getLatest: async (date?: string, limit = 500) => {
    const url = date
      ? buildApiUrl(`/api/rebar/latest?date=${encodeURIComponent(date)}&limit=${limit}`)
      : buildApiUrl(`/api/rebar/latest?limit=${limit}`);
    const response = await fetch(url);
    return response.json();
  },
  getByRange: async (start_date: string, end_date: string, material?: string, spec?: string) => {
    const params = new URLSearchParams({ start_date, end_date });
    if (material) params.append('material', material);
    if (spec) params.append('spec', spec);
    const response = await fetch(config.buildUrl(`/api/rebar/range?${params}`));
    return response.json();
  },
  getTrend: async (material?: string, spec?: string, days = 365, start_date?: string, end_date?: string) => {
    const params = new URLSearchParams({ days: String(days) });
    if (material) params.append('material', material);
    if (spec) params.append('spec', spec);
    if (start_date) params.append('start_date', start_date);
    if (end_date) params.append('end_date', end_date);
    const response = await fetch(config.buildUrl(`/api/rebar/trend?${params}`));
    return response.json();
  },
  getMaterials: async () => {
    const response = await fetch(buildApiUrl('/api/rebar/materials'));
    return response.json();
  },
  getSpecs: async (material?: string) => {
    const url = material
      ? buildApiUrl(`/api/rebar/specs?material=${encodeURIComponent(material)}`)
      : buildApiUrl('/api/rebar/specs');
    const response = await fetch(url);
    return response.json();
  },
  getDates: async (start_date?: string, end_date?: string) => {
    const params = new URLSearchParams();
    if (start_date) params.append('start_date', start_date);
    if (end_date) params.append('end_date', end_date);
    const url = config.buildUrl(`/api/rebar/dates${params.toString() ? '?' + params : ''}`);
    const response = await fetch(url);
    return response.json();
  },
  search: async (keyword: string, date?: string, limit = 100) => {
    const params = new URLSearchParams({ keyword, limit: String(limit) });
    if (date) params.append('date', date);
    const response = await fetch(config.buildUrl(`/api/rebar/search?${params}`));
    return response.json();
  },
  // 报告摘要API
  getReportSummary: async (start_date?: string, end_date?: string, material_type?: string) => {
    const params = new URLSearchParams();
    if (start_date) params.append('start_date', start_date);
    if (end_date) params.append('end_date', end_date);
    if (material_type) params.append('material_type', material_type);
    const url = config.buildUrl(`/api/rebar/report/summary${params.toString() ? '?' + params : ''}`);
    const response = await fetch(url);
    return response.json();
  },
  // 价格影响因素API
  getInfluencingFactors: async () => {
    const response = await fetch(buildApiUrl('/api/rebar/report/influencing-factors'));
    return response.json();
  },
  // 凭据管理（我的钢铁网登录凭据）
  getCredentialsStatus: async () => {
    const response = await fetch(buildApiUrl('/api/rebar/credentials'));
    return response.json();
  },
  updateCredentials: async (username: string, password: string) => {
    const response = await fetch(buildApiUrl('/api/rebar/credentials'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    return response.json();
  },
  // 上传钢筋价格截图识别（仅识别，返回可预览编辑的价格列表，不入库）
  recognizeScreenshot: async (file: File, date?: string, period?: 'AM' | 'PM') => {
    const formData = new FormData();
    formData.append('file', file);
    if (date) formData.append('date', date);
    if (period) formData.append('period', period);
    const response = await fetch(buildApiUrl('/api/rebar/recognize-screenshot'), {
      method: 'POST',
      body: formData,
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `请求失败 (${response.status})`);
    }
    return response.json();
  },
  // 确认入库（复用现有 /api/rebar/prices 端点）
  insertPrices: async (prices: any[]) => {
    const response = await authFetch(buildApiUrl('/api/rebar/prices'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(prices),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `入库失败 (${response.status})`);
    }
    return response.json();
  },
  // 上传 Excel 解析（WPS 转图/复制网页粘贴所得，仅解析，不入库）
  parseExcel: async (file: File, date?: string, period?: 'AM' | 'PM') => {
    const formData = new FormData();
    formData.append('file', file);
    if (date) formData.append('date', date);
    if (period) formData.append('period', period);
    const response = await fetch(buildApiUrl('/api/rebar/parse-excel'), {
      method: 'POST',
      body: formData,
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `请求失败 (${response.status})`);
    }
    return response.json();
  },
};

// 指标库项目管理 API - 对应 /indicator-report/database/* 端点
export const indicatorDatabaseApi = {
  // 获取指标库列表
  list: async (params?: { category?: string; location?: string; limit?: number }) => {
    const query = new URLSearchParams();
    if (params?.category) query.append('category', params.category);
    if (params?.location) query.append('location', params.location);
    if (params?.limit) query.append('limit', String(params.limit));
    const queryStr = query.toString();
    const response = await fetch(`${config.apiUrl}/indicator-report/database/list${queryStr ? '?' + queryStr : ''}`);
    if (!response.ok) throw new Error('获取指标库列表失败');
    return response.json();
  },

  // 获取单个项目
  get: async (id: string) => {
    const response = await fetch(`${config.apiUrl}/indicator-report/database/${id}`);
    if (!response.ok) throw new Error('获取项目详情失败');
    return response.json();
  },

  // 创建项目
  create: async (data: Record<string, unknown>) => {
    const response = await fetch(`${config.apiUrl}/indicator-report/database/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error('创建项目失败');
    return response.json();
  },

  // 更新项目
  update: async (id: string, data: Record<string, unknown>) => {
    const response = await fetch(`${config.apiUrl}/indicator-report/database/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error('更新项目失败');
    return response.json();
  },

  // 删除项目
  delete: async (id: string) => {
    const response = await fetch(`${config.apiUrl}/indicator-report/database/${id}`, {
      method: 'DELETE',
    });
    if (!response.ok) throw new Error('删除项目失败');
    return response.json();
  },

  // 导入 Excel
  import: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await authFetch(`${config.apiUrl}/indicator-report/import`, {
      method: 'POST',
      body: formData,
    });
    if (!response.ok) throw new Error('导入失败');
    return response.json();
  },

  // 导出（JSON 或 Excel）
  export: async (format: 'json' | 'excel' = 'json', category?: string) => {
    const query = new URLSearchParams();
    query.append('format', format);
    if (category) query.append('category', category);
    const response = await fetch(`${config.apiUrl}/indicator-report/export?${query.toString()}`);
    if (!response.ok) throw new Error('导出失败');
    if (format === 'excel') {
      return response.blob();
    }
    return response.json();
  },
};

// 指标库导入 API - 对应 /indicator-library/* 端点
import type {
  IndicatorLibrarySummary,
  IndicatorLibraryDetail,
  ValidationWarning,
  ValidationResult,
  ImportFieldError,
  ImportPreviewItem,
  ImportPreviewResult,
  ImportResult,
  IndicatorLibraryStats,
} from '../types/indicator';

export type {
  IndicatorLibrarySummary,
  IndicatorLibraryDetail,
  ValidationWarning,
  ValidationResult,
  ImportFieldError,
  ImportPreviewItem,
  ImportPreviewResult,
  ImportResult,
  IndicatorLibraryStats,
} from '../types/indicator';

export const indicatorLibraryApi = {
  // 获取汇总列表
  getSummary: async (params?: {
    category?: string;
    location?: string;
    limit?: number;
  }): Promise<IndicatorLibrarySummary[]> => {
    const query = new URLSearchParams();
    if (params?.category) query.append('category', params.category);
    if (params?.location) query.append('location', params.location);
    if (params?.limit) query.append('limit', String(params.limit));
    const queryStr = query.toString();

    const response = await fetch(`${config.apiUrl}/indicator-library/summary${queryStr ? '?' + queryStr : ''}`);
    if (!response.ok) throw new Error('获取汇总列表失败');
    return response.json();
  },

  // 获取项目详情
  getDetail: async (id: string): Promise<IndicatorLibraryDetail> => {
    const response = await fetch(`${config.apiUrl}/indicator-library/${id}`);
    if (!response.ok) {
      if (response.status === 404) throw new Error('项目不存在');
      throw new Error('获取项目详情失败');
    }
    return response.json();
  },

  // 创建项目
  create: async (data: Partial<IndicatorLibraryDetail>): Promise<IndicatorLibraryDetail> => {
    const response = await authFetch(`${config.apiUrl}/indicator-library/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: '创建失败' }));
      throw new Error(error.detail || '创建失败');
    }
    return response.json();
  },

  // 更新项目
  update: async (id: string, data: Partial<IndicatorLibraryDetail>): Promise<IndicatorLibraryDetail> => {
    const response = await fetch(`${config.apiUrl}/indicator-library/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: '更新失败' }));
      throw new Error(error.detail || '更新失败');
    }
    return response.json();
  },

  // 删除项目
  delete: async (id: string): Promise<{ success: boolean }> => {
    const response = await fetch(`${config.apiUrl}/indicator-library/${id}`, {
      method: 'DELETE',
    });
    if (!response.ok) throw new Error('删除失败');
    return response.json();
  },

  // 验证数据
  validate: async (data: Partial<IndicatorLibraryDetail>): Promise<ValidationResult> => {
    const response = await fetch(`${config.apiUrl}/indicator-library/validate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error('验证失败');
    return response.json();
  },

  // 预览 Excel 数据（解析并验证）
  preview: async (file: File): Promise<ImportPreviewResult> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await authFetch(`${config.apiUrl}/indicator-library/preview`, {
      method: 'POST',
      body: formData,
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: '预览失败' }));
      throw new Error(error.detail || '预览失败');
    }
    return response.json();
  },

  // 导入 Excel 数据
  import: async (file: File): Promise<ImportResult> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await authFetch(`${config.apiUrl}/indicator-library/import`, {
      method: 'POST',
      body: formData,
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: '导入失败' }));
      throw new Error(error.detail || '导入失败');
    }
    return response.json();
  },

  // 导出 Excel
  exportExcel: async (category?: string): Promise<Blob> => {
    const query = category ? `?category=${encodeURIComponent(category)}` : '';
    const response = await fetch(`${config.apiUrl}/indicator-library/export${query}`);
    if (!response.ok) throw new Error('导出失败');
    return response.blob();
  },

  // 下载导出文件
  downloadExport: (blob: Blob, filename: string) => {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  },

  // 获取统计概览
  getStats: async (): Promise<IndicatorLibraryStats> => {
    const response = await fetch(`${config.apiUrl}/indicator-library/stats/overview`);
    if (!response.ok) throw new Error('获取统计数据失败');
    return response.json();
  },

  // 获取导入模板
  getTemplate: async () => {
    const response = await fetch(`${config.apiUrl}/indicator-library/template`);
    if (!response.ok) throw new Error('获取模板失败');
    return response.json();
  },

  // 下载导入模板（返回 Blob 以便正确下载）
  downloadTemplate: async () => {
    const response = await fetch(`${config.apiUrl}/indicator-library/template`);
    if (!response.ok) throw new Error('下载模板失败');
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = '指标库导入模板.xlsx';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  },

  // 自动导入（先校验后入库）
  autoImport: async (file: File): Promise<{
    success: boolean;
    imported: number;
    total: number;
    warnings: any[];
    errors: string[];
    error_details?: ImportFieldError[];
  }> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await authFetch(`${config.apiUrl}/indicator-library/auto-import`, {
      method: 'POST',
      body: formData,
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: '自动导入失败' }));
      throw new Error(error.detail || '自动导入失败');
    }
    return response.json();
  },

  // 获取导入历史
  getImportHistory: async (limit: number = 50): Promise<any[]> => {
    const response = await fetch(`${config.apiUrl}/indicator-library/import-history?limit=${limit}`);
    if (!response.ok) throw new Error('获取导入历史失败');
    return response.json();
  },

  // 获取导入详情
  getImportDetail: async (importId: number): Promise<any> => {
    const response = await fetch(`${config.apiUrl}/indicator-library/import-history/${importId}`);
    if (!response.ok) throw new Error('获取导入详情失败');
    return response.json();
  },

  // 获取版本历史
  getVersionHistory: async (projectId: string): Promise<any[]> => {
    const response = await fetch(`${config.apiUrl}/indicator-library/versions/${projectId}`);
    if (!response.ok) throw new Error('获取版本历史失败');
    return response.json();
  },

  // 获取快照详情
  getSnapshotDetail: async (projectId: string, snapshotId: string): Promise<any> => {
    const response = await fetch(`${config.apiUrl}/indicator-library/versions/${projectId}/snapshot/${snapshotId}`);
    if (!response.ok) throw new Error('获取快照详情失败');
    return response.json();
  },

  // 回滚到指定版本
  rollbackVersion: async (projectId: string, snapshotId: string): Promise<{ success: boolean }> => {
    const response = await fetch(`${config.apiUrl}/indicator-library/versions/${projectId}/rollback/${snapshotId}`, {
      method: 'POST',
    });
    if (!response.ok) throw new Error('回滚失败');
    return response.json();
  },

  // 数据一致性校验
  syncCheck: async (): Promise<{
    sqlite: { project_count: number; snapshot_count: number; import_count: number; max_version: number };
    last_update: string | null;
    last_import: string | null;
    in_sync: boolean;
  }> => {
    const response = await fetch(`${config.apiUrl}/indicator-library/data-sync`);
    if (!response.ok) throw new Error('数据一致性校验失败');
    return response.json();
  },
};

// 材料管理 API（本地 SQLite）
export interface MaterialCategory {
  id: string;
  name: string;
  icon?: string;
  color?: string;
  sort_order?: number;
  count?: number;
}

export interface MaterialItem {
  id: string;
  category_id?: string;
  category?: string;
  name: string;
  spec?: string;
  unit?: string;
  base_price?: number;
  source?: string;
  source_id?: string;
  is_adjusted?: boolean;
  adjustment_threshold?: number;
}

export const materialsApi = {
  // 分类
  listCategories: async (): Promise<MaterialCategory[]> => {
    const response = await fetch(`${config.apiUrl}/materials/categories`);
    if (!response.ok) throw new Error('获取分类失败');
    return response.json();
  },
  createCategory: async (data: Partial<MaterialCategory>): Promise<MaterialCategory> => {
    const response = await fetch(`${config.apiUrl}/materials/categories`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error('创建分类失败');
    return response.json();
  },
  updateCategory: async (id: string, data: Partial<MaterialCategory>): Promise<MaterialCategory> => {
    const response = await fetch(`${config.apiUrl}/materials/categories/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error('更新分类失败');
    return response.json();
  },
  deleteCategory: async (id: string): Promise<{ success: boolean }> => {
    const response = await fetch(`${config.apiUrl}/materials/categories/${id}`, { method: 'DELETE' });
    if (!response.ok) throw new Error('删除分类失败');
    return response.json();
  },
  // 材料
  list: async (categoryId?: string): Promise<MaterialItem[]> => {
    const query = categoryId ? `?category_id=${encodeURIComponent(categoryId)}` : '';
    const response = await fetch(`${config.apiUrl}/materials/${query}`);
    if (!response.ok) throw new Error('获取材料失败');
    return response.json();
  },
  create: async (data: Partial<MaterialItem>): Promise<MaterialItem> => {
    const response = await fetch(`${config.apiUrl}/materials/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error('创建材料失败');
    return response.json();
  },
  update: async (id: string, data: Partial<MaterialItem>): Promise<MaterialItem> => {
    const response = await fetch(`${config.apiUrl}/materials/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error('更新材料失败');
    return response.json();
  },
  delete: async (id: string): Promise<{ success: boolean }> => {
    const response = await fetch(`${config.apiUrl}/materials/${id}`, { method: 'DELETE' });
    if (!response.ok) throw new Error('删除材料失败');
    return response.json();
  },
};

// 默认导出（兼容 `import api from '../services/api'`）
export default {
  config,
  statsApi,
  projectsApi,
  adjustmentRulesApi,
  adjustmentCalcApi,
  schedulerApi,
  fetchApi,
  cronFetchApi,
  costReferenceApi,
  indicatorApi,
  adjustmentProjectApi,
  fileParserApi,
  costHistoryApi,
  adjustmentPricesApi,
  dataManagerApi,
  adjustmentTemplateApi,
  indicatorReportApi,
  yantaiRebarApi,
  indicatorDatabaseApi,
  indicatorLibraryApi,
  materialsApi,
};