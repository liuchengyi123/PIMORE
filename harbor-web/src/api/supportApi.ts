import { harborRequest } from './http'
import { apiRoot } from './config'
import { browseHistoryPayload, type BrowseItem } from '@/composables/browseHistory'
import { useCart } from '@/composables/cart'
import { getItem, setItem } from '@/composables/storage'

const VID_KEY = 'harbor_cs_visitor'
const ROOM_KEY = 'harbor_cs_room'

export function getCsVisitor(): string {
  return getItem(VID_KEY)
}

export function setCsVisitor(vid: string) {
  if (!vid) return
  setItem(VID_KEY, vid)
}

export function setCsRoom(roomId: string) {
  setItem(ROOM_KEY, roomId)
}

export function getCsRoom(): string {
  return getItem(ROOM_KEY)
}

export interface CsProductCtx {
  sku: string
  name: string
  image?: string
  price?: string | number
}

export interface CsMessage {
  id: number
  room_id: string
  role: 'user' | 'staff' | 'system' | string
  body: string
  created_at: string
  staff_user?: string
}

export interface CsRoom {
  id: string
  visitor_id: string
  email: string
  status: string
  current: CsProductCtx
  history: BrowseItem[]
  updated_at: string
  unread_user?: number
}

function cartPayload() {
  try {
    return useCart().handoffPayload() || []
  } catch {
    return []
  }
}

function rootPath(path: string) {
  return path.startsWith('/') ? path : '/' + path
}

function vidHeaders(): Record<string, string> {
  const vid = getCsVisitor()
  return vid ? { 'X-Harbor-Vid': vid } : {}
}

export async function openSupportChat(current?: CsProductCtx | null) {
  const history = browseHistoryPayload(12)
  const body = {
    current: current || null,
    sku: current?.sku || '',
    name: current?.name || '',
    image: current?.image || '',
    price: current?.price ?? '',
    history,
    cart: cartPayload(),
    visitor_id: getCsVisitor(),
  }
  const res = await harborRequest<{ ok: boolean; room: CsRoom; messages: CsMessage[] }>(
    rootPath('/api/cs/open'),
    {
      method: 'POST',
      json: true,
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
        ...vidHeaders(),
      },
      data: body as Record<string, unknown>,
    },
  )
  const data = res.data as any
  if (data?.room?.visitor_id) setCsVisitor(data.room.visitor_id)
  if (data?.room?.id) setCsRoom(data.room.id)
  return res
}

export async function sendSupportMessage(roomId: string, text: string, current?: CsProductCtx | null) {
  const payload: Record<string, unknown> = {
    room_id: roomId,
    body: text,
    history: browseHistoryPayload(12),
    cart: cartPayload(),
    visitor_id: getCsVisitor(),
  }
  if (current) {
    payload.current = current
    payload.sku = current.sku
    payload.name = current.name
    payload.image = current.image
    payload.price = current.price
  }
  return harborRequest<{ ok: boolean; message: CsMessage }>(rootPath('/api/cs/send'), {
    method: 'POST',
    json: true,
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...vidHeaders(),
    },
    data: payload,
  })
}

export type CsTyping = { active: boolean; side?: string; name?: string } | null

export async function pollSupportMessages(roomId: string, afterId: number, timeout = 18) {
  const vid = getCsVisitor()
  const q = `/api/cs/poll?room_id=${encodeURIComponent(roomId)}&after=${afterId}&timeout=${timeout}&visitor_id=${encodeURIComponent(vid)}`
  return harborRequest<{ ok: boolean; messages: CsMessage[]; room: CsRoom; typing?: CsTyping }>(rootPath(q), {
    method: 'GET',
    json: true,
    headers: {
      Accept: 'application/json',
      ...vidHeaders(),
    },
  })
}

export async function fetchCsStickers() {
  return harborRequest<{
    ok: boolean
    items: { id: number; pack: string; label: string; emoji: string; image_url?: string }[]
  }>(rootPath('/api/cs/stickers'), {
    method: 'GET',
    json: true,
    headers: { Accept: 'application/json' },
  })
}

export function csMediaUrl(path: string): string {
  const p = String(path || '').trim()
  if (!p) return ''
  if (/^https?:\/\//i.test(p)) return p
  const root = apiRoot().replace(/\/$/, '')
  return root + (p.startsWith('/') ? p : '/' + p)
}

export function parseImgBody(body: string): string | null {
  const b = String(body || '')
  if (!b.startsWith('[img]')) return null
  const url = b.slice(5).trim().split(/\s+/)[0] || ''
  return url || null
}

export function parseCartBody(body: string): { n: number } | null {
  const raw = String(body || '').trim()
  if (!raw.startsWith('[cart]')) return null
  try {
    const data = JSON.parse(raw.slice(6).trim() || '{}') as { n?: number; count?: number }
    return { n: Number(data.n || data.count || 0) }
  } catch {
    return { n: 0 }
  }
}

export async function fetchVisitorProduct(sku: string, lang: string) {
  const q = new URLSearchParams({ lang: lang || 'en' })
  return harborRequest<{ ok: boolean; product: { sku: string; name: string; image: string; price: string; offers: { id: string; label: string; price: string; image: string }[] } }>(
    rootPath('/api/cs/product/' + encodeURIComponent(sku) + '?' + q.toString()),
  )
}

export function parseProductBody(body: string): null | {
  sku?: string
  name?: string
  image?: string
  price?: string
  option?: string
  option_key?: string
  offer_id?: string
} {
  const b = String(body || '')
  if (!b.startsWith('[product]')) return null
  try {
    return JSON.parse(b.slice(9).trim())
  } catch {
    return null
  }
}

export interface CsOrderCard {
  id?: number | string
  submit_id?: string
  status?: string
  currency?: string
  due_cents?: number
  items?: string[]
  created_at?: string
  tracking?: string
}

export function parseOrderBody(body: string): CsOrderCard | null {
  const b = String(body || '')
  if (!b.startsWith('[order]')) return null
  try {
    return JSON.parse(b.slice(7).trim()) as CsOrderCard
  } catch {
    return null
  }
}

export function buildProductBody(p: {
  sku?: string
  name?: string
  image?: string
  price?: string | number
  option?: string
  option_key?: string
  offer_id?: string
}): string {
  const payload = {
    sku: p.sku || '',
    name: p.name || p.sku || '',
    image: p.image || '',
    price: p.price ?? '',
    option: p.option || '',
    option_key: p.option_key || '',
    offer_id: p.offer_id || '',
  }
  return '[product]' + JSON.stringify(payload)
}

export function buildOrderBody(o: CsOrderCard): string {
  const payload = {
    id: o.id,
    submit_id: o.submit_id || '',
    status: o.status || '',
    currency: o.currency || '',
    due_cents: o.due_cents ?? 0,
    items: Array.isArray(o.items) ? o.items.slice(0, 4) : [],
    created_at: o.created_at || '',
    tracking: o.tracking || '',
  }
  return '[order]' + JSON.stringify(payload)
}

export async function fetchCsOrders(roomId: string) {
  const vid = getCsVisitor()
  const q = `/api/cs/orders?room_id=${encodeURIComponent(roomId)}&visitor_id=${encodeURIComponent(vid)}`
  return harborRequest<{ ok: boolean; orders: CsOrderCard[]; email?: string }>(rootPath(q), {
    method: 'GET',
    json: true,
    headers: {
      Accept: 'application/json',
      ...vidHeaders(),
    },
  })
}

export async function uploadCsImage(
  roomId: string,
  file: File,
): Promise<{ ok: boolean; url?: string; error?: string }> {
  const vid = getCsVisitor()
  const root = apiRoot().replace(/\/$/, '')
  const fd = new FormData()
  fd.append('file', file)
  fd.append('room_id', roomId)
  fd.append('visitor_id', vid)
  try {
    const res = await fetch(root + '/api/cs/upload', {
      method: 'POST',
      body: fd,
      credentials: 'include',
      headers: {
        ...vidHeaders(),
      },
    })
    const data = await res.json()
    if (data?.ok && data.url) return { ok: true, url: String(data.url) }
    return { ok: false, error: 'upload' }
  } catch {
    return { ok: false, error: 'network' }
  }
}

export async function sendSupportImage(roomId: string, imageUrl: string, current?: CsProductCtx | null) {
  return sendSupportMessage(roomId, '[img]' + imageUrl, current)
}
