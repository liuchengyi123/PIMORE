export const LIVE_ORIGIN =
  (import.meta as ImportMeta & { env?: Record<string, string> }).env?.VITE_HARBOR_ORIGIN ||
  'https://linkiip.com'

/**
 * Browser-facing shop HTML origin.
 * Never return /harbor-api — that proxy is for XHR/fetch only and has no CSS when opened as a page.
 */
export function shopOrigin(): string {
  const env = (import.meta as ImportMeta & { env?: Record<string, string> }).env || {}
  const fromEnv = String(env.VITE_SHOP_ORIGIN || '').trim().replace(/\/$/, '')
  if (fromEnv) return fromEnv
  try {
    if (typeof location !== 'undefined') {
      const host = location.hostname || ''
      if (host === 'localhost' || host === '127.0.0.1') {
        return 'http://127.0.0.1:8787'
      }
    }
  } catch {
    /* ignore */
  }
  return String(LIVE_ORIGIN || '').replace(/\/$/, '')
}

/** Local Vite H5 uses /harbor-api proxy → 8787 (API / XHR only) */
export function apiRoot(): string {
  try {
    if (typeof location !== 'undefined') {
      const host = location.hostname || ''
      const proto = location.protocol || ''
      if ((host === 'localhost' || host === '127.0.0.1') && (proto === 'http:' || proto === 'https:')) {
        return '/harbor-api'
      }
    }
  } catch {
    /* ignore */
  }
  return LIVE_ORIGIN
}
