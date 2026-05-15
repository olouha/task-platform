// API 服务配置
// 连接 Railway 后端（烟台钢筋价格）

const API_BASE_URL = 'https://task-platform-production-a96f.up.railway.app';

// 本地后端地址（仅开发用）
const LOCAL_API_URL = 'http://localhost:8000';

export const config = {
  apiUrl: API_BASE_URL,
  localApiUrl: LOCAL_API_URL,
};