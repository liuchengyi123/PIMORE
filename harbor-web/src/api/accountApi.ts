import { harborRequest } from './http'
import { apiRoot, LIVE_ORIGIN, shopOrigin } from './config'
import { withShopLang } from './catalogLang'

export interface OrderItemPreview {
  name: string
  image?: string
  qty?: number
  option?: string
}

export interface OrderRow {
  id: string
  status: string
  statusLabel: string
  due: string
  image?: string
  date?: string
  itemCount?: number
  tracking?: string
  items?: OrderItemPreview[]
}

export interface OrderLine {
  sku: string
  name: string
  option: string
  qty: number
  price: string
  amount: string
  image?: string
}

export interface OrderTotal {
  label: string
  value: string
  emphasis?: boolean
}

export interface OrderDetail {
  ok: boolean
  live: boolean
  id: string
  status: string
  due: string
  arrives: string
  tracking: string
  carrier: string
  summary: string[]
  canPay: boolean
  canCancel: boolean
  rawHint?: string
  email: string
  shipName: string
  address: string
  payMethod: string
  lines: OrderLine[]
  totals: OrderTotal[]
}

export interface InvoiceModel {
  ok: boolean
  id: string
  email: string
  shipName: string
  address: string
  lines: OrderLine[]
  due: string
  payMethod: string
  note: string
}

export interface AccountSummary {
  ok: boolean
  live: boolean
  signedIn: boolean
  email: string
  pending: number
  paid: number
  shipped: number
  checkedToday?: boolean
  message?: string
}

function decodeEntities(s: string): string {
  return s
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&nbsp;/g, ' ')
}

function strip(s: string): string {
  return decodeEntities(s.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim())
}

function absUrl(path: string): string {
  if (!path) return ''
  if (/^https?:\/\//i.test(path)) return path
  const root = apiRoot()
  const p = path.startsWith('/') ? path : '/' + path
  if (root.startsWith('/')) return root + p
  return LIVE_ORIGIN + p
}

function statusFromLabel(st: string): string {
  const s = st.toLowerCase()
  if (/return|refund|退/.test(s)) return 'return'
  if (/ship|运输|发货/.test(s)) return 'shipped'
  if (/paid|complete|完成|已付/.test(s)) return 'paid'
  if (/await|pend|unpaid|待付|待支付/.test(s)) return 'pending'
  return s || 'unknown'
}

function pushArtOrder(orders: OrderRow[], id: string, block: string) {
  const img = block.match(/<img[^>]+src="([^"]+)"/i)?.[1]
  const nm = strip(block.match(/class="nm"[^>]*>([\s\S]*?)<\/div>/i)?.[1] || '')
  const meta = strip(block.match(/class="meta"[^>]*>([\s\S]*?)<\/div>/i)?.[1] || '')
  const st = strip(block.match(/class="st[^"]*"[^>]*>([\s\S]*?)<\/span>/i)?.[1] || '')
  const status = statusFromLabel(st)
  orders.push({
    id,
    status,
    statusLabel: st || status,
    due: meta || nm,
    image: img ? absUrl(img) : undefined,
    items: img ? [{ name: nm, image: absUrl(img) }] : nm ? [{ name: nm }] : [],
  })
}

function parseOrderCard(chunk: string): OrderRow | null {
  const head = strip(chunk.match(/<span class="tiny"[^>]*>([\s\S]*?)<\/span>/i)?.[1] || '')
  if (!head) return null
  const bits = head.split('·').map((s) => s.trim()).filter(Boolean)
  const id = bits[0] || ''
  const date = bits.slice(1).join(' · ')
  const st = strip(chunk.match(/class="fn-pill[^"]*"[^>]*>([\s\S]*?)<\/span>/i)?.[1] || '')
  const nm = strip(chunk.match(/class="nm"[^>]*>([\s\S]*?)<\/div>/i)?.[1] || '')
  const due = strip(chunk.match(/class="price"[^>]*>([\s\S]*?)<\/div>/i)?.[1] || '')
  const images = [...chunk.matchAll(/<img[^>]+src="([^"]+)"/gi)].map((m) => absUrl(m[1])).filter(Boolean)
  const tinies = [...chunk.matchAll(/<div class="tiny"[^>]*>([\s\S]*?)<\/div>/gi)].map((m) => strip(m[1])).filter(Boolean)
  const countMatch = nm.match(/^(\d+)\s*(?:items|件)/i)
  const nameLine = countMatch ? (tinies.find((t) => t.includes('+') || t.includes('、')) || tinies[0] || '') : ''
  const tracking = (countMatch ? tinies.find((t) => t !== nameLine) : tinies[0]) || ''
  const names = (nameLine ? nameLine.split(/\s+\+\s+/) : nm && !countMatch ? [nm] : [])
    .map((s) => s.trim())
    .filter(Boolean)
  const items: OrderItemPreview[] = images.map((image, i) => ({
    name: names[i] || (countMatch ? '' : nm),
    image,
  }))
  if (!items.length && nm && !countMatch) items.push({ name: nm })
  const itemCount = countMatch ? Number(countMatch[1]) : Math.max(items.length, names.length)
  return {
    id,
    status: statusFromLabel(st),
    statusLabel: st || statusFromLabel(st),
    due,
    image: images[0],
    date,
    itemCount: itemCount || undefined,
    tracking,
    items,
  }
}

export function parseOrdersHtml(html: string): { signedIn: boolean; loginRequired: boolean; orders: OrderRow[] } {
  if (!html) return { signedIn: false, loginRequired: true, orders: [] }
  const hasCard = /fn-order-card/i.test(html)
  const hasArt = /class=["']art["']/i.test(html)
  if (/name=["']password["']/i.test(html) && !hasArt && !hasCard && /\/login/i.test(html)) {
    return { signedIn: false, loginRequired: true, orders: [] }
  }
  const orders: OrderRow[] = []
  const re = /<a\s+class="art"\s+href="\/orders\/([^"?]+)[^"]*"[^>]*>([\s\S]*?)<\/a>/gi
  let m: RegExpExecArray | null
  while ((m = re.exec(html))) pushArtOrder(orders, m[1], m[2])
  if (!orders.length && hasCard) {
    const parts = html.split(/<div class="fn-order-card">/i).slice(1)
    for (const part of parts) {
      const chunk = part.split(/<div class="fn-sec-head"|<p class="fn-empty"|<a class="fn-me-cs/)[0]
      const row = parseOrderCard(chunk)
      if (row?.id) orders.push(row)
    }
  }
  const signedIn = orders.length > 0 || /class=["']acchead["']/i.test(html) || /fn-order-tabs/i.test(html)
  return { signedIn, loginRequired: !signedIn && /\/login/i.test(html), orders }
}

export async function fetchOrders(status = '') {
  const q = status ? '?status=' + encodeURIComponent(status) : ''
  try {
    const res = await harborRequest<string>('/account/orders' + q, { method: 'GET' })
    const raw = typeof res.data === 'string' ? res.data : String(res.data || '')
    const parsed = parseOrdersHtml(raw)
    return { ok: true, live: true, loginRequired: parsed.loginRequired, orders: parsed.orders }
  } catch (e) {
    return {
      ok: false,
      live: false,
      loginRequired: false,
      orders: [] as OrderRow[],
      message: e instanceof Error ? e.message : 'network',
    }
  }
}

function blankDetail(id: string, extra: Partial<OrderDetail> = {}): OrderDetail {
  return {
    ok: false,
    live: false,
    id,
    status: '',
    due: '',
    arrives: '',
    tracking: '',
    carrier: '',
    summary: [],
    canPay: false,
    canCancel: false,
    email: '',
    shipName: '',
    address: '',
    payMethod: '',
    lines: [],
    totals: [],
    ...extra,
  }
}

function parseSumRows(html: string): OrderTotal[] {
  const totals: OrderTotal[] = []
  const re = /<div class="fn-sum-row([^"]*)"[^>]*>\s*<span[^>]*>([\s\S]*?)<\/span>\s*<span[^>]*>([\s\S]*?)<\/span>/gi
  let m: RegExpExecArray | null
  while ((m = re.exec(html))) {
    const label = strip(m[2])
    const value = strip(m[3])
    if (!label && !value) continue
    if (/×|x\s*\d/i.test(label) && !value) continue
    totals.push({ label, value, emphasis: /total/i.test(m[1]) })
  }
  return totals
}

export function parseOrderDetail(html: string, id: string): OrderDetail {
  if (!html || html.length < 40) return blankDetail(id)
  const steps = html.match(/class="fn-track-steps"[\s\S]*?<\/div>/i)?.[0] || ''
  const spans = [...steps.matchAll(/<span class="([^"]*)"[^>]*>([\s\S]*?)<\/span>/gi)]
  const onCount = spans.filter((s) => /\bon\b/.test(s[1])).length
  let status = ''
  if (onCount >= 3) status = 'shipped'
  else if (onCount === 2) status = 'paid'
  else if (onCount === 1) status = 'pending'
  if (!status) {
    const legacy = strip(
      html.match(/<ol class="steps[\s\S]*?<\/ol>[\s\S]*?<p class="price"[^>]*>[\s\S]*?<\/p>\s*<p>([\s\S]*?)<\/p>/i)?.[1] || '',
    )
    const nm = strip(html.match(/class="nm"[^>]*>([\s\S]*?)<\/div>/i)?.[1] || '')
    status = statusFromLabel(legacy || nm)
  }
  const due =
    strip(html.match(/class="price"[^>]*>([\s\S]*?)<\/(?:p|span|div)>/i)?.[1] || '') ||
    strip(html.match(/data-due-local="([^"]*)"/i)?.[1] || '')
  const tiny = strip(html.match(/<p class="tiny"[^>]*>([\s\S]*?)<\/p>/i)?.[1] || '')
  const trackM = tiny.match(/(?:承运商|carrier)\s*([^·]+)\s*·\s*([^·]+)/i)
  const carrier = trackM ? trackM[1].trim() : strip(html.match(/carrier[^<]*<\/[^>]+>\s*([^<]+)/i)?.[1] || '')
  const tracking = trackM
    ? trackM[2].trim()
    : strip(html.match(/tracking[^<]*<a[^>]*>([\s\S]*?)<\/a>/i)?.[1] || '')
  const arrivesM = tiny.match(/(\d+)\s*[–-]\s*(\d+)/) || html.match(/>(\d+)\s*[–-]\s*(\d+)\s*days/i)
  const arrives = arrivesM ? `${arrivesM[1]}–${arrivesM[2]}` : ''
  const summary: string[] = []
  const sumBlock = html.match(/class="summary"[^>]*>([\s\S]*?)<\/section>/i)?.[1] || ''
  for (const pm of sumBlock.matchAll(/<p>([\s\S]*?)<\/p>/gi)) {
    const t = strip(pm[1])
    if (t) summary.push(t)
  }
  const totals = parseSumRows(html)
  for (const row of totals) {
    if (row.label && row.value) summary.push(`${row.label} ${row.value}`)
  }
  const email = strip(html.match(/data-email="([^"]*)"/i)?.[1] || '')
  const payChecked = strip(html.match(/name="pay_method"[^>]*checked[^>]*value="([^"]+)"|name="pay_method"[^>]*value="([^"]+)"[^>]*checked/i)?.[1] || html.match(/name="pay_method"[^>]*value="([^"]+)"[^>]*checked/i)?.[1] || '')
  return {
    ok: true,
    live: true,
    id,
    status: status || 'unknown',
    due,
    arrives,
    tracking,
    carrier,
    summary,
    canPay: /action="\/orders\/[^"]+\/pay"/i.test(html),
    canCancel: /action="\/orders\/[^"]+\/cancel"/i.test(html),
    email,
    shipName: '',
    address: '',
    payMethod: payChecked,
    lines: [],
    totals,
  }
}

export function parseInvoiceHtml(html: string): InvoiceModel {
  const empty: InvoiceModel = {
    ok: false, id: '', email: '', shipName: '', address: '', lines: [], due: '', payMethod: '', note: '',
  }
  if (!html || !/fn-invoice|invoice/i.test(html)) return empty
  const tinies = [...html.matchAll(/<p class="tiny"[^>]*>([\s\S]*?)<\/p>/gi)].map((m) => strip(m[1])).filter(Boolean)
  const email = tinies.find((t) => /@/.test(t)) || ''
  const idTiny = tinies.find((t) => /订单|order/i.test(t)) || ''
  const id = (idTiny.match(/(\d{2,}|[A-Z]{1,4}-?\d{3,})/i) || [])[1] || ''
  const addrTiny = tinies.find((t) => t !== email && t !== idTiny && t.includes('·') && !/paypal|stripe|card|lianlian|连连/i.test(t)) || ''
  const [shipName, ...rest] = addrTiny.split('·').map((s) => s.trim())
  const payTiny = [...tinies].reverse().find((t) => /paypal|stripe|card|lianlian|连连|standard|express/i.test(t)) || ''
  const lines: OrderLine[] = []
  for (const m of html.matchAll(/<div class="fn-sum-row(?![^"]*total)[^"]*"[^>]*>\s*<span[^>]*>([\s\S]*?)<\/span>/gi)) {
    const label = strip(m[1])
    const qtyM = label.match(/^(.*?)\s*[×x]\s*(\d+)\s*$/i)
    if (!qtyM) continue
    lines.push({
      sku: qtyM[1].trim(),
      name: qtyM[1].trim(),
      option: '',
      qty: Number(qtyM[2]) || 1,
      price: '',
      amount: '',
    })
  }
  const due = strip(html.match(/class="fn-sum-row total"[\s\S]*?class="price"[^>]*>([\s\S]*?)<\/span>/i)?.[1] || '')
  return {
    ok: Boolean(id || email || lines.length || due),
    id,
    email,
    shipName: shipName || '',
    address: rest.join(' ').trim(),
    lines,
    due,
    payMethod: payTiny.split('·')[0]?.trim() || '',
    note: payTiny,
  }
}

export async function postOrderReturn(id: string, reason: string) {
  const res = await harborRequest<string>('/orders/' + encodeURIComponent(id) + '/return', {
    method: 'POST',
    form: true,
    data: { reason },
  })
  return { ok: res.statusCode < 400, status: res.statusCode }
}

export async function postBuyAgain(id: string) {
  const res = await harborRequest<string>('/orders/' + encodeURIComponent(id) + '/again', {
    method: 'POST',
    form: true,
    data: {},
  })
  return { ok: res.statusCode < 400, status: res.statusCode }
}

export async function fetchOrderDetail(id: string): Promise<OrderDetail> {
  try {
    const res = await harborRequest<string>('/orders/' + encodeURIComponent(id), { method: 'GET' })
    const html = typeof res.data === 'string' ? res.data : String(res.data || '')
    return parseOrderDetail(html, id)
  } catch (e) {
    return blankDetail(id, { rawHint: e instanceof Error ? e.message : 'network' })
  }
}

export async function fetchAccountSummary(): Promise<AccountSummary> {
  try {
    const res = await harborRequest<string>('/account', { method: 'GET' })
    const html = typeof res.data === 'string' ? res.data : String(res.data || '')
    if (/name=["']password["']/i.test(html) && /\/login/i.test(html) && !/class=["']acchead["']/i.test(html)) {
      return { ok: true, live: true, signedIn: false, email: '', pending: 0, paid: 0, shipped: 0, message: 'login-required' }
    }
    const head = html.match(/class=["']acchead["'][\s\S]*?<\/div>\s*<\/div>/i)?.[0] || html.slice(0, 4000)
    const emailM = head.match(/<b>([^<]+)<\/b>/i)
    let email = emailM ? strip(emailM[1]) : ''
    if (!email.includes('@')) email = ''
    const nums = [...html.matchAll(/class=["']status-row["'][\s\S]*?<\/div>/gi)]
    let pending = 0
    let paid = 0
    let shipped = 0
    if (nums[0]) {
      const bs = [...nums[0][0].matchAll(/<b>(\d+)<\/b>/gi)].map((m) => Number(m[1]))
      pending = bs[0] || 0
      paid = bs[1] || 0
      shipped = bs[2] || 0
    }
    const checkedToday = /act_checked|checked|✓/i.test(
      html.match(/href=["'][^"']*\/check-in[^"']*["'][\s\S]{0,200}/i)?.[0] || '',
    )
    return {
      ok: true,
      live: true,
      signedIn: Boolean(email),
      email,
      pending,
      paid,
      shipped,
      checkedToday,
    }
  } catch (e) {
    return {
      ok: false,
      live: false,
      signedIn: false,
      email: '',
      pending: 0,
      paid: 0,
      shipped: 0,
      message: e instanceof Error ? e.message : 'network',
    }
  }
}

export function loginUrl(next = '/account') {
  // Shop HTML login page (not /harbor-api). H5 pages should prefer router /login.
  return withShopLang(shopOrigin() + '/login?next=' + encodeURIComponent(next))
}

export function checkoutUrl(buy = false) {
  return withShopLang(shopOrigin() + (buy ? '/checkout?buy=1' : '/checkout'))
}


export interface AddressRow {
  name: string
  line: string
}

export interface PayMethodRow {
  brand: string
  last4: string
}

function stripHtml(s: string): string {
  return decodeEntities(s.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim())
}

export async function fetchHtmlPath(path: string): Promise<string> {
  const res = await harborRequest<string>(path, { method: 'GET' })
  return typeof res.data === 'string' ? res.data : String(res.data || '')
}

export function parseAddressArts(html: string): { loginRequired: boolean; rows: AddressRow[] } {
  if (/name=["']password["']/i.test(html) && !/class=["']art["']/i.test(html)) {
    return { loginRequired: true, rows: [] }
  }
  const rows: AddressRow[] = []
  const re = /<article\s+class="art">([\s\S]*?)<\/article>/gi
  let m: RegExpExecArray | null
  while ((m = re.exec(html))) {
    const block = m[1]
    const name = stripHtml(block.match(/class="nm"[^>]*>([\s\S]*?)<\/div>/i)?.[1] || '')
    const line = stripHtml(block.match(/class="meta"[^>]*>([\s\S]*?)<\/div>/i)?.[1] || '')
    if (name || line) rows.push({ name: name || 'Address', line })
  }
  return { loginRequired: false, rows }
}

export function parsePaymentArts(html: string): { loginRequired: boolean; rows: PayMethodRow[] } {
  if (/name=["']password["']/i.test(html) && !/class=["']art["']/i.test(html) && /\/login/i.test(html)) {
    return { loginRequired: true, rows: [] }
  }
  const rows: PayMethodRow[] = []
  const re = /<article\s+class="art">([\s\S]*?)<\/article>/gi
  let m: RegExpExecArray | null
  while ((m = re.exec(html))) {
    const block = m[1]
    const brand = stripHtml(block.match(/class="nm"[^>]*>([\s\S]*?)<\/div>/i)?.[1] || 'Card')
    const meta = stripHtml(block.match(/class="meta"[^>]*>([\s\S]*?)<\/div>/i)?.[1] || '')
    const last4 = (meta.match(/(\d{4})\s*$/) || [])[1] || meta.replace(/[^\d]/g, '').slice(-4)
    rows.push({ brand, last4 })
  }
  return { loginRequired: false, rows }
}

export async function fetchAddresses() {
  const html = await fetchHtmlPath('/account/addresses')
  return parseAddressArts(html)
}

export async function fetchPayments() {
  const html = await fetchHtmlPath('/account/payments')
  return parsePaymentArts(html)
}

export async function fetchWishlistHtml(): Promise<string> {
  return fetchHtmlPath('/account/wishlist')
}

export function parsePolicyBlocks(html: string): { title: string; body: string }[] {
  const out: { title: string; body: string }[] = []
  const re = /class="pdinfo"[^>]*>([\s\S]*?)<\/div>/gi
  let m: RegExpExecArray | null
  while ((m = re.exec(html))) {
    const block = m[1]
    const title = stripHtml(block.match(/<b>([\s\S]*?)<\/b>/i)?.[1] || 'Info')
    const body = stripHtml(block.replace(/<b>[\s\S]*?<\/b>/i, ''))
    out.push({ title, body })
  }
  return out
}

/** POST /login — cookie set via /harbor-api proxy. */
export async function loginAccount(email: string, password: string, next = '/me'): Promise<{ ok: boolean; status: number; next?: string; error?: string }> {
  const root = apiRoot().replace(/\/$/, '')
  // Prefer JSON stay-on-page API (Function D45+); fall back to form POST.
  try {
    const jr = await fetch(root + '/api/auth/login', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
      body: JSON.stringify({ email: email.trim().toLowerCase(), password }),
    })
    const data = await jr.json().catch(() => ({} as any))
    if (jr.ok && data && data.ok) return { ok: true, status: jr.status, next: next.startsWith('/') ? next : '/me' }
    if (jr.status === 401 || data?.code === 'bad') return { ok: false, status: 401, error: 'bad-credentials' }
  } catch (_) { /* fall through */ }
  const body = new URLSearchParams({
    email: email.trim().toLowerCase(),
    password,
    next: next.startsWith('/') ? next : '/me',
  })
  const res = await fetch(root + '/login', {
    method: 'POST',
    credentials: 'include',
    redirect: 'manual',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded', Accept: 'text/html,*/*' },
    body,
  })
  if (res.status === 401) return { ok: false, status: 401, error: 'bad-credentials' }
  if (res.status >= 300 && res.status < 400) {
    const loc = res.headers.get('Location') || next
    return { ok: true, status: res.status, next: loc }
  }
  if (res.ok) return { ok: true, status: res.status, next }
  return { ok: false, status: res.status, error: 'login-failed' }
}

export async function registerAccount(email: string, password: string, next = '/me'): Promise<{ ok: boolean; status: number; next?: string; error?: string }> {
  const root = apiRoot().replace(/\/$/, '')
  try {
    const jr = await fetch(root + '/api/auth/register', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
      body: JSON.stringify({ email: email.trim().toLowerCase(), password }),
    })
    const data = await jr.json().catch(() => ({} as any))
    if (jr.ok && data && data.ok) return { ok: true, status: jr.status, next: next.startsWith('/') ? next : '/me' }
    if (data?.code === 'taken' || data?.code === 'short' || data?.code === 'email') {
      return { ok: false, status: jr.status, error: data.code }
    }
  } catch (_) { /* fall through */ }
  const body = new URLSearchParams({
    email: email.trim().toLowerCase(),
    password,
    next: next.startsWith('/') ? next : '/me',
  })
  const res = await fetch(root + '/register', {
    method: 'POST',
    credentials: 'include',
    redirect: 'manual',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded', Accept: 'text/html,*/*' },
    body,
  })
  if (res.status === 400) return { ok: false, status: 400, error: 'invalid' }
  if (res.status >= 300 && res.status < 400) {
    return { ok: true, status: res.status, next: res.headers.get('Location') || next }
  }
  if (res.ok) return { ok: true, status: res.status, next }
  return { ok: false, status: res.status, error: 'register-failed' }
}

/** In-app checkout POST → order page or PayPal URL. */
export async function submitCheckoutForm(fields: Record<string, string>): Promise<{
  ok: boolean
  orderId?: string
  payUrl?: string
  status: number
  error?: string
  html?: string
}> {
  const root = apiRoot().replace(/\/$/, '')
  const body = new URLSearchParams()
  for (const [k, v] of Object.entries(fields)) body.set(k, v ?? '')
  const res = await fetch(root + '/checkout', {
    method: 'POST',
    credentials: 'include',
    redirect: 'manual',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded', Accept: 'text/html,*/*' },
    body,
  })
  const loc = res.headers.get('Location') || ''
  if (res.status >= 300 && res.status < 400 && loc) {
    const orderM = loc.match(/\/orders\/([^/?#]+)/i)
    if (orderM) return { ok: true, status: res.status, orderId: decodeURIComponent(orderM[1]), payUrl: loc.startsWith('http') ? loc : undefined }
    if (/^https?:\/\//i.test(loc)) return { ok: true, status: res.status, payUrl: loc }
    // relative non-order redirect
    return { ok: true, status: res.status, payUrl: root + (loc.startsWith('/') ? loc : '/' + loc) }
  }
  const html = await res.text()
  // validation errors re-render checkout
  return { ok: false, status: res.status, error: 'checkout-error', html }
}


export interface CouponRow {
  name: string
  meta: string
  owned: boolean
}

export interface BalanceInfo {
  ok: boolean
  live: boolean
  signedIn: boolean
  balanceText: string
  note: string
  message?: string
}

export function parseCouponsHtml(html: string): { signedIn: boolean; loginRequired: boolean; coupons: CouponRow[] } {
  if (!html) return { signedIn: false, loginRequired: true, coupons: [] }
  if (/name=["']password["']/i.test(html) && !/class=["']art["']/i.test(html)) {
    return { signedIn: false, loginRequired: true, coupons: [] }
  }
  const coupons: CouponRow[] = []
  const re = /<article\s+class="art">([\s\S]*?)<\/article>/gi
  let m: RegExpExecArray | null
  while ((m = re.exec(html))) {
    const block = m[1]
    const name = stripHtml(block.match(/class="nm"[^>]*>([\s\S]*?)<\/div>/i)?.[1] || '')
    const meta = stripHtml(block.match(/class="meta"[^>]*>([\s\S]*?)<\/div>/i)?.[1] || '')
    const owned = /class="st\s+ok"/i.test(block)
    if (!name) continue
    coupons.push({ name, meta, owned })
  }
  return {
    signedIn: coupons.length > 0 || /class=["']acchead["']/i.test(html),
    loginRequired: coupons.length === 0 && /\/login/i.test(html),
    coupons,
  }
}

export function parseBalanceHtml(html: string): BalanceInfo {
  if (!html) return { ok: false, live: false, signedIn: false, balanceText: '—', note: '', message: 'empty' }
  if (/name=["']password["']/i.test(html) && !/class=["']amt["']/i.test(html)) {
    return {
      ok: true,
      live: true,
      signedIn: false,
      balanceText: '—',
      note: '登录后查看返利余额',
      message: 'login-required',
    }
  }
  const amt = stripHtml(html.match(/class=["']amt["'][^>]*>([\s\S]*?)<\/div>/i)?.[1] || '')
  const note = stripHtml(html.match(/class=["']note["'][^>]*>([\s\S]*?)<\/div>/i)?.[1] || '')
  return {
    ok: true,
    live: true,
    signedIn: Boolean(amt) || /class=["']acchead["']/i.test(html),
    balanceText: amt || '—',
    note: note || '返利钱包 · 可在提现页申请打款',
  }
}

export async function fetchCoupons() {
  try {
    const html = await fetchHtmlPath('/account/coupons')
    const parsed = parseCouponsHtml(html)
    return { ok: true, live: true, loginRequired: parsed.loginRequired, coupons: parsed.coupons }
  } catch (e) {
    return {
      ok: false,
      live: false,
      loginRequired: false,
      coupons: [] as CouponRow[],
      message: e instanceof Error ? e.message : 'network',
    }
  }
}

export async function fetchBalancePanel(): Promise<BalanceInfo> {
  try {
    return parseBalanceHtml(await fetchHtmlPath('/account/balance'))
  } catch (e) {
    return {
      ok: false,
      live: false,
      signedIn: false,
      balanceText: '—',
      note: '',
      message: e instanceof Error ? e.message : 'network',
    }
  }
}

export async function fetchShareHtml(): Promise<string> {
  return fetchHtmlPath('/share')
}

export async function fetchCheckInHtml(): Promise<string> {
  return fetchHtmlPath('/check-in')
}

export async function postCheckIn(): Promise<{ ok: boolean; message?: string }> {
  try {
    const res = await harborRequest<string>('/check-in', { method: 'POST', form: true, data: {} })
    return { ok: res.statusCode < 400, message: `http ${res.statusCode}` }
  } catch (e) {
    return { ok: false, message: e instanceof Error ? e.message : 'network' }
  }
}

export async function fetchHistoryHtml(): Promise<string> {
  return fetchHtmlPath('/account/history')
}

export async function fetchWithdrawHtml(): Promise<string> {
  return fetchHtmlPath('/account/withdraw')
}

export async function postWithdraw(payout: string, amountCents: string) {
  return harborRequest<string>('/account/withdraw', {
    method: 'POST',
    form: true,
    data: { payout, amount_cents: amountCents },
  })
}

export async function postContact(email: string, body: string, topic = '') {
  const payload: Record<string, string> = { email, body }
  if (topic) payload.topic = topic
  return harborRequest<string>('/contact', { method: 'POST', form: true, data: payload })
}

export async function postLocale(lang: string, currency: string, country = 'US') {
  return harborRequest<string>('/locale', {
    method: 'POST',
    form: true,
    data: { lang, currency, country },
  })
}

export async function fetchInvoiceHtml(id: string): Promise<string> {
  return fetchHtmlPath('/orders/' + encodeURIComponent(id) + '/invoice')
}

export function shopPath(path: string): string {
  // User-visible shop HTML links must hit the real shop origin, never /harbor-api.
  const root = shopOrigin().replace(/\/$/, '')
  const url = root + (path.startsWith('/') ? path : '/' + path)
  return withShopLang(url)
}

export async function addAddress(fields: Record<string, string>): Promise<{ ok: boolean; status: number }> {
  const root = apiRoot().replace(/\/$/, '')
  const body = new URLSearchParams()
  for (const [k, v] of Object.entries(fields)) body.set(k, v ?? '')
  const res = await fetch(root + '/account/addresses', {
    method: 'POST',
    credentials: 'include',
    redirect: 'manual',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  })
  return { ok: res.status === 401 ? false : res.status < 400 || (res.status >= 300 && res.status < 400), status: res.status }
}

export async function addPaymentMethod(brand: string, last4: string): Promise<{ ok: boolean; status: number }> {
  const root = apiRoot().replace(/\/$/, '')
  const body = new URLSearchParams({ brand, last4 })
  const res = await fetch(root + '/account/payments', {
    method: 'POST',
    credentials: 'include',
    redirect: 'manual',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  })
  return { ok: res.status === 401 ? false : res.status < 400 || (res.status >= 300 && res.status < 400), status: res.status }
}
