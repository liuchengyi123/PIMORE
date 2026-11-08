/**
 * Harbor cart client — POST /cart/add (JSON), POST /cart/update, GET /cart HTML.
 */
import { harborRequest, storefrontPath } from './http'
import { LIVE_ORIGIN, type Product } from './products'

export interface CartRailItem {
  sku: string
  productSku: string
  name: string
  qty: number
  price: number
  priceText: string
  image?: string
  label?: string
}

export interface CartSnapshot {
  ok: boolean
  live: boolean
  lines: CartRailItem[]
  cartCount: number
  subtotal: number
  subtotalText: string
  progress: number
  shipMet: boolean
  shipLine: string
  freeShipThreshold: number
  message?: string
}

function parseMoney(raw: string): number {
  const m = String(raw || '').replace(/,/g, '').match(/-?\d+(?:\.\d+)?/)
  return m ? Number(m[0]) : 0
}

function absUrl(path: string): string {
  if (!path) return ''
  if (/^https?:\/\//i.test(path)) return path
  if (path.startsWith('//')) return 'https:' + path
  return LIVE_ORIGIN + (path.startsWith('/') ? path : '/' + path)
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

function thresholdFromGap(gapTitle: string, shipLine: string): number {
  const blob = `${gapTitle} ${shipLine}`
  const m =
    blob.match(/minimum(?:\s+order)?[^\d]*\$?\s*([0-9]+(?:\.[0-9]+)?)/i) ||
    blob.match(/below the[^\d]*\$?\s*([0-9]+(?:\.[0-9]+)?)/i) ||
    blob.match(/checkout from[^\d]*\$?\s*([0-9]+(?:\.[0-9]+)?)/i) ||
    blob.match(/最低(?:下单|訂單|结算|結算)?[^\d]*\$?\s*([0-9]+(?:\.[0-9]+)?)/) ||
    blob.match(/(?:away from free shipping|below the)[\s\S]{0,40}\$?\s*([0-9]+(?:\.[0-9]+)?)/i) ||
    blob.match(/free shipping[^\d]*\$?\s*([0-9]+(?:\.[0-9]+)?)/i)
  return m ? Number(m[1]) : 0
}

function fromAddJson(data: Record<string, unknown>): CartSnapshot {
  const railRaw = Array.isArray(data.rail) ? data.rail : []
  const lines: CartRailItem[] = railRaw.map((row: Record<string, unknown>) => {
    const sku = String(row.sku || '')
    const productSku = String(row.product_sku || sku.split('~')[0] || sku)
    const priceText = String(row.price || '')
    return {
      sku,
      productSku,
      name: decodeEntities(String(row.name || productSku)),
      qty: Number(row.qty || 1),
      price: parseMoney(priceText),
      priceText,
      image: absUrl(String(row.image || '')),
      label: '',
    }
  })
  const subtotalText = String(data.subtotal || '')
  const gapTitle = String(data.gap_title || '')
  const shipLine = String(data.ship_line || '')
  return {
    ok: Boolean(data.ok),
    live: true,
    lines,
    cartCount: Number(data.cart_count || lines.reduce((n, l) => n + l.qty, 0)),
    subtotal: parseMoney(subtotalText),
    subtotalText,
    progress: Number(data.progress || 0),
    shipMet: Boolean(data.ship_met),
    shipLine: decodeEntities(shipLine.replace(/<[^>]+>/g, '')),
    freeShipThreshold: thresholdFromGap(gapTitle, shipLine),
    message: String(data.message || ''),
  }
}

function parseCartHtml(html: string): CartSnapshot {
  const lines: CartRailItem[] = []
  const re = /class="cart-line"[^>]*>([\s\S]*?)(?=<div class="cart-line"|<script|<\/main|<\/section|$)/gi
  let m: RegExpExecArray | null
  const blocks = [...html.matchAll(/<div class="cart-line">([\s\S]*?)<\/div>\s*<\/div>/gi)]
  const chunks = blocks.length
    ? blocks.map((b) => b[1])
    : (() => {
        const out: string[] = []
        const loose = /class="cart-line"[^>]*>([\s\S]*?)(?=class="cart-line"|id="del-modal"|<\/form>\s*<script)/gi
        while ((m = loose.exec(html))) out.push(m[1])
        return out
      })()

  for (const block of chunks) {
    const skuM = block.match(/name="sku"[^>]*value="([^"]+)"/i)
    if (!skuM) continue
    const code = skuM[1]
    const productSku = code.split('~')[0]
    const imgM = block.match(/<img[^>]+src="([^"]+)"/i)
    const nameM = block.match(/<a[^>]*href="\/p\/[^"]*"[^>]*>([\s\S]*?)<\/a>/i)
    const priceM = block.match(/class="price"[^>]*>([\s\S]*?)<\/p>/i)
    const qtyM = block.match(/class="qty-num"[^>]*>([\s\S]*?)<\/span>/i)
    const nameRaw = decodeEntities((nameM?.[1] || '').replace(/<[^>]+>/g, '').trim())
    const [name, label] = nameRaw.includes(' · ') ? nameRaw.split(/\s·\s(.*)/).filter(Boolean) : [nameRaw, '']
    const priceText = decodeEntities((priceM?.[1] || '').replace(/<[^>]+>/g, '').trim())
    lines.push({
      sku: code,
      productSku,
      name: name || productSku,
      label: label || '',
      qty: Number((qtyM?.[1] || '1').replace(/[^\d]/g, '') || 1),
      price: parseMoney(priceText),
      priceText,
      image: absUrl(imgM?.[1] || ''),
    })
  }

  // Deduplicate by sku code (HTML may repeat forms)
  const seen = new Set<string>()
  const unique = lines.filter((l) => {
    if (seen.has(l.sku)) return false
    seen.add(l.sku)
    return true
  })

  const subtotal = unique.reduce((n, l) => n + l.price * l.qty, 0)
  let threshold = 0
  const away = html.match(/\$([0-9.]+)\s*<\/em>\s*(?:away from free shipping|below the)[\s\S]{0,80}\$([0-9.]+)/i)
  if (away) threshold = Number(away[2]) || threshold
  else {
    const t = html.match(/(?:unlock free shipping at|minimum order|checkout from|最低下单金额)\s*\$?([0-9.]+)/i)
    if (t) threshold = Number(t[1])
  }
  const progress = threshold > 0 ? Math.min(100, Math.round((subtotal * 100) / threshold)) : 0

  return {
    ok: true,
    live: unique.length > 0 || /cart-line/i.test(html),
    lines: unique,
    cartCount: unique.reduce((n, l) => n + l.qty, 0),
    subtotal,
    subtotalText: subtotal ? `$${subtotal.toFixed(2)}` : '$0.00',
    progress,
    shipMet: subtotal >= threshold && unique.length > 0,
    shipLine: unique.length
      ? threshold <= 0
        ? 'Free shipping on this order'
        : subtotal >= threshold
          ? 'Minimum met · free shipping'
          : `Add $${Math.max(0, threshold - subtotal).toFixed(2)} to reach minimum order`
      : '',
    freeShipThreshold: threshold,
  }
}

export async function addToCartServer(opts: {
  sku: string
  offer?: string
  qty?: number
  country?: string
}): Promise<CartSnapshot> {
  const res = await harborRequest<Record<string, unknown> | string>('/cart/add', {
    method: 'POST',
    json: true,
    form: true,
    data: {
      sku: opts.sku,
      offer: opts.offer || '',
      qty: opts.qty ?? 1,
      country: opts.country || 'US',
      ajax: '1',
    },
  })
  if (typeof res.data === 'string') {
    // unexpected HTML — try parse as failure
    throw new Error('cart/add returned HTML')
  }
  if (res.statusCode >= 400 || !res.data || (res.data as { ok?: boolean }).ok === false) {
    const err = (res.data as { error?: string })?.error || `HTTP ${res.statusCode}`
    throw new Error(err)
  }
  return fromAddJson(res.data as Record<string, unknown>)
}

export async function updateCartServer(skuCode: string, qty: number, country = 'US'): Promise<CartSnapshot> {
  await harborRequest('/cart/update', {
    method: 'POST',
    form: true,
    data: { sku: skuCode, qty, country },
  })
  return fetchCartServer()
}

export async function fetchCartServer(): Promise<CartSnapshot> {
  const res = await harborRequest<string>('/cart', { method: 'GET' })
  const html = typeof res.data === 'string' ? res.data : ''
  return parseCartHtml(html)
}

export function lineToProduct(line: CartRailItem): Product {
  return {
    id: line.productSku,
    sku: line.productSku,
    name: line.name,
    price: line.price,
    category: 'Harbor',
    image: line.image,
    images: line.image ? [line.image] : [],
    live: true,
  }
}

export function checkoutBridgeItems(lines: { productSku: string; offerId?: string; sku: string; qty: number }[]) {
  return lines.map((l) => ({
    sku: l.productSku,
    offer: l.offerId || (l.sku.includes('~') ? l.sku.split('~')[1] : ''),
    qty: l.qty,
  }))
}

export { storefrontPath }
