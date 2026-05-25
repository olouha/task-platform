// API 服务配置
// 连接 Railway 后端（烟台钢筋价格）

const API_BASE_URL = 'https://task-platform-production-a96f.up.railway.app';

// 本地后端地址（仅开发用）
const LOCAL_API_URL = 'http://localhost:8000';

export const config = {
  apiUrl: API_BASE_URL,
  localApiUrl: LOCAL_API_URL,
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
    const response = await fetch(`${LOCAL_API_URL}/api/stats`);
    return response.json();
  }
};

// Projects API
export const projectsApi = {
  list: async () => {
    const response = await fetch(`${LOCAL_API_URL}/api/projects`);
    return response.json();
  },
  create: async (data: any) => {
    const response = await fetch(`${LOCAL_API_URL}/api/projects`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return response.json();
  },
  delete: async (id: string) => {
    const response = await fetch(`${LOCAL_API_URL}/api/projects/${id}`, {
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
    const response = await fetch(`${LOCAL_API_URL}/api/adjustment-rules/`);
    return response.json();
  },
  get: async (id: string) => {
    const response = await fetch(`${LOCAL_API_URL}/api/adjustment-rules/${id}`);
    return response.json();
  },
  create: async (data: any) => {
    const response = await fetch(`${LOCAL_API_URL}/api/adjustment-rules/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return response.json();
  },
  update: async (id: string, data: any) => {
    const response = await fetch(`${LOCAL_API_URL}/api/adjustment-rules/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return response.json();
  },
  delete: async (id: string) => {
    const response = await fetch(`${LOCAL_API_URL}/api/adjustment-rules/${id}`, {
      method: 'DELETE',
    });
    return response.json();
  },
  getPresets: async () => {
    const response = await fetch(`${LOCAL_API_URL}/api/adjustment-rules/presets`);
    return response.json();
  },
  applyPreset: async (_presetName: string, projectName: string) => {
    const response = await fetch(`${LOCAL_API_URL}/api/adjustment-rules/apply-preset`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 项目名称: projectName }),
    });
    return response.json();
  },
  saveBidPrices: async (ruleId: string, bidPrices: any[]) => {
    const response = await fetch(`${LOCAL_API_URL}/api/adjustment-rules/bid-prices`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ rule_id: ruleId, bid_prices: bidPrices }),
    });
    return response.json();
  },
  getBidPrices: async (ruleId: string) => {
    const response = await fetch(`${LOCAL_API_URL}/api/adjustment-rules/${ruleId}/bid-prices`);
    return response.json();
  },
};

// 调差计算 API
export const adjustmentCalcApi = {
  calculate: async (request: any) => {
    const response = await fetch(`${LOCAL_API_URL}/api/adjustments/calculate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });
    return response.json();
  },
  calculateByProject: async (projectId: string) => {
    const response = await fetch(`${LOCAL_API_URL}/api/adjustments/calculate-by-project/${projectId}`, {
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
    const response = await fetch(`${LOCAL_API_URL}/api/adjustments/calculate-simple?${query}`);
    return response.json();
  },
  validateConfig: async (config: any) => {
    const response = await fetch(`${LOCAL_API_URL}/api/adjustments/validate-config`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    });
    return response.json();
  },
};

// 调度器 API
export const schedulerApi = {
  getStatus: async () => {
    const response = await fetch(`${LOCAL_API_URL}/api/scheduler/status`);
    return response.json();
  },
  getTaskStatus: async (sourceId: string) => {
    const response = await fetch(`${LOCAL_API_URL}/api/scheduler/${sourceId}/status`);
    return response.json();
  },
  executeTask: async (sourceId: string, force: boolean = false) => {
    const response = await fetch(`${LOCAL_API_URL}/api/scheduler/${sourceId}/execute?force=${force}`, {
      method: 'POST',
    });
    return response.json();
  },
  executeAllPending: async () => {
    const response = await fetch(`${LOCAL_API_URL}/api/scheduler/execute-all`, {
      method: 'POST',
    });
    return response.json();
  },
  executeAllSites: async (force: boolean = false) => {
    const response = await fetch(`${LOCAL_API_URL}/api/scheduler/execute-all-sites?force=${force}`, {
      method: 'POST',
    });
    return response.json();
  },
  forceFetchAll: async () => {
    const response = await fetch(`${LOCAL_API_URL}/api/scheduler/force-fetch-all`, {
      method: 'POST',
    });
    return response.json();
  },
  getNextExecution: async () => {
    const response = await fetch(`${LOCAL_API_URL}/api/scheduler/next-execution`);
    return response.json();
  },
  getSupportedMaterials: async () => {
    const response = await fetch(`${LOCAL_API_URL}/api/scheduler/supported-materials`);
    return response.json();
  },
};

// 人工抓取 API
export const fetchApi = {
  getFetchStatus: async () => {
    const response = await fetch(`${LOCAL_API_URL}/api/fetch/status`);
    return response.json();
  },
  triggerManualFetch: async (cookies: any[]) => {
    const response = await fetch(`${LOCAL_API_URL}/api/fetch/manual`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cookies }),
    });
    return response.json();
  },
  triggerAutoFetch: async () => {
    const response = await fetch(`${LOCAL_API_URL}/api/fetch/auto`, {
      method: 'POST',
    });
    return response.json();
  },
  getManualRequired: async () => {
    const response = await fetch(`${LOCAL_API_URL}/api/fetch/manual-required`);
    return response.json();
  },
  getExcelData: async () => {
    const response = await fetch(`${LOCAL_API_URL}/api/fetch/excel-data`);
    return response.json();
  },
  downloadExcel: () => {
    window.open(`${LOCAL_API_URL}/api/fetch/download`, '_blank');
  },
  getCookieGuide: async () => {
    const response = await fetch(`${LOCAL_API_URL}/api/fetch/export-cookie-guide`);
    return response.json();
  },
};

// 定时抓取 API (Cloudflare Workers cron 触发)
export const cronFetchApi = {
  fetchToday: async () => {
    const response = await fetch(`${LOCAL_API_URL}/api/cron/fetch-today`);
    return response.json();
  },
  getStatus: async () => {
    const response = await fetch(`${LOCAL_API_URL}/api/cron/status`);
    return response.json();
  },
  forceFetch: async () => {
    const response = await fetch(`${LOCAL_API_URL}/api/cron/force-fetch`, {
      method: 'POST',
    });
    return response.json();
  },
  getLatest: async () => {
    const response = await fetch(`${LOCAL_API_URL}/api/cron/latest`);
    return response.json();
  },
};

// 造价参考价 API
export const costReferenceApi = {
  getSources: async () => {
    const response = await fetch(`${LOCAL_API_URL}/api/cost-reference/sources`);
    return response.json();
  },
  getCategories: async () => {
    const response = await fetch(`${LOCAL_API_URL}/api/cost-reference/categories`);
    return response.json();
  },
  getSummary: async () => {
    const response = await fetch(`${LOCAL_API_URL}/api/cost-reference/summary`);
    return response.json();
  },
  getSteelPrices: async (params?: { spec?: string; steel_type?: string }) => {
    const query = new URLSearchParams(params || {}).toString();
    const response = await fetch(`${LOCAL_API_URL}/api/cost-reference/steel${query ? '?' + query : ''}`);
    return response.json();
  },
  getSteelTypes: async () => {
    const response = await fetch(`${LOCAL_API_URL}/api/cost-reference/steel/types`);
    return response.json();
  },
  getSteelSpecs: async () => {
    const response = await fetch(`${LOCAL_API_URL}/api/cost-reference/steel/specs`);
    return response.json();
  },
  getConcretePrices: async (params?: { min_grade?: string; max_grade?: string }) => {
    const query = new URLSearchParams(params || {}).toString();
    const response = await fetch(`${LOCAL_API_URL}/api/cost-reference/concrete${query ? '?' + query : ''}`);
    return response.json();
  },
  getConcreteGrades: async () => {
    const response = await fetch(`${LOCAL_API_URL}/api/cost-reference/concrete/grades`);
    return response.json();
  },
  getMortarPrices: async () => {
    const response = await fetch(`${LOCAL_API_URL}/api/cost-reference/mortar`);
    return response.json();
  },
  search: async (keyword: string, category?: string) => {
    const query = new URLSearchParams({ keyword, ...(category && { category }) }).toString();
    const response = await fetch(`${LOCAL_API_URL}/api/cost-reference/search?${query}`);
    return response.json();
  },
};

// 调差项目管理 API
export const adjustmentProjectApi = {
  list: async () => {
    const response = await fetch(`${LOCAL_API_URL}/api/adjustment-projects/`);
    return response.json();
  },
  get: async (id: string) => {
    const response = await fetch(`${LOCAL_API_URL}/api/adjustment-projects/${id}`);
    return response.json();
  },
  create: async (data: {
    name: string;
    contract_no?: string;
    rule_id?: string;
    rule_name?: string;
    base_price_source?: string;
  }) => {
    const response = await fetch(`${LOCAL_API_URL}/api/adjustment-projects/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return response.json();
  },
  update: async (id: string, data: any) => {
    const response = await fetch(`${LOCAL_API_URL}/api/adjustment-projects/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return response.json();
  },
  delete: async (id: string) => {
    const response = await fetch(`${LOCAL_API_URL}/api/adjustment-projects/${id}`, {
      method: 'DELETE',
    });
    return response.json();
  },
  getMaterials: async (id: string) => {
    const response = await fetch(`${LOCAL_API_URL}/api/adjustment-projects/${id}/materials`);
    return response.json();
  },
  setMaterials: async (id: string, materials: any[]) => {
    const response = await fetch(`${LOCAL_API_URL}/api/adjustment-projects/${id}/materials`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(materials),
    });
    return response.json();
  },
  addAttachment: async (id: string, attachment: any) => {
    const response = await fetch(`${LOCAL_API_URL}/api/adjustment-projects/${id}/attachments`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(attachment),
    });
    return response.json();
  },
  deleteAttachment: async (id: string, attachmentId: string) => {
    const response = await fetch(`${LOCAL_API_URL}/api/adjustment-projects/${id}/attachments/${attachmentId}`, {
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
    const response = await fetch(`${LOCAL_API_URL}/api/file-parser/upload`, {
      method: 'POST',
      body: formData,
    });
    return response.json();
  },
  preview: async (file: File): Promise<any> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await fetch(`${LOCAL_API_URL}/api/file-parser/preview`, {
      method: 'POST',
      body: formData,
    });
    return response.json();
  },
  getTemplates: async () => {
    const response = await fetch(`${LOCAL_API_URL}/api/file-parser/templates`);
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
    const response = await fetch(`${LOCAL_API_URL}/api/adjustment-prices/query?${query}`);
    return response.json();
  },
  getPeriodAverage: async (params: {
    material: string;
    start_date: string;
    end_date: string;
    brands?: string;
  }) => {
    const query = new URLSearchParams(params).toString();
    const response = await fetch(`${LOCAL_API_URL}/api/adjustment-prices/period-average?${query}`);
    return response.json();
  },
  getBasePrice: async (params: {
    material: string;
    base_date: string;
    spec?: string;
    brands?: string;
  }) => {
    const query = new URLSearchParams(params).toString();
    const response = await fetch(`${LOCAL_API_URL}/api/adjustment-prices/base-price?${query}`);
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
    const response = await fetch(`${LOCAL_API_URL}/api/adjustment-prices/adjustment-prices?${query}`);
    return response.json();
  },
  batchGet: async (params: {
    materials: string;
    base_date: string;
    period_start: string;
    period_end: string;
  }) => {
    const query = new URLSearchParams(params).toString();
    const response = await fetch(`${LOCAL_API_URL}/api/adjustment-prices/batch?${query}`);
    return response.json();
  },
  getLatest: async (material: string, spec?: string) => {
    const query = new URLSearchParams({ material, ...(spec && { spec }) }).toString();
    const response = await fetch(`${LOCAL_API_URL}/api/adjustment-prices/latest?${query}`);
    return response.json();
  },
};