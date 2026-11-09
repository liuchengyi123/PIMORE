const loginView = document.getElementById('loginView');
const appView = document.getElementById('appView');
const loginForm = document.getElementById('loginForm');
const loginError = document.getElementById('loginError');
const roomList = document.getElementById('roomList');
const msgList = document.getElementById('msgList');
const chatEmpty = document.getElementById('chatEmpty');
const chatPanel = document.getElementById('chatPanel');
const chatTitle = document.getElementById('chatTitle');
const chatMeta = document.getElementById('chatMeta');
const currentProduct = document.getElementById('currentProduct');
const historyList = document.getElementById('historyList');
const replyForm = document.getElementById('replyForm');
const replyBody = document.getElementById('replyBody');
const searchQ = document.getElementById('searchQ');
const baseLabel = document.getElementById('baseLabel');
const statOpen = document.getElementById('statOpen');
const statUnread = document.getElementById('statUnread');
const pingSound = document.getElementById('pingSound');
const agentName = document.getElementById('agentName');
const agentTitle = document.getElementById('agentTitle');
const agentStatus = document.getElementById('agentStatus');
const visitorInfo = document.getElementById('visitorInfo');
const ordersList = document.getElementById('ordersList');
const emojiBar = document.getElementById('emojiBar');
const emojiToggle = document.getElementById('emojiToggle');
const imageToggle = document.getElementById('imageToggle');
const imagePick = document.getElementById('imagePick');

const state = {
  peerTyping: null,
  status: 'open',
  q: '',
  rooms: [],
  latest: '',
  activeId: null,
  activeRoom: null,
  messages: [],
  lastMsgId: 0,
  inboxLoop: 0,
  roomLoop: 0,
  knownUnread: 0,
  agent: null,
  agents: [],
  agentMap: {},
  settings: {},
  activeRoom: null,
  settings: {},
  orders: [],
  inboxChip: 'all',
  orderFilter: 'all',
  openCount: 0,
  closedCount: 0,
  deskViewApplied: false,
};

const DEFAULT_CANNED = ['商品尺码说明', '发货时间说明', '退换货政策', '发票相关问题', '感谢您的咨询', '帮您催一下物流', '其他问题'];

function cannedLines() {
  let raw = null;
  try { raw = localStorage.getItem('cs_canned'); } catch (_) {}
  if (raw == null || raw === '') {
    if (raw === '') return [];
    return DEFAULT_CANNED.slice();
  }
  return String(raw).split('\n').map((s) => s.trim()).filter(Boolean);
}

function pageSize() {
  const n = Number(localStorage.getItem('cs_page_size') || 20);
  return n > 0 ? n : 20;
}

function esc(s) {
  return String(s ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function fmtTime(iso) {
  if (!iso) return '';
  try {
    const d = new Date(iso.endsWith('Z') ? iso : iso + 'Z');
    return d.toLocaleString('zh-CN', { hour12: false });
  } catch (_) {
    return iso;
  }
}

function shortTime(iso) {
  if (!iso) return '';
  try {
    const d = new Date(String(iso).endsWith('Z') ? iso : iso + 'Z');
    if (Number.isNaN(d.getTime())) return '';
    const now = new Date();
    const start = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const day = new Date(d.getFullYear(), d.getMonth(), d.getDate());
    const diff = Math.round((start - day) / 86400000);
    const hm = d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false });
    if (diff === 0) return hm;
    if (diff === 1) return '昨天';
    if (diff > 1 && diff < 7) return d.toLocaleDateString('zh-CN', { weekday: 'short' });
    return d.toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric' });
  } catch (_) {
    return '';
  }
}

function deskPref(key, fallbackOn) {
  try {
    const v = localStorage.getItem(key);
    if (v == null || v === '') return !!fallbackOn;
    return v !== '0';
  } catch (_) {
    return !!fallbackOn;
  }
}

function playPing() {
  if (!deskPref('cs_sound', true) || !pingSound) return;
  try { pingSound.currentTime = 0; pingSound.play(); } catch (_) {}
}

function deskNotify(title, body) {
  if (!deskPref('cs_desktop', true) || !window.csDesk || !window.csDesk.notify) return;
  window.csDesk.notify({ title, body });
}

function paintAvatar(el, label) {
  if (!el) return;
  const text = String(label || '访').trim() || '访';
  el.textContent = text.slice(0, 1);
  const hues = ['#F96141', '#3B82F6', '#8B5CF6', '#10B981', '#F59E0B', '#EC4899'];
  let n = 0;
  for (let i = 0; i < text.length; i++) n = (n + text.charCodeAt(i)) % hues.length;
  el.style.background = hues[n];
  el.style.color = '#fff';
}

function syncWorkspace(open) {
  const ctx = document.querySelector('.context');
  const ws = document.querySelector('.workspace');
  if (ctx) ctx.hidden = !open;
  if (ws) ws.classList.toggle('room-open', !!open);
}

function syncRail(key) {
  document.querySelectorAll('.rail-item').forEach((btn) => {
    btn.classList.toggle('on', btn.getAttribute('data-rail') === key);
  });
}

function showCtx(name) {
  const key = name || 'visitor';
  document.querySelectorAll('[data-ctx]').forEach((btn) => {
    btn.classList.toggle('on', btn.getAttribute('data-ctx') === key);
  });
  ['visitor', 'sku', 'orders', 'history'].forEach((k) => {
    const el = document.getElementById('ctx-' + k);
    if (el) el.hidden = k !== key;
  });
  syncWorkspace(true);
  syncRail(key);
}

function renderCannedBar() {
  const bar = document.getElementById('cannedBar');
  if (!bar) return;
  const lines = cannedLines();
  if (!deskPref('cs_canned_on', true) || !lines.length) {
    bar.hidden = true;
    bar.innerHTML = '';
    return;
  }
  bar.hidden = false;
  bar.innerHTML = '<span class="canned-label">快捷回复</span>' + lines.slice(0, 8).map((line) => {
    return `<button type="button" data-canned="${esc(line)}">${esc(line)}</button>`;
  }).join('');
}

function applyDeskPrefs() {
  let compact = false;
  try { compact = localStorage.getItem('cs_compact') === '1'; } catch (_) {}
  document.body.classList.toggle('cs-compact', compact);
  renderCannedBar();
  if (state.messages && state.messages.length) renderMessages();
  if (state.rooms && state.rooms.length && typeof renderRooms === 'function') renderRooms();
}

function swapProduct(p) {
  const old = document.getElementById('currentProduct');
  if (!old) return;
  const tmp = document.createElement('div');
  tmp.innerHTML = productHtml(p);
  const card = tmp.firstElementChild;
  if (!card) return;
  card.id = 'currentProduct';
  old.replaceWith(card);
}

function showLogin() {
  loginView.hidden = false;
  appView.hidden = true;
  loginView.style.display = "";
  appView.style.display = "none";
  loginView.removeAttribute("aria-hidden");
  appView.setAttribute("aria-hidden", "true");
}

let localCatalog = [];

function searchLocalCatalog(q) {
  const text = String(q || '').trim().toLowerCase();
  if (!text) return localCatalog.slice(0, 12);
  const hits = [];
  for (const it of localCatalog) {
    const name = String(it.name || '');
    const sku = String(it.sku || '');
    const offers = Array.isArray(it.offers) ? it.offers : [];
    const optionHit = offers.some((o) => String(o.label || '').toLowerCase().includes(text));
    if (sku.toLowerCase().includes(text) || name.toLowerCase().includes(text) || optionHit) hits.push(it);
    if (hits.length >= 12) break;
  }
  return hits;
}

async function ensureCatalog() {
  if (!window.csDesk.catalog) return;
  try {
    const res = await window.csDesk.catalog();
    if (res && Array.isArray(res.items) && res.items.length) localCatalog = res.items;
  } catch (err) { /* search falls back to the server */ }
}

function showApp() {
  loginView.hidden = true;
  appView.hidden = false;
  loginView.style.display = "none";
  appView.style.display = "grid";
  loginView.setAttribute("aria-hidden", "true");
  appView.removeAttribute("aria-hidden");
  console.log("cs-desk showApp", { loginHidden: loginView.hidden, appHidden: appView.hidden });
  ensureCatalog();
}

function productHtml(p) {
  if (!p || !p.sku) return '<div class="product-card empty-card">暂无当前商品</div>';
  const img = p.image
    ? `<img src="${esc(mediaUrl(p.image))}" alt="" />`
    : '<div class="ph"></div>';
  return `<div class="product-card" data-sku="${esc(p.sku)}">${img}<div class="body"><div class="pname">${esc(p.name || p.sku)}</div><div class="price">${esc(p.price || '')}</div><div class="muted small">SKU ${esc(p.sku)}</div></div><div class="send-row"><button type="button" class="btn-send-prod" data-send-sku="${esc(p.sku)}">发送给用户</button></div></div>`;
}

function renderHistory(list) {
  const items = Array.isArray(list) ? list : [];
  if (!items.length) {
    historyList.innerHTML = '<div class="muted small">暂无</div>';
    return;
  }
  historyList.innerHTML = items
    .slice(0, 20)
    .map((it) => {
      const img = it.image ? `<img src="${esc(mediaUrl(it.image))}" alt="" />` : '<div></div>';
      const sku = it.sku || '';
      return `<div class="history-item" data-sku="${esc(sku)}">${img}<div class="t"><div class="hn">${esc(it.name || it.sku)}</div><div class="price">${esc(it.price || '')}</div></div><button type="button" class="btn-send-mini" data-send-sku="${esc(sku)}">发送</button></div>`;
    })
    .join('');
}

function roomMatchesChip(r) {
  const chip = state.inboxChip || 'all';
  const me = (state.agent && state.agent.username) || '';
  const assignee = String(r.assignee || '').trim();
  if (chip === 'mine') return Boolean(me) && assignee === me;
  if (chip === 'unassigned') return !assignee;
  if (chip === 'hung') {
    // hung = open room with AI mode or assignee marked busy via hang flag
    return Number(r.ai_mode || 0) === 1 || Number(r.hung || r.on_hold || 0) === 1 || String(r.hold_status || '') === 'busy';
  }
  return true;
}

function renderRooms() {
  const rooms = (state.rooms || []).filter(roomMatchesChip);
  const inboxEmpty = document.getElementById('inboxEmpty');
  const closedEmpty = document.getElementById('closedEmpty');
  const isClosed = String(state.status || 'open') === 'closed';
  const openCountEl = document.getElementById('tabOpenCount');
  const closedCountEl = document.getElementById('tabClosedCount');
  if (isClosed) {
    state.closedCount = (state.rooms || []).length;
    if (closedCountEl) closedCountEl.textContent = String(state.closedCount);
    if (openCountEl) openCountEl.textContent = String(state.openCount || 0);
  } else {
    state.openCount = (state.rooms || []).length;
    if (openCountEl) openCountEl.textContent = String(state.openCount);
    if (closedCountEl) closedCountEl.textContent = String(state.closedCount || 0);
  }
  if (!rooms.length) {
    roomList.innerHTML = '';
    if (inboxEmpty) inboxEmpty.hidden = !!isClosed;
    if (closedEmpty) closedEmpty.hidden = !isClosed;
    if (!isClosed && chatEmpty && !state.activeId) chatEmpty.hidden = true;
    if (!inboxEmpty && !closedEmpty) {
      roomList.innerHTML = '<div class="empty" style="padding:24px">暂无会话</div>';
    }
    return;
  }
  if (inboxEmpty) inboxEmpty.hidden = true;
  if (closedEmpty) closedEmpty.hidden = true;
  if (chatEmpty && !state.activeId) chatEmpty.hidden = false;
  const limit = pageSize();
  const shown = rooms.slice(0, limit);
  const more = rooms.length - shown.length;
  roomList.innerHTML = shown
    .map((r) => {
      const active = r.id === state.activeId ? 'active' : '';
      const unread = Number(r.unread_staff || 0);
      const title = r.email || r.visitor_id || r.id;
      const preview = r.last_body || r.last_message || r.preview || (r.current && (r.current.name || r.current.sku)) || '未关联商品';
      const badge = unread > 0 ? `<span class="unread-dot">${unread > 99 ? '99+' : unread}</span>` : '';
      const ai = Number(r.ai_mode || 0) === 1;
      const flag = r.status === 'closed'
        ? '<span class="room-status">已关闭</span>'
        : (ai ? '<span class="room-status ai">AI</span>' : '');
      const initial = String(title).trim().slice(0, 1) || '访';
      return `<button type="button" class="room-item ${active}" data-id="${esc(r.id)}"><span class="avatar">${esc(initial)}</span><span class="room-main"><span class="row"><span class="name">${esc(title)}</span>${flag}<span class="time">${esc(shortTime(r.updated_at))}</span></span><span class="row"><span class="preview">${esc(preview)}</span>${badge}</span></span></button>`;
    })
    .join('') + (more > 0 ? `<div class="page-more muted small">还有 ${more} 个会话</div>` : '');
}


function deskBase() {
  const fromLabel = (baseLabel && baseLabel.textContent || '').trim();
  if (fromLabel && /^https?:\/\//i.test(fromLabel)) return fromLabel.replace(/\/$/, '');
  const input = document.getElementById('baseUrl');
  const fromInput = input && input.value ? String(input.value).trim() : '';
  if (fromInput) return fromInput.replace(/\/$/, '');
  return 'http://127.0.0.1:8787';
}

function mediaUrl(path) {
  const p = String(path || '').trim();
  if (!p) return '';
  if (/^(https?:|data:)/i.test(p)) return p;
  return deskBase() + (p.startsWith('/') ? p : '/' + p);
}

function parseProductBody(body) {
  const b = String(body || '');
  if (!b.startsWith('[product]')) return null;
  try {
    return JSON.parse(b.slice(9).trim());
  } catch (_) {
    return null;
  }
}

function parseOrderBody(body) {
  const b = String(body || '');
  if (!b.startsWith('[order]')) return null;
  try {
    return JSON.parse(b.slice(7).trim());
  } catch (_) {
    return null;
  }
}

function renderBodyHtml(body) {
  const b = String(body || '');
  if (b.startsWith('[img]')) {
    const rest = b.slice(5).trim();
    const url = rest.split(/\s+/)[0] || '';
    const caption = rest.slice(url.length).trim();
    const src = mediaUrl(url);
    if (!src) return esc(b);
    return `<div class="img-bubble"><img class="bubble-img" src="${esc(src)}" alt="${esc(caption || '图片')}" data-full="${esc(src)}" /><div class="img-cap">${esc(caption || '图片')}</div></div>`;
  }
  const prod = parseProductBody(b);
  if (prod) {
    const img = prod.image
      ? `<img src="${esc(mediaUrl(prod.image))}" alt="" />`
      : '<div style="width:64px;height:64px;background:#F7F8FA;border-radius:8px"></div>';
    const opt = prod.option ? `<div class="muted small">规格：${esc(prod.option)}</div>` : '';
    return `<div class="bubble-product">${img}<div><div>${esc(prod.name || prod.sku || '')}</div><div class="price">${esc(prod.price || '')}</div>${opt}<div class="tip">已选规格，用户可直达下单</div></div></div>`;
  }
  const order = parseOrderBody(b);
  if (order) {
    const items = Array.isArray(order.items) ? order.items.filter(Boolean).join(' · ') : '';
    const track = order.tracking ? `<div class="muted small">${esc(order.tracking)}</div>` : '';
    return `<div class="bubble-order"><div class="ord-title">订单 #${esc(String(order.id || order.submit_id || ''))}</div><div class="ord-status">状态：${esc(order.status || '—')}</div>${items ? `<div class="ord-items">${esc(items)}</div>` : ''}${track}</div>`;
  }
  return esc(b);
}

async function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(new Error('read'));
    reader.readAsDataURL(file);
  });
}

async function sendImageFile(file) {
  if (!file || !state.activeId) return;
  if (!window.csDesk || !window.csDesk.uploadImage) {
    alert('桌面桥接未加载，请重启客服台');
    return;
  }
  try {
    const dataUrl = await fileToDataUrl(file);
    const res = await window.csDesk.uploadImage({
      roomId: state.activeId,
      dataUrl,
      filename: file.name || 'image.png',
    });
    if (res && res.ok && Array.isArray(res.messages)) {
      state.messages = res.messages;
      state.lastMsgId = state.messages.reduce((m, x) => Math.max(m, Number(x.id || 0)), 0);
      renderMessages();
      refreshInbox();
    } else {
      alert((res && res.error) || '图片发送失败');
    }
  } catch (err) {
    console.error(err);
    alert('图片发送失败');
  }
}

function renderMessages() {
  const showOps = deskPref('cs_ops', true);
  msgList.innerHTML = state.messages
    .filter((m) => showOps || !(m.role === 'system' && String(m.body || '').startsWith('[ops]')))
    .map((m) => {
      const role = m.role === 'staff' ? 'staff' : m.role === 'system' ? 'system' : 'user';
      const who = role === 'staff' ? staffWhoLabel(m.staff_user) : role === 'system' ? '系统' : '用户';
      let extra = '';
      let rawBody = String(m.body || '');
      const ops = role === 'system' && rawBody.startsWith('[ops]');
      if (ops) rawBody = rawBody.slice(5);
      const isImg = rawBody.startsWith('[img]');
      const isCard = rawBody.startsWith('[product]') || rawBody.startsWith('[order]');
      if (!isImg && !isCard && role === 'user' && m.body_user_original && m.body_user_original !== m.body) {
        const lang = m.lang || m.user_lang || 'zh';
        extra = `<div class="tr-cap"><span class="tr-mark">译</span><span class="tr-lines"><span>原文：${esc(m.body_user_original)}</span><span>已译为 ${esc(lang)}</span></span></div>`;
      } else if (!isImg && !isCard && role === 'staff' && m.translated && m.body_original && m.lang && m.lang !== 'zh') {
        extra = `<div class="tr-cap"><span class="tr-mark">译</span><span class="tr-lines"><span>已译为 ${esc(m.lang)}</span><span>${esc(m.body_original)}</span></span></div>`;
      }
      const showBody = ops ? rawBody : m.body;
      const cls = `bubble ${role}${isCard ? ' cardish' : ''}${isImg ? ' img-card' : ''}${ops ? ' ops' : ''}`;
      return `<div class="${cls}">${renderBodyHtml(showBody)}${extra}<span class="meta">${esc(who)} · ${esc(fmtTime(m.created_at))}</span></div>`;
    })
    .join('');
  scrollMessagesToEnd();
}

function scrollMessagesToEnd() {
  const el = msgList;
  if (!el) return;
  const go = () => {
    try { el.scrollTop = el.scrollHeight; } catch (_) {}
  };
  go();
  requestAnimationFrame(() => {
    go();
    requestAnimationFrame(go);
  });
  setTimeout(go, 40);
  setTimeout(go, 120);
  setTimeout(go, 280);
}

function staffWhoLabel(staffUser) {
  const raw = String(staffUser || '').trim();
  if (!raw) return '客服';
  const isAi = /\bAI\b/i.test(raw) || raw.endsWith(' AI') || raw.includes('AI');
  if (isAi) {
    const aiName = (state.settings && state.settings.ai_name) || 'Harbor';
    return 'AI ' + aiName;
  }
  const hit = state.agentMap[raw];
  const dn = (hit && (hit.display_name || hit.username)) || raw;
  return dn;
}

function updateAssigneeLine(room) {
  const el = document.getElementById('chatAssignee');
  const btnAi = document.getElementById('btnToAi');
  if (!el) return;
  if (!room) {
    el.textContent = '';
    if (btnAi) btnAi.disabled = true;
    return;
  }
  const a = (room.assignee || '').trim();
  const prev = (room.prev_assignee || '').trim();
  const aiOn = Number(room.ai_mode || 0) === 1;
  const aName = a ? staffWhoLabel(a) : '未分配';
  let line = '接待：' + aName;
  if (aiOn) {
    const aiName = (state.settings && state.settings.ai_name) || 'Harbor';
    line += ' · AI接待中（' + aiName + '）';
  }
  if (prev && prev !== a) line += ' · 此前：' + staffWhoLabel(prev);
  el.textContent = line;
  if (btnAi) {
    btnAi.disabled = false;
    btnAi.textContent = aiOn ? 'AI 接待中' : '转给 AI';
  }
}

function fillTransferSelect() {
  const sel = document.getElementById('transferSelect');
  if (!sel) return;
  const me = (state.agent && state.agent.username) || '';
  const online = (state.agents || []).filter((a) => a.enabled && a.can_cs && a.status === 'online' && a.username !== me);
  const cur = sel.value;
  sel.innerHTML = '<option value="">转交给…</option>' + online.map((a) => {
    const label = (a.display_name || a.username) + (a.title ? (' · ' + a.title) : '');
    return `<option value="${esc(a.username)}">${esc(label)}</option>`;
  }).join('');
  if (cur && online.some((a) => a.username === cur)) sel.value = cur;
}

async function loadAgents() {
  if (!window.csDesk.getAgents) return;
  const res = await window.csDesk.getAgents();
  if (res && res.ok) {
    state.agents = res.agents || [];
    const map = {};
    state.agents.forEach((a) => { map[a.username] = a; });
    state.agentMap = map;
    fillTransferSelect();
  }
}

function closeSkuPicker() {
  const modal = document.getElementById('skuPickerModal');
  if (modal) modal.hidden = true;
}

async function sendProductPayload(prod, option) {
  if (!state.activeId) {
    alert('请先选择会话');
    return;
  }
  const payload = {
    sku: prod.sku || '',
    name: prod.name || prod.sku || '',
    image: prod.image || '',
    price: (option && option.price) || prod.price || '',
    option: (option && (option.label || option.option)) || '',
    option_key: (option && (option.id || option.option_key)) || '',
    offer_id: (option && (option.id || option.offer_id)) || '',
  };
  const body = '[product]' + JSON.stringify(payload);
  if (body.length > 2000) {
    alert('商品信息过长，无法发送');
    return;
  }
  const res = await window.csDesk.reply({ roomId: state.activeId, body });
  if (res && res.ok && Array.isArray(res.messages)) {
    state.messages = res.messages;
    state.lastMsgId = state.messages.reduce((m, x) => Math.max(m, Number(x.id || 0)), 0);
    renderMessages();
    refreshInbox();
    closeSkuPicker();
  } else {
    alert((res && res.error) || '发送失败');
  }
}

function openSkuPickerWithProduct(prod) {
  const modal = document.getElementById('skuPickerModal');
  const body = document.getElementById('skuPickerBody');
  const title = document.getElementById('skuPickerTitle');
  if (!modal || !body) return;
  const offers = (prod.offers && prod.offers.length)
    ? prod.offers
    : (prod.sizes || []).map((s) => ({ id: s, label: s, price: prod.price || '', image: prod.image || '' }));
  title.textContent = (prod.name || prod.sku || '商品') + ' · 选择规格';
  if (!offers.length) {
    // single default — send immediately
    sendProductPayload(prod, { label: '', id: '', price: prod.price || '' });
    return;
  }
  if (offers.length === 1) {
    sendProductPayload(prod, offers[0]);
    return;
  }
  body.innerHTML = offers.map((o, i) => {
    const img = o.image
      ? `<img src="${esc(mediaUrl(o.image))}" alt="" />`
      : (prod.image ? `<img src="${esc(mediaUrl(prod.image))}" alt="" />` : '<div style="width:44px;height:44px;background:#F7F8FA;border-radius:8px"></div>');
    return `<button type="button" class="sku-opt" data-opt-idx="${i}">${img}<div><div>${esc(o.label || o.id || '')}</div><div class="muted small">${esc(o.price || prod.price || '')}</div></div></button>`;
  }).join('');
  body.querySelectorAll('.sku-opt').forEach((btn) => {
    btn.addEventListener('click', () => {
      const idx = Number(btn.getAttribute('data-opt-idx') || 0);
      sendProductPayload(prod, offers[idx]);
    });
  });
  modal.hidden = false;
}

async function beginSendProduct(sku) {
  const key = String(sku || '').trim();
  if (!key) return;
  if (!window.csDesk.getProduct) {
    alert('桌面桥接未更新，请重启客服台');
    return;
  }
  const res = await window.csDesk.getProduct(key);
  if (!(res && res.ok && res.product)) {
    // fallback: use room context card fields
    const room = state.activeRoom || {};
    let fallback = null;
    if (room.current && room.current.sku === key) fallback = room.current;
    else if (Array.isArray(room.history)) fallback = room.history.find((h) => h.sku === key);
    if (fallback) {
      openSkuPickerWithProduct({
        sku: fallback.sku,
        name: fallback.name,
        image: fallback.image,
        price: fallback.price,
        offers: [],
        sizes: [],
      });
      return;
    }
    alert((res && res.error) || '找不到商品');
    return;
  }
  openSkuPickerWithProduct(res.product);
}


function renderAgent() {
  const a = state.agent || {};
  const name = a.display_name || a.username || '客服';
  if (agentName) agentName.textContent = name;
  if (agentTitle) agentTitle.textContent = a.title || (a.username ? `@${a.username}` : '');
  if (agentStatus && a.status) agentStatus.value = a.status;
  paintAvatar(document.getElementById('agentAvatar'), name);
  const onlineEl = document.getElementById('statOnline');
  if (onlineEl) {
    const onlineN = (state.agents || []).filter((ag) => ag.status === 'online' && ag.enabled !== false).length;
    onlineEl.textContent = `在线 ${onlineN || (a.status === 'online' ? 1 : 0)}`;
  }
}

function cartCountOf(room) {
  const cart = Array.isArray(room && room.cart) ? room.cart : [];
  return cart.reduce((n, line) => n + Number(line.qty || line.quantity || 1), 0);
}

function visitorStamp(room) {
  if (!room) return '';
  const geo = (room.geo && room.geo.label) || '';
  return [room.email || '', room.visitor_id || '', room.client_ip || '', room.user_lang || '', geo, cartCountOf(room)].join('|');
}

function renderVisitor(room) {
  state.visitorStamp = visitorStamp(room);
  if (!visitorInfo) return;
  if (!room) {
    visitorInfo.innerHTML = '<div class="muted small">选择会话后显示</div>';
    return;
  }
  const geo = (room.geo && room.geo.label) || '';
  const ip = room.client_ip || '-';
  const lang = room.user_lang || '-';
  const cart = Array.isArray(room.cart) ? room.cart : [];
  const count = cart.reduce((n, line) => n + Number(line.qty || line.quantity || 1), 0);
  const title = room.email || room.visitor_id || '访客';
  const live = room.status !== 'closed';
  visitorInfo.innerHTML = `
    <div class="visitor-card">
      <div class="visitor-head">
        <span class="avatar" id="visitorAvatar">${esc(String(title).trim().slice(0, 1) || '访')}</span>
        <div>
          <strong>${esc(title)}</strong>
          <div class="presence ${live ? '' : 'off'}">${live ? '进行中' : '已关闭'}</div>
        </div>
      </div>
      <div class="kv"><span>邮箱</span><strong>${esc(room.email || '-')}</strong></div>
      <div class="kv"><span>访客</span><strong>${esc(room.visitor_id || '-')}</strong></div>
      <div class="kv"><span>IP</span><strong>${esc(ip)}</strong></div>
      <div class="kv"><span>归属地</span><strong>${esc(geo || '未知')}</strong></div>
      <div class="kv"><span>语种</span><strong>${esc(lang)}</strong></div>
      <div class="kv"><span>购物车</span><strong>${count} 件</strong></div>
      <button type="button" id="inviteCart" ${count ? '' : 'disabled'}>邀请下单</button>
    </div>
    <div class="ctx-jumps">
      <button type="button" data-jump="sku">商品</button>
      <button type="button" data-jump="orders">订单</button>
      <button type="button" data-jump="history">足迹</button>
    </div>
  `;
  paintAvatar(document.getElementById('visitorAvatar'), title);
  paintAvatar(document.getElementById('chatAvatar'), title);
  const invite = document.getElementById('inviteCart');
  if (invite) {
    invite.addEventListener('click', async () => {
      if (!state.activeId || !window.csDesk.reply) return;
      const body = '[cart]' + JSON.stringify({ n: count });
      const res = await window.csDesk.reply({ roomId: state.activeId, body });
      if (res && Array.isArray(res.messages)) {
        state.messages = res.messages;
        state.lastMsgId = state.messages.reduce((m, x) => Math.max(m, Number(x.id || 0)), 0);
        renderMessages();
      }
    });
  }
}

function orderMatchesFilter(o) {
  const f = state.orderFilter || 'all';
  if (f === 'all') return true;
  const st = String(o.status || '');
  if (f === 'pending') return /待|未发|pending|paid|待发|处理/.test(st);
  if (f === 'shipped') return /发货|运输|ship|transit|配送/.test(st);
  if (f === 'done') return /完成|签收|done|deliver|关闭|已收/.test(st);
  return true;
}

function renderOrders(orders) {
  if (!ordersList) return;
  const list = (Array.isArray(orders) ? orders : []).filter(orderMatchesFilter);
  if (!list.length) {
    ordersList.innerHTML = '<div class="muted small">暂无该状态订单</div>';
    return;
  }
  ordersList.innerHTML = list.slice(0, 12).map((o) => {
    const id = o.id ?? o.submit_id ?? '';
    const st = o.status || '—';
    const track = o.tracking_no || o.tracking || o.logistics_no || '';
    const carrier = o.carrier || o.shipping_carrier || '';
    return `<div class="order-item" data-id="${esc(id)}">
      <div class="row"><strong>订单号 ${esc(id)}</strong><span class="pill">${esc(st)}</span></div>
      <div class="muted small">${track ? '物流 ' + esc(carrier ? carrier + ' ' : '') + esc(track) : '暂无物流'}</div>
      <div class="order-actions">
        <button type="button" class="btn ghost sm" data-order-view="${esc(id)}">详情</button>
        ${track ? `<button type="button" class="btn ghost sm" data-ship-send="${esc(id)}">发送物流</button>` : ''}
        <button type="button" class="btn primary sm" data-order-send="${esc(id)}">发送订单卡</button>
      </div>
    </div>`;
  }).join('');
}


async function loadStickers() {
  if (!emojiBar) return;
  const fallback = ['🥰','👍','😄','🙏','✨','❤️','🤗','😍','😢','🤔','👏','🙌','🤝','💪','⭐','🎉','🎁','🛒','📦','🚚','✅','❌','🙇','🙇‍♂️'];
  const fill = (list) => {
    const emojis = (list || []).map((x) => (typeof x === 'string' ? x : (x && x.emoji) || '')).filter(Boolean);
    const use = emojis.length ? emojis : fallback;
    emojiBar.innerHTML = use.map((e) => `<button type="button" data-emoji="${e}">${e}</button>`).join('');
  };
  try {
    if (!window.csDesk || !window.csDesk.getStickers) {
      fill(fallback);
      return;
    }
    const res = await window.csDesk.getStickers();
    const items = (res && res.items) || [];
    fill(items);
  } catch (err) {
    console.error(err);
    fill(fallback);
  }
}

async function loadAgent() {
  const res = await window.csDesk.getMe();
  if (!res || !res.ok) return;
  state.agent = res.agent || null;
  state.settings = res.settings || {};
  renderAgent();
  // desk open => mark online unless already busy/away
  const cur = (state.agent && state.agent.status) || 'offline';
  if (cur === 'offline') {
    const up = await window.csDesk.setStatus({ status: 'online' });
    if (up && up.ok) {
      state.agent = up.agent || state.agent;
      renderAgent();
    }
  }
}

async function loadOrders(room) {
  if (!room) {
    state.orders = [];
    renderOrders([]);
    return;
  }
  const res = await window.csDesk.getOrders({ roomId: room.id, email: room.email || '' });
  state.orders = (res && res.ok) ? (res.orders || []) : [];
  renderOrders(state.orders);
}


function updateContext(room) {
  state.activeRoom = room; __harborSyncAiBanner(state.activeRoom);
  if (!room) {
    chatTitle.textContent = '会话';
    chatMeta.textContent = '';
    updateAssigneeLine(null);
    swapProduct(null);
    renderHistory([]);
    syncWorkspace(false);
    return;
  }
  const title = room.email || room.visitor_id || room.id;
  chatTitle.textContent = title;
  paintAvatar(document.getElementById('chatAvatar'), title);
  chatMeta.textContent = `访客 ${room.visitor_id || '-'} · ${room.status === 'closed' ? '已关闭' : '进行中'} · 更新 ${fmtTime(room.updated_at)}`;
  updateAssigneeLine(room);
  fillTransferSelect();
  swapProduct(room.current);
  renderHistory(room.history || []);
}

async function refreshInbox() {
  const res = await window.csDesk.inbox({ status: state.status, q: state.q });
  if (!res.ok) return res;
  const prevUnread = state.rooms.reduce((n, r) => n + Number(r.unread_staff || 0), 0);
  state.rooms = res.rooms || [];
  state.latest = res.latest || state.latest;
  if (state.activeId && !state.rooms.some((r) => r.id === state.activeId)) {
    state.activeId = '';
    state.activeRoom = null; __harborSyncAiBanner(state.activeRoom);
    state.messages = [];
    const empty = document.getElementById('chatEmpty');
    const panel = document.getElementById('chatPanel');
    if (empty) empty.hidden = false;
    if (panel) panel.hidden = true;
    updateContext(null);
    renderVisitor(null);
    renderOrders([]);
    syncWorkspace(false);
  }
  const unread = Number(res.unread_n != null ? res.unread_n : state.rooms.reduce((n, r) => n + Number(r.unread_staff || 0), 0));
  const openN = Number(res.open_n != null ? res.open_n : state.rooms.filter((r) => r.status === 'open').length);
  statOpen.textContent = `进行中 ${openN}`;
  statUnread.textContent = `未读 ${unread}`;
  if (unread > prevUnread && prevUnread >= 0 && state.knownUnread) {
    playPing();
    deskNotify('Harbor 客服', '收到新的用户消息');
  }
  state.knownUnread = 1;
  renderRooms();
  if (!state.deskViewApplied && !state.activeId && localStorage.getItem('cs_desk_view') === 'chat' && state.rooms.length) {
    state.deskViewApplied = true;
    openRoom(state.rooms[0].id);
  }
  return res;
}

async function openRoom(roomId) {
  clearTimeout(typingTimer);
  notifyTyping(false);
  setPeerTyping(null);

  state.activeId = roomId;
  state.roomLoop += 1;
  const loop = state.roomLoop;
  const cached = state.rooms.find((r) => r.id === roomId);
  if (cached) {
    chatEmpty.hidden = true;
    chatPanel.hidden = false;
    chatTitle.textContent = cached.email || cached.visitor_id || roomId;
    chatMeta.textContent = '正在打开…';
  }
  const res = await window.csDesk.getRoom(roomId);
  if (!res.ok) return;
  chatEmpty.hidden = true;
  chatPanel.hidden = false;
  state.messages = res.messages || [];
  state.lastMsgId = state.messages.reduce((m, x) => Math.max(m, Number(x.id || 0)), 0);
  swapProduct(res.room && res.room.current);
  const openedTitle = (res.room && (res.room.email || res.room.visitor_id)) || roomId;
  chatTitle.textContent = openedTitle;
  paintAvatar(document.getElementById('chatAvatar'), openedTitle);
  chatMeta.textContent = `访客 ${(res.room && res.room.visitor_id) || '-'} · ${(res.room && res.room.status) === 'closed' ? '已关闭' : '进行中'} · 更新 ${fmtTime(res.room && res.room.updated_at)}`;
  updateAssigneeLine(res.room || null);
  fillTransferSelect();
  renderHistory((res.room && res.room.history) || []);
  renderVisitor(res.room || null);
  loadOrders(res.room || null);
  renderMessages();
  renderCannedBar();
  showCtx('visitor');
  renderRooms();
  // panel just became visible — pin to latest after layout
  requestAnimationFrame(() => scrollMessagesToEnd());
  setTimeout(() => scrollMessagesToEnd(), 80);
  setTimeout(() => scrollMessagesToEnd(), 250);
  pollRoomLoop(loop, roomId);
}


function setPeerTyping(tp) {
  state.peerTyping = (tp && tp.active) ? tp : null;
  let el = document.getElementById('peerTyping');
  if (!el) {
    const list = document.getElementById('msgList');
    if (!list) return;
    el = document.createElement('div');
    el.id = 'peerTyping';
    el.className = 'peer-typing muted small';
    el.style.padding = '4px 12px 8px';
    el.style.fontStyle = 'italic';
    list.after(el);
  }
  if (state.peerTyping && state.peerTyping.side === 'user') {
    el.hidden = false;
    el.textContent = '用户正在输入…';
  } else {
    el.hidden = true;
    el.textContent = '';
  }
}

let typingTimer = null;
let typingSent = false;
function notifyTyping(on) {
  if (!state.activeId || !window.csDesk.setTyping) return;
  const flag = !!on;
  if (!flag && !typingSent) return;
  typingSent = flag;
  window.csDesk.setTyping({ roomId: state.activeId, typing: flag }).catch(() => {});
}
function fitComposer() {
  if (!replyBody) return;
  replyBody.style.height = '36px';
  replyBody.style.height = Math.min(72, Math.max(36, replyBody.scrollHeight)) + 'px';
}

function onComposerInput() {
  fitComposer();
  if (!state.activeId) return;
  notifyTyping(true);
  clearTimeout(typingTimer);
  typingTimer = setTimeout(() => notifyTyping(false), 2800);
}

async function pollRoomLoop(loop, roomId) {
  while (state.roomLoop === loop && state.activeId === roomId) {
    const res = await window.csDesk.pollRoom({ roomId, after: state.lastMsgId, timeout: 20 });
    if (state.roomLoop !== loop) return;
    if (!res.ok) {
      await new Promise((r) => setTimeout(r, 1500));
      continue;
    }
    const incoming = res.messages || [];
    if (incoming.length) {
      const existing = new Set(state.messages.map((m) => m.id));
      let added = 0;
      for (const m of incoming) {
        if (!existing.has(m.id)) {
          state.messages.push(m);
          added += 1;
          if (m.role === 'user') {
            playPing();
            deskNotify('新消息', String(m.body || '').slice(0, 80));
          }
        }
        state.lastMsgId = Math.max(state.lastMsgId, Number(m.id || 0));
      }
      if (added) renderMessages();
    }
    if (incoming.length) setPeerTyping(null);
    else setPeerTyping(res.typing || null);
    if (res.room && visitorStamp(res.room) !== state.visitorStamp) {
      state.activeRoom = res.room; __harborSyncAiBanner(state.activeRoom);
      renderVisitor(res.room);
    }
    if (res.room && incoming.length) {
      swapProduct(res.room.current);
      renderHistory(res.room.history || []);
      renderVisitor(res.room);
      updateAssigneeLine(res.room); __harborSyncAiBanner(res.room);
      chatMeta.textContent = `访客 ${res.room.visitor_id || '-'} · ${res.room.status === 'closed' ? '已关闭' : '进行中'} · 更新 ${fmtTime(res.room.updated_at)}`;
    }
  }
}

async function pollInboxLoop(loop) {
  while (state.inboxLoop === loop) {
    const res = await window.csDesk.pollInbox({ after: state.latest, timeout: 20 });
    if (state.inboxLoop !== loop) return;
    if (res.ok) {
      if (Array.isArray(res.rooms)) {
        // merge only when viewing open
        if (state.status === 'open') {
          const prevUnread = state.rooms.reduce((n, r) => n + Number(r.unread_staff || 0), 0);
          state.rooms = res.rooms;
          const unread = state.rooms.reduce((n, r) => n + Number(r.unread_staff || 0), 0);
          if (unread > prevUnread) {
            playPing();
            deskNotify('Harbor 客服', '收件箱有更新');
          }
          statOpen.textContent = `进行中 ${state.rooms.length}`;
          statUnread.textContent = `未读 ${unread}`;
          renderRooms();
        }
      }
      if (res.latest) state.latest = res.latest;
    } else {
      await new Promise((r) => setTimeout(r, 2000));
    }
  }
}

function startLoops() {
  state.inboxLoop += 1;
  pollInboxLoop(state.inboxLoop);
  refreshInbox();
  loadStickers();
  loadAgent();
  loadAgents();
}

loginForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  e.stopPropagation();
  loginError.hidden = true;
  loginError.textContent = '';
  if (!window.csDesk || typeof window.csDesk.login !== 'function') {
    loginError.textContent = '桌面桥接未加载，请完全退出后重新打开 Harbor 客服台';
    loginError.hidden = false;
    return;
  }
  const btn = loginForm.querySelector('button[type="submit"]');
  const payload = {
    base: document.getElementById('baseUrl').value.trim(),
    username: document.getElementById('username').value.trim(),
    password: document.getElementById('password').value,
  };
  if (btn) { btn.disabled = true; btn.textContent = '登录中…'; }
  try {
    console.log('cs-desk login start', { base: payload.base, username: payload.username, pwLen: (payload.password || '').length });
    const res = await window.csDesk.login(payload);
    console.log('cs-desk login result', res);
    if (!res || res.ok !== true) {
      showLogin();
      loginError.textContent = (res && res.error) || '登录失败';
      loginError.hidden = false;
      return;
    }
    baseLabel.textContent = res.baseUrl || payload.base;
    showApp();
    startLoops();
  } catch (err) {
    console.log('cs-desk login exception', err);
    showLogin();
    loginError.textContent = '登录异常：' + (err && err.message ? err.message : String(err));
    loginError.hidden = false;
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = '登录'; }
  }
});

document.getElementById('btnLogout').addEventListener('click', async () => {
  state.inboxLoop += 1;
  state.roomLoop += 1;
  await window.csDesk.logout();
  showLogin();
});

document.getElementById('btnRefresh').addEventListener('click', () => refreshInbox());

document.querySelectorAll('.tab').forEach((btn) => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach((b) => b.classList.remove('active'));
    btn.classList.add('active');
    state.status = btn.dataset.status;
    refreshInbox();
  });
});

let searchTimer = null;
searchQ.addEventListener('input', () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    state.q = searchQ.value.trim();
    refreshInbox();
  }, 280);
});

roomList.addEventListener('click', (e) => {
  const btn = e.target.closest('.room-item');
  if (!btn) return;
  openRoom(btn.dataset.id);
});

replyForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const body = replyBody.value.trim();
  if (!body || !state.activeId) return;
  clearTimeout(typingTimer);
  notifyTyping(false);
  replyBody.value = '';
  const res = await window.csDesk.reply({ roomId: state.activeId, body });
  if (res.ok && Array.isArray(res.messages)) {
    state.messages = res.messages;
    state.lastMsgId = state.messages.reduce((m, x) => Math.max(m, Number(x.id || 0)), 0);
    renderMessages();
    refreshInbox();
  }
});

replyBody.addEventListener('input', () => onComposerInput());
replyBody.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    replyForm.requestSubmit();
  }
});

function askConfirm(message) {
  var modal = document.getElementById('askModal');
  var body = document.getElementById('askModalBody');
  var yes = document.getElementById('askModalYes');
  var no = document.getElementById('askModalNo');
  body.textContent = message;
  modal.hidden = false;
  return new Promise(function (resolve) {
    function done(ok) {
      modal.hidden = true;
      yes.removeEventListener('click', onYes);
      no.removeEventListener('click', onNo);
      resolve(ok);
    }
    function onYes() { done(true); }
    function onNo() { done(false); }
    yes.addEventListener('click', onYes);
    no.addEventListener('click', onNo);
  });
}

document.getElementById('btnCloseRoom').addEventListener('click', async () => {
  if (!state.activeId) return;
  if (!(await askConfirm('确认结束该会话？'))) return;
  await window.csDesk.closeRoom(state.activeId);
  state.activeId = null;
  chatPanel.hidden = true;
  chatEmpty.hidden = false;
  syncWorkspace(false);
  state.roomLoop += 1;
  refreshInbox();
});

if (emojiToggle && emojiBar) {
  emojiToggle.addEventListener('click', async () => {
    const opening = emojiBar.hidden;
    if (opening && !emojiBar.childElementCount) {
      await loadStickers();
    }
    emojiBar.hidden = !opening ? true : false;
    if (!emojiBar.hidden && !emojiBar.childElementCount) {
      await loadStickers();
    }
  });
  replyBody.addEventListener('focus', () => { emojiBar.hidden = true; });
}
if (emojiBar) {
  emojiBar.addEventListener('click', (e) => {
    const btn = e.target.closest('button[data-emoji]');
    if (!btn) return;
    const emoji = btn.dataset.emoji || '';
    const start = replyBody.selectionStart || replyBody.value.length;
    const end = replyBody.selectionEnd || start;
    const v = replyBody.value;
    replyBody.value = v.slice(0, start) + emoji + v.slice(end);
    replyBody.focus();
    const pos = start + emoji.length;
    replyBody.setSelectionRange(pos, pos);
  });
}


if (imageToggle && imagePick) {
  imageToggle.addEventListener('click', () => imagePick.click());
  imagePick.addEventListener('change', async () => {
    const file = imagePick.files && imagePick.files[0];
    imagePick.value = '';
    if (file) await sendImageFile(file);
  });
}

if (replyBody) {
  replyBody.addEventListener('paste', async (e) => {
    const items = e.clipboardData && e.clipboardData.items;
    if (!items || !items.length) return;
    for (const it of items) {
      if (it.type && it.type.startsWith('image/')) {
        e.preventDefault();
        const file = it.getAsFile();
        if (file) await sendImageFile(file);
        return;
      }
    }
  });
}

if (msgList) {
  msgList.addEventListener('click', (e) => {
    const img = e.target.closest('img.bubble-img');
    if (!img) return;
    const full = img.getAttribute('data-full') || img.src;
    if (full) window.open(full, '_blank');
  });
}

if (agentStatus) {
  agentStatus.addEventListener('change', async () => {
    const status = agentStatus.value;
    const res = await window.csDesk.setStatus({ status });
    if (res && res.ok) {
      state.agent = res.agent || state.agent;
      renderAgent();
    } else {
      alert((res && res.error) || '状态更新失败');
      renderAgent();
    }
  });
}

ordersList && ordersList.addEventListener('click', async (e) => {
  const shipBtn = e.target.closest('[data-ship-send]');
  const sendBtn = e.target.closest('[data-order-send]');
  const viewBtn = e.target.closest('[data-order-view]');
  if (shipBtn && !sendBtn && !viewBtn) {
    const sid = shipBtn.getAttribute('data-ship-send');
    const found = (state.orders || []).find((row) => String(row.id ?? row.submit_id ?? '') === String(sid));
    const track = found && (found.tracking_no || found.tracking || found.logistics_no || '');
    const carrier = found && (found.carrier || found.shipping_carrier || '');
    if (!state.activeId) { alert('请先选择会话'); return; }
    const text = `物流更新 #${sid}${carrier ? ' · ' + carrier : ''}${track ? ' · ' + track : ''}`;
    const reply = await window.csDesk.reply({ roomId: state.activeId, body: text });
    if (!reply || !reply.ok) { alert((reply && reply.error) || '发送失败'); return; }
    await openRoom(state.activeId);
    refreshInbox();
    return;
  }
  const id = (sendBtn && sendBtn.getAttribute('data-order-send'))
    || (viewBtn && viewBtn.getAttribute('data-order-view'))
    || ((e.target.closest('.order-item') || {}).dataset || {}).id;
  if (!id) return;
  const res = await window.csDesk.getOrder(id);
  if (!res || !res.ok || !res.order) {
    alert('无法打开订单');
    return;
  }
  const o = res.order;
  if (sendBtn) {
    if (!state.activeId) {
      alert('请先选择会话');
      return;
    }
    const payload = {
      id: o.id ?? id,
      status: o.status || '',
      email: o.email || '',
      tracking: o.tracking_no || o.tracking || o.logistics_no || '',
      carrier: o.carrier || o.shipping_carrier || '',
      total: o.due_text || o.total || o.due || '',
      items: Array.isArray(o.items)
        ? o.items.slice(0, 8).map((it) => ({
            sku: it.sku || '',
            name: it.name || it.sku || '',
            qty: it.qty || it.quantity || 1,
          }))
        : [],
    };
    const body = '[order]' + JSON.stringify(payload);
    const reply = await window.csDesk.reply({ roomId: state.activeId, body });
    if (!reply || !reply.ok) {
      alert((reply && reply.error) || '发送失败');
      return;
    }
    await openRoom(state.activeId);
    refreshInbox();
    return;
  }
  const modal = document.getElementById('orderDetailModal');
  const body = document.getElementById('orderDetailBody');
  const send = document.getElementById('orderDetailSend');
  if (modal && body) {
    const rows = [
      ['订单', '#' + (o.id ?? '')],
      ['状态', o.status || '—'],
      ['邮箱', o.email || '—'],
      ['物流', o.tracking_no || o.tracking || o.logistics_no || '无'],
      ['承运', o.carrier || o.shipping_carrier || '—'],
      ['金额', o.due_text || o.total || o.due || '—'],
    ];
    let html = rows.map(([k, v]) => `<div class="line"><span>${esc(k)}</span><b>${esc(String(v))}</b></div>`).join('');
    if (Array.isArray(o.items) && o.items.length) {
      html += '<div class="items">' + o.items.slice(0, 8).map((it) => `<div>${esc(it.name || it.sku || '')} ×${esc(String(it.qty || it.quantity || 1))}</div>`).join('') + '</div>';
    }
    body.innerHTML = html;
    if (send) send.dataset.orderId = String(o.id ?? id);
    modal.hidden = false;
    return;
  }
});

const orderDetailModal = document.getElementById('orderDetailModal');
const orderDetailClose = document.getElementById('orderDetailClose');
const orderDetailSend = document.getElementById('orderDetailSend');
if (orderDetailClose && orderDetailModal) {
  orderDetailClose.addEventListener('click', () => { orderDetailModal.hidden = true; });
  orderDetailModal.addEventListener('click', (ev) => { if (ev.target === orderDetailModal) orderDetailModal.hidden = true; });
}
if (orderDetailSend && orderDetailModal) {
  orderDetailSend.addEventListener('click', () => {
    const oid = orderDetailSend.dataset.orderId || '';
    const btn = oid && ordersList ? ordersList.querySelector('[data-order-send="' + oid.replace(/"/g, '') + '"]') : null;
    orderDetailModal.hidden = true;
    if (btn) btn.click();
  });
}


const inboxChips = document.getElementById('inboxChips');
if (inboxChips) {
  inboxChips.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-chip]');
    if (!btn) return;
    state.inboxChip = btn.getAttribute('data-chip') || 'all';
    inboxChips.querySelectorAll('[data-chip]').forEach((el) => el.classList.toggle('on', el === btn));
    const chipHint = document.getElementById('chipHint');
    const chipCopy = { all: '全部进行中会话', mine: '只看分配给我的', unassigned: '还没有客服接手', hung: '挂起或 AI 接待中' };
    if (chipHint) chipHint.textContent = chipCopy[state.inboxChip] || chipCopy.all;
    renderRooms();
  });
}

(async function boot() {
  try {
    if (!window.csDesk) {
      showLogin();
      loginError.textContent = '桌面桥接未加载，请完全退出后重新打开 Harbor 客服台';
      loginError.hidden = false;
      return;
    }
    const cfg = await window.csDesk.getConfig();
    if (cfg.baseUrl) document.getElementById('baseUrl').value = cfg.baseUrl;
    if (cfg.loggedIn) {
      // validate session; stale cookie must not fake a logged-in shell
      const probe = await window.csDesk.inbox({ status: 'open', q: '' });
      console.log('cs-desk boot probe', probe);
      if (probe && probe.ok) {
        baseLabel.textContent = cfg.baseUrl;
        showApp();
        startLoops();
        return;
      }
      try { await window.csDesk.logout(); } catch (_) {}
    }
    showLogin();
  } catch (err) {
    console.log('cs-desk boot fail', err);
    showLogin();
  }
})();

// --- product send / transfer / sku search ---
document.addEventListener('click', (ev) => {
  const btn = ev.target && ev.target.closest ? ev.target.closest('[data-send-sku]') : null;
  if (btn) {
    ev.preventDefault();
    beginSendProduct(btn.getAttribute('data-send-sku'));
  }
});

const skuPickerClose = document.getElementById('skuPickerClose');
if (skuPickerClose) skuPickerClose.addEventListener('click', closeSkuPicker);
const skuPickerModal = document.getElementById('skuPickerModal');
if (skuPickerModal) {
  skuPickerModal.addEventListener('click', (ev) => {
    if (ev.target === skuPickerModal) closeSkuPicker();
  });
}


const btnToAi = document.getElementById('btnToAi');
if (btnToAi) {
  btnToAi.addEventListener('click', async () => {
    if (!state.activeId) {
      alert('请先选择会话');
      return;
    }
    if (!window.csDesk.toAi) {
      alert('桌面桥接未更新，请重启客服台');
      return;
    }
    if (!(await askConfirm('确认把当前会话转给 AI 自动接待？之后用户发言将由 AI 回复；你再手动回复会接回人工。'))) return;
    btnToAi.disabled = true;
    try {
      const res = await window.csDesk.toAi({ roomId: state.activeId });
      if (!(res && res.ok)) {
        alert((res && res.error) || '转给 AI 失败');
        return;
      }
      if (Array.isArray(res.messages)) {
        state.messages = res.messages;
        state.lastMsgId = state.messages.reduce((m, x) => Math.max(m, Number(x.id || 0)), 0);
        renderMessages();
      }
      if (res.room) {
        state.activeRoom = res.room;
        updateAssigneeLine(res.room); __harborSyncAiBanner(res.room);
      }
    } finally {
      btnToAi.disabled = false;
    }
  });
}

const btnTransfer = document.getElementById('btnTransfer');
if (btnTransfer) {
  btnTransfer.addEventListener('click', async () => {
    const sel = document.getElementById('transferSelect');
    const to = sel && sel.value;
    if (!state.activeId) {
      alert('请先选择会话');
      return;
    }
    if (!to) {
      alert('请选择要转交的在线客服');
      return;
    }
    if (!window.csDesk.transferRoom) {
      alert('桌面桥接未更新，请重启客服台');
      return;
    }
    const res = await window.csDesk.transferRoom({ roomId: state.activeId, toUsername: to });
    if (!(res && res.ok)) {
      alert((res && res.error) || '转交失败');
      return;
    }
    if (Array.isArray(res.messages)) {
      state.messages = res.messages;
      state.lastMsgId = state.messages.reduce((m, x) => Math.max(m, Number(x.id || 0)), 0);
      renderMessages();
    }
    if (res.room) {
      state.activeRoom = res.room;
      updateAssigneeLine(res.room); __harborSyncAiBanner(res.room);
    }
    await refreshInbox();
    // if no longer visible, selection cleared by refreshInbox
    await loadAgents();
  });
}

let skuSearchTimer = null;
const skuSearch = document.getElementById('skuSearch');
const skuSearchResults = document.getElementById('skuSearchResults');
if (skuSearch && skuSearchResults) {
  skuSearch.addEventListener('input', () => {
    clearTimeout(skuSearchTimer);
    skuSearchTimer = setTimeout(async () => {
      const q = skuSearch.value.trim();
      let items = localCatalog.length ? searchLocalCatalog(q) : [];
      if (!items.length && window.csDesk.searchProducts) {
        const res = await window.csDesk.searchProducts(q);
        items = (res && res.items) || [];
      }
      if (!items.length) {
        skuSearchResults.innerHTML = '<div class="muted small">无结果</div>';
        return;
      }
      skuSearchResults.innerHTML = items.slice(0, 12).map((it) => {
        const img = it.image ? `<img src="${esc(mediaUrl(it.image))}" alt="" />` : '<div></div>';
        return `<div class="sku-search-item">${img}<div class="t"><div class="hn">${esc(it.name || it.sku)}</div><div class="sub">SKU ${esc(it.sku)}</div><div class="price">${esc(it.price || '')}</div></div><button type="button" data-send-sku="${esc(it.sku)}">发送</button></div>`;
      }).join('');
    }, 280);
  });
}




/* Function S-state wire */
(function () {
  const $ = (id) => document.getElementById(id);
  const settingsBtn = $('btnSettings');
  const settingsPanel = $('settingsPanel');
  const settingsClose = $('settingsClose');
  const settingsSave = $('settingsSave');
  const statusSel = $('agentStatus');
  const statusHint = $('statusHint');
  const agentBox = document.querySelector('.agent-box');
  const transferModal = $('transferModal');
  const transferClose = $('transferModalClose');
  const transferConfirm = $('transferModalConfirm');
  const transferModalSelect = $('transferModalSelect');
  const btnTransfer = $('btnTransfer');
  const aiBanner = $('aiBanner');

  function openSettings() {
    if (!settingsPanel) return;
    settingsPanel.hidden = false;
    /* Global CS settings: /admin/cs (no duplicate APIs here). */
    const nick = $('setNick'); const title = $('setTitle');
    try {
      if (nick) nick.value = localStorage.getItem('cs_nick') || ($('agentName')?.textContent || '');
      if (title) title.value = localStorage.getItem('cs_title') || ($('agentTitle')?.textContent || '');
      const sound = $('setSound'); if (sound) sound.checked = localStorage.getItem('cs_sound') !== '0';
      const desk = $('setDesktop'); if (desk) desk.checked = localStorage.getItem('cs_desktop') !== '0';
      const compact = $('setCompact'); if (compact) compact.checked = localStorage.getItem('cs_compact') === '1';
      const ops = $('setShowOps'); if (ops) ops.checked = localStorage.getItem('cs_ops') !== '0';
      const canned = $('setCanned'); if (canned) canned.value = localStorage.getItem('cs_canned') ?? DEFAULT_CANNED.join('\n');
      const cannedOn = $('setCannedOn'); if (cannedOn) cannedOn.checked = localStorage.getItem('cs_canned_on') !== '0';
      const view = $('setDeskView'); if (view) view.value = localStorage.getItem('cs_desk_view') || 'list';
      const size = $('setPageSize'); if (size) size.value = localStorage.getItem('cs_page_size') || '20';
      const admin = $('openAdminCs');
      if (admin) admin.href = (typeof deskBase === 'function' ? deskBase() : '') + '/admin/cs';
    } catch (_) {}
  }
  function closeSettings() {
    if (settingsPanel) settingsPanel.hidden = true;
    const ctx = document.querySelector('.context');
    const on = document.querySelector('.ctx-tabs button.on');
    syncRail(ctx && !ctx.hidden && on ? on.getAttribute('data-ctx') : 'inbox');
  }
  settingsBtn?.addEventListener('click', () => { openSettings(); syncRail('settings'); });
  settingsClose?.addEventListener('click', closeSettings);
  $('settingsCancel')?.addEventListener('click', closeSettings);
  settingsPanel?.addEventListener('click', (e) => { if (e.target === settingsPanel) closeSettings(); });

  document.querySelectorAll('.settings-tabs button').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.settings-tabs button').forEach((b) => b.classList.remove('on'));
      btn.classList.add('on');
      const id = btn.getAttribute('data-stab');
      ['profile','canned','notify','desk'].forEach((k) => {
        const el = $('stab-' + k);
        if (el) el.hidden = k !== id;
      });
    });
  });

  settingsSave?.addEventListener('click', () => {
    try {
      localStorage.setItem('cs_nick', $('setNick')?.value || '');
      localStorage.setItem('cs_title', $('setTitle')?.value || '');
      localStorage.setItem('cs_sound', $('setSound')?.checked ? '1' : '0');
      localStorage.setItem('cs_desktop', $('setDesktop')?.checked ? '1' : '0');
      localStorage.setItem('cs_compact', $('setCompact')?.checked ? '1' : '0');
      localStorage.setItem('cs_ops', $('setShowOps')?.checked ? '1' : '0');
      localStorage.setItem('cs_canned', $('setCanned')?.value || '');
      localStorage.setItem('cs_canned_on', $('setCannedOn')?.checked ? '1' : '0');
      localStorage.setItem('cs_desk_view', $('setDeskView')?.value || 'list');
      localStorage.setItem('cs_page_size', $('setPageSize')?.value || '20');
      if ($('agentName') && $('setNick')?.value) $('agentName').textContent = $('setNick').value;
      if ($('agentTitle') && $('setTitle')) $('agentTitle').textContent = $('setTitle').value;
      paintAvatar($('agentAvatar'), $('setNick')?.value || $('agentName')?.textContent || '客');
    } catch (_) {}
    applyDeskPrefs();
    closeSettings();
  });

  function syncStatusUi() {
    const v = statusSel?.value || 'online';
    if (statusHint) statusHint.hidden = !(v === 'away' || v === 'busy');
    if (agentBox) {
      agentBox.classList.toggle('away-mode', v === 'away');
      agentBox.classList.toggle('busy-mode', v === 'busy');
    }
  }
  statusSel?.addEventListener('change', syncStatusUi);
  syncStatusUi();
  applyDeskPrefs();

  document.querySelectorAll('[data-ctx]').forEach((btn) => {
    btn.addEventListener('click', () => showCtx(btn.getAttribute('data-ctx')));
  });
  $('ctxClose')?.addEventListener('click', () => { syncWorkspace(false); syncRail('inbox'); });
  document.querySelectorAll('.rail-item').forEach((btn) => {
    btn.addEventListener('click', () => {
      const key = btn.getAttribute('data-rail') || 'inbox';
      if (key === 'settings') {
        openSettings();
        syncRail('settings');
        return;
      }
      if (key === 'inbox') {
        syncRail('inbox');
        return;
      }
      if (!state.activeId) {
        syncRail('inbox');
        return;
      }
      showCtx(key);
    });
  });
  $('btnVisitor')?.addEventListener('click', () => showCtx('visitor'));
  $('btnSku')?.addEventListener('click', () => showCtx('sku'));
  $('btnOrders')?.addEventListener('click', () => showCtx('orders'));
  visitorInfo?.addEventListener('click', (e) => {
    const jump = e.target.closest('[data-jump]');
    if (!jump) return;
    showCtx(jump.getAttribute('data-jump'));
  });
  const orderFilters = $('orderFilters');
  orderFilters?.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-ofilt]');
    if (!btn) return;
    state.orderFilter = btn.getAttribute('data-ofilt') || 'all';
    orderFilters.querySelectorAll('[data-ofilt]').forEach((el) => el.classList.toggle('on', el === btn));
    renderOrders(state.orders);
  });
  const cannedBar = $('cannedBar');
  cannedBar?.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-canned]');
    if (!btn || !replyBody) return;
    const line = btn.getAttribute('data-canned') || '';
    const start = replyBody.selectionStart || replyBody.value.length;
    const v = replyBody.value;
    const glue = v && start && !/\s$/.test(v.slice(0, start)) ? ' ' : '';
    replyBody.value = v.slice(0, start) + glue + line + v.slice(start);
    replyBody.focus();
    fitComposer();
  });
  $('pwToggle')?.addEventListener('click', () => {
    const input = $('password');
    const toggle = $('pwToggle');
    if (!input || !toggle) return;
    const show = input.type === 'password';
    input.type = show ? 'text' : 'password';
    toggle.setAttribute('aria-pressed', show ? 'true' : 'false');
    toggle.setAttribute('aria-label', show ? '隐藏密码' : '显示密码');
  });

  function openTransferModal() {
    if (!transferModal) return;
    const src = $('transferSelect');
    if (transferModalSelect && src) {
      transferModalSelect.innerHTML = src.innerHTML;
      transferModalSelect.value = src.value;
    }
    transferModal.hidden = false;
  }
  function closeTransferModal() { if (transferModal) transferModal.hidden = true; }
  // Prefer modal when clicking 转交 if modal exists; keep original handler by cloning option sync
  // Open modal when clicking 转交 without a selected agent; confirm calls real transferRoom API
  btnTransfer?.addEventListener('click', (e) => {
    if (!transferModal) return;
    const src = $('transferSelect');
    if (src && !src.value) {
      e.preventDefault();
      e.stopImmediatePropagation();
      openTransferModal();
    }
  }, true);
  transferClose?.addEventListener('click', closeTransferModal);
  transferModal?.addEventListener('click', (e) => { if (e.target === transferModal) closeTransferModal(); });
  transferConfirm?.addEventListener('click', async () => {
    const to = transferModalSelect && transferModalSelect.value;
    const src = $('transferSelect');
    if (src && to) src.value = to;
    closeTransferModal();
    if (!to || !state.activeId) {
      alert('请选择要转交的在线客服');
      return;
    }
    if (!window.csDesk || !window.csDesk.transferRoom) {
      alert('桌面桥接未更新，请重启客服台');
      return;
    }
    const note = ($('transferNote') && $('transferNote').value) || '';
    const res = await window.csDesk.transferRoom({ roomId: state.activeId, toUsername: to, note });
    if (!(res && res.ok)) {
      alert((res && res.error) || '转交失败');
      return;
    }
    if (Array.isArray(res.messages)) {
      state.messages = res.messages;
      state.lastMsgId = state.messages.reduce((m, x) => Math.max(m, Number(x.id || 0)), 0);
      if (typeof renderMessages === 'function') renderMessages();
    }
    if (res.room) {
      state.activeRoom = res.room;
      if (typeof updateAssigneeLine === 'function') updateAssigneeLine(res.room);
      __harborSyncAiBanner(res.room);
    }
    if (typeof refreshInbox === 'function') await refreshInbox();
    if (typeof loadAgents === 'function') await loadAgents();
  });

  // Expose AI banner helper for existing room render if present
  window.__harborShowAiBanner = function (on) {
    if (aiBanner) aiBanner.hidden = !on;
  };

  // Empty inbox visibility helper
  window.__harborInboxEmpty = function (empty, closedEmpty) {
    const ie = $('inboxEmpty');
    const ce = $('closedEmpty');
    const rl = $('roomList');
    if (ie) ie.hidden = !empty;
    if (ce) ce.hidden = !closedEmpty;
    if (rl && empty) { /* list may still render */ }
  };
})();

function __harborSyncAiBanner(room) {
  const aiBanner = document.getElementById('aiBanner');
  if (!aiBanner) return;
  const on = room && Number(room.ai_mode || 0) === 1;
  aiBanner.hidden = !on;
}
