import { reactive } from 'vue'
import { harborRequest } from '@/api/http'
import { browseHistoryPayload } from '@/composables/browseHistory'
import { useCart } from '@/composables/cart'

const TOKEN_KEY = 'harbor_lucky_token'

export interface LuckyGood {
  name: string
  image: string
  from: number
  to: number
  now: number
}

interface LuckySpin {
  percent: number
  expires_at: string
  seconds_left: number
  used: boolean
  browse_kept: number
  pay_kept: number
  live: boolean
}

interface LuckyFree {
  order_id: number
  amount_cents: number
  stamps: number
  needed: number
  status: string
  deadline_at: string
}

type Pane = '' | 'wheel' | 'win' | 'browse' | 'pay' | 'placed' | 'eggs' | 'status'

export const lucky = reactive({
  enabled: false,
  percent: 10,
  browseMinutes: 3,
  offerSpin: false,
  spin: null as LuckySpin | null,
  free: null as LuckyFree | null,
  eggOrder: 0,
  pane: '' as Pane,
  spinning: false,
  goods: [] as LuckyGood[],
  eggs: ['Egg', 'Egg', 'Egg'] as string[],
  eggDone: false,
  prize: '',
  clock: '06:00:00',
})

let booted = false
let dismissed = false
let browseReady = false
let startedAt = 0
let browseTimer: ReturnType<typeof setTimeout> | null = null
let clockTimer: ReturnType<typeof setInterval> | null = null
let keepAt = 0

export function luckyToken(): string {
  try {
    return String(uni.getStorageSync(TOKEN_KEY) || '')
  } catch {
    return ''
  }
}

function saveToken(token: string) {
  if (!token) return
  try {
    uni.setStorageSync(TOKEN_KEY, token)
  } catch {
    /* ignore */
  }
}

function withToken(path: string): string {
  const token = luckyToken()
  if (!token) return path
  return path + (path.includes('?') ? '&' : '?') + 'lucky_spin=' + encodeURIComponent(token)
}

async function postLucky(path: string, data: Record<string, unknown>) {
  const res = await harborRequest<Record<string, unknown>>(withToken(path), {
    method: 'POST',
    json: true,
    form: false,
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    data,
  })
  return res.data || {}
}

function asNumber(value: unknown): number {
  if (typeof value === 'number') return value
  const n = parseFloat(String(value || '').replace(/[^0-9.]/g, ''))
  return Number.isFinite(n) ? n : 0
}

function priceGoods(rows: { name: string; image?: string; price: number }[], percent: number): LuckyGood[] {
  return rows
    .filter((row) => row.price > 0)
    .slice(0, 4)
    .map((row) => {
      const from = row.price
      const to = Math.round(from * (100 - percent)) / 100
      return { name: row.name, image: row.image || '', from, to, now: from }
    })
}

function browseGoods(): LuckyGood[] {
  const rows = browseHistoryPayload(4).map((item) => ({
    name: item.name,
    image: item.image,
    price: asNumber(item.price),
  }))
  return priceGoods(rows, lucky.percent)
}

const cart = useCart()

function cartGoods(): LuckyGood[] {
  const rows = cart.lines.value.map((line) => ({
    name: `${line.product.name} × ${line.qty}`,
    image: line.product.image,
    price: line.product.price * line.qty,
  }))
  return priceGoods(rows, lucky.percent)
}

function applyState(data: Record<string, unknown>) {
  lucky.enabled = Boolean(data.enabled)
  lucky.percent = Number(data.percent || lucky.percent || 10)
  lucky.browseMinutes = Number(data.browse_minutes || 3)
  lucky.offerSpin = Boolean(data.offer_spin)
  lucky.spin = (data.spin as LuckySpin) || null
  lucky.free = (data.free as LuckyFree) || null
  const egg = data.egg as { order_id?: number } | null
  if (egg && egg.order_id) lucky.eggOrder = Number(egg.order_id)
  if (typeof data.token === 'string') saveToken(data.token)
  if (lucky.spin && lucky.spin.percent) lucky.percent = lucky.spin.percent
}

function clockText(sec: number): string {
  const safe = Math.max(0, sec)
  const h = Math.floor(safe / 3600)
  const m = Math.floor((safe % 3600) / 60)
  const s = safe % 60
  const pad = (n: number) => (n < 10 ? '0' : '') + n
  return `${pad(h)}:${pad(m)}:${pad(s)}`
}

function secondsLeft(): number {
  if (!lucky.spin || !lucky.spin.live) return 0
  const end = Date.parse(lucky.spin.expires_at)
  if (!end) return lucky.spin.seconds_left || 0
  return Math.max(0, Math.floor((end - Date.now()) / 1000))
}

export function tickLuckyClock() {
  lucky.clock = clockText(secondsLeft())
}

function recentKeep(): boolean {
  return keepAt > 0 && Date.now() - keepAt < 60000
}

function currentRoute(): string {
  try {
    const pages = getCurrentPages()
    const cur = pages[pages.length - 1] as { route?: string } | undefined
    return cur?.route || ''
  } catch {
    return ''
  }
}

function armBrowse() {
  if (!lucky.spin?.live || startedAt) return
  startedAt = Date.now()
  const wait = Math.max(0, lucky.browseMinutes * 60000)
  if (browseTimer) clearTimeout(browseTimer)
  browseTimer = setTimeout(() => {
    browseReady = true
  }, wait)
}

export async function refreshLucky() {
  try {
    const res = await harborRequest<Record<string, unknown>>(withToken('/api/lucky'), {
      json: true,
      headers: { Accept: 'application/json' },
    })
    const data = res.data || {}
    if (!data || typeof data !== 'object' || !('enabled' in data)) return
    applyState(data)
    tickLuckyClock()
    armBrowse()
    if (!booted) {
      booted = true
      if (lucky.offerSpin && !dismissed && !lucky.eggOrder) lucky.pane = 'wheel'
    }
  } catch {
    /* shop offline or lucky not deployed on this host */
  }
}

export function startLuckyClock() {
  tickLuckyClock()
  if (clockTimer) return
  clockTimer = setInterval(tickLuckyClock, 1000)
}

export function stopLuckyClock() {
  if (!clockTimer) return
  clearInterval(clockTimer)
  clockTimer = null
}

export function closeLucky() {
  if (lucky.pane === 'wheel' && lucky.offerSpin && !lucky.spin) dismissed = true
  lucky.pane = ''
}

function animateGoods() {
  const started = Date.now()
  const from = lucky.goods.map((item) => item.from)
  const to = lucky.goods.map((item) => item.to)
  const step = () => {
    const t = Math.min(1, (Date.now() - started) / 800)
    const eased = 1 - Math.pow(1 - t, 3)
    lucky.goods.forEach((item, i) => {
      item.now = Math.round((from[i] + (to[i] - from[i]) * eased) * 100) / 100
    })
    if (t < 1) setTimeout(step, 40)
  }
  step()
}

async function markKeep(kind: 'browse' | 'pay') {
  keepAt = Date.now()
  if (lucky.spin && kind === 'browse') lucky.spin.browse_kept = 1
  if (lucky.spin && kind === 'pay') lucky.spin.pay_kept = 1
  try {
    await postLucky('/api/lucky/keep', { kind, token: luckyToken() })
  } catch {
    /* the sheet already showed */
  }
}

export function openBrowseRetain(): boolean {
  if (!browseReady || !lucky.spin?.live || lucky.spin.browse_kept || recentKeep()) return false
  const route = currentRoute()
  if (route.includes('checkout') || route.includes('webview') || route.includes('order-success')) return false
  const goods = browseGoods()
  if (!goods.length) return false
  lucky.goods = goods
  lucky.pane = 'browse'
  animateGoods()
  markKeep('browse')
  return true
}

export function openPayRetain(): boolean {
  if (!lucky.spin?.live || lucky.spin.pay_kept || recentKeep()) return false
  const goods = cartGoods()
  if (!goods.length) return false
  lucky.goods = goods
  lucky.pane = 'pay'
  animateGoods()
  markKeep('pay')
  return true
}

export function handleLuckyBack(): boolean {
  if (lucky.pane) {
    closeLucky()
    return true
  }
  const route = currentRoute()
  if (route.includes('pages/checkout')) return openPayRetain()
  if (browseReady) return openBrowseRetain()
  return false
}

export async function spinLucky() {
  if (lucky.spinning) return
  lucky.spinning = true
  try {
    const data = await postLucky('/api/lucky/spin', { token: luckyToken() })
    applyState(data)
    tickLuckyClock()
    armBrowse()
    setTimeout(() => {
      lucky.spinning = false
      lucky.pane = 'win'
    }, 4100)
  } catch {
    lucky.spinning = false
  }
}

export function showOrderEgg(orderId: string | number) {
  const id = Number(orderId || 0)
  if (id) lucky.eggOrder = id
  lucky.eggs = ['Egg', 'Egg', 'Egg']
  lucky.eggDone = false
  lucky.prize = ''
  lucky.pane = 'placed'
}

export function openEggs() {
  lucky.pane = 'eggs'
}

export async function smashEgg(index: number) {
  if (lucky.eggDone) return
  lucky.eggDone = true
  const misses = ['5% OFF', 'No prize']
  let used = 0
  lucky.eggs = lucky.eggs.map((_, i) => (i === index ? 'Free order' : misses[used++] || 'No prize'))
  try {
    const data = await postLucky('/api/lucky/egg', { order_id: lucky.eggOrder, token: luckyToken() })
    if (data.ok) {
      lucky.prize = 'Free-order coupon'
      if (data.free) lucky.free = data.free as LuckyFree
    } else {
      lucky.prize = 'This order can’t take the coupon.'
    }
  } catch {
    lucky.prize = 'Couldn’t reach Harbor. Try again from the order.'
    lucky.eggDone = false
  }
}

export function openLuckyChip() {
  if (lucky.free) {
    lucky.pane = 'status'
    return
  }
  if (lucky.eggOrder && !lucky.free) {
    lucky.pane = 'placed'
    return
  }
  if (lucky.spin?.live) {
    lucky.pane = 'win'
    return
  }
  if (lucky.offerSpin) lucky.pane = 'wheel'
}

export function chipText(): string {
  if (lucky.free) return `Free order ${lucky.free.stamps}/${lucky.free.needed}`
  if (lucky.spin?.live) return `${lucky.percent}% OFF · ${lucky.clock}`
  if (lucky.offerSpin) return `${lucky.percent}% OFF`
  return ''
}

export function showChip(): boolean {
  return Boolean(chipText()) && lucky.pane === ''
}
