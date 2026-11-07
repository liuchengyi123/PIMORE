import { reactive, computed } from 'vue'
import type { Product } from '@/api/products'
import { addToCartServer, fetchCartServer, updateCartServer, type CartSnapshot } from '@/api/cartApi'

export interface CartHandoffLine {
  sku: string
  offer: string
  qty: number
  name: string
}

export interface LocalCartLine {
  sku: string
  offer: string
  qty: number
  name: string
  price: number
  image?: string
  size?: string
  /** Server line code e.g. sku~offer */
  code?: string
  live?: boolean
}

const state = reactive({
  lines: [] as LocalCartLine[],
  live: false,
  syncing: false,
  lastError: '',
})

const CART_KEY = 'harbor_web_cart_local'

function persist() {
  try {
    localStorage.setItem(CART_KEY, JSON.stringify(state.lines))
  } catch {
    /* ignore */
  }
}

function load() {
  try {
    const raw = localStorage.getItem(CART_KEY)
    if (!raw) return
    const list = JSON.parse(raw)
    if (Array.isArray(list)) state.lines = list
  } catch {
    /* ignore */
  }
}

load()

function applySnapshot(snap: CartSnapshot) {
  state.live = snap.live
  state.lines = snap.lines.map((l) => ({
    sku: l.productSku,
    offer: l.sku.includes('~') ? l.sku.split('~')[1] : '',
    qty: l.qty,
    name: l.name,
    price: l.price,
    image: l.image,
    size: l.label || '',
    code: l.sku,
    live: true,
  }))
  persist()
}

export function useCart() {
  const count = computed(() => state.lines.reduce((n, l) => n + (l.qty || 0), 0))
  const subtotal = computed(() =>
    state.lines.reduce((n, l) => n + (Number(l.price) || 0) * (l.qty || 0), 0),
  )

  function handoffPayload(): CartHandoffLine[] {
    return state.lines.map((l) => ({
      sku: l.sku,
      offer: l.offer || '',
      qty: l.qty || 1,
      name: l.name || l.sku,
    }))
  }

  function setLines(lines: LocalCartLine[]) {
    state.lines = lines
    persist()
  }

  function add(product: Product, size = 'default', qty = 1) {
    const offer =
      product.offers?.find((o) => o.label === size) ||
      product.offers?.find((o) => o.id === size) ||
      null
    const offerId = offer?.id || ''
    const unit = offer?.price ?? product.price
    const image = offer?.image || product.image || ''
    const hit = state.lines.find(
      (l) => l.sku === product.sku && (l.offer || '') === offerId && (l.size || '') === (size || ''),
    )
    if (hit) hit.qty += qty
    else {
      state.lines.push({
        sku: product.sku,
        offer: offerId,
        qty,
        name: product.name || product.sku,
        price: unit,
        image,
        size: size || 'default',
        live: false,
      })
    }
    state.live = false
    persist()
    return { ok: true, live: false, message: 'Saved locally' }
  }

  async function setQty(sku: string, offer: string, qty: number) {
    const hit = state.lines.find((l) => l.sku === sku && (l.offer || '') === (offer || ''))
    if (!hit) return
    const code = hit.code || (offer ? `${sku}~${offer}` : sku)
    if (qty <= 0) state.lines = state.lines.filter((l) => l !== hit)
    else hit.qty = qty
    persist()
    try {
      const snap = await updateCartServer(code, Math.max(0, qty))
      applySnapshot(snap)
    } catch {
      /* keep local */
    }
  }

  function clear() {
    state.lines = []
    state.live = false
    persist()
  }

  async function refreshFromServer() {
    state.syncing = true
    state.lastError = ''
    try {
      const snap = await fetchCartServer()
      if (snap.lines.length || snap.live) applySnapshot(snap)
    } catch (e) {
      state.lastError = e instanceof Error ? e.message : String(e)
    } finally {
      state.syncing = false
    }
  }

  async function syncLocalToServer() {
    for (const line of state.lines) {
      await addToCartServer({ sku: line.sku, offer: line.offer || '', qty: line.qty || 1 })
    }
    await refreshFromServer()
  }

  function adopt(snap: CartSnapshot) {
    if (snap.lines && snap.lines.length) applySnapshot(snap)
  }

  return {
    lines: computed(() => state.lines),
    count,
    subtotal,
    live: computed(() => state.live),
    syncing: computed(() => state.syncing),
    lastError: computed(() => state.lastError),
    handoffPayload,
    setLines,
    add,
    setQty,
    clear,
    refreshFromServer,
    syncLocalToServer,
    adopt,
  }
}
