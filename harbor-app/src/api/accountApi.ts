/**
 * Harbor account client — GET /account (+ panels) HTML parse.
 * Session: buyer_session cookie (HttpOnly). Local H5 needs login via /harbor-api proxy.
 */
import { harborRequest, storefrontPath } from './http'
import { appStorefrontUrl, publicStorefrontUrl } from './urls'
import { LIVE_ORIGIN } from './products'

export interface AccountSummary {
  ok: boolean
  live: boolean
  signedIn: boolean
  email: string
  pending: number
  paid: number
  shipped: number
  openOrders: number
  couponCount: number
  balanceText: string
  checkedToday: boolean
  wishCount: number
  invitePath: string
  message?: string
}

const GUEST_RE = /guest|游客|ゲスト|초대|гость|invité|convidado/i

function decodeEntities(s: string): string {
  return s
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&nbsp;/g, ' ')
}

function stripTags(s: string): string {
  return decodeEntities(s.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim())
}

export function accountLinks() {
  return {
    home: appStorefrontUrl('/account'),
    orders: appStorefrontUrl('/account/orders'),
    coupons: appStorefrontUrl('/account/coupons'),
    balance: appStorefrontUrl('/account/balance'),
    wishlist: appStorefrontUrl('/account/wishlist'),
    history: appStorefrontUrl('/account/history'),
    checkIn: appStorefrontUrl('/check-in'),
    share: appStorefrontUrl('/share'),
    install: appStorefrontUrl('/install'),
    rewards: appStorefrontUrl('/rewards'),
    register: '/account/register',
    login: appStorefrontUrl('/login?next=/account'),
    register: appStorefrontUrl('/register?next=/account'),
    publicLogin: publicStorefrontUrl('/login?next=/account'),
  }
}

function emptySummary(partial: Partial<AccountSummary> = {}): AccountSummary {
  return {
    ok: false,
    live: false,
    signedIn: false,
    email: '',
    pending: 0,
    paid: 0,
    shipped: 0,
    openOrders: 0,
    couponCount: 0,
    balanceText: '—',
    checkedToday: false,
    wishCount: 0,
    invitePath: '/share',
    ...partial,
  }
}

export function parseAccountHtml(html: string): AccountSummary {
  if (!html || html.length < 40) return emptySummary({ message: 'empty' })

  // Redirected to login form
  if (/name=["']password["']/i.test(html) && /mode["']?\s*[:=]\s*["']?login|auth\.html|Sign in|Log in/i.test(html) && !/class=["']acchead["']/i.test(html)) {
    return emptySummary({ ok: true, live: true, message: 'login-required' })
  }

  const head = html.match(/class=["']acchead["'][\s\S]*?<\/div>\s*<\/div>/i)?.[0] || html.slice(0, 4000)
  const emailM = head.match(/<b>([^<]+)<\/b>/i)
  let email = emailM ? stripTags(emailM[1]) : ''
  if (GUEST_RE.test(email) || email === 'H') email = ''
  // Login CTA present ⇒ guest
  const hasLoginCta = /href=["'][^"']*\/login/i.test(head)
  const signedIn = Boolean(email && email.includes('@') && !hasLoginCta)

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

  const balM =
    html.match(/class=["']amt["'][^>]*>([\s\S]*?)<\/div>/i) ||
    html.match(/class=["']asset-row["'][\s\S]*?href=["'][^"']*\/account\/balance[^"']*["'][\s\S]*?<b>([\s\S]*?)<\/b>/i)
  const balanceText = balM ? stripTags(balM[1]) : '—'

  const ownedCoupons = (html.match(/class=["']st\s+ok["']/gi) || []).length
  const couponArts = (html.match(/class=["']art["']/gi) || []).length
  const couponCount = ownedCoupons || couponArts

  const checkedToday = /act_checked|checked|✓|✔/i.test(
    html.match(/href=["'][^"']*\/check-in[^"']*["'][\s\S]{0,200}/i)?.[0] || '',
  )

  const wishM = html.match(/\/account\/wishlist[^"']*["'][\s\S]*?<b>(\d+)<\/b>/i)
  const wishCount = wishM ? Number(wishM[1]) : 0

  return {
    ok: true,
    live: true,
    signedIn: signedIn || (Boolean(email) && email.includes('@')),
    email: email.includes('@') ? email : email,
    pending,
    paid,
    shipped,
    openOrders: pending + paid + shipped,
    couponCount,
    balanceText: balanceText || '—',
    checkedToday,
    wishCount,
    invitePath: '/share',
  }
}

export async function fetchAccountSummary(): Promise<AccountSummary> {
  try {
    const res = await harborRequest<string>('/account', { method: 'GET' })
    const raw = typeof res.data === 'string' ? res.data : String(res.data || '')
    // Some runtimes follow redirects into login HTML
    const parsed = parseAccountHtml(raw)
    if (res.statusCode >= 400) {
      return emptySummary({ live: false, message: `http ${res.statusCode}` })
    }
    return parsed
  } catch (e) {
    return emptySummary({ message: e instanceof Error ? e.message : 'network' })
  }
}

export function openHarborWeb(pathOrUrl: string, title = 'Harbor') {
  const url = /^https?:\/\//i.test(pathOrUrl) || pathOrUrl.startsWith('/harbor-api')
    ? pathOrUrl
    : appStorefrontUrl(pathOrUrl)
  const q = `url=${encodeURIComponent(url)}&title=${encodeURIComponent(title)}`
  uni.navigateTo({ url: `/pages/webview/index?${q}` })
}

export { LIVE_ORIGIN, storefrontPath }


export interface OrderRow {
  id: string
  status: string
  statusLabel: string
  due: string
  image?: string
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

function strip(s: string): string {
  return decodeEntities(s.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim())
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
    const status = /ship/i.test(st) ? 'shipped' : /paid/i.test(st) ? 'paid' : /await|pend/i.test(st) ? 'pending' : st.toLowerCase() || 'unknown'
    orders.push({
      id,
      status,
      statusLabel: st || status,
      due: meta || nm,
      image: img ? (img.startsWith('http') ? img : LIVE_ORIGIN + img) : undefined,
    })
  }
  const signedIn = orders.length > 0 || /class=["']acchead["']/i.test(html)
  return { signedIn, loginRequired: !signedIn && /\/login/i.test(html), orders }
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
    const name = strip(block.match(/class="nm"[^>]*>([\s\S]*?)<\/div>/i)?.[1] || '')
    const meta = strip(block.match(/class="meta"[^>]*>([\s\S]*?)<\/div>/i)?.[1] || '')
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
    return { ok: true, live: true, signedIn: false, balanceText: '—', note: 'Sign in to see rebate balance', message: 'login-required' }
  }
  const amt = strip(html.match(/class=["']amt["'][^>]*>([\s\S]*?)<\/div>/i)?.[1] || '')
  const note = strip(html.match(/class=["']note["'][^>]*>([\s\S]*?)<\/div>/i)?.[1] || '')
  return {
    ok: true,
    live: true,
    signedIn: Boolean(amt) || /class=["']acchead["']/i.test(html),
    balanceText: amt || '—',
    note: note || 'Rebate wallet · withdraw on Harbor',
  }
}

export async function fetchOrders(): Promise<{ ok: boolean; live: boolean; loginRequired: boolean; orders: OrderRow[]; message?: string }> {
  try {
    const res = await harborRequest<string>('/account/orders', { method: 'GET' })
    const raw = typeof res.data === 'string' ? res.data : String(res.data || '')
    const parsed = parseOrdersHtml(raw)
    return { ok: true, live: true, loginRequired: parsed.loginRequired, orders: parsed.orders }
  } catch (e) {
    return { ok: false, live: false, loginRequired: false, orders: [], message: e instanceof Error ? e.message : 'network' }
  }
}

export async function fetchCoupons(): Promise<{ ok: boolean; live: boolean; loginRequired: boolean; coupons: CouponRow[]; message?: string }> {
  try {
    const res = await harborRequest<string>('/account/coupons', { method: 'GET' })
    const raw = typeof res.data === 'string' ? res.data : String(res.data || '')
    const parsed = parseCouponsHtml(raw)
    return { ok: true, live: true, loginRequired: parsed.loginRequired, coupons: parsed.coupons }
  } catch (e) {
    return { ok: false, live: false, loginRequired: false, coupons: [], message: e instanceof Error ? e.message : 'network' }
  }
}

export async function fetchBalancePanel(): Promise<BalanceInfo> {
  try {
    const res = await harborRequest<string>('/account/balance', { method: 'GET' })
    const raw = typeof res.data === 'string' ? res.data : String(res.data || '')
    return parseBalanceHtml(raw)
  } catch (e) {
    return { ok: false, live: false, signedIn: false, balanceText: '—', note: '', message: e instanceof Error ? e.message : 'network' }
  }
}

export async function fetchWishlistHtml(): Promise<string> {
  const res = await harborRequest<string>('/account/wishlist', { method: 'GET' })
  return typeof res.data === 'string' ? res.data : String(res.data || '')
}

export async function fetchShareHtml(): Promise<string> {
  const res = await harborRequest<string>('/share', { method: 'GET' })
  return typeof res.data === 'string' ? res.data : String(res.data || '')
}

export async function fetchCheckInHtml(): Promise<string> {
  const res = await harborRequest<string>('/check-in', { method: 'GET' })
  return typeof res.data === 'string' ? res.data : String(res.data || '')
}

export async function postCheckIn(): Promise<{ ok: boolean; message?: string }> {
  try {
    const res = await harborRequest<string>('/check-in', { method: 'POST', data: {} })
    return { ok: res.statusCode < 400, message: `http ${res.statusCode}` }
  } catch (e) {
    return { ok: false, message: e instanceof Error ? e.message : 'network' }
  }
}


export interface AddressRow {
  name: string
  line: string
}

export interface PayMethodRow {
  brand: string
  last4: string
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

export async function fetchHistoryHtml(): Promise<string> {
  return fetchHtmlPath('/account/history')
}

export async function fetchWithdrawHtml(): Promise<string> {
  return fetchHtmlPath('/account/withdraw')
}

export async function postWithdraw(payout: string, amountCents: string) {
  return harborRequest<string>('/account/withdraw', {
    method: 'POST',
    data: { payout, amount_cents: amountCents },
  })
}

export async function postContact(email: string, body: string, topic = '') {
  const payload: Record<string, string> = { email, body }
  if (topic) payload.topic = topic
  return harborRequest<string>('/contact', { method: 'POST', data: payload })
}

export async function postLocale(lang: string, currency: string, country = 'US') {
  return harborRequest<string>('/locale', {
    method: 'POST',
    data: { lang, currency, country },
  })
}

export function parseOrderDetail(html: string, id: string): OrderDetail {
  if (!html || html.length < 40) {
    return { ok: false, live: false, id, status: '', due: '', arrives: '', tracking: '', carrier: '', summary: [], canPay: false, canCancel: false }
  }
  const status = stripHtml(html.match(/<ol class="steps[\s\S]*?<\/ol>[\s\S]*?<p class="price"[^>]*>[\s\S]*?<\/p>\s*<p>([\s\S]*?)<\/p>/i)?.[1] || '')
  const due = stripHtml(html.match(/class="price"[^>]*>([\s\S]*?)<\/p>/i)?.[1] || '')
  const arrivesM = html.match(/arrives[\s\S]{0,40}?(\d+)\s*[–-]\s*(\d+)/i) || html.match(/>(\d+)\s*[–-]\s*(\d+)\s*days/i)
  const arrives = arrivesM ? `${arrivesM[1]}–${arrivesM[2]} days` : ''
  const tracking = stripHtml(html.match(/tracking[^<]*<a[^>]*>([\s\S]*?)<\/a>/i)?.[1] || '')
  const carrier = stripHtml(html.match(/carrier[^<]*<\/[^>]+>\s*([^<]+)/i)?.[1] || '')
  const summary: string[] = []
  const sumBlock = html.match(/class="summary"[^>]*>([\s\S]*?)<\/section>/i)?.[1] || ''
  for (const pm of sumBlock.matchAll(/<p>([\s\S]*?)<\/p>/gi)) {
    const t = stripHtml(pm[1])
    if (t) summary.push(t)
  }
  const canPay = /action="\/orders\/[^"]+\/pay"/i.test(html)
  const canCancel = /action="\/orders\/[^"]+\/cancel"/i.test(html)
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
    canPay,
    canCancel,
  }
}

export async function fetchOrderDetail(id: string): Promise<OrderDetail> {
  try {
    const html = await fetchHtmlPath('/orders/' + encodeURIComponent(id))
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

export async function fetchInvoiceHtml(id: string): Promise<string> {
  return fetchHtmlPath('/orders/' + encodeURIComponent(id) + '/invoice')
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

export function parseCompareColumns(html: string): { headers: string[]; rows: { label: string; cells: string[] }[] } {
  const headers: string[] = []
  const head = html.match(/<tr>\s*<th><\/th>([\s\S]*?)<\/tr>/i)?.[1] || ''
  for (const m of head.matchAll(/<th>[\s\S]*?<a[^>]*>([\s\S]*?)<\/a>/gi)) {
    headers.push(stripHtml(m[1]))
  }
  const rows: { label: string; cells: string[] }[] = []
  for (const rm of html.matchAll(/<tr>\s*<th>([^<]+)<\/th>([\s\S]*?)<\/tr>/gi)) {
    const label = stripHtml(rm[1])
    if (!label) continue
    const cells = [...rm[2].matchAll(/<td[^>]*>([\s\S]*?)<\/td>/gi)].map((c) => stripHtml(c[1]))
    if (cells.length) rows.push({ label, cells })
  }
  return { headers, rows }
}
