/**
 * Harbor catalog client — live feed from shop (HTML cards + JSON-LD PDP).
 * Same routes as harbor-app: /home/feed, /p/:sku, /p/:sku/peek
 */
import { apiRoot, LIVE_ORIGIN } from './config'
import { withCatalogLang, catalogLangHeaders } from './catalogLang'

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
  onlyLeft?: number
  flashEnds?: string
}

export interface CategoryChip {
  id: string
  name: string
  tip?: string
}

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

/** Media URLs: absolute stay; relative go through local proxy or LIVE_ORIGIN. */
function absUrl(path: string): string {
  if (!path) return ''
  if (/^https?:\/\//i.test(path)) return path
  if (path.startsWith('//')) return 'https:' + path
  if (!path.startsWith('/')) path = '/' + path
  const root = apiRoot()
  if (root.startsWith('/')) return root + path
  return LIVE_ORIGIN + path
}

function parseMoney(raw: string): number {
  const m = String(raw || '').replace(/,/g, '').match(/-?\d+(?:\.\d+)?/)
  return m ? Number(m[0]) : 0
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
  if (forced === 'Deal' && !(offPct && offPct > 0)) return 'Deal'
  return undefined
}

async function requestText(url: string): Promise<string> {
  const finalUrl = withCatalogLang(url)
  const res = await fetch(finalUrl, {
    method: 'GET',
    credentials: 'include',
    headers: {
      Accept: 'text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8',
      ...catalogLangHeaders(),
    },
  })
  if (!res.ok) throw new Error('HTTP ' + res.status + ' for ' + url)
  return await res.text()
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
      onlyLeft: onlyLeftN > 0 ? onlyLeftN : undefined,
      category: 'Harbor',
      image,
      images: image ? [image] : [],
      shipsIn: 'Tracked shipping · worldwide',
      hub: 'US / EU',
      live: true,
    }
    cache.set(sku, { ...(cache.get(sku) || {}), ...product })
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
      /* skip */
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
  const html = await requestText(url)
  return parseFeedCards(html)
}


export async function fetchProductInterest(sku: string): Promise<number> {
  const key = decodeURIComponent(sku || '').trim()
  if (!key) return 0
  const root = apiRoot()
  try {
    const res = await fetch(`${root}/api/catalog/interest/${encodeURIComponent(key)}`, {
      method: 'GET',
      credentials: 'include',
      headers: {
        Accept: 'application/json',
        ...catalogLangHeaders(),
      },
    })
    if (!res.ok) return 0
    const data = await res.json()
    const n = Number(data && data.count)
    return Number.isFinite(n) && n > 0 ? Math.floor(n) : 0
  } catch (err) {
    console.warn('[harbor] fetchProductInterest failed', key, err)
    return 0
  }
}

export async function getProduct(skuOrId: string): Promise<Product | undefined> {
  const key = decodeURIComponent(skuOrId || '').trim()
  if (!key) return undefined
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
    if (ld || peek.price || peek.blurb || peek.offers?.length) {
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
        shipsIn: 'Tracked shipping · worldwide',
        hub: 'US / EU',
        live: true,
      }
      cache.set(key, product)
      return product
    }
  } catch (err) {
    console.warn('[harbor] getProduct failed', key, err)
  }
  return cached
}

export async function listByCategory(category: string): Promise<Product[]> {
  if (!category || category === 'All') return listProducts('recommended', 1)
  const hit =
    ALL_CATEGORIES.find((c) => c.id === category) ||
    ALL_CATEGORIES.find((c) => c.name === category) ||
    CATEGORIES.find((c) => c.id === category || c.name === category)
  const tab = hit?.id || category.toLowerCase()
  return listProducts(tab, 1)
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
      shipsIn: 'Tracked shipping · worldwide',
      hub: 'US / EU',
      live: true,
    }
    cache.set(sku, { ...(cache.get(sku) || {}), ...product })
    out.push(product)
  }
  // fallback: some templates reuse .card on sale pages
  if (!out.length) return parseFeedCards(html).map((p) => ({ ...p, tag: defaultTag }))
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

export async function listCompareProducts(): Promise<{ headers: string[]; products: Product[] }> {
  try {
    const html = await requestText(`${apiRoot()}/compare`)
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

export function parseDealEnds(html: string): string | undefined {
  const m =
    html.match(/data-ends=["']([^"']+)["']/i) ||
    html.match(/ends_at["']?\s*[:=]\s*["']([^"']+)["']/i)
  return m?.[1]
}

export async function fetchDealEnds(): Promise<string> {
  try {
    const html = await requestText(`${apiRoot()}/sale`)
    return parseDealEnds(html) || ''
  } catch {
    return ''
  }
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
      offPct: compareAt > price ? Math.round((1 - price / compareAt) * 100) : undefined,
      category: 'Harbor',
      image,
      images: image ? [image] : [],
      shipsIn: 'Tracked shipping · worldwide',
      hub: 'US / EU',
      live: true,
    }
    cache.set(sku, { ...(cache.get(sku) || {}), ...product })
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

export async function fetchFlashEnds(): Promise<string> {
  try {
    const html = await requestText(`${apiRoot()}/lp/ship`)
    return parseDealEnds(html) || (await fetchDealEnds())
  } catch {
    return fetchDealEnds()
  }
}
