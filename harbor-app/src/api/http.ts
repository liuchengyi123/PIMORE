/**
 * Cookie-aware Harbor HTTP helper.
 * H5 localhost: same-origin `/harbor-api` so the browser stores Set-Cookie.
 * Native / non-local: hit LIVE_ORIGIN and mirror Set-Cookie into a small jar
 * (uni.request does not always persist cross-domain cookies the way a browser does).
 */
import { LIVE_ORIGIN, apiRoot } from './products'
import { withCatalogLang, catalogLangHeaders } from './catalogLang'

const JAR_KEY = 'harbor_cookie_jar'

type Jar = Record<string, string>

function readJar(): Jar {
  try {
    const raw = uni.getStorageSync(JAR_KEY)
    if (!raw) return {}
    return typeof raw === 'string' ? (JSON.parse(raw) as Jar) : (raw as Jar)
  } catch {
    return {}
  }
}

function writeJar(jar: Jar) {
  try {
    uni.setStorageSync(JAR_KEY, jar)
  } catch {
    /* ignore */
  }
}

function parseSetCookie(raw: string | string[] | undefined): void {
  if (!raw) return
  const parts = Array.isArray(raw) ? raw : String(raw).split(/,(?=[^;]+?=)/)
  const jar = readJar()
  for (const part of parts) {
    const nv = String(part).split(';')[0]
    const i = nv.indexOf('=')
    if (i <= 0) continue
    const name = nv.slice(0, i).trim()
    const value = nv.slice(i + 1).trim()
    if (!name) continue
    if (/^(Max-Age|Expires|Path|Domain|SameSite|Secure|HttpOnly)$/i.test(name)) continue
    jar[name] = value
  }
  writeJar(jar)
}

function cookieHeader(): string {
  const jar = readJar()
  return Object.entries(jar)
    .map(([k, v]) => `${k}=${v}`)
    .join('; ')
}

export function clearHarborCookies() {
  try {
    uni.removeStorageSync(JAR_KEY)
  } catch {
    /* ignore */
  }
}

export function storefrontPath(path: string): string {
  if (!path) return LIVE_ORIGIN
  if (/^https?:\/\//i.test(path)) return path
  return LIVE_ORIGIN + (path.startsWith('/') ? path : '/' + path)
}

/** Checkout URL. Local H5 stays on the proxied shop so the spin cookie applies. */
export function checkoutHandoffUrl(buy = false, luckyToken = ''): string {
  const path = buy ? '/checkout?buy=1' : '/checkout'
  const root = apiRoot()
  let url = root.startsWith('/') && typeof location !== 'undefined'
    ? location.origin + root + path
    : storefrontPath(path)
  if (luckyToken) url += (url.includes('?') ? '&' : '?') + 'lucky_spin=' + encodeURIComponent(luckyToken)
  return url
}

export interface HarborRequestOptions {
  method?: 'GET' | 'POST'
  data?: Record<string, any>
  headers?: Record<string, string>
  /** Prefer JSON Accept for cart/add ajax */
  json?: boolean
  /** application/x-www-form-urlencoded body */
  form?: boolean
}

export interface HarborResponse<T = unknown> {
  statusCode: number
  data: T
  header: Record<string, string>
  raw: any
}

function encodeForm(data: Record<string, string | number | boolean | undefined | null>): string {
  return Object.entries(data)
    .filter(([, v]) => v !== undefined && v !== null)
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
    .join('&')
}

function isLocalH5Proxy(): boolean {
  return apiRoot().startsWith('/')
}

export function harborRequest<T = unknown>(path: string, opts: HarborRequestOptions = {}): Promise<HarborResponse<T>> {
  const method = opts.method || 'GET'
  const root = apiRoot()
  const url = withCatalogLang(root + (path.startsWith('/') ? path : '/' + path))

  const headers: Record<string, string> = {
    ...catalogLangHeaders(),
    ...(opts.headers || {}),
  }
  if (opts.json) {
    headers.Accept = headers.Accept || 'application/json'
    headers['X-Harbor-Ajax'] = '1'
  } else {
    headers.Accept = headers.Accept || 'text/html,*/*'
  }

  // Mirror jar on native / direct origin; browser handles localhost proxy cookies.
  if (!isLocalH5Proxy()) {
    const cookie = cookieHeader()
    if (cookie) headers.Cookie = cookie
  }

  let body: string | Record<string, unknown> | undefined
  if (method === 'POST') {
    const data = opts.data || {}
    if (opts.form !== false) {
      headers['Content-Type'] = 'application/x-www-form-urlencoded'
      body = encodeForm(data)
    } else if ((headers['Content-Type'] || '').includes('application/json')) {
      body = JSON.stringify(data)
    } else {
      body = data as Record<string, unknown>
    }
  }

  return new Promise((resolve, reject) => {
    uni.request({
      url,
      method,
      data: body,
      header: headers,
      timeout: 20000,
      // H5: include cookies for same-origin proxy
      withCredentials: true,
      success: (res) => {
        const header = (res.header || {}) as Record<string, string>
        // Collect Set-Cookie under various casings / platforms
        const setCookie =
          header['Set-Cookie'] ||
          header['set-cookie'] ||
          (header as Record<string, string>)['Set-Cookie'] ||
          Object.entries(header).find(([k]) => k.toLowerCase() === 'set-cookie')?.[1]
        parseSetCookie(setCookie)
        resolve({
          statusCode: res.statusCode || 0,
          data: res.data as T,
          header,
          raw: res,
        })
      },
      fail: (err) => reject(err instanceof Error ? err : new Error(String(err))),
    })
  })
}
