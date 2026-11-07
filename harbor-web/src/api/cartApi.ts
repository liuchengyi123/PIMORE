import { harborRequest } from './http'
import { apiRoot, LIVE_ORIGIN } from './config'

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
  const root = apiRoot()
  const p = path.startsWith('/') ? path : '/' + path
  if (root.startsWith('/')) return root + p
  return LIVE_ORIGIN + p
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

function fromAddJson(data: Record<string, unknown>): CartSnapshot {
  const railRaw = Array.isArray(data.rail) ? (data.rail as Record<string, unknown>[]) : []
  const lines: CartRailItem[] = railRaw.map((row) => {
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
  return {
    ok: Boolean(data.ok),
    live: true,
    lines,
    cartCount: Number(data.cart_count || lines.reduce((n, l) => n + l.qty, 0)),
    subtotal: parseMoney(subtotalText),
    subtotalText,
    progress: Number(data.progress || 0),
    shipMet: Boolean(data.ship_met),
    shipLine: decodeEntities(String(data.ship_line || '').replace(/<[^>]+>/g, '')),
    freeShipThreshold: 19,
    message: String(data.message || ''),
  }
}

export async function addToCartServer(opts: {
  sku: string
  offer?: string
  qty?: number
  country?: string
}): Promise<CartSnapshot> {
  const res = await harborRequest<Record<string, unknown>>('/cart/add', {
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
  if (res.statusCode >= 400 || !res.data || (res.data as { ok?: boolean }).ok === false) {
    const err = (res.data as { error?: string })?.error || `HTTP ${res.statusCode}`
    throw new Error(err)
  }
  return fromAddJson(res.data as Record<string, unknown>)
}

export async function syncLocalLinesToServer(
  lines: { sku: string; offer?: string; qty: number }[],
): Promise<void> {
  for (const line of lines) {
    await addToCartServer({
      sku: line.sku,
      offer: line.offer || '',
      qty: line.qty || 1,
    })
  }
}


export async function fetchCartServer(): Promise<CartSnapshot> {
  const res = await harborRequest<string>('/cart', { method: 'GET' })
  const html = typeof res.data === 'string' ? res.data : ''
  const lines: CartRailItem[] = []
  const blocks = [...html.matchAll(/<div class="cart-line">([\s\S]*?)<\/div>\s*<\/div>/gi)]
  const chunks = blocks.length
    ? blocks.map((b) => b[1])
    : (() => {
        const out: string[] = []
        const loose = /class="cart-line"[^>]*>([\s\S]*?)(?=class="cart-line"|id="del-modal"|<\/form>\s*<script)/gi
        let m: RegExpExecArray | null
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
    const [name, label] = nameRaw.includes(' · ')
      ? nameRaw.split(/\s·\s(.*)/).filter(Boolean)
      : [nameRaw, '']
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
  const seen = new Set<string>()
  const unique = lines.filter((l) => {
    if (seen.has(l.sku)) return false
    seen.add(l.sku)
    return true
  })
  const subtotal = unique.reduce((n, l) => n + l.price * l.qty, 0)
  return {
    ok: true,
    live: unique.length > 0 || /cart-line/i.test(html),
    lines: unique,
    cartCount: unique.reduce((n, l) => n + l.qty, 0),
    subtotal,
    subtotalText: subtotal ? `$${subtotal.toFixed(2)}` : '$0.00',
    progress: 0,
    shipMet: false,
    shipLine: '',
    freeShipThreshold: 19,
  }
}

export async function updateCartServer(skuCode: string, qty: number, country = 'US'): Promise<CartSnapshot> {
  await harborRequest('/cart/update', {
    method: 'POST',
    form: true,
    data: { sku: skuCode, qty, country },
  })
  return fetchCartServer()
}
