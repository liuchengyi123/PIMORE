const { app, BrowserWindow, ipcMain, Notification, net } = require('electron');
const path = require('path');
const fs = require('fs');

const DEFAULT_BASE = 'http://127.0.0.1:8787';
let mainWindow = null;
let baseUrl = DEFAULT_BASE;
let cookieJar = '';
let STATE_FILE = '';
let LOG_FILE = '';

function ignoreBrokenPipe(err) {
  const code = err && err.code;
  return code === 'EPIPE' || code === 'EIO' || code === 'ERR_STREAM_DESTROYED';
}

for (const stream of [process.stdout, process.stderr]) {
  if (stream && typeof stream.on === 'function') {
    stream.on('error', (err) => { if (!ignoreBrokenPipe(err)) throw err; });
  }
}

process.on('uncaughtException', (err) => {
  if (ignoreBrokenPipe(err)) return;
  try { if (LOG_FILE) fs.appendFileSync(LOG_FILE, '[uncaught] ' + String(err && err.stack || err) + '\n'); } catch (_) {}
  throw err;
});

function log(...args) {
  const line = '[' + new Date().toISOString() + '] ' + args.map((a) => {
    try { return typeof a === 'string' ? a : JSON.stringify(a); } catch (_) { return String(a); }
  }).join(' ');
  try { if (LOG_FILE) fs.appendFileSync(LOG_FILE, line + '\n'); } catch (_) {}
  try { console.log(line); } catch (err) { if (!ignoreBrokenPipe(err)) throw err; }
}

function loadState() {
  try {
    const raw = JSON.parse(fs.readFileSync(STATE_FILE, 'utf8'));
    if (raw.baseUrl) baseUrl = String(raw.baseUrl).replace(/\/$/, '');
    if (raw.cookieJar) cookieJar = String(raw.cookieJar);
  } catch (_) {}
}

function saveState() {
  try {
    fs.mkdirSync(path.dirname(STATE_FILE), { recursive: true });
    fs.writeFileSync(STATE_FILE, JSON.stringify({ baseUrl, cookieJar }, null, 2));
  } catch (err) { log('saveState fail', String(err)); }
}

function parseSetCookie(headers) {
  if (!headers) return [];
  try {
    if (typeof headers.getSetCookie === 'function') {
      const list = headers.getSetCookie();
      if (Array.isArray(list) && list.length) return list;
    }
  } catch (_) {}
  try {
    const raw = headers.raw && headers.raw()['set-cookie'];
    if (Array.isArray(raw)) return raw;
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
    } else if (typeof opts.body === 'string') {
      init.body = opts.body;
    } else {
      headers['Content-Type'] = 'application/json';
      init.body = JSON.stringify(opts.body);
    }
  }
  let res;
  try {
    res = await fetch(url, init);
  } catch (err) {
    log('fetch fail', url, String(err));
    throw new Error('无法连接店铺服务 ' + baseUrl + '：' + (err.message || err));
  }
  const setCookies = parseSetCookie(res.headers);
  if (setCookies.length) mergeCookies(setCookies);
  const text = await res.text();
  let json = null;
  try { json = text ? JSON.parse(text) : null; } catch (_) { json = null; }
  return { status: res.status, ok: res.status >= 200 && res.status < 400, text, json, headers: res.headers, url };
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 820,
    minWidth: 980,
    minHeight: 640,
    title: 'Harbor 客服台',
    backgroundColor: '#0f1f1a',
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  });
  mainWindow.webContents.on('console-message', (_e, level, message) => log('renderer', level, message));
  mainWindow.loadFile(path.join(__dirname, 'renderer', 'index.html'));
}

app.whenReady().then(() => {
  STATE_FILE = path.join(app.getPath('userData'), 'cs-desk-state.json');
  LOG_FILE = path.join(app.getPath('userData'), 'cs-desk.log');
  loadState();
  log('ready', { baseUrl, hasCookie: cookieJar.includes('admin_session=') });
  createWindow();
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

ipcMain.handle('get-config', async () => ({
  baseUrl,
  loggedIn: Boolean(cookieJar && cookieJar.includes('admin_session=')),
}));

ipcMain.handle('set-base-url', async (_e, url) => {
  baseUrl = String(url || DEFAULT_BASE).replace(/\/$/, '') || DEFAULT_BASE;
  saveState();
  return { baseUrl };
});

ipcMain.handle('login', async (_e, payload) => {
  try {
    const username = String((payload && payload.username) || '').trim();
    const password = String((payload && payload.password) || '');
    const base = payload && payload.base;
    if (base) baseUrl = String(base).trim().replace(/\/$/, '') || DEFAULT_BASE;
    if (!username || !password) return { ok: false, error: '请输入账号和密码' };
    cookieJar = '';
    log('login attempt', { baseUrl, username, pwLen: password.length });
    const body = new URLSearchParams({ username, password }).toString();
    const res = await api('/admin/login', { method: 'POST', form: true, body, accept: 'text/html' });
    log('login response', { status: res.status, jar: cookieJar.includes('admin_session=') });
    if (res.status === 401) return { ok: false, error: '账号或密码不正确' };
    if (res.status >= 300 && res.status < 400) {
      const loc = res.headers.get('location') || '/admin/orders';
      const pathOnly = loc.startsWith('http') ? new URL(loc).pathname + (new URL(loc).search || '') : loc;
      try { await api(pathOnly, { accept: 'text/html' }); } catch (err) { log('follow fail', String(err)); }
    } else if (!(res.status >= 200 && res.status < 300) && !cookieJar.includes('admin_session=')) {
      return { ok: false, error: '登录失败（HTTP ' + res.status + '）。请确认店铺已启动：' + baseUrl };
    }
    if (!cookieJar.includes('admin_session=')) {
      return { ok: false, error: '账号或密码不正确，或店铺未设置员工账号' };
    }
    // probe with inbox JSON (not poll — poll used to be swallowed by {room_id})
    const probe = await api('/admin/support/inbox?status=open');
    log('probe', { status: probe.status, ok: !!(probe.json && probe.json.ok) });
    if (probe.status === 401 || probe.status === 403) {
      return { ok: false, error: '登录成功但无权访问客服台（需要员工账号）' };
    }
    if (!(probe.json && probe.json.ok)) {
      // still allow in if cookie exists; inbox may 404 on old server
      const poll = await api('/admin/support/poll?timeout=1');
      log('probe poll fallback', { status: poll.status });
      if (poll.status === 401 || poll.status === 403) {
        return { ok: false, error: '登录成功但无权访问客服台' };
      }
    }
    saveState();
    return { ok: true, baseUrl };
  } catch (err) {
    log('login exception', String(err && err.stack || err));
    return { ok: false, error: String((err && err.message) || err || '登录异常') };
  }
});

ipcMain.handle('logout', async () => {
  try { await api('/admin/logout', { method: 'POST', form: true, body: '', accept: 'text/html' }); } catch (_) {}
  cookieJar = '';
  saveState();
  return { ok: true };
});

ipcMain.handle('inbox', async (_e, { status, q } = {}) => {
  try {
    const st = status || 'open';
    const query = new URLSearchParams();
    if (st) query.set('status', st);
    if (q) query.set('q', q);
    const inbox = await api(`/admin/support/inbox?${query.toString()}`);
    if (inbox.ok && inbox.json && Array.isArray(inbox.json.rooms)) {
      return { ok: true, rooms: inbox.json.rooms, latest: inbox.json.latest || '', open_n: inbox.json.open_n || 0, unread_n: inbox.json.unread_n || 0 };
    }
    const poll = await api('/admin/support/poll?timeout=1&after=');
    if (poll.ok && poll.json && Array.isArray(poll.json.rooms)) {
      let rooms = poll.json.rooms;
      if (q) {
        const needle = String(q).toLowerCase();
        rooms = rooms.filter((r) => JSON.stringify(r).toLowerCase().includes(needle));
      }
      return { ok: true, rooms, latest: poll.json.latest || '' };
    }
    return { ok: false, error: '无法拉取会话', status: inbox.status || poll.status, detail: (inbox.text || poll.text || '').slice(0, 200) };
  } catch (err) {
    return { ok: false, error: String(err.message || err) };
  }
});

ipcMain.handle('poll-inbox', async (_e, { after, timeout } = {}) => {
  const qs = new URLSearchParams({ after: after || '', timeout: String(timeout || 20) });
  try {
    const res = await api(`/admin/support/poll?${qs.toString()}`);
    if (!res.ok) return { ok: false, status: res.status };
    return { ok: true, latest: (res.json && res.json.latest) || '', rooms: (res.json && res.json.rooms) || [] };
  } catch (err) {
    return { ok: false, error: String(err.message || err) };
  }
});

ipcMain.handle('get-room', async (_e, roomId) => {
  const res = await api(`/api/cs/room/${encodeURIComponent(roomId)}`);
  if (!res.ok || !(res.json && res.json.ok)) return { ok: false, error: (res.json && res.json.error) || 'room', status: res.status };
  return { ok: true, room: res.json.room, messages: res.json.messages || [] };
});

ipcMain.handle('poll-room', async (_e, { roomId, after, timeout } = {}) => {
  const qs = new URLSearchParams({ room_id: roomId, after: String(after || 0), timeout: String(timeout || 20) });
  try {
    const res = await api(`/admin/support/api/room/${encodeURIComponent(roomId)}/poll?${qs.toString()}`);
    if (!res.ok) return { ok: false, status: res.status };
    return { ok: true, messages: (res.json && res.json.messages) || [], room: (res.json && res.json.room) || null, typing: (res.json && res.json.typing) || null };
  } catch (err) {
    return { ok: false, error: String(err.message || err) };
  }
});

ipcMain.handle('reply', async (_e, { roomId, body }) => {
  const form = new URLSearchParams({ body: String(body || '') }).toString();
  const res = await api(`/admin/support/${encodeURIComponent(roomId)}/reply`, { method: 'POST', form: true, body: form });
  if (res.json && res.json.ok) return { ok: true, messages: res.json.messages || [] };
  const room = await api(`/api/cs/room/${encodeURIComponent(roomId)}`);
  if (room.ok && room.json && room.json.ok) return { ok: true, messages: room.json.messages || [] };
  return { ok: false, error: '发送失败', status: res.status };
});

ipcMain.handle('close-room', async (_e, roomId) => {
  const res = await api(`/admin/support/${encodeURIComponent(roomId)}/close`, { method: 'POST', form: true, body: '', accept: 'text/html' });
  return { ok: res.status >= 200 && res.status < 400 };
});


ipcMain.handle('get-stickers', async () => {
  const res = await api('/admin/support/api/stickers');
  if (res.ok && res.json) return { ok: true, items: res.json.items || [] };
  return { ok: false, items: [] };
});

ipcMain.handle('upload-image', async (_e, { roomId, dataUrl, filename } = {}) => {
  if (!roomId) return { ok: false, error: '无会话' };
  const upload = await api('/admin/support/api/upload', {
    method: 'POST',
    headers: { Accept: 'application/json' },
    body: {
      filename: filename || 'image.png',
      data_base64: dataUrl || '',
      room_id: roomId,
    },
  });
  if (!upload.ok || !upload.json || !upload.json.ok || !upload.json.url) {
    return { ok: false, error: '图片上传失败', status: upload.status, detail: (upload.text || '').slice(0, 200) };
  }
  const body = '[img]' + String(upload.json.url);
  const form = new URLSearchParams({ body }).toString();
  const res = await api(`/admin/support/${encodeURIComponent(roomId)}/reply`, { method: 'POST', form: true, body: form });
  if (res.json && res.json.ok) return { ok: true, url: upload.json.url, messages: res.json.messages || [] };
  const room = await api(`/api/cs/room/${encodeURIComponent(roomId)}`);
  if (room.ok && room.json && room.json.ok) return { ok: true, url: upload.json.url, messages: room.json.messages || [] };
  return { ok: false, error: '发送失败', status: res.status };
});

ipcMain.handle('get-me', async () => {
  const res = await api('/admin/support/api/me');
  if (res.ok && res.json) return { ok: true, ...(res.json) };
  return { ok: false, error: '无法读取客服资料', status: res.status };
});

ipcMain.handle('set-status', async (_e, { status, note } = {}) => {
  const res = await api('/admin/support/api/status', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify({ status: status || 'online', note: note || '' }),
  });
  if (res.ok && res.json) return { ok: true, ...(res.json) };
  return { ok: false, error: '状态更新失败', status: res.status, detail: (res.text || '').slice(0, 200) };
});

ipcMain.handle('get-orders', async (_e, { roomId, email } = {}) => {
  const qs = new URLSearchParams();
  if (roomId) qs.set('room_id', roomId);
  if (email) qs.set('email', email);
  const res = await api(`/admin/support/api/orders?${qs.toString()}`);
  if (res.ok && res.json) return { ok: true, orders: res.json.orders || [] };
  return { ok: false, error: '无法拉取订单', status: res.status };
});

ipcMain.handle('get-order', async (_e, orderId) => {
  const res = await api(`/admin/support/api/orders/${encodeURIComponent(orderId)}`);
  if (res.ok && res.json) return { ok: true, order: res.json.order };
  return { ok: false, error: '订单不存在', status: res.status };
});


ipcMain.handle('get-product', async (_e, sku) => {
  const res = await api('/admin/support/api/product/' + encodeURIComponent(sku || ''));
  if (res.ok && res.json && res.json.ok) return { ok: true, product: res.json.product };
  return { ok: false, error: '商品不存在', status: res.status };
});

ipcMain.handle('search-products', async (_e, q) => {
  const query = new URLSearchParams();
  if (q) query.set('q', q);
  const res = await api('/admin/support/api/product-search?' + query.toString());
  if (res.ok && res.json && res.json.ok) return { ok: true, items: res.json.items || [] };
  return { ok: false, error: '搜索失败', status: res.status, items: [] };
});

ipcMain.handle('catalog', async () => {
  const file = path.join(app.getPath('userData'), 'harbor-catalog.json');
  const fresh = (items) => {
    try { fs.writeFileSync(file, JSON.stringify(items)); } catch (err) { /* keep memory copy */ }
    return { ok: true, items };
  };
  const res = await api('/admin/support/api/catalog');
  if (res.ok && res.json && Array.isArray(res.json.items) && res.json.items.length) return fresh(res.json.items);
  try {
    const cached = JSON.parse(fs.readFileSync(file, 'utf8'));
    if (Array.isArray(cached) && cached.length) return { ok: true, items: cached, stale: true };
  } catch (err) { /* no cache yet */ }
  return { ok: false, items: [], error: '目录还没拉下来' };
});

ipcMain.handle('get-agents', async () => {
  const res = await api('/admin/support/api/agents');
  if (res.ok && res.json && res.json.ok) return { ok: true, agents: res.json.agents || [] };
  return { ok: false, error: '无法拉取客服列表', status: res.status, agents: [] };
});

ipcMain.handle('transfer-room', async (_e, { roomId, toUsername } = {}) => {
  const res = await api('/admin/support/api/transfer', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json', 'X-Harbor-Ajax': '1' },
    body: JSON.stringify({ room_id: roomId, to_username: toUsername }),
  });
  if (res.ok && res.json && res.json.ok) {
    return {
      ok: true,
      room: res.json.room,
      messages: res.json.messages || [],
      assignee: res.json.assignee,
      prev_assignee: res.json.prev_assignee,
    };
  }
  return { ok: false, error: (res.json && res.json.error) || '转交失败', status: res.status };
});


ipcMain.handle('set-typing', async (_e, { roomId, typing } = {}) => {
  if (!roomId) return { ok: false, error: 'room' };
  try {
    const res = await api('/admin/support/api/typing', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json', 'X-Harbor-Ajax': '1' },
      body: { room_id: roomId, typing: !!typing },
    });
    if (res.ok && res.json && res.json.ok) return { ok: true, typing: res.json.typing || null };
    return { ok: false, error: (res.json && res.json.error) || 'typing', status: res.status };
  } catch (err) {
    return { ok: false, error: String(err.message || err) };
  }
});

ipcMain.handle('to-ai', async (_e, { roomId } = {}) => {
  const res = await api('/admin/support/api/to-ai', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json', 'X-Harbor-Ajax': '1' },
    body: JSON.stringify({ room_id: roomId }),
  });
  if (res.ok && res.json && res.json.ok) {
    return { ok: true, room: res.json.room || null, messages: res.json.messages || [] };
  }
  return { ok: false, error: (res.json && res.json.error) || '转给 AI 失败', status: res.status };
});

ipcMain.handle('notify', async (_e, { title, body }) => {
  if (!Notification.isSupported()) return { ok: false };
  const n = new Notification({ title: title || 'Harbor 客服', body: body || '有新消息', silent: false });
  n.show();
  return { ok: true };
});

