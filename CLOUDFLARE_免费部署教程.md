# Cloudflare 免费云端部署教程

## 第一步：注册 Cloudflare（2分钟）

1. 打开：**https://dash.cloudflare.com/**
2. 点击 "Sign up"（注册）
3. 输入邮箱和密码
4. 完成验证

---

## 第二步：创建一个 Worker

1. 登录后，点击左侧菜单 **"Workers & Pages"**
2. 点击 **"Create Application"**
3. 点击 **"Create Worker"**
4. 给 Worker 取个名字，比如：`taskplatform-db`
5. 点击 **"Deploy"**

---

## 第三步：粘贴后端代码

1. 在编辑器中，删除所有代码
2. 复制下面这个代码，粘贴进去：

```javascript
// TaskPlatform Cloudflare Worker Backend
// 免费云端数据库

const DB_KEY = 'taskplatform_data';
const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
  'Content-Type': 'application/json'
};

async function getDB(env) {
  let data = await env.KV.get(DB_KEY);
  if (!data) {
    data = JSON.stringify({ tasks: [], logs: [], data: {}, config: {} });
    await env.KV.put(DB_KEY, data);
  }
  return JSON.parse(data);
}

async function saveDB(env, data) {
  await env.KV.put(DB_KEY, JSON.stringify(data));
}

async function handleRequest(request, env) {
  const url = new URL(request.url);
  const path = url.pathname;

  // 处理 CORS 预检请求
  if (request.method === 'OPTIONS') {
    return new Response(null, { headers: CORS_HEADERS });
  }

  // 健康检查
  if (path === '/health') {
    return new Response(JSON.stringify({ status: 'ok' }), { headers: CORS_HEADERS });
  }

  // 获取统计数据
  if (path === '/stats') {
    const db = await getDB(env);
    return new Response(JSON.stringify({
      total_tasks: db.tasks.length,
      total_logs: db.logs.length
    }), { headers: CORS_HEADERS });
  }

  // 获取所有数据
  if (path === '/data') {
    const db = await getDB(env);
    return new Response(JSON.stringify(db), { headers: CORS_HEADERS });
  }

  // 保存数据
  if (path === '/save' && request.method === 'POST') {
    try {
      const body = await request.json();
      await saveDB(env, body);
      return new Response(JSON.stringify({ success: true }), { headers: CORS_HEADERS });
    } catch (e) {
      return new Response(JSON.stringify({ error: e.message }), { 
        status: 400, 
        headers: CORS_HEADERS 
      });
    }
  }

  // 保存单个任务
  if (path.startsWith('/task/') && request.method === 'PUT') {
    const taskId = path.split('/')[2];
    const body = await request.json();
    const db = await getDB(env);
    
    const index = db.tasks.findIndex(t => t.id === taskId);
    if (index >= 0) {
      db.tasks[index] = body;
    } else {
      db.tasks.push(body);
    }
    
    await saveDB(env, db);
    return new Response(JSON.stringify({ success: true }), { headers: CORS_HEADERS });
  }

  // 删除任务
  if (path.startsWith('/task/') && request.method === 'DELETE') {
    const taskId = path.split('/')[2];
    const db = await getDB(env);
    db.tasks = db.tasks.filter(t => t.id !== taskId);
    await saveDB(env, db);
    return new Response(JSON.stringify({ success: true }), { headers: CORS_HEADERS });
  }

  // 添加日志
  if (path === '/log' && request.method === 'POST') {
    const body = await request.json();
    const db = await getDB(env);
    db.logs.push(body);
    if (db.logs.length > 1000) {
      db.logs = db.logs.slice(-1000);
    }
    await saveDB(env, db);
    return new Response(JSON.stringify({ success: true }), { headers: CORS_HEADERS });
  }

  return new Response(JSON.stringify({ error: 'Not found' }), { 
    status: 404, 
    headers: CORS_HEADERS 
  });
}

addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request, event.locals.env));
});
```

3. 点击 **"Save and Deploy"**

---

## 第四步：绑定 KV 数据库

1. 在 Workers 页面，点击刚创建的 Worker
2. 点击 **"Settings"** → **"Variables"**
3. 往下滚，找到 **"KV Namespace Bindings"**
4. 点击 **"Add binding"**
5. 设置：
   - Variable name: `KV`
   - KV namespace: 点击 "Create a namespace"
   - 输入名字：`taskplatform-db`
6. 点击 **"Save and Redeploy"**

---

## 第五步：获取 API 地址

部署成功后，你的 API 地址就是：
```
https://taskplatform-db.<你的子域名>.workers.dev
```

例如：`https://taskplatform-db.chenwang.workers.dev`

---

## 完成！

把上面的地址保存到 `config/cloud.json`：

```json
{
  "mode": "cloudflare-workers",
  "api_url": "https://taskplatform-db.chenwang.workers.dev",
  "version": "1.0.0"
}
```

---

## 分享给朋友

告诉朋友你的 API 地址，他们就能自动同步数据了！

---

准备好了吗？完成后告诉我，我们继续配置客户端！