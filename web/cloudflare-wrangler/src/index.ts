/**
 * Cloudflare Workers 后端入口
 * 工程调差计算系统 API
 * 支持 D1 数据库持久化存储
 */

interface Env {
  taskplatform_db: D1Database;
  ENVIRONMENT: string;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    const path = url.pathname;

    // CORS 头
    const corsHeaders = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization, apikey',
    };

    // 处理 OPTIONS 预检请求
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders });
    }

    // 健康检查
    if (path === '/health' || path === '/api/health') {
      return new Response(JSON.stringify({
        status: 'healthy',
        version: '1.0.0',
        database: 'D1',
        timestamp: new Date().toISOString()
      }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });
    }

    // API 路由处理
    if (path.startsWith('/api/')) {
      try {
        // ===== 项目管理 =====

        // 获取所有项目
        if (path === '/api/projects' && request.method === 'GET') {
          const stmt = env.taskplatform_db.prepare('SELECT * FROM projects ORDER BY created_at DESC');
          const result = await stmt.all();
          return new Response(JSON.stringify(result.results), {
            headers: { ...corsHeaders, 'Content-Type': 'application/json' }
          });
        }

        // 创建项目
        if (path === '/api/projects' && request.method === 'POST') {
          const body = await request.json();
          const id = crypto.randomUUID();
          const now = new Date().toISOString();
          const stmt = env.taskplatform_db.prepare(`
            INSERT INTO projects (id, name, description, status, contract_no, contract_date, base_date, completion_date, total_value, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
          `);
          await stmt.bind(
            id,
            body.name || '未命名项目',
            body.description || '',
            body.status || 'active',
            body.contract_no || '',
            body.contract_date || '',
            body.base_date || '',
            body.completion_date || '',
            body.total_value || 0,
            now,
            now
          ).run();

          const project = { id, ...body, created_at: now, updated_at: now };
          return new Response(JSON.stringify(project), {
            status: 201,
            headers: { ...corsHeaders, 'Content-Type': 'application/json' }
          });
        }

        // 获取单个项目
        if (path.match(/^\/api\/projects\/[^/]+$/) && request.method === 'GET') {
          const id = path.split('/')[3];
          const stmt = env.taskplatform_db.prepare('SELECT * FROM projects WHERE id = ?');
          const result = await stmt.bind(id).first();
          if (!result) {
            return new Response(JSON.stringify({ error: 'Project not found' }), {
              status: 404,
              headers: { ...corsHeaders, 'Content-Type': 'application/json' }
            });
          }
          return new Response(JSON.stringify(result), {
            headers: { ...corsHeaders, 'Content-Type': 'application/json' }
          });
        }

        // 更新项目
        if (path.match(/^\/api\/projects\/[^/]+$/) && request.method === 'PUT') {
          const id = path.split('/')[3];
          const body = await request.json();
          const now = new Date().toISOString();
          const stmt = env.taskplatform_db.prepare(`
            UPDATE projects SET name = ?, description = ?, status = ?, contract_no = ?, contract_date = ?, base_date = ?, completion_date = ?, total_value = ?, updated_at = ?
            WHERE id = ?
          `);
          const result = await stmt.bind(
            body.name,
            body.description || '',
            body.status || 'active',
            body.contract_no || '',
            body.contract_date || '',
            body.base_date || '',
            body.completion_date || '',
            body.total_value || 0,
            now,
            id
          ).run();

          if (result.changes === 0) {
            return new Response(JSON.stringify({ error: 'Project not found' }), {
              status: 404,
              headers: { ...corsHeaders, 'Content-Type': 'application/json' }
            });
          }

          const updated = await env.taskplatform_db.prepare('SELECT * FROM projects WHERE id = ?').bind(id).first();
          return new Response(JSON.stringify(updated), {
            headers: { ...corsHeaders, 'Content-Type': 'application/json' }
          });
        }

        // 删除项目
        if (path.match(/^\/api\/projects\/[^/]+$/) && request.method === 'DELETE') {
          const id = path.split('/')[3];
          const stmt = env.taskplatform_db.prepare('DELETE FROM projects WHERE id = ?');
          await stmt.bind(id).run();
          return new Response(JSON.stringify({ success: true }), {
            headers: { ...corsHeaders, 'Content-Type': 'application/json' }
          });
        }

        // ===== 材料管理 =====

        // 获取所有材料
        if (path === '/api/materials' && request.method === 'GET') {
          const stmt = env.taskplatform_db.prepare('SELECT * FROM materials ORDER BY created_at DESC');
          const result = await stmt.all();
          return new Response(JSON.stringify(result.results), {
            headers: { ...corsHeaders, 'Content-Type': 'application/json' }
          });
        }

        // 创建材料
        if (path === '/api/materials' && request.method === 'POST') {
          const body = await request.json();
          const id = crypto.randomUUID();
          const now = new Date().toISOString();
          const stmt = env.taskplatform_db.prepare(`
            INSERT INTO materials (id, name, type, unit, current_price, specification, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
          `);
          await stmt.bind(
            id,
            body.name || '未命名材料',
            body.type || 'unknown',
            body.unit || '吨',
            body.current_price || 0,
            body.specification || '',
            now,
            now
          ).run();

          const material = { id, ...body, created_at: now, updated_at: now };
          return new Response(JSON.stringify(material), {
            status: 201,
            headers: { ...corsHeaders, 'Content-Type': 'application/json' }
          });
        }

        // 获取单个材料
        if (path.match(/^\/api\/materials\/[^/]+$/) && request.method === 'GET') {
          const id = path.split('/')[3];
          const stmt = env.taskplatform_db.prepare('SELECT * FROM materials WHERE id = ?');
          const result = await stmt.bind(id).first();
          if (!result) {
            return new Response(JSON.stringify({ error: 'Material not found' }), {
              status: 404,
              headers: { ...corsHeaders, 'Content-Type': 'application/json' }
            });
          }
          return new Response(JSON.stringify(result), {
            headers: { ...corsHeaders, 'Content-Type': 'application/json' }
          });
        }

        // 更新材料
        if (path.match(/^\/api\/materials\/[^/]+$/) && request.method === 'PUT') {
          const id = path.split('/')[3];
          const body = await request.json();
          const now = new Date().toISOString();
          const stmt = env.taskplatform_db.prepare(`
            UPDATE materials SET name = ?, type = ?, unit = ?, current_price = ?, specification = ?, updated_at = ?
            WHERE id = ?
          `);
          const result = await stmt.bind(
            body.name,
            body.type || 'unknown',
            body.unit || '吨',
            body.current_price || 0,
            body.specification || '',
            now,
            id
          ).run();

          if (result.changes === 0) {
            return new Response(JSON.stringify({ error: 'Material not found' }), {
              status: 404,
              headers: { ...corsHeaders, 'Content-Type': 'application/json' }
            });
          }

          const updated = await env.taskplatform_db.prepare('SELECT * FROM materials WHERE id = ?').bind(id).first();
          return new Response(JSON.stringify(updated), {
            headers: { ...corsHeaders, 'Content-Type': 'application/json' }
          });
        }

        // 删除材料
        if (path.match(/^\/api\/materials\/[^/]+$/) && request.method === 'DELETE') {
          const id = path.split('/')[3];
          const stmt = env.taskplatform_db.prepare('DELETE FROM materials WHERE id = ?');
          await stmt.bind(id).run();
          return new Response(JSON.stringify({ success: true }), {
            headers: { ...corsHeaders, 'Content-Type': 'application/json' }
          });
        }

        // ===== 价格历史 =====

        // 获取价格历史
        if (path === '/api/price-history' && request.method === 'GET') {
          const materialId = url.searchParams.get('material_id');
          let stmt;
          if (materialId) {
            stmt = env.taskplatform_db.prepare('SELECT * FROM price_history WHERE material_id = ? ORDER BY recorded_at DESC');
            stmt = stmt.bind(materialId);
          } else {
            stmt = env.taskplatform_db.prepare('SELECT * FROM price_history ORDER BY recorded_at DESC LIMIT 100');
          }
          const result = await stmt.all();
          return new Response(JSON.stringify(result.results), {
            headers: { ...corsHeaders, 'Content-Type': 'application/json' }
          });
        }

        // 添加价格记录
        if (path === '/api/price-history' && request.method === 'POST') {
          const body = await request.json();
          const id = crypto.randomUUID();
          const now = new Date().toISOString();
          const stmt = env.taskplatform_db.prepare(`
            INSERT INTO price_history (id, material_id, price, source, recorded_at)
            VALUES (?, ?, ?, ?, ?)
          `);
          await stmt.bind(
            id,
            body.material_id,
            body.price,
            body.source || 'manual',
            now
          ).run();

          const record = { id, material_id: body.material_id, price: body.price, source: body.source || 'manual', recorded_at: now };
          return new Response(JSON.stringify(record), {
            status: 201,
            headers: { ...corsHeaders, 'Content-Type': 'application/json' }
          });
        }

        // ===== 统计信息 =====
        if (path === '/api/stats') {
          const projectsCount = await env.taskplatform_db.prepare('SELECT COUNT(*) as count FROM projects').first();
          const materialsCount = await env.taskplatform_db.prepare('SELECT COUNT(*) as count FROM materials').first();
          const priceHistoryCount = await env.taskplatform_db.prepare('SELECT COUNT(*) as count FROM price_history').first();

          return new Response(JSON.stringify({
            projects: projectsCount?.count || 0,
            materials: materialsCount?.count || 0,
            priceHistory: priceHistoryCount?.count || 0,
            timestamp: new Date().toISOString()
          }), {
            headers: { ...corsHeaders, 'Content-Type': 'application/json' }
          });
        }

        // 未找到 API 路由
        return new Response(JSON.stringify({ error: 'API not found', path }), {
          status: 404,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        });

      } catch (error) {
        return new Response(JSON.stringify({ error: 'Internal server error', message: String(error) }), {
          status: 500,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        });
      }
    }

    // 前端路由 - 返回 index.html
    return new Response(`<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>TaskPlatform - 工程调差计算系统</title>
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
    <h1>TaskPlatform - 工程调差计算系统</h1>
    <p>欢迎使用工程调差计算系统 API</p>

    <div class="card">
      <h2>📊 系统状态</h2>
      <div class="status">
        <div class="stat">
          <div class="stat-number" id="projects-count">-</div>
          <div class="stat-label">项目数量</div>
        </div>
        <div class="stat">
          <div class="stat-number" id="materials-count">-</div>
          <div class="stat-label">材料数量</div>
        </div>
        <div class="stat">
          <div class="stat-number" id="price-history-count">-</div>
          <div class="stat-label">价格记录</div>
        </div>
        <div class="stat">
          <div class="stat-number" style="font-size: 20px;"><span class="badge db-badge">D1</span></div>
          <div class="stat-label">数据库</div>
        </div>
      </div>
    </div>

    <div class="card">
      <h2>🔌 API 接口</h2>
      <ul class="api-list">
        <li><span class="badge badge-get">GET</span> <code>/api/projects</code> - 获取所有项目</li>
        <li><span class="badge badge-post">POST</span> <code>/api/projects</code> - 创建项目</li>
        <li><span class="badge badge-get">GET</span> <code>/api/projects/:id</code> - 获取单个项目</li>
        <li><span class="badge badge-put">PUT</span> <code>/api/projects/:id</code> - 更新项目</li>
        <li><span class="badge badge-delete">DEL</span> <code>/api/projects/:id</code> - 删除项目</li>
        <li><span class="badge badge-get">GET</span> <code>/api/materials</code> - 获取所有材料</li>
        <li><span class="badge badge-post">POST</span> <code>/api/materials</code> - 创建材料</li>
        <li><span class="badge badge-get">GET</span> <code>/api/price-history</code> - 获取价格历史</li>
        <li><span class="badge badge-post">POST</span> <code>/api/price-history</code> - 添加价格记录</li>
        <li><span class="badge badge-get">GET</span> <code>/health</code> - 健康检查</li>
        <li><span class="badge badge-get">GET</span> <code>/api/stats</code> - 统计信息</li>
      </ul>
    </div>

    <div class="card">
      <h2>📖 使用说明</h2>
      <p>这是一个基于 Cloudflare Workers 的无服务器 API 后端。</p>
      <p>数据存储在 Cloudflare D1 数据库中，永久保存。</p>
    </div>

    <div class="footer">
      <p>Powered by Cloudflare Workers + D1 &copy; ${new Date().getFullYear()}</p>
    </div>
  </div>

  <script>
    // 获取统计数据
    fetch('/api/stats')
      .then(res => res.json())
      .then(data => {
        document.getElementById('projects-count').textContent = data.projects;
        document.getElementById('materials-count').textContent = data.materials;
        document.getElementById('price-history-count').textContent = data.priceHistory;
      })
      .catch(console.error);
  </script>
</body>
</html>`, {
      headers: { 'Content-Type': 'text/html; charset=utf-8' }
    });
  }
};