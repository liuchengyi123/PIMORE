/**
 * Harbor catalog client - live feed from linkiip.com (HTML cards + JSON-LD PDP).
 * No secrets. Cart uses /cart/add JSON + cookie jar; checkout hands off to linkiip.com.
 */
import { withCatalogLang, catalogLangHeaders } from './catalogLang'

export const LIVE_ORIGIN = (import.meta as ImportMeta & { env?: Record<string, string> }).env?.VITE_HARBOR_ORIGIN
  || 'https://linkiip.com'

/** H5 browser on localhost uses Vite proxy `/harbor-api`. Capacitor / native / prod hit LIVE_ORIGIN. */
export function apiRoot(): string {
  try {
    const w = typeof window !== 'undefined' ? (window as unknown as { Capacitor?: unknown; plus?: unknown }) : undefined
    if (w?.Capacitor || w?.plus) return LIVE_ORIGIN
    if (typeof location !== 'undefined') {
      const proto = location.protocol || ''
      if (proto === 'capacitor:' || proto === 'ionic:' || proto === 'file:') return LIVE_ORIGIN
      const host = location.hostname || ''
      // Capacitor Android WebView is https://localhost — must NOT use Vite proxy
      if ((host === 'localhost' || host === '127.0.0.1') && (proto === 'http:' || proto === 'https:')) {
        // Only browser H5 via Vite uses the proxy; Capacitor sets window.Capacitor above
        if (!w?.Capacitor) return '/harbor-api'
      }
    }
  } catch {
    /* ignore */
  }
  return LIVE_ORIGIN
}

export const API_BASE = LIVE_ORIGIN

export type ProductTag = 'New' | 'Ship-fast' | 'Deal' | 'Staff' | 'Flash'

export interface ProductOffer {
  id: string
  label: string
  price?: number
  compareAt?: number
  image?: string
}

export interface Product {
  id: string
  sku: string
  name: string
  price: number
  compareAt?: number
  /** Discount percent from shop off-badge or computed from compareAt */
  offPct?: number
  tag?: ProductTag
  category: string
  image?: string
  images?: string[]
  sizes?: string[]
  offers?: ProductOffer[]
  material?: string
  care?: string
  hub?: string
  blurb?: string
  shipsIn?: string
  live?: boolean
  /** Stock count from shop; <=0 means sold out */
  stock?: number
  /** Low-stock hint from shop only-left */
  onlyLeft?: number
  /** ISO end time for flash/deal countdown when known */
  flashEnds?: string
}

export interface CategoryChip {
  id: string
  name: string
  tip?: string
}

const MOCK: Product[] = [
  {
    id: '1',
    sku: 'SPATULA-5',
    name: 'Silicone spatula set',
    price: 8.9,
    compareAt: 12.5,
    tag: 'New',
    category: 'Kitchen',
    sizes: ['3pcs', '5pcs', 'Pro kit'],
    material: 'Silicone',
    care: 'Dishwasher',
    hub: 'US / EU',
    blurb: 'Soft edge, stainless core. Built for everyday kitchens, not showroom photos.',
    shipsIn: 'Ships in 2鈥? days 路 tracked',
  },
  {
    id: '2',
    sku: 'BIN-3',
    name: 'Stackable bin 3-pack',
    price: 14.2,
    compareAt: 19,
    tag: 'Ship-fast',
    category: 'Store',
    sizes: ['Clear', 'Smoke', 'White'],
    material: 'PP',
    care: 'Wipe clean',
    hub: 'US / EU',
    blurb: 'Nest when empty, stack when full. Small-apartment storage without the clutter look.',
    shipsIn: 'Ships in 2鈥? days 路 tracked',
  },
  {
    id: '3',
    sku: 'CLOTH-12',
    name: 'Microfiber cloths x12',
    price: 6.4,
    compareAt: 9.9,
    tag: 'Deal',
    category: 'Clean',
    sizes: ['12 pack', '24 pack'],
    material: 'Microfiber',
    care: 'Machine wash',
    hub: 'US / EU',
    blurb: 'Lint-light cloths for glass, counters, and screens.',
    shipsIn: 'Ships in 2鈥? days 路 tracked',
  },
  {
    id: '4',
    sku: 'TRAY-DESK',
    name: 'Cable desk tray',
    price: 11,
    compareAt: 15,
    tag: 'Staff',
    category: 'Desk',
    sizes: ['S', 'M', 'L'],
    material: 'ABS',
    care: 'Wipe clean',
    hub: 'US / EU',
    blurb: 'Keeps chargers and pens in one quiet tray instead of across the desk.',
    shipsIn: 'Ships in 2鈥? days 路 tracked',
  },
]

/** Align with shop/i18n.py CATEGORIES (subset shown on Home chips). */
export const CATEGORIES: CategoryChip[] = [
  { id: 'kitchen', name: 'Kitchen', tip: 'Cook' },
  { id: 'cleaning', name: 'Clean', tip: 'Home' },
  { id: 'storage', name: 'Store', tip: 'Organize' },
  { id: 'personal', name: 'Care', tip: 'Body' },
  { id: 'pet', name: 'Pet', tip: 'Pets' },
  { id: 'office', name: 'Desk', tip: 'Work' },
]

export const ALL_CATEGORIES: CategoryChip[] = [
  { id: 'daily', name: 'Home basics', tip: 'Home' },
  { id: 'kitchen', name: 'Kitchen', tip: 'Cook' },
  { id: 'tableware', name: 'Tableware', tip: 'Table' },
  { id: 'storage', name: 'Storage', tip: 'Store' },
  { id: 'cleaning', name: 'Cleaning', tip: 'Clean' },
  { id: 'paper', name: 'Paper', tip: 'Paper' },
  { id: 'personal', name: 'Personal', tip: 'Care' },
  { id: 'beauty', name: 'Skin care', tip: 'Skin' },
  { id: 'makeup', name: 'Makeup', tip: 'Make' },
  { id: 'textile', name: 'Textiles', tip: 'Soft' },
  { id: 'decor', name: 'Decor', tip: 'Decor' },
  { id: 'appliance', name: 'Appliances', tip: 'App' },
  { id: 'hardware', name: 'Tools', tip: 'Tool' },
  { id: 'pet', name: 'Pet', tip: 'Pet' },
  { id: 'office', name: 'Office', tip: 'Desk' },
  { id: 'party', name: 'Party', tip: 'Party' },
]

const cache = new Map<string, Product>()

export function clearProductCache() {
  cache.clear()
}


export function money(n: number): string {
  if (!Number.isFinite(n)) return '$0.00'
  return '$' + n.toFixed(2)
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

function absUrl(path: string): string {
  if (!path) return ''
  if (/^https?:\/\//i.test(path)) return path
  if (path.startsWith('//')) return 'https:' + path
  if (!path.startsWith('/')) path = '/' + path
  return LIVE_ORIGIN + path
}

function parseMoney(raw: string): number {
  const m = String(raw || '').replace(/,/g, '').match(/-?\d+(?:\.\d+)?/)
  return m ? Number(m[0]) : 0
}

/** Match shop deal_ends_iso fallback: seckill ends_at if provided, else end of UTC day. */
export function dealEndsAt(iso?: string | null): number {
  if (iso) {
    const t = Date.parse(String(iso))
    if (Number.isFinite(t) && t > Date.now()) return t
  }
  const now = new Date()
  let end = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate(), 23, 59, 59)
  if (end <= Date.now()) end += 24 * 3600 * 1000
  return end
}

export function formatCountdown(msLeft: number): string {
  const left = Math.max(0, Math.floor(msLeft / 1000))
  const h = Math.floor(left / 3600)
  const m = Math.floor((left % 3600) / 60)
  const s = left % 60
  const z = (n: number) => (n < 10 ? '0' : '') + n
  return z(h) + ':' + z(m) + ':' + z(s)
}

function parseOffPct(raw: string, price: number, compareAt: number): number | undefined {
  const text = decodeEntities(raw || '').replace(/<[^>]+>/g, ' ')
  const m = text.match(/(\d+(?:\.\d+)?)\s*%/)
  if (m) {
    const n = Math.round(Number(m[1]))
    if (n > 0 && n < 100) return n
  }
  if (compareAt > price && price > 0) {
    return Math.round((1 - price / compareAt) * 100)
  }
  return undefined
}

function pickCardTag(block: string, offPct: number | undefined, forced?: ProductTag): ProductTag | undefined {
  if (forced === 'New' || forced === 'Flash') return forced
  if (/lp-deal-badge(?!-)|\bFLASH\b/i.test(block)) return 'Flash'
  if (/new-badge|lp-deal-badge-new|\bNEW\b/i.test(block)) return 'New'
  if (/ship-badge|free[_ -]?ship/i.test(block)) return 'Ship-fast'
  // Sale feed: prefer price-row off-% (shop card.html). Image Deal only when no % signal.
  if (forced === 'Deal' && !(offPct && offPct > 0)) return 'Deal'
  // Browse/home: never stamp Deal on the photo — shop uses price-row off-badge (%).
  return undefined
}


function requestText(url: string): Promise<string> {
  const finalUrl = withCatalogLang(url)
  return new Promise((resolve, reject) => {
    uni.request({
      url: finalUrl,
      method: 'GET',
      timeout: 15000,
      header: {
        Accept: 'text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8',
        ...catalogLangHeaders(),
      },
      success: (res) => {
        const code = res.statusCode || 0
        if (code >= 400) {
          reject(new Error('HTTP ' + code + ' for ' + url))
          return
        }
        const data = res.data
        if (typeof data === 'string') resolve(data)
        else if (data == null) resolve('')
        else resolve(typeof data === 'object' ? JSON.stringify(data) : String(data))
      },
      fail: (err) => reject(err instanceof Error ? err : new Error(String(err))),
    })
  })
}

export function parseFeedCards(html: string): Product[] {
  const out: Product[] = []
  const re = /<a\s+class="card"\s+href="\/p\/([^"?]+)[^"]*"[^>]*>([\s\S]*?)<\/a>/gi
  let m: RegExpExecArray | null
  while ((m = re.exec(html))) {
    const sku = decodeURIComponent(m[1])
    const block = m[2]
    const imgM = block.match(/<img[^>]+src="([^"]+)"/i)
    const nameM = block.match(/class="name"[^>]*>([\s\S]*?)<\/span>/i)
    const priceM = block.match(/class="price"[^>]*>([\s\S]*?)<\/span>/i)
    const wasM = block.match(/class="was[^"]*"[^>]*>([\s\S]*?)<\/span>/i)
    const offM = block.match(/class="off-badge"[^>]*>([\s\S]*?)<\/span>/i)
    const onlyM = block.match(/class="only-left"[^>]*>([\s\S]*?)<\/span>/i)
    const name = decodeEntities((nameM?.[1] || '').replace(/<[^>]+>/g, '').trim()) || sku
    const price = parseMoney(decodeEntities(priceM?.[1] || ''))
    const compareAtRaw = parseMoney(decodeEntities(wasM?.[1] || ''))
    const compareAt = compareAtRaw > price ? compareAtRaw : 0
    const image = absUrl(imgM?.[1] || '')
    const offPct = parseOffPct(offM?.[1] || '', price, compareAt)
    const tag = pickCardTag(block, offPct)
    const onlyLeftN = onlyM ? parseInt(String(onlyM[1]).replace(/\D+/g, ''), 10) : 0
    const product: Product = {
      id: sku,
      sku,
      name,
      price,
      compareAt: compareAt || undefined,
      offPct,
      tag,
      stock: Number((raw as any).stock ?? (raw as any).qty ?? 1),
    onlyLeft: onlyLeftN > 0 ? onlyLeftN : undefined,
      category: 'Harbor',
      image,
      images: image ? [image] : [],
      shipsIn: 'Tracked shipping · worldwide',
      hub: 'US / EU',
      live: true,
    }
    cache.set(sku, { ...cache.get(sku), ...product })
    out.push(product)
  }
  return out
}

function parseJsonLdProduct(html: string, sku: string): Partial<Product> | null {
  const blocks = html.match(/<script[^>]*type=["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/gi) || []
  for (const block of blocks) {
    const bodyM = block.match(/>([\s\S]*?)<\/script>/i)
    if (!bodyM) continue
    try {
      const data = JSON.parse(bodyM[1])
      const nodes = Array.isArray(data) ? data : [data]
      for (const node of nodes) {
        if (!node || node['@type'] !== 'Product') continue
        const images = Array.isArray(node.image)
          ? node.image.map((u: string) => absUrl(String(u)))
          : node.image
            ? [absUrl(String(node.image))]
            : []
        const offer = node.offers || {}
        const price = parseMoney(String(offer.price ?? ''))
        return {
          id: String(node.sku || sku),
          sku: String(node.sku || sku),
          name: decodeEntities(String(node.name || sku)),
          price,
          blurb: decodeEntities(String(node.description || '')),
          image: images[0],
          images,
          live: true,
        }
      }
    } catch {
      /* skip bad json-ld */
    }
  }
  return null
}

function parseBreadcrumbCategory(html: string): string {
  const blocks = html.match(/<script[^>]*type=["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/gi) || []
  for (const block of blocks) {
    const bodyM = block.match(/>([\s\S]*?)<\/script>/i)
    if (!bodyM) continue
    try {
      const data = JSON.parse(bodyM[1])
      if (data?.['@type'] !== 'BreadcrumbList') continue
      const items = data.itemListElement || []
      if (items.length >= 2) {
        const mid = items[items.length - 2]
        if (mid?.name) return decodeEntities(String(mid.name))
      }
    } catch {
      /* ignore */
    }
  }
  const c = html.match(/href="\/c\/([^"?]+)/i)
  if (c) {
    const id = c[1]
    const hit = ALL_CATEGORIES.find((x) => x.id === id)
    return hit?.name || id
  }
  return 'Harbor'
}

function parsePeekExtras(html: string): {
  sizes: string[]
  offers: ProductOffer[]
  compareAt?: number
  price?: number
  blurb?: string
  image?: string
} {
  const offers: ProductOffer[] = []
  const offerRe = /<label class="peek-offer">([\s\S]*?)<\/label>/gi
  let m: RegExpExecArray | null
  while ((m = offerRe.exec(html))) {
    const block = m[1]
    const idM = block.match(/name="offer"[^>]*value="([^"]+)"/i) || block.match(/value="([^"]+)"[^>]*name="offer"/i)
    const labelM = block.match(/<span>([\s\S]*?)<\/span>/i)
    const priceAttr = block.match(/data-price="([^"]+)"/i)
    const origAttr = block.match(/data-original="([^"]+)"/i)
    const imgM = block.match(/<img[^>]+src="([^"]+)"/i)
    const id = idM?.[1] || ''
    const label = decodeEntities((labelM?.[1] || '').replace(/<[^>]+>/g, '').trim())
    if (!id && !label) continue
    offers.push({
      id: id || label,
      label: label || id,
      price: priceAttr ? parseMoney(priceAttr[1]) : undefined,
      compareAt: origAttr ? parseMoney(origAttr[1]) : undefined,
      image: imgM ? absUrl(imgM[1]) : undefined,
    })
  }
  const sizes = offers.map((o) => o.label)
  const priceM = html.match(/class="peek-price"[\s\S]*?<b>([\s\S]*?)<\/b>/i)
  const wasM = html.match(/class="peek-price"[\s\S]*?<s>([\s\S]*?)<\/s>/i)
  const aboutM = html.match(/class="peek-about"[^>]*>([\s\S]*?)<\/p>/i)
  const imgM = html.match(/class="peek-media"[\s\S]*?<img[^>]+src="([^"]+)"/i)
  return {
    sizes,
    offers,
    price: priceM ? parseMoney(decodeEntities(priceM[1])) : undefined,
    compareAt: wasM ? parseMoney(decodeEntities(wasM[1])) : undefined,
    blurb: aboutM ? decodeEntities(aboutM[1].replace(/<[^>]+>/g, '').trim()) : undefined,
    image: imgM ? absUrl(imgM[1]) : undefined,
  }
}

function tagFromPrices(price: number, compareAt?: number): ProductTag | undefined {
  if (compareAt && compareAt > price) return 'Deal'
  return undefined
}

export async function listProducts(tab = 'recommended', page = 1): Promise<Product[]> {
  const root = apiRoot()
  const url = `${root}/home/feed?partial=1&tab=${encodeURIComponent(tab)}&page=${page}`
  try {
    const html = await requestText(url)
    const items = parseFeedCards(html)
    if (items.length) return items
  } catch (err) {
    console.warn('[harbor] listProducts failed, using mock', err)
  }
  return MOCK.slice()
}

export async function getProduct(skuOrId: string): Promise<Product | undefined> {
  const key = decodeURIComponent(skuOrId || '').trim()
  if (!key) return undefined

  const mockHit = MOCK.find((p) => p.sku === key || p.id === key)
  const cached = cache.get(key)

  const root = apiRoot()
  try {
    const [pdpHtml, peekHtml] = await Promise.all([
      requestText(`${root}/p/${encodeURIComponent(key)}`),
      requestText(`${root}/p/${encodeURIComponent(key)}/peek`).catch(() => ''),
    ])
    const ld = parseJsonLdProduct(pdpHtml, key)
    const peek = peekHtml ? parsePeekExtras(peekHtml) : { sizes: [] as string[], offers: [] as ProductOffer[] }
    const category = parseBreadcrumbCategory(pdpHtml)
    if (ld || peek.price || peek.blurb) {
      const price = ld?.price || peek.price || cached?.price || 0
      const compareAt = peek.compareAt && peek.compareAt > price ? peek.compareAt : cached?.compareAt
      const image = ld?.image || peek.image || cached?.image
      const images = ld?.images?.length ? ld.images : image ? [image] : cached?.images
      const product: Product = {
        id: key,
        sku: key,
        name: ld?.name || cached?.name || key,
        price,
        compareAt,
        tag: tagFromPrices(price, compareAt),
        category,
        image,
        images,
        sizes: peek.sizes?.length ? peek.sizes : cached?.sizes,
        offers: peek.offers?.length ? peek.offers : cached?.offers,
        blurb: peek.blurb || ld?.blurb || cached?.blurb,
        shipsIn: 'Tracked shipping 路 worldwide',
        hub: 'US / EU',
        live: true,
      }
      cache.set(key, product)
      return product
    }
  } catch (err) {
    console.warn('[harbor] getProduct failed', key, err)
  }

  if (cached) return cached
  return mockHit
}

export async function listByCategory(category: string): Promise<Product[]> {
  if (!category || category === 'All') return listProducts('recommended', 1)
  // accept display name or id
  const hit =
    ALL_CATEGORIES.find((c) => c.id === category) ||
    ALL_CATEGORIES.find((c) => c.name === category) ||
    CATEGORIES.find((c) => c.id === category || c.name === category)
  const tab = hit?.id || category.toLowerCase()
  return listProducts(tab, 1)
}


/** English subcategory chips aligned with shop/taxonomy.py CHILDREN. */
export const SUBCATEGORIES: Record<string, CategoryChip[]> = {
  daily: [
    { id: 'hangers', name: 'Hangers' }, { id: 'rain', name: 'Rain' }, { id: 'warmth', name: 'Warmers' },
    { id: 'shoecare', name: 'Shoe care' }, { id: 'gloves', name: 'Gloves' },
  ],
  kitchen: [
    { id: 'cookware', name: 'Cookware' }, { id: 'gadgets', name: 'Utensils' }, { id: 'bakeware', name: 'Bakeware' },
    { id: 'drinkware', name: 'Drinkware' }, { id: 'foodkeep', name: 'Food storage' },
  ],
  tableware: [
    { id: 'dishes', name: 'Bowls & plates' }, { id: 'cutlery', name: 'Chopsticks' }, { id: 'teaware', name: 'Tea & coffee' },
  ],
  storage: [
    { id: 'boxes', name: 'Boxes' }, { id: 'closet', name: 'Closet' }, { id: 'hooks', name: 'Hooks' },
    { id: 'drawers', name: 'Drawers' }, { id: 'shelves', name: 'Shelves' },
  ],
  cleaning: [
    { id: 'cleantools', name: 'Tools' }, { id: 'laundry', name: 'Laundry' }, { id: 'bathclean', name: 'Bathroom' },
    { id: 'trash', name: 'Trash' },
  ],
  paper: [
    { id: 'tissue', name: 'Paper' }, { id: 'sanitary', name: 'Sanitary' }, { id: 'scent', name: 'Fragrance' },
    { id: 'repellent', name: 'Repellent' },
  ],
  personal: [
    { id: 'bath', name: 'Bath' }, { id: 'hair', name: 'Hair' }, { id: 'oral', name: 'Oral' }, { id: 'shave', name: 'Shave' },
  ],
  beauty: [
    { id: 'skin', name: 'Skin' }, { id: 'mask', name: 'Masks' }, { id: 'body', name: 'Body oil' },
  ],
  makeup: [
    { id: 'color', name: 'Color' }, { id: 'perfume', name: 'Perfume' }, { id: 'mtools', name: 'Makeup tools' },
  ],
  textile: [
    { id: 'towel', name: 'Towels' }, { id: 'bedding', name: 'Bedding' }, { id: 'curtain', name: 'Curtains' },
    { id: 'cushion', name: 'Cushions' },
  ],
  decor: [
    { id: 'ornament', name: 'Ornaments' }, { id: 'wall', name: 'Wall art' }, { id: 'vase', name: 'Vases' },
  ],
  appliance: [
    { id: 'fan', name: 'Fans' }, { id: 'humidity', name: 'Humidity' }, { id: 'heat', name: 'Heaters' },
  ],
  hardware: [
    { id: 'handtool', name: 'Hand tools' }, { id: 'lock', name: 'Locks' }, { id: 'measure', name: 'Measuring' },
    { id: 'tape', name: 'Tape' },
  ],
  pet: [
    { id: 'feeding', name: 'Feeding' }, { id: 'toys', name: 'Toys' }, { id: 'groom', name: 'Grooming' },
    { id: 'waste', name: 'Waste' }, { id: 'beds', name: 'Beds' },
  ],
  office: [
    { id: 'writing', name: 'Writing' }, { id: 'notepaper', name: 'Paper' }, { id: 'files', name: 'Files' },
    { id: 'correct', name: 'Corrections' }, { id: 'organize', name: 'Organizers' }, { id: 'light', name: 'Lighting' },
    { id: 'stands', name: 'Stands' }, { id: 'cables', name: 'Cables' },
  ],
  party: [
    { id: 'holiday', name: 'Holiday' }, { id: 'giftbox', name: 'Gift wrap' }, { id: 'festive', name: 'Party' },
  ],
}

export interface ListingPage {
  items: Product[]
  hasMore: boolean
  page: number
  live: boolean
}

async function fetchCardPartial(pathWithQuery: string): Promise<ListingPage> {
  const root = apiRoot()
  const joiner = pathWithQuery.includes('?') ? '&' : '?'
  const url = `${root}${pathWithQuery}${joiner}partial=1`
  try {
    const html = await requestText(url)
    const items = parseFeedCards(html)
    return { items, hasMore: items.length >= 12, page: 1, live: items.length > 0 }
  } catch (err) {
    console.warn('[harbor] listing failed', pathWithQuery, err)
    return { items: [], hasMore: false, page: 1, live: false }
  }
}

export async function searchProducts(q: string, page = 1): Promise<ListingPage> {
  const query = (q || '').trim()
  if (!query) return { items: [], hasMore: false, page, live: false }
  const path = `/search?q=${encodeURIComponent(query)}&page=${page}`
  const res = await fetchCardPartial(path)
  res.page = page
  if (!res.items.length && page === 1) {
    // soft fallback: home feed tab search is not available; keep empty
  }
  return res
}

export async function listCategoryPage(category: string, sub = '', page = 1): Promise<ListingPage> {
  const cat = (category || '').trim().toLowerCase()
  if (!cat) return listProducts('recommended', page).then((items) => ({ items, hasMore: items.length >= 12, page, live: items.some((p) => p.live) }))
  const path = sub
    ? `/c/${encodeURIComponent(cat)}/${encodeURIComponent(sub)}?page=${page}`
    : `/c/${encodeURIComponent(cat)}?page=${page}`
  const res = await fetchCardPartial(path)
  res.page = page
  if (!res.items.length && page === 1) {
    const fallback = await listByCategory(cat)
    return { items: fallback, hasMore: false, page, live: fallback.some((p) => p.live) }
  }
  return res
}

export function parseDealCards(html: string, defaultTag: ProductTag = 'Deal'): Product[] {
  const out: Product[] = []
  const re = /<a\s+class="deal"\s+href="\/p\/([^"?]+)[^"]*"[^>]*>([\s\S]*?)<\/a>/gi
  let m: RegExpExecArray | null
  while ((m = re.exec(html))) {
    const sku = decodeURIComponent(m[1])
    const block = m[2]
    const imgM = block.match(/<img[^>]+src="([^"]+)"/i)
    const nameM = block.match(/class="name"[^>]*>([\s\S]*?)<\/span>/i)
    const priceM = block.match(/class="price"[^>]*>([\s\S]*?)<\/span>/i)
    const wasM = block.match(/class="was[^"]*"[^>]*>([\s\S]*?)<\/span>/i)
    const name = decodeEntities((nameM?.[1] || '').replace(/<[^>]+>/g, '').trim()) || sku
    const price = parseMoney(decodeEntities(priceM?.[1] || ''))
    const compareAt = parseMoney(decodeEntities(wasM?.[1] || ''))
    const image = absUrl(imgM?.[1] || '')
    const product: Product = {
      id: sku,
      sku,
      name,
      price,
      compareAt: compareAt > price ? compareAt : undefined,
      tag: defaultTag,
      offPct: compareAt > price ? Math.round((1 - price / compareAt) * 100) : undefined,
      category: 'Harbor',
      image,
      images: image ? [image] : [],
      shipsIn: 'Tracked shipping 路 worldwide',
      hub: 'US / EU',
      live: true,
    }
    cache.set(sku, { ...cache.get(sku), ...product })
    out.push(product)
  }
  return out
}

export async function listSaleProducts(): Promise<Product[]> {
  try {
    const html = await requestText(`${apiRoot()}/sale`)
    const items = parseDealCards(html, 'Deal')
    if (items.length) return items
  } catch (err) {
    console.warn('[harbor] sale failed', err)
  }
  return listProducts('recommended', 1).then((rows) =>
    rows.filter((p) => p.tag === 'Deal' || (p.compareAt && p.compareAt > p.price)).slice(0, 12),
  )
}

export async function listNewProducts(): Promise<Product[]> {
  try {
    const html = await requestText(`${apiRoot()}/new`)
    const items = parseDealCards(html, 'New')
    if (items.length) return items
  } catch (err) {
    console.warn('[harbor] new failed', err)
  }
  return listProducts('recommended', 1)
}

export function categoryLabel(id: string): string {
  return ALL_CATEGORIES.find((c) => c.id === id)?.name || id
}


export function parseLpDealCards(html: string): Product[] {
  const out: Product[] = []
  const re = /<a\s+class="lp-deal[^"]*"[^>]*href="([^"]+)"[^>]*>([\s\S]*?)<\/a>/gi
  let m: RegExpExecArray | null
  while ((m = re.exec(html))) {
    const href = m[1]
    const block = m[2]
    const skuM = href.match(/sku=([^&"']+)/i) || href.match(/\/p\/([^"?]+)/i)
    const sku = decodeURIComponent(skuM?.[1] || '')
    if (!sku) continue
    const imgM = block.match(/<img[^>]+src="([^"]+)"/i)
    const nameM = block.match(/class="lp-deal-name"[^>]*>([\s\S]*?)<\/span>/i)
    const priceM = block.match(/class="price"[^>]*>([\s\S]*?)<\/span>/i)
    const wasM = block.match(/class="was[^"]*"[^>]*>([\s\S]*?)<\/span>/i)
    const name = decodeEntities((nameM?.[1] || '').replace(/<[^>]+>/g, '').trim()) || sku
    const price = parseMoney(decodeEntities(priceM?.[1] || ''))
    const compareAt = parseMoney(decodeEntities(wasM?.[1] || ''))
    const image = absUrl(imgM?.[1] || '')
    const product: Product = {
      id: sku,
      sku,
      name,
      price,
      compareAt: compareAt > price ? compareAt : undefined,
      tag: 'Flash',
      category: 'Flash',
      image,
      images: image ? [image] : [],
      shipsIn: 'Flash 路 tracked',
      hub: 'US / EU',
      live: true,
    }
    cache.set(sku, { ...cache.get(sku), ...product })
    out.push(product)
  }
  return out
}

export async function listShipLpProducts(): Promise<Product[]> {
  try {
    const html = await requestText(`${apiRoot()}/lp/ship`)
    const items = parseLpDealCards(html)
    if (items.length) return items
    return parseDealCards(html, 'Deal')
  } catch (err) {
    console.warn('[harbor] lp/ship failed', err)
    return listSaleProducts()
  }
}

export async function listCompareProducts(): Promise<{ headers: string[]; products: Product[] }> {
  try {
    const html = await requestText(`${apiRoot()}/compare`)
    // Prefer card-like product links in headers
    const skus: string[] = []
    for (const m of html.matchAll(/href="\/p\/([^"?]+)/gi)) {
      const sku = decodeURIComponent(m[1])
      if (!skus.includes(sku)) skus.push(sku)
    }
    const products: Product[] = []
    for (const sku of skus.slice(0, 4)) {
      const p = await getProduct(sku)
      if (p) products.push(p)
    }
    return { headers: products.map((p) => p.name), products }
  } catch (err) {
    console.warn('[harbor] compare failed', err)
    return { headers: [], products: [] }
  }
}



/** Pull first data-ends / ends_at from sale or LP HTML for the deal clock. */
export function parseDealEnds(html: string): string | undefined {
  const m =
    html.match(/data-ends="([^"]+)"/i) ||
    html.match(/ends_at["']?\s*[:=]\s*["']([^"']+)/i)
  return m?.[1] || undefined
}


/** Prefer live /sale seckill ends_at; else empty so UI falls back to UTC day-end. */
export async function fetchDealEnds(): Promise<string> {
  try {
    const html = await requestText(`${apiRoot()}/sale`)
    return parseDealEnds(html) || ''
  } catch {
    return ''
  }
}

/** Ship LP uses a short flash window (shop: ~10 min per IP); parse data-ends from /lp/ship. */
export async function fetchFlashEnds(): Promise<string> {
  try {
    const html = await requestText(`${apiRoot()}/lp/ship`)
    return parseDealEnds(html) || (await fetchDealEnds())
  } catch {
    return fetchDealEnds()
  }
}
