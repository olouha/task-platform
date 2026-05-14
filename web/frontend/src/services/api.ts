// API 服务配置
// 连接 Cloudflare Workers 后端

// Workers 后端地址
const API_BASE_URL = 'https://taskplatform-api.447904942.workers.dev';

// 本地后端地址 (用于价格数据)
const LOCAL_API_URL = 'http://localhost:8000';

export const config = {
  apiUrl: API_BASE_URL,
  localApiUrl: LOCAL_API_URL,
};

// 请求封装
async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;

  const defaultHeaders: HeadersInit = {
    'Content-Type': 'application/json',
  };

  const response = await fetch(url, {
    ...options,
    headers: {
      ...defaultHeaders,
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Unknown error' }));
    throw new Error(error.error || `HTTP ${response.status}`);
  }

  return response.json();
}

// 本地请求封装
async function localRequest<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${LOCAL_API_URL}${endpoint}`;

  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    return response.json();
  } catch (error) {
    console.error('Local API error:', error);
    throw error;
  }
}

// ===== 项目 API =====

export interface Project {
  id: string;
  name: string;
  description?: string;
  status?: string;
  created_at?: string;
  updated_at?: string;
}

export const projectsApi = {
  list: () => request<Project[]>('/api/projects'),
  get: (id: string) => request<Project>(`/api/projects/${id}`),
  create: (data: Partial<Project>) => request<Project>('/api/projects', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  update: (id: string, data: Partial<Project>) => request<Project>(`/api/projects/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  }),
  delete: (id: string) => request<{ success: boolean }>(`/api/projects/${id}`, {
    method: 'DELETE',
  }),
};

// ===== 材料 API =====

export interface Material {
  id: string;
  name: string;
  type?: string;
  unit?: string;
  current_price?: number;
  created_at?: string;
  updated_at?: string;
}

export const materialsApi = {
  list: () => request<Material[]>('/api/materials'),
  get: (id: string) => request<Material>(`/api/materials/${id}`),
  create: (data: Partial<Material>) => request<Material>('/api/materials', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  update: (id: string, data: Partial<Material>) => request<Material>(`/api/materials/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  }),
  delete: (id: string) => request<{ success: boolean }>(`/api/materials/${id}`, {
    method: 'DELETE',
  }),
};

// ===== 价格历史 API =====

export interface PriceRecord {
  id: string;
  material_id: string;
  price: number;
  source: string;
  recorded_at: string;
}

export const priceHistoryApi = {
  list: (materialId?: string) => {
    const params = materialId ? `?material_id=${materialId}` : '';
    return request<PriceRecord[]>(`/api/price-history${params}`);
  },
  create: (data: Partial<PriceRecord>) => request<PriceRecord>('/api/price-history', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
};

// ===== 统计 API =====

export interface Stats {
  projects: number;
  materials: number;
  priceHistory: number;
  timestamp: string;
}

export const statsApi = {
  get: () => request<Stats>('/api/stats'),
};

// ===== 健康检查 =====

export const healthApi = {
  check: () => request<{ status: string; version: string; timestamp: string }>('/health'),
};

// ===== 烟台钢筋价格 API =====

export interface YantaiPrice {
  material_id: string;
  material_name: string;
  spec: string;
  material_type: string;
  brand: string;
  price: number;
  price_max?: number;
  unit: string;
  price_change: string;
  remark: string;
  steel_code: string;
  region: string;
  date?: string;
  time?: string;
}

export interface YantaiSummary {
  total_count: number;
  brands: string[];
  material_types: Record<string, number>;
  brands_detail: Record<string, string[]>;
}

export const yantaiApi = {
  // 获取最新价格
  getLatest: () => localRequest<{ success: boolean; prices: YantaiPrice[]; sheet?: string }>('/api/yantai-prices/latest'),

  // 获取价格汇总
  getSummary: () => localRequest<YantaiSummary>('/api/yantai-prices/summary'),

  // 获取所有日期的sheets
  getSheets: () => localRequest<{ success: boolean; sheets: string[] }>('/api/price-sources/sheets'),

  // 获取指定日期的价格
  getByDate: (date: string) => localRequest<{ success: boolean; prices: YantaiPrice[]; sheet: string }>(`/api/yantai-prices/latest?date=${date}`),

  // 手动抓取
  fetch: () => localRequest<{ success: boolean; message: string }>('/api/yantai-prices/fetch', { method: 'POST' }),

  // 获取抓取状态
  getStatus: () => localRequest<{ can_fetch: boolean; reason: string; last_fetch?: string }>('/api/yantai-prices/status'),
};

export default {
  projects: projectsApi,
  materials: materialsApi,
  priceHistory: priceHistoryApi,
  stats: statsApi,
  health: healthApi,
  yantai: yantaiApi,
};