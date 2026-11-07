/**
 * Harbor storefront URL helpers + payment/account return classification.
 * Success: /orders/{id} after PayPal/LianLian/Stripe return.
 * Cancel / abandon: /cart or explicit cancel.
 */
import { LIVE_ORIGIN, apiRoot } from './products'

export type HarborNavKind =
  | 'order-success'
  | 'order-pending'
  | 'payment'
  | 'cart'
  | 'login'
  | 'account'
  | 'checkout'
  | 'other'

const ORDER_RE = /\/orders\/([^/?#]+)(?:\/(paypal|lianlian))?/i

/** Same-origin proxy path on local H5 so cookies (buyer_session, cart) stick. */
export function appStorefrontUrl(path: string): string {
  const p = path.startsWith('/') ? path : '/' + path
  const root = apiRoot()
  if (root.startsWith('/')) return root + p
  return LIVE_ORIGIN + p
}

/** Always absolute public origin (system browser / external). */
export function publicStorefrontUrl(path: string): string {
  const p = path.startsWith('/') ? path : '/' + path
  return LIVE_ORIGIN + p
}

export function classifyHarborUrl(raw: string): { kind: HarborNavKind; orderId?: string } {
  if (!raw) return { kind: 'other' }
  let path = raw
  try {
    if (/^https?:\/\//i.test(raw)) {
      const u = new URL(raw)
      path = u.pathname + u.search
    }
  } catch {
    /* keep path */
  }
  // Strip proxy prefix if present
  path = path.replace(/^\/harbor-api/, '')

  const om = path.match(ORDER_RE)
  if (om) {
    const orderId = om[1]
    const gate = (om[2] || '').toLowerCase()
    // Pay/LianLian return gates always land (or redirect) as paid handoff
    if (gate === 'paypal' || gate === 'lianlian') {
      return { kind: 'order-success', orderId }
    }
    // Stripe confirm uses ?session_id=
    if (/[?&]session_id=/i.test(path)) {
      return { kind: 'order-success', orderId }
    }
    // Bare order page: treat as success handoff (pending still showable in-app)
    return { kind: 'order-pending', orderId }
  }
  if (/\/payment(?:\/|\?|$)/i.test(path)) return { kind: 'payment' }
  if (/\/cart(?:\/|\?|$)/i.test(path)) return { kind: 'cart' }
  if (/\/login(?:\/|\?|$)/i.test(path)) return { kind: 'login' }
  if (/\/checkout(?:\/|\?|$)/i.test(path)) return { kind: 'checkout' }
  if (/\/account(?:\/|\?|$)/i.test(path)) return { kind: 'account' }
  return { kind: 'other' }
}

/** Native later: map these hosts/paths into the app. */
export const UNIVERSAL_LINK_NOTES = [
  'https://linkiip.com/orders/*  →  pages/order-success?id=',
  'https://linkiip.com/account/* →  pages/me or webview',
  'https://linkiip.com/cart      →  pages/cart',
  'https://linkiip.com/login     →  webview login',
]
