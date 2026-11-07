import { reactive, computed } from 'vue'
import type { Product } from '@/api/products'
import {
  addToCartServer,
  fetchCartServer,
  updateCartServer,
  lineToProduct,
  type CartSnapshot,
} from '@/api/cartApi'

export interface CartLine {
  /** Server line code e.g. b13418~H9382 when live */
  code: string
  product: Product
  size: string
  offerId?: string
  qty: number
  live?: boolean
}

const state = reactive({
  lines: [] as CartLine[],
  live: false,
  syncing: false,
  shipLine: '',
  progress: 0,
  freeShipThreshold: 19,
  shipMet: false,
  lastError: '',
})

function applySnapshot(snap: CartSnapshot) {
  state.live = snap.live
  state.shipLine = snap.shipLine
  state.progress = snap.progress
  state.freeShipThreshold = snap.freeShipThreshold || 19
  state.shipMet = snap.shipMet
  state.lines = snap.lines.map((l) => ({
    code: l.sku,
    product: lineToProduct(l),
    size: l.label || 'default',
    offerId: l.sku.includes('~') ? l.sku.split('~')[1] : undefined,
    qty: l.qty,
    live: true,
  }))
}

function addLocal(product: Product, size: string, offerId: string | undefined, qty: number) {
  const hit = state.lines.find(
    (l) => l.product.sku === product.sku && (l.offerId || '') === (offerId || '') && l.size === size,
  )
  if (hit) hit.qty += qty
  else {
    state.lines.push({
      code: offerId ? `${product.sku}~${offerId}` : product.sku,
      product,
      size,
      offerId,
      qty,
      live: false,
    })
  }
  state.live = false
}

export function useCart() {
  const count = computed(() => state.lines.reduce((n, l) => n + l.qty, 0))
  const subtotal = computed(() =>
    state.lines.reduce((n, l) => n + l.product.price * l.qty, 0),
  )
  const remainingToFreeShip = computed(() =>
    Math.max(0, state.freeShipThreshold - subtotal.value),
  )
  const freeShipProgress = computed(() => {
    if (state.progress > 0) return Math.min(1, state.progress / 100)
    const t = state.freeShipThreshold || 19
    return Math.min(1, subtotal.value / t)
  })

  async function refresh() {
    state.syncing = true
    state.lastError = ''
    try {
      const snap = await fetchCartServer()
      if (snap.lines.length || snap.live) applySnapshot(snap)
    } catch (err) {
      state.lastError = err instanceof Error ? err.message : String(err)
      console.warn('[harbor] cart refresh failed', err)
    } finally {
      state.syncing = false
    }
  }

  async function add(product: Product, size: string, qty = 1) {
    const offer =
      product.offers?.find((o) => o.label === size) ||
      product.offers?.[0]
    const offerId = offer?.id
    const unitPrice = offer?.price ?? product.price
    const priced: Product = { ...product, price: unitPrice, image: offer?.image || product.image }

    state.syncing = true
    state.lastError = ''
    try {
      const snap = await addToCartServer({
        sku: product.sku,
        offer: offerId || '',
        qty,
        country: 'US',
      })
      applySnapshot(snap)
      return { ok: true as const, live: true as const, message: snap.message || 'Added' }
    } catch (err) {
      state.lastError = err instanceof Error ? err.message : String(err)
      console.warn('[harbor] addToCart server failed, local fallback', err)
      addLocal(priced, size || offer?.label || 'default', offerId, qty)
      return { ok: true as const, live: false as const, message: 'Saved locally' }
    } finally {
      state.syncing = false
    }
  }

  async function setQty(codeOrId: string, size: string, qty: number) {
    const hit =
      state.lines.find((l) => l.code === codeOrId && l.size === size) ||
      state.lines.find((l) => l.product.id === codeOrId && l.size === size)
    if (!hit) return

    if (hit.live !== false && hit.code.includes('~')) {
      state.syncing = true
      try {
        const snap = await updateCartServer(hit.code, qty)
        applySnapshot(snap)
        return
      } catch (err) {
        state.lastError = err instanceof Error ? err.message : String(err)
        console.warn('[harbor] updateCart failed, local', err)
      } finally {
        state.syncing = false
      }
    }

    if (qty <= 0) state.lines = state.lines.filter((l) => l !== hit)
    else hit.qty = qty
  }

  function clear() {
    state.lines = []
    state.live = false
    state.shipLine = ''
    state.progress = 0
    state.shipMet = false
  }

  function handoffPayload() {
    return state.lines.map((l) => ({
      sku: l.product.sku,
      offer: l.offerId || '',
      qty: l.qty,
      name: l.product.name,
    }))
  }

  return {
    lines: computed(() => state.lines),
    count,
    subtotal,
    remainingToFreeShip,
    freeShipProgress,
    freeShipThreshold: computed(() => state.freeShipThreshold),
    shipLine: computed(() => state.shipLine),
    shipMet: computed(() => state.shipMet),
    live: computed(() => state.live),
    syncing: computed(() => state.syncing),
    lastError: computed(() => state.lastError),
    add,
    setQty,
    clear,
    refresh,
    handoffPayload,
  }
}
