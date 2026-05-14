# TaskPlatform 部署指南

## 一、部署架构

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   用户A      │     │   用户B      │     │   用户C      │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                    │
       └────────────────────┼────────────────────┘
                           │
                    ┌──────▼───────┐
                    │   Railway     │
                    │  (后端+定时) │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │   Vercel     │
                    │   (前端)     │
                    └──────────────┘
```

## 二、快速部署（推荐）

### 步骤1：部署后端到 Railway

1. 访问 https://railway.app 并用 GitHub 登录
2. 点击 "New Project" → "Deploy from GitHub repo"
3. 选择 `web/backend` 目录
4. 添加环境变量（从 `.env.example` 复制）：
   ```
   MYSTEEL_USERNAME=你的我的钢铁网用户名
   MYSTEEL_PASSWORD=你的我的钢铁网密码
   ```
5. Railway 自动检测 Python 并部署
6. 部署完成后，记下后端地址（如 `https://task-platform.railway.app`）

### 步骤2：部署前端到 Vercel

1. 修改 `web/frontend/src/pages/PriceMonitor.tsx` 中的 API 地址：
   ```typescript
   // 改成你的 Railway 后端地址
   const LOCAL_API = 'https://你的后端地址.railway.app'
   ```

2. 同样修改 `web/frontend/src/pages/Settings.tsx` 中的地址

3. 访问 https://vercel.com 并登录
4. 点击 "Add New" → "Project"
5. 导入 `web/frontend` 目录
6. 构建命令: `npm run build`
7. 输出目录: `dist`
8. 点击 Deploy

### 步骤3：配置 CORS

在 Railway 后端环境变量中添加：
```
ALLOWED_ORIGINS=https://你的vercel地址.vercel.app
```

## 三、定时抓取

Railway 部署后会自动每天早上8点执行价格抓取。

手动触发：
1. Railway 项目页面 → "Triggers" 标签
2. 点击 "Run Now"

## 四、访问地址

部署完成后：
- **前端**: `https://你的项目.vercel.app`
- **后端 API**: `https://xxxx.railway.app`
- **WebSocket**: `wss://xxxx.railway.app/ws`

## 五、功能状态

| 功能 | 状态 |
|------|------|
| 前端部署 | 待完成 |
| 后端部署 | 待完成 |
| 定时抓取 | ✅ 已配置 |
| WebSocket推送 | ✅ 已实现 |
| 凭据管理 | ✅ 已实现 |
| Excel导出 | ✅ 已实现 |