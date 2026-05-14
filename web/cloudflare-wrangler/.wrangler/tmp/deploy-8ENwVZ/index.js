// src/index.ts
var index_default = {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;
    const corsHeaders = {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, Authorization, apikey"
    };
    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders });
    }
    if (path === "/health" || path === "/api/health") {
      return new Response(JSON.stringify({
        status: "healthy",
        version: "1.0.0",
        database: "D1",
        timestamp: (/* @__PURE__ */ new Date()).toISOString()
      }), {
        headers: { ...corsHeaders, "Content-Type": "application/json" }
      });
    }
    if (path.startsWith("/api/")) {
      try {
        if (path === "/api/projects" && request.method === "GET") {
          const stmt = env.taskplatform_db.prepare("SELECT * FROM projects ORDER BY created_at DESC");
          const result = await stmt.all();
          return new Response(JSON.stringify(result.results), {
            headers: { ...corsHeaders, "Content-Type": "application/json" }
          });
        }
        if (path === "/api/projects" && request.method === "POST") {
          const body = await request.json();
          const id = crypto.randomUUID();
          const now = (/* @__PURE__ */ new Date()).toISOString();
          const stmt = env.taskplatform_db.prepare(`
            INSERT INTO projects (id, name, description, status, contract_no, contract_date, base_date, completion_date, total_value, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
          `);
          await stmt.bind(
            id,
            body.name || "\u672A\u547D\u540D\u9879\u76EE",
            body.description || "",
            body.status || "active",
            body.contract_no || "",
            body.contract_date || "",
            body.base_date || "",
            body.completion_date || "",
            body.total_value || 0,
            now,
            now
          ).run();
          const project = { id, ...body, created_at: now, updated_at: now };
          return new Response(JSON.stringify(project), {
            status: 201,
            headers: { ...corsHeaders, "Content-Type": "application/json" }
          });
        }
        if (path.match(/^\/api\/projects\/[^/]+$/) && request.method === "GET") {
          const id = path.split("/")[3];
          const stmt = env.taskplatform_db.prepare("SELECT * FROM projects WHERE id = ?");
          const result = await stmt.bind(id).first();
          if (!result) {
            return new Response(JSON.stringify({ error: "Project not found" }), {
              status: 404,
              headers: { ...corsHeaders, "Content-Type": "application/json" }
            });
          }
          return new Response(JSON.stringify(result), {
            headers: { ...corsHeaders, "Content-Type": "application/json" }
          });
        }
        if (path.match(/^\/api\/projects\/[^/]+$/) && request.method === "PUT") {
          const id = path.split("/")[3];
          const body = await request.json();
          const now = (/* @__PURE__ */ new Date()).toISOString();
          const stmt = env.taskplatform_db.prepare(`
            UPDATE projects SET name = ?, description = ?, status = ?, contract_no = ?, contract_date = ?, base_date = ?, completion_date = ?, total_value = ?, updated_at = ?
            WHERE id = ?
          `);
          const result = await stmt.bind(
            body.name,
            body.description || "",
            body.status || "active",
            body.contract_no || "",
            body.contract_date || "",
            body.base_date || "",
            body.completion_date || "",
            body.total_value || 0,
            now,
            id
          ).run();
          if (result.changes === 0) {
            return new Response(JSON.stringify({ error: "Project not found" }), {
              status: 404,
              headers: { ...corsHeaders, "Content-Type": "application/json" }
            });
          }
          const updated = await env.taskplatform_db.prepare("SELECT * FROM projects WHERE id = ?").bind(id).first();
          return new Response(JSON.stringify(updated), {
            headers: { ...corsHeaders, "Content-Type": "application/json" }
          });
        }
        if (path.match(/^\/api\/projects\/[^/]+$/) && request.method === "DELETE") {
          const id = path.split("/")[3];
          const stmt = env.taskplatform_db.prepare("DELETE FROM projects WHERE id = ?");
          await stmt.bind(id).run();
          return new Response(JSON.stringify({ success: true }), {
            headers: { ...corsHeaders, "Content-Type": "application/json" }
          });
        }
        if (path === "/api/materials" && request.method === "GET") {
          const stmt = env.taskplatform_db.prepare("SELECT * FROM materials ORDER BY created_at DESC");
          const result = await stmt.all();
          return new Response(JSON.stringify(result.results), {
            headers: { ...corsHeaders, "Content-Type": "application/json" }
          });
        }
        if (path === "/api/materials" && request.method === "POST") {
          const body = await request.json();
          const id = crypto.randomUUID();
          const now = (/* @__PURE__ */ new Date()).toISOString();
          const stmt = env.taskplatform_db.prepare(`
            INSERT INTO materials (id, name, type, unit, current_price, specification, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
          `);
          await stmt.bind(
            id,
            body.name || "\u672A\u547D\u540D\u6750\u6599",
            body.type || "unknown",
            body.unit || "\u5428",
            body.current_price || 0,
            body.specification || "",
            now,
            now
          ).run();
          const material = { id, ...body, created_at: now, updated_at: now };
          return new Response(JSON.stringify(material), {
            status: 201,
            headers: { ...corsHeaders, "Content-Type": "application/json" }
          });
        }
        if (path.match(/^\/api\/materials\/[^/]+$/) && request.method === "GET") {
          const id = path.split("/")[3];
          const stmt = env.taskplatform_db.prepare("SELECT * FROM materials WHERE id = ?");
          const result = await stmt.bind(id).first();
          if (!result) {
            return new Response(JSON.stringify({ error: "Material not found" }), {
              status: 404,
              headers: { ...corsHeaders, "Content-Type": "application/json" }
            });
          }
          return new Response(JSON.stringify(result), {
            headers: { ...corsHeaders, "Content-Type": "application/json" }
          });
        }
        if (path.match(/^\/api\/materials\/[^/]+$/) && request.method === "PUT") {
          const id = path.split("/")[3];
          const body = await request.json();
          const now = (/* @__PURE__ */ new Date()).toISOString();
          const stmt = env.taskplatform_db.prepare(`
            UPDATE materials SET name = ?, type = ?, unit = ?, current_price = ?, specification = ?, updated_at = ?
            WHERE id = ?
          `);
          const result = await stmt.bind(
            body.name,
            body.type || "unknown",
            body.unit || "\u5428",
            body.current_price || 0,
            body.specification || "",
            now,
            id
          ).run();
          if (result.changes === 0) {
            return new Response(JSON.stringify({ error: "Material not found" }), {
              status: 404,
              headers: { ...corsHeaders, "Content-Type": "application/json" }
            });
          }
          const updated = await env.taskplatform_db.prepare("SELECT * FROM materials WHERE id = ?").bind(id).first();
          return new Response(JSON.stringify(updated), {
            headers: { ...corsHeaders, "Content-Type": "application/json" }
          });
        }
        if (path.match(/^\/api\/materials\/[^/]+$/) && request.method === "DELETE") {
          const id = path.split("/")[3];
          const stmt = env.taskplatform_db.prepare("DELETE FROM materials WHERE id = ?");
          await stmt.bind(id).run();
          return new Response(JSON.stringify({ success: true }), {
            headers: { ...corsHeaders, "Content-Type": "application/json" }
          });
        }
        if (path === "/api/price-history" && request.method === "GET") {
          const materialId = url.searchParams.get("material_id");
          let stmt;
          if (materialId) {
            stmt = env.taskplatform_db.prepare("SELECT * FROM price_history WHERE material_id = ? ORDER BY recorded_at DESC");
            stmt = stmt.bind(materialId);
          } else {
            stmt = env.taskplatform_db.prepare("SELECT * FROM price_history ORDER BY recorded_at DESC LIMIT 100");
          }
          const result = await stmt.all();
          return new Response(JSON.stringify(result.results), {
            headers: { ...corsHeaders, "Content-Type": "application/json" }
          });
        }
        if (path === "/api/price-history" && request.method === "POST") {
          const body = await request.json();
          const id = crypto.randomUUID();
          const now = (/* @__PURE__ */ new Date()).toISOString();
          const stmt = env.taskplatform_db.prepare(`
            INSERT INTO price_history (id, material_id, price, source, recorded_at)
            VALUES (?, ?, ?, ?, ?)
          `);
          await stmt.bind(
            id,
            body.material_id,
            body.price,
            body.source || "manual",
            now
          ).run();
          const record = { id, material_id: body.material_id, price: body.price, source: body.source || "manual", recorded_at: now };
          return new Response(JSON.stringify(record), {
            status: 201,
            headers: { ...corsHeaders, "Content-Type": "application/json" }
          });
        }
        if (path === "/api/stats") {
          const projectsCount = await env.taskplatform_db.prepare("SELECT COUNT(*) as count FROM projects").first();
          const materialsCount = await env.taskplatform_db.prepare("SELECT COUNT(*) as count FROM materials").first();
          const priceHistoryCount = await env.taskplatform_db.prepare("SELECT COUNT(*) as count FROM price_history").first();
          return new Response(JSON.stringify({
            projects: projectsCount?.count || 0,
            materials: materialsCount?.count || 0,
            priceHistory: priceHistoryCount?.count || 0,
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
    .db-badge { background: #722ed1; }
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
          <div class="stat-number" id="price-history-count">-</div>
          <div class="stat-label">\u4EF7\u683C\u8BB0\u5F55</div>
        </div>
        <div class="stat">
          <div class="stat-number" style="font-size: 20px;"><span class="badge db-badge">D1</span></div>
          <div class="stat-label">\u6570\u636E\u5E93</div>
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
        <li><span class="badge badge-get">GET</span> <code>/api/price-history</code> - \u83B7\u53D6\u4EF7\u683C\u5386\u53F2</li>
        <li><span class="badge badge-post">POST</span> <code>/api/price-history</code> - \u6DFB\u52A0\u4EF7\u683C\u8BB0\u5F55</li>
        <li><span class="badge badge-get">GET</span> <code>/health</code> - \u5065\u5EB7\u68C0\u67E5</li>
        <li><span class="badge badge-get">GET</span> <code>/api/stats</code> - \u7EDF\u8BA1\u4FE1\u606F</li>
      </ul>
    </div>

    <div class="card">
      <h2>\u{1F4D6} \u4F7F\u7528\u8BF4\u660E</h2>
      <p>\u8FD9\u662F\u4E00\u4E2A\u57FA\u4E8E Cloudflare Workers \u7684\u65E0\u670D\u52A1\u5668 API \u540E\u7AEF\u3002</p>
      <p>\u6570\u636E\u5B58\u50A8\u5728 Cloudflare D1 \u6570\u636E\u5E93\u4E2D\uFF0C\u6C38\u4E45\u4FDD\u5B58\u3002</p>
    </div>

    <div class="footer">
      <p>Powered by Cloudflare Workers + D1 &copy; ${(/* @__PURE__ */ new Date()).getFullYear()}</p>
    </div>
  </div>

  <script>
    // \u83B7\u53D6\u7EDF\u8BA1\u6570\u636E
    fetch('/api/stats')
      .then(res => res.json())
      .then(data => {
        document.getElementById('projects-count').textContent = data.projects;
        document.getElementById('materials-count').textContent = data.materials;
        document.getElementById('price-history-count').textContent = data.priceHistory;
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
