// TaskPlatform Cloudflare Worker
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

  if (request.method === 'OPTIONS') {
    return new Response(null, { headers: CORS_HEADERS });
  }

  if (path === '/health') {
    return new Response(JSON.stringify({ status: 'ok' }), { headers: CORS_HEADERS });
  }

  if (path === '/stats') {
    const db = await getDB(env);
    return new Response(JSON.stringify({ total_tasks: db.tasks.length, total_logs: db.logs.length }), { headers: CORS_HEADERS });
  }

  if (path === '/data') {
    const db = await getDB(env);
    return new Response(JSON.stringify(db), { headers: CORS_HEADERS });
  }

  if (path === '/save' && request.method === 'POST') {
    const body = await request.json();
    await saveDB(env, body);
    return new Response(JSON.stringify({ success: true }), { headers: CORS_HEADERS });
  }

  if (path.startsWith('/task/') && request.method === 'PUT') {
    const taskId = path.split('/')[2];
    const body = await request.json();
    const db = await getDB(env);
    const index = db.tasks.findIndex(t => t.id === taskId);
    if (index >= 0) db.tasks[index] = body;
    else db.tasks.push(body);
    await saveDB(env, db);
    return new Response(JSON.stringify({ success: true }), { headers: CORS_HEADERS });
  }

  if (path.startsWith('/task/') && request.method === 'DELETE') {
    const taskId = path.split('/')[2];
    const db = await getDB(env);
    db.tasks = db.tasks.filter(t => t.id !== taskId);
    await saveDB(env, db);
    return new Response(JSON.stringify({ success: true }), { headers: CORS_HEADERS });
  }

  if (path === '/log' && request.method === 'POST') {
    const body = await request.json();
    const db = await getDB(env);
    db.logs.push(body);
    if (db.logs.length > 1000) db.logs = db.logs.slice(-1000);
    await saveDB(env, db);
    return new Response(JSON.stringify({ success: true }), { headers: CORS_HEADERS });
  }

  return new Response(JSON.stringify({ error: 'Not found' }), { status: 404, headers: CORS_HEADERS });
}

addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request, event.locals.env));
});
