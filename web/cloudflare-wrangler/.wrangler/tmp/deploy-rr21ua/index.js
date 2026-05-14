// src/index.ts
var projectsStore = /* @__PURE__ */ new Map();
var materialsStore = /* @__PURE__ */ new Map();
var index_default = {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;
    const corsHeaders = {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, Authorization"
    };
    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders });
    }
    if (path.startsWith("/api/")) {
      try {
        if (path === "/api/projects" && request.method === "GET") {
          return new Response(JSON.stringify(Array.from(projectsStore.values())), {
            headers: { ...corsHeaders, "Content-Type": "application/json" }
          });
        }
        if (path === "/api/projects" && request.method === "POST") {
          const body = await request.json();
          const id = crypto.randomUUID();
          const project = { id, ...body, created_at: (/* @__PURE__ */ new Date()).toISOString() };
          projectsStore.set(id, project);
          return new Response(JSON.stringify(project), {
            status: 201,
            headers: { ...corsHeaders, "Content-Type": "application/json" }
          });
        }
        if (path.match(/^\/api\/projects\/[^/]+$/) && request.method === "GET") {
          const id = path.split("/")[3];
          const project = projectsStore.get(id);
          if (!project) {
            return new Response(JSON.stringify({ error: "Project not found" }), {
              status: 404,
              headers: { ...corsHeaders, "Content-Type": "application/json" }
            });
          }
          return new Response(JSON.stringify(project), {
            headers: { ...corsHeaders, "Content-Type": "application/json" }
          });
        }
        if (path.match(/^\/api\/projects\/[^/]+$/) && request.method === "PUT") {
          const id = path.split("/")[3];
          const body = await request.json();
          const existing = projectsStore.get(id);
          if (!existing) {
            return new Response(JSON.stringify({ error: "Project not found" }), {
              status: 404,
              headers: { ...corsHeaders, "Content-Type": "application/json" }
            });
          }
          const updated = { ...existing, ...body, updated_at: (/* @__PURE__ */ new Date()).toISOString() };
          projectsStore.set(id, updated);
          return new Response(JSON.stringify(updated), {
            headers: { ...corsHeaders, "Content-Type": "application/json" }
          });
        }
        if (path.match(/^\/api\/projects\/[^/]+$/) && request.method === "DELETE") {
          const id = path.split("/")[3];
          projectsStore.delete(id);
          return new Response(JSON.stringify({ success: true }), {
            headers: { ...corsHeaders, "Content-Type": "application/json" }
          });
        }
        if (path === "/api/materials" && request.method === "GET") {
          return new Response(JSON.stringify(Array.from(materialsStore.values())), {
            headers: { ...corsHeaders, "Content-Type": "application/json" }
          });
        }
        if (path === "/api/materials" && request.method === "POST") {
          const body = await request.json();
          const id = crypto.randomUUID();
          const material = { id, ...body, created_at: (/* @__PURE__ */ new Date()).toISOString() };
          materialsStore.set(id, material);
          return new Response(JSON.stringify(material), {
            status: 201,
            headers: { ...corsHeaders, "Content-Type": "application/json" }
          });
        }
        if (path === "/health") {
          return new Response(JSON.stringify({ status: "healthy", timestamp: (/* @__PURE__ */ new Date()).toISOString() }), {
            headers: { ...corsHeaders, "Content-Type": "application/json" }
          });
        }
        if (path === "/api/stats") {
          return new Response(JSON.stringify({
            projects: projectsStore.size,
            materials: materialsStore.size,
            timestamp: (/* @__PURE__ */ new Date()).toISOString()
          }), {
            headers: { ...corsHeaders, "Content-Type": "application/json" }
          });
        }
        return new Response(JSON.stringify({ error: "API not found", path }), {
          status: 404,
          headers: { ...corsHeaders, "Content-Type": "application/json" }
        });
      } catch (error) {
        return new Response(JSON.stringify({ error: "Internal server error", message: String(error) }), {
          status: 500,
          headers: { ...corsHeaders, "Content-Type": "application/json" }
        });
      }
    }
    const indexPath = "/index.html";
    return new Response(`<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>TaskPlatform - \u5DE5\u7A0B\u8C03\u5DEE\u8BA1\u7B97\u7CFB\u7EDF</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f0f2f5; }
    .container { max-width: 1200px; margin: 0 auto; }
    h1 { color: #1890ff; }
    .card { background: white; border-radius: 8px; padding: 24px; margin: 16px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
    .status { display: flex; gap: 16px; margin: 20px 0; }
    .stat { flex: 1; text-align: center; padding: 20px; background: #f8f9fa; border-radius: 8px; }
    .stat-number { font-size: 32px; font-weight: bold; color: #1890ff; }
    .stat-label { color: #666; margin-top: 8px; }
    .api-list { list-style: none; padding: 0; }
    .api-list li { padding: 12px; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; }
    .api-list li:last-child { border: none; }
    .badge { background: #1890ff; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px; }
    .badge-get { background: #52c41a; }
    .badge-post { background: #1890ff; }
    .badge-put { background: #faad14; }
    .badge-delete { background: #f5222d; }
    .footer { text-align: center; color: #999; margin-top: 40px; }
  </style>
</head>
<body>
  <div class="container">
    <h1>TaskPlatform - \u5DE5\u7A0B\u8C03\u5DEE\u8BA1\u7B97\u7CFB\u7EDF</h1>
    <p>\u6B22\u8FCE\u4F7F\u7528\u5DE5\u7A0B\u8C03\u5DEE\u8BA1\u7B97\u7CFB\u7EDF API</p>

    <div class="card">
      <h2>\u{1F4CA} \u7CFB\u7EDF\u72B6\u6001</h2>
      <div class="status">
        <div class="stat">
          <div class="stat-number" id="projects-count">-</div>
          <div class="stat-label">\u9879\u76EE\u6570\u91CF</div>
        </div>
        <div class="stat">
          <div class="stat-number" id="materials-count">-</div>
          <div class="stat-label">\u6750\u6599\u6570\u91CF</div>
        </div>
        <div class="stat">
          <div class="stat-number" id="uptime">\u8FD0\u884C\u4E2D</div>
          <div class="stat-label">\u670D\u52A1\u72B6\u6001</div>
        </div>
      </div>
    </div>

    <div class="card">
      <h2>\u{1F50C} API \u63A5\u53E3</h2>
      <ul class="api-list">
        <li><span class="badge badge-get">GET</span> <code>/api/projects</code> - \u83B7\u53D6\u6240\u6709\u9879\u76EE</li>
        <li><span class="badge badge-post">POST</span> <code>/api/projects</code> - \u521B\u5EFA\u9879\u76EE</li>
        <li><span class="badge badge-get">GET</span> <code>/api/projects/:id</code> - \u83B7\u53D6\u5355\u4E2A\u9879\u76EE</li>
        <li><span class="badge badge-put">PUT</span> <code>/api/projects/:id</code> - \u66F4\u65B0\u9879\u76EE</li>
        <li><span class="badge badge-delete">DEL</span> <code>/api/projects/:id</code> - \u5220\u9664\u9879\u76EE</li>
        <li><span class="badge badge-get">GET</span> <code>/api/materials</code> - \u83B7\u53D6\u6240\u6709\u6750\u6599</li>
        <li><span class="badge badge-post">POST</span> <code>/api/materials</code> - \u521B\u5EFA\u6750\u6599</li>
        <li><span class="badge badge-get">GET</span> <code>/health</code> - \u5065\u5EB7\u68C0\u67E5</li>
        <li><span class="badge badge-get">GET</span> <code>/api/stats</code> - \u7EDF\u8BA1\u4FE1\u606F</li>
      </ul>
    </div>

    <div class="card">
      <h2>\u{1F4D6} \u4F7F\u7528\u8BF4\u660E</h2>
      <p>\u8FD9\u662F\u4E00\u4E2A\u57FA\u4E8E Cloudflare Workers \u7684\u65E0\u670D\u52A1\u5668 API \u540E\u7AEF\u3002\u6570\u636E\u5B58\u50A8\u5728\u5185\u5B58\u4E2D\uFF0C\u91CD\u542F\u540E\u4F1A\u4E22\u5931\u3002</p>
      <p>\u5982\u9700\u6301\u4E45\u5316\u5B58\u50A8\uFF0C\u5EFA\u8BAE\u4F7F\u7528 Cloudflare D1 \u6570\u636E\u5E93\u6216\u8FDE\u63A5\u5916\u90E8\u6570\u636E\u5E93\u3002</p>
    </div>

    <div class="footer">
      <p>Powered by Cloudflare Workers &copy; ${(/* @__PURE__ */ new Date()).getFullYear()}</p>
    </div>
  </div>

  <script>
    // \u83B7\u53D6\u7EDF\u8BA1\u6570\u636E
    fetch('/api/stats')
      .then(res => res.json())
      .then(data => {
        document.getElementById('projects-count').textContent = data.projects;
        document.getElementById('materials-count').textContent = data.materials;
      })
      .catch(console.error);
  <\/script>
</body>
</html>`, {
      headers: { "Content-Type": "text/html; charset=utf-8" }
    });
  }
};
export {
  index_default as default
};
//# sourceMappingURL=index.js.map
