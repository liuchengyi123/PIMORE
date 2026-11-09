<template>
  <div class="fn-page page" :class="{ desktop: isDesktop }" data-figma="M24">
    <header class="head">
      <button type="button" class="back" @click="goBack" aria-label="back"><ChevronLeft :size="22" :stroke-width="1.75" /></button>
      <div class="head-main">
        <div class="title">{{ t('chat_title') }}</div>
        <div class="sub">{{ statusLabel }}</div>
      </div>
    </header>

    <div class="chat-body">
      <aside v-show="isDesktop" class="side-pane fn-half-sheet" aria-label="context">
        <div class="side-tabs">
          <button type="button" class="side-tab" :class="{ on: sideTab === 'browse' }" @click="activateSide('browse')">{{ lab.visits }}</button>
          <button type="button" class="side-tab" :class="{ on: sideTab === 'orders' }" @click="activateSide('orders')">{{ lab.orders }}</button>
        </div>
        <div class="side-list">
          <template v-if="sideTab === 'browse'">
            <div v-if="!browseList.length" class="sheet-empty">{{ lab.noVisits }}</div>
            <div v-for="item in browseList" :key="item.sku + String(item.ts)" class="sheet-item">
              <img v-if="item.image" class="sheet-img" :src="csMediaUrl(item.image)" alt="" />
              <div class="sheet-body">
                <div class="sheet-name">{{ item.name || item.sku }}</div>
                <div class="sheet-meta">{{ item.price || item.sku }}</div>
              </div>
              <button type="button" class="sheet-btn" @click="sendBrowseItem(item)">{{ lab.send }}</button>
            </div>
          </template>
          <template v-else>
            <div v-if="ordersLoading" class="sheet-empty">…</div>
            <div v-else-if="!orderList.length" class="sheet-empty">{{ lab.noOrders }}</div>
            <div v-for="o in orderList" :key="String(o.id || o.submit_id)" class="sheet-item order-item">
              <div class="sheet-body">
                <div class="sheet-name">#{{ o.id || o.submit_id }} · {{ o.status || '—' }}</div>
                <div class="sheet-meta">{{ orderItemsText(o) || lab.noItems }}</div>
              </div>
              <button type="button" class="sheet-btn" @click="sendOrderItem(o)">{{ lab.send }}</button>
            </div>
          </template>
        </div>
      </aside>

      <div class="main-pane">
        <div ref="msgsEl" class="msgs" @scroll.passive="onScroll">
          <div v-if="!messages.length && !booting" class="fn-chat-empty">
            <div class="fn-chat-ico">💬</div>
            <div class="fn-chat-title">{{ lab.help }}</div>
            <div class="fn-chat-sub">{{ t('chat_empty') }}</div>
          </div>
          <div
            v-for="m in messages"
            :id="'m' + m.id"
            :key="m.id"
            class="bubble-row"
            :class="m.role"
          >
            <div class="bubble">
              <div class="who">{{ whoLabel(m) }}</div>
              <img
                v-if="imgOf(m)"
                class="bubble-img"
                :src="imgOf(m)"
                alt=""
                @click="previewImg(imgOf(m))"
                @load="scrollToLatest"
              />
              <div v-else-if="cartOf(m)" class="prod-card" @click="goShopCart">
                <div class="prod-body">
                  <div class="prod-name">{{ buyLab.cart }}</div>
                  <div class="prod-price">{{ cartOf(m)!.n ? cartOf(m)!.n : '' }}</div>
                  <div class="prod-tip">{{ buyLab.buy }}</div>
                </div>
              </div>
              <div v-else-if="prodOf(m)" class="prod-card" @click="openProduct(prodOf(m))">
                <img v-if="prodOf(m)!.image" class="prod-img" :src="csMediaUrl(prodOf(m)!.image || '')" alt="" />
                <div class="prod-body">
                  <div class="prod-name">{{ prodOf(m)!.name || prodOf(m)!.sku }}</div>
                  <div class="prod-price">{{ prodOf(m)!.price }}</div>
                  <div v-if="prodOf(m)!.option" class="prod-opt">{{ prodOf(m)!.option }}</div>
                  <div class="prod-tip">{{ lab.prodTip }}</div>
                </div>
              </div>
              <div v-else-if="orderOf(m)" class="order-card" @click="openOrderPreview(orderOf(m))">
                <div class="order-title">{{ lab.orderCard }} #{{ orderOf(m)!.id || orderOf(m)!.submit_id }}</div>
                <div class="order-status">{{ lab.status }}: {{ orderOf(m)!.status || '—' }}</div>
                <div v-if="orderItemsText(orderOf(m))" class="order-items">{{ orderItemsText(orderOf(m)) }}</div>
                <div v-if="orderOf(m)!.tracking" class="order-track">{{ orderOf(m)!.tracking }}</div>
                <div class="prod-tip">{{ lab.orderTip }}</div>
              </div>
              <div v-else class="body">{{ m.body }}</div>
            </div>
          </div>
          <div v-if="typingHint" class="typing-row">
            <span class="typing">{{ typingHint }}</span>
          </div>
          <div id="m-end" class="tail" />
        </div>

        <div v-if="entryOffer && entryOffer.sku" class="offer-bar">
          <img v-if="entryOffer.image" class="offer-img" :src="csMediaUrl(entryOffer.image)" alt="" />
          <div class="offer-body">
            <div class="offer-name">{{ entryOffer.name || entryOffer.sku }}</div>
            <div class="offer-meta">{{ entryOffer.price || entryOffer.sku }}</div>
          </div>
          <button type="button" class="offer-send" @click="sendEntryProduct">{{ lab.send }}</button>
          <button type="button" class="offer-x" @click="dismissEntry">×</button>
        </div>

        <div class="composer">
          <div v-if="emojiOpen" class="emoji-panel">
            <button
              v-for="e in stickers"
              :key="e"
              type="button"
              class="emoji"
              @click="insertEmoji(e)"
            >{{ e }}</button>
          </div>

          <div v-if="!isDesktop" class="tool-row">
            <button type="button" class="tool" @click="openBrowseSheet">
              <ImagePlus :size="18" :stroke-width="1.7" class="tool-ico" />
              <span class="tool-lab">{{ lab.visits }}</span>
            </button>
            <button type="button" class="tool" @click="openOrderSheet">
              <ImagePlus :size="18" :stroke-width="1.7" class="tool-ico" />
              <span class="tool-lab">{{ lab.orders }}</span>
            </button>
          </div>

          <div class="composer-row">
            <button type="button" class="emoji-btn" :class="{ on: emojiOpen }" @click.stop="toggleEmoji" aria-label="emoji"><Smile :size="20" :stroke-width="1.7" /></button>
            <button type="button" class="emoji-btn" @click.stop="pickImage" aria-label="image"><ImagePlus :size="20" :stroke-width="1.7" /></button>
            <input
              class="inp"
              v-model="draft"
              :placeholder="t('chat_placeholder')"
              @keydown.enter.prevent="send"
              @focus="emojiOpen = false"
            />
            <button type="button" class="send" :class="{ on: canSend }" @click="send">{{ t('chat_send') }}</button>
          </div>
          <input ref="fileInput" type="file" accept="image/*" class="file-hidden" @change="onFilePicked" />
        </div>
      </div>
    </div>

    <div v-if="!isDesktop && sheet === 'browse'" class="sheet-mask" @click="sheet = ''">
      <div class="sheet" @click.stop>
        <div class="sheet-head">
          <div class="sheet-title">{{ lab.visits }}</div>
          <button type="button" class="sheet-close" @click="sheet = ''">×</button>
        </div>
        <div class="sheet-list">
          <div v-if="!browseList.length" class="sheet-empty">{{ lab.noVisits }}</div>
          <div v-for="item in browseList" :key="item.sku + String(item.ts)" class="sheet-item">
            <img v-if="item.image" class="sheet-img" :src="csMediaUrl(item.image)" alt="" />
            <div class="sheet-body">
              <div class="sheet-name">{{ item.name || item.sku }}</div>
              <div class="sheet-meta">{{ item.price || item.sku }}</div>
            </div>
            <button type="button" class="sheet-btn" @click="sendBrowseItem(item)">{{ lab.send }}</button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="!isDesktop && sheet === 'orders'" class="sheet-mask" @click="sheet = ''">
      <div class="sheet" @click.stop>
        <div class="sheet-head">
          <div class="sheet-title">{{ lab.orders }}</div>
          <button type="button" class="sheet-close" @click="sheet = ''">×</button>
        </div>
        <div class="sheet-list">
          <div v-if="ordersLoading" class="sheet-empty">…</div>
          <div v-else-if="!orderList.length" class="sheet-empty">{{ lab.noOrders }}</div>
          <div v-for="o in orderList" :key="String(o.id || o.submit_id)" class="sheet-item order-item">
            <div class="sheet-body">
              <div class="sheet-name">#{{ o.id || o.submit_id }} · {{ o.status || '—' }}</div>
              <div class="sheet-meta">{{ orderItemsText(o) || lab.noItems }}</div>
            </div>
            <button type="button" class="sheet-btn" @click="sendOrderItem(o)">{{ lab.send }}</button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="previewSrc" class="preview-mask" @click="previewSrc = ''">
      <img :src="previewSrc" class="preview-img" alt="" @click.stop />
    </div>

    <div v-if="prodPreview" class="detail-mask" @click="closeProdPreview">
      <div class="detail-sheet" @click.stop>
        <div class="detail-head">
          <div class="detail-title">{{ lab.prodDetail }}</div>
          <button type="button" class="sheet-close" @click="closeProdPreview">×</button>
        </div>
        <div class="detail-body">
          <img
            v-if="prodPreview.image"
            class="detail-img"
            :src="csMediaUrl(prodPreview.image || '')"
            alt=""
          />
          <div class="detail-name">{{ prodPreview.name || prodPreview.sku }}</div>
          <div v-if="shownPrice" class="detail-price">{{ shownPrice }}</div>
          <div v-if="offerChoices.length" class="detail-offers">
            <button
              v-for="o in offerChoices"
              :key="o.id"
              type="button"
              class="offer-chip"
              :class="{ on: pickedOffer === o.id }"
              @click="selectOffer(o)"
            >{{ o.label }}</button>
          </div>
          <div v-else-if="prodPreview.option" class="detail-opt">{{ lab.option }}: {{ prodPreview.option }}</div>
          <div v-if="prodPreview.sku" class="detail-sku">SKU: {{ prodPreview.sku }}</div>
          <div v-if="addError" class="detail-sku">{{ addError }}</div>
        </div>
        <div class="detail-actions">
          <button type="button" class="detail-btn ghost" :disabled="adding" @click="addPreviewToCart">{{ adding ? '…' : (addedOk ? buyLab.added : buyLab.add) }}</button>
          <button type="button" class="detail-btn primary" @click="goShopCart">{{ buyLab.buy }}</button>
        </div>
      </div>
    </div>

    <div v-if="orderPreview" class="detail-mask" @click="closeOrderPreview">
      <div class="detail-sheet" @click.stop>
        <div class="detail-head">
          <div class="detail-title">{{ lab.orderDetail }}</div>
          <button type="button" class="sheet-close" @click="closeOrderPreview">×</button>
        </div>
        <div class="detail-body">
          <div class="detail-name">{{ lab.orderCard }} #{{ orderPreview.id || orderPreview.submit_id }}</div>
          <div class="detail-opt">{{ lab.status }}: {{ orderPreview.status || '—' }}</div>
          <div v-if="orderItemsText(orderPreview)" class="detail-opt">{{ orderItemsText(orderPreview) }}</div>
          <div v-if="orderPreview.tracking" class="detail-sku">{{ orderPreview.tracking }}</div>
          <div v-if="orderPreview.due_cents != null" class="detail-price">
            {{ formatOrderMoney(orderPreview) }}
          </div>
          <div v-if="orderPreview.created_at" class="detail-sku">{{ orderPreview.created_at }}</div>
        </div>
        <div class="detail-actions">
          <button type="button" class="detail-btn ghost" @click="closeOrderPreview">{{ lab.close }}</button>
          <button
            v-if="orderPreview.id || orderPreview.submit_id"
            type="button"
            class="detail-btn primary"
            @click="goOrderFromPreview"
          >{{ lab.viewOrder }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { ChevronLeft, ImagePlus, Smile, Package, SendHorizontal } from 'lucide-vue-next'
import { useRoute, useRouter } from 'vue-router'
import { shopOrigin } from '@/api/config'
import { addToCartServer } from '@/api/cartApi'
import { useCart } from '@/composables/cart'
import { useI18n } from '@/composables/i18n'
import { loadBrowseHistory, trackBrowse, type BrowseItem } from '@/composables/browseHistory'
import {
  openSupportChat,
  sendSupportMessage,
  pollSupportMessages,
  fetchCsStickers,
  uploadCsImage,
  sendSupportImage,
  parseImgBody,
  parseProductBody,
  parseCartBody,
  parseOrderBody,
  fetchVisitorProduct,
  buildProductBody,
  buildOrderBody,
  fetchCsOrders,
  csMediaUrl,
  type CsMessage,
  type CsProductCtx,
  type CsOrderCard,
} from '@/api/supportApi'

const { t, lang } = useI18n()
const route = useRoute()
const router = useRouter()

const roomId = ref('')
const messages = ref<CsMessage[]>([])
const draft = ref('')
const booting = ref(true)
const online = ref(false)
const productCard = ref<CsProductCtx | null>(null)
const entryOffer = ref<CsProductCtx | null>(null)
const sending = ref(false)
const emojiOpen = ref(false)
const stickers = ref<string[]>(['👍', '❤️', '😊', '🙏', '😂', '🔥', '🎉', '😅', '🤝', '✨'])
let pollAlive = false
let lastId = 0
const typingHint = ref('')
const sheet = ref<'' | 'browse' | 'orders'>('')
const browseList = ref<BrowseItem[]>([])
const orderList = ref<CsOrderCard[]>([])
const ordersLoading = ref(false)
const msgsEl = ref<HTMLElement | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const previewSrc = ref('')
const prodPreview = ref<ReturnType<typeof parseProductBody>>(null)
const offerChoices = ref<{ id: string; label: string; price: string; image: string }[]>([])
const pickedOffer = ref('')
const adding = ref(false)
const addedOk = ref(false)
const addError = ref('')
const buyLab = computed(() => {
  const code = String(lang.value || '')
  if (code.startsWith('ja')) return { add: 'カートに入れる', buy: '注文へ', cart: 'カートの商品を注文', added: '追加しました', fail: '追加できませんでした' }
  if (code.startsWith('en')) return { add: 'Add to cart', buy: 'Go to cart', cart: 'Your cart is ready', added: 'Added to cart', fail: 'Could not add this item' }
  return { add: '加购', buy: '去下单', cart: '购物车可以下单了', added: '已加入购物车', fail: '没加进去，换个规格再试' }
})
const shownPrice = computed(() => {
  const hit = offerChoices.value.find((o) => o.id === pickedOffer.value)
  return hit?.price || prodPreview.value?.price || ''
})
const orderPreview = ref<CsOrderCard | null>(null)
const isDesktop = ref(false)
const sideTab = ref<'browse' | 'orders'>('browse')
let mq: MediaQueryList | null = null
let stickBottom = true

function syncDesktop() {
  isDesktop.value = !!(mq && mq.matches)
  if (isDesktop.value) {
    browseList.value = loadBrowseHistory().slice(0, 20)
    sheet.value = ''
  }
}

async function activateSide(tab: 'browse' | 'orders') {
  sideTab.value = tab
  if (tab === 'browse') {
    browseList.value = loadBrowseHistory().slice(0, 20)
  } else {
    await refreshOrders()
  }
}

async function refreshOrders() {
  if (!roomId.value) return
  ordersLoading.value = true
  try {
    const res = await fetchCsOrders(roomId.value)
    orderList.value = ((res.data as any)?.orders || []) as CsOrderCard[]
  } catch {
    orderList.value = []
  } finally {
    ordersLoading.value = false
  }
}


const lab = computed(() =>
  lang.value === 'en'
    ? {
        visits: 'Visits',
        orders: 'Orders',
        send: 'Send',
        noVisits: 'No recent views',
        noOrders: 'No orders yet',
        noItems: 'Items n/a',
        orderCard: 'Order',
        status: 'Status',
        prodTip: 'Tap to preview',
        orderTip: 'Tap to preview order',
        prodDetail: 'Product',
        orderDetail: 'Order',
        option: 'Option',
        close: 'Close',
        goBuy: 'Buy now',
        viewOrder: 'View order',
        help: 'How can we help?',
      }
    : {
        visits: '访问纪录',
        orders: '订单纪录',
        send: '发送',
        noVisits: '暂无浏览足迹',
        noOrders: '暂无订单（登录后可同步）',
        noItems: '商品明细暂无',
        orderCard: '订单',
        status: '状态',
        prodTip: '点击查看商品',
        orderTip: '点击查看订单',
        prodDetail: '商品详情',
        orderDetail: '订单详情',
        option: '规格',
        close: '关闭',
        goBuy: '去下单',
        viewOrder: '查看订单',
        help: '需要什么帮助？',
      },
)

const canSend = computed(() => !!draft.value.trim() && !!roomId.value && !sending.value)
const statusLabel = computed(() => {
  if (booting.value) return t('chat_connecting')
  return online.value ? t('chat_online') : t('chat_reconnecting')
})

function whoLabel(m: CsMessage) {
  if (m.role === 'user') return t('chat_you')
  if (m.role === 'staff') {
    let name = String(m.staff_user || '').trim()
    name = name
      .replace(/^AI\s*[.\-·]?\s*/i, '')
      .replace(/\s*AI$/i, '')
      .replace(/\s+AI\b/gi, '')
      .trim()
    if (!name || /^AI$/i.test(name)) name = 'Harbor'
    return name
  }
  return t('chat_system')
}

function imgOf(m: CsMessage) {
  const path = parseImgBody(m?.body || '')
  return path ? csMediaUrl(path) : ''
}

function previewImg(src: string) {
  if (!src) return
  previewSrc.value = src
}

function prodOf(m: CsMessage) {
  return parseProductBody(m?.body || '')
}

function orderOf(m: CsMessage) {
  return parseOrderBody(m?.body || '')
}

function orderItemsText(o: CsOrderCard | null) {
  if (!o?.items?.length) return ''
  return o.items.join(' · ')
}

function pickImage() {
  if (!roomId.value || sending.value) return
  emojiOpen.value = false
  fileInput.value?.click()
}

async function onFilePicked(ev: Event) {
  const input = ev.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file || !roomId.value || sending.value) return
  sending.value = true
  try {
    const up = await uploadCsImage(roomId.value, file)
    if (!up.ok || !up.url) {
      alert(t('chat_fail'))
      return
    }
    const res = await sendSupportImage(roomId.value, up.url, productCard.value)
    const data = res.data as any
    if (data?.messages?.length) mergeMessages(data.messages)
    else if (data?.message) mergeMessages([data.message])
    else alert(t('chat_fail'))
  } catch {
    alert(t('chat_fail'))
  } finally {
    sending.value = false
  }
}

function cartOf(m: CsMessage) {
  return parseCartBody(m?.body || '')
}

function goShopCart() {
  const origin = shopOrigin().replace(/\/$/, '')
  window.location.href = origin + '/cart'
}

function selectOffer(o: { id: string; label: string; price: string; image: string }) {
  pickedOffer.value = o.id
  if (!prodPreview.value) return
  prodPreview.value = {
    ...prodPreview.value,
    option: o.label,
    price: o.price || prodPreview.value.price,
    image: o.image || prodPreview.value.image,
    offer_id: o.id,
  }
}

async function openProduct(p: ReturnType<typeof parseProductBody>) {
  if (!p?.sku && !p?.name) return
  prodPreview.value = p
  orderPreview.value = null
  addedOk.value = false
  addError.value = ''
  offerChoices.value = []
  pickedOffer.value = String(p?.offer_id || p?.option_key || '')
  if (!p?.sku) return
  try {
    const res = await fetchVisitorProduct(p.sku, String(lang.value || 'en'))
    const product = (res.data as { product?: { name?: string; price?: string; image?: string; offers?: { id: string; label: string; price: string; image: string }[] } })?.product
    if (!product || prodPreview.value?.sku !== p.sku) return
    prodPreview.value = {
      ...prodPreview.value,
      name: product.name || prodPreview.value.name,
      price: product.price || prodPreview.value.price,
      image: product.image || prodPreview.value.image,
    }
    offerChoices.value = product.offers || []
    const current = offerChoices.value.find((o) => o.id === pickedOffer.value) || offerChoices.value[0]
    if (current) selectOffer(current)
  } catch {
    /* keep the card already shown */
  }
}

async function addPreviewToCart() {
  const p = prodPreview.value
  if (!p?.sku || adding.value) return
  adding.value = true
  addError.value = ''
  try {
    const snap = await addToCartServer({ sku: p.sku, offer: pickedOffer.value, qty: 1 })
    useCart().adopt(snap)
    addedOk.value = true
  } catch {
    addedOk.value = false
    addError.value = buyLab.value.fail
  } finally {
    adding.value = false
  }
}

function closeProdPreview() {
  prodPreview.value = null
}

function openOrderPreview(o: CsOrderCard | null) {
  if (!o) return
  orderPreview.value = o
  prodPreview.value = null
}

function closeOrderPreview() {
  orderPreview.value = null
}

function goOrderFromPreview() {
  const o = orderPreview.value
  if (!o) return
  const id = String(o.id || o.submit_id || '').trim()
  closeOrderPreview()
  if (!id) return
  router.push({ path: `/orders/${encodeURIComponent(id)}` })
}

function formatOrderMoney(o: CsOrderCard) {
  if (o.due_cents == null) return ''
  const cur = (o.currency || 'USD').toUpperCase()
  const n = Number(o.due_cents) / 100
  try {
    return new Intl.NumberFormat(undefined, { style: 'currency', currency: cur }).format(n)
  } catch {
    return `${cur} ${n.toFixed(2)}`
  }
}

function toggleEmoji() {
  emojiOpen.value = !emojiOpen.value
}

function insertEmoji(e: string) {
  draft.value = (draft.value || '') + e
}

async function loadStickers() {
  try {
    const res = await fetchCsStickers()
    const items = (res.data as any)?.items || []
    if (items.length) stickers.value = items.map((x: any) => x.emoji).filter(Boolean)
  } catch {
    /* keep fallback */
  }
}

function mergeMessages(list: CsMessage[]) {
  if (!list?.length) return
  const map = new Map(messages.value.map((m) => [m.id, m]))
  for (const m of list) map.set(m.id, m)
  messages.value = Array.from(map.values()).sort((a, b) => a.id - b.id)
  if (messages.value.length) lastId = messages.value[messages.value.length - 1].id
  scrollToLatest()
}

function onScroll() {
  const el = msgsEl.value
  if (!el) return
  stickBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 80
}

function scrollToLatest() {
  nextTick(() => {
    const el = msgsEl.value
    if (!el) return
    if (!stickBottom && messages.value.length > 1) return
    el.scrollTop = el.scrollHeight
    ;[50, 150, 350].forEach((ms) =>
      setTimeout(() => {
        if (msgsEl.value) msgsEl.value.scrollTop = msgsEl.value.scrollHeight
      }, ms),
    )
  })
}

async function boot(ctx: CsProductCtx | null) {
  booting.value = true
  try {
    const res = await openSupportChat(ctx)
    if (res.statusCode >= 400 || !(res.data as any)?.ok) {
      alert(t('chat_fail'))
      return
    }
    const data = res.data as any
    roomId.value = data.room.id
    productCard.value = data.room.current?.sku ? data.room.current : ctx
    mergeMessages(data.messages || [])
    online.value = true
    startPoll()
    loadStickers()
  } catch {
    alert(t('chat_fail'))
  } finally {
    booting.value = false
    nextTick(() => scrollToLatest())
  }
}

function applyTyping(data: any) {
  const tp = data?.typing
  if (tp && tp.active && (tp.side === 'staff' || tp.side === 'ai')) {
    typingHint.value = t('chat_typing')
  } else {
    typingHint.value = ''
  }
}

async function startPoll() {
  if (pollAlive) return
  pollAlive = true
  while (pollAlive && roomId.value) {
    try {
      const res = await pollSupportMessages(roomId.value, lastId, 18)
      online.value = res.statusCode < 400
      const data = res.data as any
      if (data?.messages?.length) {
        mergeMessages(data.messages)
        typingHint.value = ''
      }
      applyTyping(data)
      if (data?.messages?.length) typingHint.value = ''
      if (data?.room?.current?.sku) productCard.value = data.room.current
    } catch {
      online.value = false
      await new Promise((r) => setTimeout(r, 1200))
    }
  }
}

async function sendRaw(body: string) {
  if (!body || !roomId.value || sending.value) return false
  sending.value = true
  try {
    const res = await sendSupportMessage(roomId.value, body, productCard.value)
    const data = res.data as any
    if (data?.messages?.length) mergeMessages(data.messages)
    else if (data?.message) mergeMessages([data.message])
    else {
      alert(t('chat_fail'))
      return false
    }
    return true
  } catch {
    alert(t('chat_fail'))
    return false
  } finally {
    sending.value = false
  }
}

async function send() {
  const text = draft.value.trim()
  if (!text || !roomId.value || sending.value) return
  draft.value = ''
  const ok = await sendRaw(text)
  if (!ok) draft.value = text
}

function openBrowseSheet() {
  browseList.value = loadBrowseHistory().slice(0, 20)
  sheet.value = 'browse'
  emojiOpen.value = false
}

async function openOrderSheet() {
  sheet.value = 'orders'
  emojiOpen.value = false
  await refreshOrders()
}

async function sendBrowseItem(item: BrowseItem) {
  const body = buildProductBody(item)
  sheet.value = ''
  await sendRaw(body)
}

async function sendOrderItem(o: CsOrderCard) {
  const body = buildOrderBody(o)
  sheet.value = ''
  await sendRaw(body)
}

async function sendEntryProduct() {
  if (!entryOffer.value?.sku) return
  const body = buildProductBody(entryOffer.value)
  const ok = await sendRaw(body)
  if (ok) entryOffer.value = null
}

function dismissEntry() {
  entryOffer.value = null
}

function goBack() {
  if (window.history.length > 1) router.back()
  else router.push('/home')
}

function readQueryCtx(): CsProductCtx | null {
  const q = route.query
  const sku = q.sku ? String(q.sku) : ''
  if (!sku) return null
  return {
    sku: decodeURIComponent(sku),
    name: q.name ? decodeURIComponent(String(q.name)) : decodeURIComponent(sku),
    image: q.image ? decodeURIComponent(String(q.image)) : '',
    price: q.price ? decodeURIComponent(String(q.price)) : '',
  }
}

onMounted(() => {
  mq = window.matchMedia('(min-width: 960px)')
  syncDesktop()
  const onMq = () => syncDesktop()
  if (mq.addEventListener) mq.addEventListener('change', onMq)
  else mq.addListener(onMq)
  ;(window as any).__harborCsMq = onMq

  const ctx = readQueryCtx()
  productCard.value = ctx
  entryOffer.value = ctx && ctx.sku ? { ...ctx } : null
  if (ctx?.sku) trackBrowse(ctx)
  browseList.value = loadBrowseHistory().slice(0, 20)
  boot(ctx).then(async () => {
    try {
      const pre = sessionStorage.getItem('harbor_cs_prefill_order')
      if (pre) {
        sessionStorage.removeItem('harbor_cs_prefill_order')
        await sendRaw(pre)
      }
    } catch { /* ignore */ }
    if (isDesktop.value) await refreshOrders()
  })
})

watch(isDesktop, async (v) => {
  if (v) {
    browseList.value = loadBrowseHistory().slice(0, 20)
    sheet.value = ''
    if (roomId.value) await refreshOrders()
  }
})

onUnmounted(() => {
  pollAlive = false
  const onMq = (window as any).__harborCsMq
  if (mq && onMq) {
    if (mq.removeEventListener) mq.removeEventListener('change', onMq)
    else mq.removeListener(onMq)
  }
})
</script>

<style lang="scss" scoped>
@import '@/styles/theme.scss';

.page {
  min-height: 100vh;
  height: 100dvh;
  background: $hb-paper;
  display: flex;
  flex-direction: column;
  padding-top: calc(10px + env(safe-area-inset-top));
  overflow: hidden;
}
.head {
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 0 16px 10px;
  flex: 0 0 auto;
}
.back { width: 40px; height: 40px; border: 0; border-radius: 14px; background: #fff; color: #121816; display: inline-flex; align-items: center; justify-content: center; box-shadow: 0 4px 16px rgba(18,24,22,0.06); cursor: pointer; }
.head-main { flex: 1; min-width: 0; }
.title { font-size: 20px; font-weight: 720; color: $hb-ink; }
.sub { font-size: 12px; color: $hb-muted; margin-top: 2px; }

.chat-body {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.side-pane { display: none; }
.main-pane {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.msgs {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 8px 16px 12px;
  -webkit-overflow-scrolling: touch;
}
.empty { text-align: center; color: $hb-muted; padding: 40px 8px; font-size: 13px; }
.bubble-row { display: flex; margin-bottom: 10px; }
.bubble-row.user { justify-content: flex-end; }
.bubble-row.staff, .bubble-row.system { justify-content: flex-start; }
.bubble {
  max-width: 78%;
  border-radius: 16px;
  padding: 10px 12px;
  background: $hb-white;
  box-shadow: $hb-shadow-soft;
}
.bubble-row.user .bubble { background: $hb-forest; }
.bubble-row.user .who, .bubble-row.user .body { color: $hb-white; }
.bubble-row.staff .bubble { background: $hb-coral-soft; border: 1px solid rgba(224, 82, 46, 0.12); }
.bubble-row.system .bubble { background: transparent; box-shadow: none; padding: 4px 0; }
.who { font-size: 11px; color: $hb-muted; margin-bottom: 4px; font-weight: 650; }
.body { font-size: 14px; line-height: 1.45; color: $hb-ink; white-space: pre-wrap; word-break: break-word; }
.bubble-img { display: block; max-width: 220px; width: 220px; border-radius: 10px; margin-top: 4px; cursor: zoom-in; }
.tail { height: 8px; }
.typing-row { padding: 0 4px 8px; }
.typing { color: #6B7280; font-size: 12px; /* C02 typing */
 font-size: 12px; color: $hb-muted; font-style: italic; }

.offer-bar {
  background: #fff !important;
  border: 1px solid #E8E4DC !important;
  border-radius: 14px !important;

  margin: 0 12px 8px;
  background: $hb-white;
  border-radius: 14px;
  padding: 8px 10px;
  display: flex;
  gap: 8px;
  align-items: center;
  box-shadow: $hb-shadow-soft;
  border: 1px solid $hb-soft;
  flex: 0 0 auto;
}
.offer-img { width: 44px; height: 44px; border-radius: 10px; background: $hb-paper; object-fit: cover; flex: 0 0 auto; }
.offer-body { min-width: 0; flex: 1; }
.offer-name {
  font-size: 12px; font-weight: 680; color: $hb-ink;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.offer-meta { font-size: 11px; color: $hb-muted; margin-top: 2px; }
.offer-send {
  border: 0; padding: 6px 12px; border-radius: 999px; background: $hb-coral; color: #fff;
  font-size: 12px; font-weight: 700; flex: 0 0 auto; cursor: pointer;
}
.offer-x {
  border: 0; width: 28px; height: 28px; border-radius: 10px; text-align: center; line-height: 28px;
  color: $hb-muted; font-size: 18px; flex: 0 0 auto; background: transparent; cursor: pointer;
}

.tool-row { display: flex; gap: 8px; padding: 0 2px 8px; }
.tool {
  display: flex; align-items: center; gap: 4px;
  padding: 6px 10px; border-radius: 999px; background: $hb-paper;
  border: 1px solid $hb-line; cursor: pointer;
}
.tool-ico { font-size: 13px; }
.tool-lab { font-size: 12px; color: $hb-ink; font-weight: 650; }

.emoji-panel {
  display: flex; flex-wrap: wrap; gap: 4px; padding: 8px 4px 10px;
  background: $hb-white; border-radius: 14px; margin-bottom: 8px;
  max-height: 160px; overflow: auto;
}
.emoji-btn {
  border: 0; width: 40px; height: 40px; border-radius: 12px; background: $hb-white;
  text-align: center; line-height: 40px; font-size: 22px;
  box-shadow: $hb-shadow-soft; flex: 0 0 auto; cursor: pointer;
}
.emoji-btn.on { outline: 2px solid rgba(15, 90, 60, 0.25); }
.emoji { border: 0; background: transparent; display: inline-block; font-size: 22px; padding: 4px 8px; cursor: pointer; }
.composer-row { display: flex; gap: 10px; align-items: center; width: 100%; }
.composer {
  display: flex; flex-direction: column; gap: 0; align-items: stretch;
  padding: 10px 16px calc(10px + env(safe-area-inset-bottom));
  background: rgba(255, 255, 255, 0.94);
  border-top: 1px solid $hb-line;
  backdrop-filter: blur(12px);
  flex: 0 0 auto;
}
.inp {
  flex: 1; border: 0; outline: none; background: $hb-paper; border-radius: 14px; padding: 12px 14px; font-size: 14px;
}
.send {
  border: 0; min-width: 64px; height: 44px; border-radius: 14px; background: $hb-line; color: $hb-muted;
  display: flex; align-items: center; justify-content: center; font-weight: 720; font-size: 14px; cursor: pointer;
  &.on { background: $hb-coral; color: $hb-white; }
}
.file-hidden { display: none; }

.prod-card {
  display: flex; gap: 10px; align-items: center; max-width: 260px;
  background: rgba(255,255,255,0.7); border-radius: 12px; padding: 8px;
  border: 1px solid rgba(0,0,0,0.06); cursor: pointer;
}
.prod-img { width: 64px; height: 64px; border-radius: 10px; flex: 0 0 auto; background: $hb-paper; object-fit: cover; }
.prod-body { min-width: 0; flex: 1; display: flex; flex-direction: column; gap: 2px; }
.prod-name { font-size: 13px; font-weight: 650; color: $hb-ink; }
.prod-price { font-size: 13px; color: $hb-ink; font-weight: 700; }
.prod-opt { font-size: 11px; color: $hb-muted; }
.prod-tip { font-size: 11px; color: $hb-forest; margin-top: 2px; line-height: 1.3; }

.order-card {
  display: flex; flex-direction: column; gap: 3px; min-width: 180px; max-width: 260px;
  background: rgba(255,255,255,0.75); border-radius: 12px; padding: 8px 10px;
  border: 1px solid rgba(0,0,0,0.06);
}
.order-title { font-size: 13px; font-weight: 700; color: $hb-ink; }
.order-status { font-size: 12px; color: $hb-coral; font-weight: 650; }
.order-items { font-size: 12px; color: $hb-ink; line-height: 1.35; }
.order-track { font-size: 11px; color: $hb-muted; }

.sheet-mask {
  position: fixed; inset: 0; background: rgba(0,0,0,0.35); z-index: 50;
  display: flex; align-items: flex-end; justify-content: center;
}
.sheet {
  width: 100%; max-width: 560px; max-height: 58vh;
  background: $hb-white; border-radius: 22px 22px 0 0;
  padding: 12px 14px calc(14px + env(safe-area-inset-bottom));
  box-shadow: 0 -8px 30px rgba(0,0,0,0.12);
}
.sheet-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.sheet-title { font-size: 16px; font-weight: 720; color: $hb-ink; }
.sheet-close { border: 0; background: transparent; font-size: 22px; color: $hb-muted; padding: 4px 8px; cursor: pointer; }
.sheet-list { max-height: 46vh; overflow-y: auto; }
.sheet-empty { text-align: center; color: $hb-muted; padding: 28px 8px; font-size: 13px; }
.sheet-item {
  display: flex; gap: 10px; align-items: center;
  padding: 10px 4px; border-bottom: 1px solid $hb-line;
}
.sheet-img { width: 48px; height: 48px; border-radius: 10px; background: $hb-paper; flex: 0 0 auto; object-fit: cover; }
.sheet-body { min-width: 0; flex: 1; }
.sheet-name {
  font-size: 13px; font-weight: 650; color: $hb-ink;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.sheet-meta { font-size: 11px; color: $hb-muted; margin-top: 2px; }
.sheet-btn {
  border: 0; padding: 6px 12px; border-radius: 999px; background: $hb-forest; color: #fff;
  font-size: 12px; font-weight: 700; flex: 0 0 auto; cursor: pointer;
}
.order-item .sheet-btn { background: $hb-coral; }

.preview-mask {
  position: fixed; inset: 0; z-index: 80; background: rgba(0,0,0,0.85);
  display: flex; align-items: center; justify-content: center; padding: 16px;
}
.preview-img { max-width: 100%; max-height: 90vh; border-radius: 8px; }

.order-card { cursor: pointer; }

.detail-mask {
  position: fixed; inset: 0; z-index: 90; background: rgba(0,0,0,0.45);
  display: flex; align-items: flex-end; justify-content: center;
  padding: 16px; padding-bottom: calc(16px + env(safe-area-inset-bottom));
}
@media (min-width: 960px) {
  .detail-mask { align-items: center; }
}
.detail-mask {
  background: rgba(15, 39, 68, 0.4) !important;
}
.detail-sheet {
  border-radius: 18px !important;
  box-shadow: 0 16px 40px rgba(15, 39, 68, 0.25) !important;
  /* fn-c03-popup */

  width: 100%; max-width: 640px; max-height: 92vh;
  display: flex; flex-direction: column;
  background: $hb-white; border-radius: 18px;
  box-shadow: 0 16px 48px rgba(0,0,0,0.18);
  padding: 14px 16px 16px;
}
.detail-head {
  display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;
}
.detail-title { font-size: 16px; font-weight: 720; color: $hb-ink; }
.detail-body { display: flex; flex-direction: column; gap: 8px; overflow: auto; }
.detail-img {
  width: 100%; aspect-ratio: 1/1; max-height: 420px; object-fit: cover;
  border-radius: 14px; background: $hb-paper;
}
.detail-offers { display: flex; flex-wrap: wrap; gap: 8px; }
.offer-chip {
  border: 1px solid #d7e0da; background: #f7faf8; color: $hb-ink;
  border-radius: 999px; padding: 8px 12px; font-size: 13px; cursor: pointer;
}
.offer-chip.on { border-color: #2F6BFF; background: #2F6BFF; color: #fff; }
.detail-name { font-size: 16px; font-weight: 720; color: $hb-ink; line-height: 1.35; }
.detail-price { font-size: 18px; font-weight: 780; color: $hb-ink; }
.detail-opt { font-size: 13px; color: $hb-ink; }
.detail-sku { font-size: 12px; color: $hb-muted; }
.detail-actions {
  display: flex; gap: 10px; margin-top: 14px;
}
.detail-btn {
  flex: 1; border: 0; height: 44px; border-radius: 14px;
  font-weight: 720; font-size: 14px; cursor: pointer;
}
.detail-btn.ghost { background: $hb-paper; color: $hb-ink; }
.detail-btn.primary { background: $hb-coral; color: #fff; }

.side-tabs { display: flex; gap: 6px; padding: 0 0 10px; }
.side-tab {
  flex: 1; border: 0; border-radius: 999px; padding: 8px 10px;
  background: $hb-paper; color: $hb-muted; font-weight: 700; font-size: 13px; cursor: pointer;
}
.side-tab.on { background: $hb-forest; color: #fff; }
.side-list { flex: 1; min-height: 0; overflow-y: auto; }

/* —— PC / 宽屏双栏 —— */
@media (min-width: 960px) {
  .page.desktop {
    max-width: 1120px;
    margin: 0 auto;
    padding: 16px 20px 20px;
    height: 100dvh;
    background: linear-gradient(180deg, #eef2ef 0%, $hb-paper 40%);
  }
  .page.desktop .head {
    padding: 0 4px 14px;
  }
  .page.desktop .title { font-size: 22px; }
  .chat-body {
    flex-direction: row;
    gap: 14px;
    min-height: 0;
    height: calc(100dvh - 72px);
  }
  .side-pane {
    display: flex;
    flex-direction: column;
    width: 320px;
    flex: 0 0 320px;
    background: $hb-white;
    border-radius: 18px;
    box-shadow: $hb-shadow-soft;
    padding: 14px;
    min-height: 0;
  }
  .main-pane {
    background: $hb-white;
    border-radius: 18px;
    box-shadow: $hb-shadow-soft;
    overflow: hidden;
  }
  .msgs { padding: 16px 20px; }
  .bubble { max-width: 62%; }
  .composer {
    padding: 12px 16px 14px;
    border-radius: 0 0 18px 18px;
  }
  .offer-bar { margin: 0 16px 10px; }
  .sheet-list { max-height: none; }
}
.fn-chat-empty { text-align: center; padding: 60px 32px; }
.fn-chat-ico {
  width: 64px; height: 64px; margin: 0 auto 14px; border-radius: 20px; background: #FFF1EC;
  display: flex; align-items: center; justify-content: center; font-size: 24px;
}
.fn-chat-title { font-weight: 700; color: #1C2430; font-size: 17px; }
.fn-chat-sub { margin-top: 8px; font-size: 12px; color: #6B7280; line-height: 1.5; }
.head { background: #fff !important; border-bottom: 1px solid #E8E4DC; }
.title { color: #1C2430 !important; }
.bubble-row.mine .bubble, .bubble.me, .mine .bubble {
  background: #F96141 !important; color: #fff !important; border-bottom-right-radius: 4px !important;
}
.bubble-row.theirs .bubble, .bubble.them, .theirs .bubble {
  background: #fff !important; border: 1px solid #E8E4DC !important; color: #1C2430 !important;
  border-bottom-left-radius: 4px !important;
}
.composer, .input-bar {
  background: #fff !important; border-top: 1px solid #E8E4DC !important;
}
.page { background: #FCFAF8 !important; }

@media (max-width: 959px) {
  .side-pane.fn-half-sheet, .side-pane.open-sheet {
    position: fixed; left: 0; right: 0; bottom: 0; top: auto;
    max-height: 62%; z-index: 50; border-radius: 20px 20px 0 0;
    box-shadow: 0 -8px 30px rgba(15,39,68,.15); background: #fff;
  }
  .detail-btn.primary, .detail-btn:not(.ghost) {
    background: #F96141 !important; color: #fff !important; border-radius: 10px;
  }
  .detail-btn.ghost {
    background: #fff !important; border: 1px solid #E8E4DC !important; color: #1C2430 !important;
  }
  .detail-price { color: #F96141 !important; font-weight: 700; font-size: 18px; }
  .prod-card, .order-card {
    background: #FCFAF8 !important; border-radius: 12px !important; border: 0 !important;
  }
}

.fn-page { --ink:#1C2430; --teal:#0E7490; --amber:#F96141; --sand:#FCFAF8; }
</style>
