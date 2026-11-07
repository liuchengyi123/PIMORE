export interface BrowseItem {
  sku: string
  name: string
  image?: string
  price?: string | number
  ts: number
}

const KEY = 'harbor_browse_history'
const MAX = 30

export function loadBrowseHistory(): BrowseItem[] {
  try {
    const raw = uni.getStorageSync(KEY)
    if (!raw) return []
    const list = typeof raw === 'string' ? JSON.parse(raw) : raw
    return Array.isArray(list) ? (list as BrowseItem[]) : []
  } catch {
    return []
  }
}

export function trackBrowse(item: Omit<BrowseItem, 'ts'> & { ts?: number }) {
  if (!item?.sku) return
  const next: BrowseItem = {
    sku: String(item.sku),
    name: String(item.name || item.sku),
    image: item.image ? String(item.image) : '',
    price: item.price ?? '',
    ts: item.ts || Date.now(),
  }
  const list = [next, ...loadBrowseHistory().filter((x) => x.sku !== next.sku)].slice(0, MAX)
  try {
    uni.setStorageSync(KEY, list)
  } catch {
    /* ignore */
  }
}

export function browseHistoryPayload(limit = 12): BrowseItem[] {
  return loadBrowseHistory().slice(0, limit)
}
