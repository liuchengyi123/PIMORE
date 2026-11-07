import { harborRequest } from './http'
import { apiRoot, LIVE_ORIGIN, shopOrigin } from './config'
import { withShopLang } from './catalogLang'

export interface OrderRow {
  id: string
  status: string
  statusLabel: string
  due: string
  image?: string
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

export function parseOrdersHtml(html: string): { signedIn: boolean; loginRequired: boolean; orders: OrderRow[] } {
  if (!html) return { signedIn: false, loginRequired: true, orders: [] }
  if (/name=["']password["']/i.test(html) && !/class=["']art["']/i.test(html) && /\/login/i.test(html)) {
    return { signedIn: false, loginRequired: true, orders: [] }
  }
  const orders: OrderRow[] = []
  const re = /<a\s+class="art"\s+href="\/orders\/([^"?]+)[^"]*"[^>]*>([\s\S]*?)<\/a>/gi
  let m: RegExpExecArray | null
  while ((m = re.exec(html))) {
    const id = m[1]
    const block = m[2]
    const img = block.match(/<img[^>]+src="([^"]+)"/i)?.[1]
    const nm = strip(block.match(/class="nm"[^>]*>([\s\S]*?)<\/div>/i)?.[1] || '')
    const meta = strip(block.match(/class="meta"[^>]*>([\s\S]*?)<\/div>/i)?.[1] || '')
    const st = strip(block.match(/class="st[^"]*"[^>]*>([\s\S]*?)<\/span>/i)?.[1] || '')
    const status = /ship/i.test(st)
      ? 'shipped'
      : /paid/i.test(st)
        ? 'paid'
        : /await|pend/i.test(st)
          ? 'pending'
          : st.toLowerCase() || 'unknown'
    orders.push({
      id,
      status,
      statusLabel: st || status,
      due: meta || nm,
      image: img ? absUrl(img) : undefined,
    })
  }
  const signedIn = orders.length > 0 || /class=["']acchead["']/i.test(html)
  return { signedIn, loginRequired: !signedIn && /\/login/i.test(html), orders }
}

export async function fetchOrders() {
  try {
    const res = await harborRequest<string>('/account/orders', { method: 'GET' })
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

export function parseOrderDetail(html: string, id: string): OrderDetail {
  if (!html || html.length < 40) {
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
    }
  }
  const status = strip(
    html.match(/<ol class="steps[\s\S]*?<\/ol>[\s\S]*?<p class="price"[^>]*>[\s\S]*?<\/p>\s*<p>([\s\S]*?)<\/p>/i)?.[1] ||
      '',
  )
  const due = strip(html.match(/class="price"[^>]*>([\s\S]*?)<\/p>/i)?.[1] || '')
  const tracking = strip(html.match(/tracking[^<]*<a[^>]*>([\s\S]*?)<\/a>/i)?.[1] || '')
  const carrier = strip(html.match(/carrier[^<]*<\/[^>]+>\s*([^<]+)/i)?.[1] || '')
  const summary: string[] = []
  const sumBlock = html.match(/class="summary"[^>]*>([\s\S]*?)<\/section>/i)?.[1] || ''
  for (const pm of sumBlock.matchAll(/<p>([\s\S]*?)<\/p>/gi)) {
    const t = strip(pm[1])
    if (t) summary.push(t)
  }
  return {
    ok: true,
    live: true,
    id,
    status: status || 'unknown',
    due,
    arrives: '',
    tracking,
    carrier,
    summary,
    canPay: /action="\/orders\/[^"]+\/pay"/i.test(html),
    canCancel: /action="\/orders\/[^"]+\/cancel"/i.test(html),
  }
}

export async function fetchOrderDetail(id: string): Promise<OrderDetail> {
  try {
    const res = await harborRequest<string>('/orders/' + encodeURIComponent(id), { method: 'GET' })
    const html = typeof res.data === 'string' ? res.data : String(res.data || '')
    return parseOrderDetail(html, id)
  } catch (e) {
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
      rawHint: e instanceof Error ? e.message : 'network',
    }
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
