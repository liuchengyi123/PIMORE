const { app } = require('electron');
const fs = require('fs');

let baseUrl = 'http://127.0.0.1:8787';
let cookieJar = '';

function parseSetCookie(headers) {
  if (!headers) return [];
  try {
    if (typeof headers.getSetCookie === 'function') {
      const list = headers.getSetCookie();
      if (Array.isArray(list) && list.length) return list;
    }
  } catch (_) {}
  const single = headers.get && headers.get('set-cookie');
  return single ? [single] : [];
}
function mergeCookies(setCookieLines) {
  const map = {};
  for (const part of (cookieJar || '').split(';')) {
    const s = part.trim();
    if (!s) continue;
    const i = s.indexOf('=');
    if (i > 0) map[s.slice(0, i)] = s.slice(i + 1);
  }
  for (const line of setCookieLines || []) {
    const first = String(line).split(';')[0];
    const i = first.indexOf('=');
    if (i > 0) map[first.slice(0, i).trim()] = first.slice(i + 1).trim();
  }
  cookieJar = Object.entries(map).map(([k, v]) => `${k}=${v}`).join('; ');
}
async function api(pathname, opts = {}) {
  const url = `${baseUrl}${pathname}`;
  const headers = Object.assign({
    Accept: opts.accept || 'application/json',
    'X-Harbor-Ajax': '1',
  }, opts.headers || {});
  if (cookieJar) headers.Cookie = cookieJar;
  const init = { method: opts.method || 'GET', headers, redirect: 'manual' };
  if (opts.body !== undefined) {
    if (opts.form) {
      headers['Content-Type'] = 'application/x-www-form-urlencoded';
      init.body = opts.body;
    }
  }
  const res = await fetch(url, init);
  const setCookies = parseSetCookie(res.headers);
  if (setCookies.length) mergeCookies(setCookies);
  const text = await res.text();
  let json = null;
  try { json = text ? JSON.parse(text) : null; } catch (_) { json = null; }
  return { status: res.status, json, text, headers: res.headers };
}

async function login(username, password) {
  cookieJar = '';
  const body = new URLSearchParams({ username, password }).toString();
  const res = await api('/admin/login', { method: 'POST', form: true, body, accept: 'text/html' });
  if (res.status === 401) return { ok: false, error: '账号或密码不正确', status: res.status };
  if (res.status >= 300 && res.status < 400) {
    const loc = res.headers.get('location') || '/admin/orders';
    const pathOnly = loc.startsWith('http') ? new URL(loc).pathname : loc;
    await api(pathOnly, { accept: 'text/html' });
  }
  if (!cookieJar.includes('admin_session=')) return { ok: false, error: 'no cookie', jar: cookieJar, status: res.status };
  const probe = await api('/admin/support/inbox?status=open');
  return { ok: true, probeStatus: probe.status, rooms: probe.json && probe.json.rooms && probe.json.rooms.length, jar: cookieJar.slice(0, 40) };
}

app.whenReady().then(async () => {
  const result = await login('admin', 'harbor-local');
  fs.writeFileSync('D:/1010/_electron_login_result.json', JSON.stringify(result, null, 2));
  app.quit();
}).catch((e) => {
  fs.writeFileSync('D:/1010/_electron_login_result.json', JSON.stringify({ ok:false, error:String(e) }));
  app.quit();
});
