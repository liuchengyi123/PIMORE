<template>
  <view class="page">
    <view class="status hb-status"><text>9:41</text><text>●●● 5G</text></view>
    <view class="head">
      <view class="back" @click="goBack">‹</view>
      <view class="head-main">
        <text class="title">Harbor</text>
        <text class="sub">App chat · no AI badge</text>
      </view>
    </view>

    <scroll-view
      class="msgs"
      scroll-y
      :scroll-top="scrollTop"
      :scroll-into-view="scrollInto"
      :scroll-with-animation="scrollAnim"
      enable-flex
    >
      <view v-if="!messages.length && !booting" class="empty">{{ t('chat_empty') }}</view>
      <view
        v-for="m in messages"
        :id="'m' + m.id"
        :key="m.id"
        class="bubble-row"
        :class="m.role"
      >
        <view class="bubble">
          <text class="who">{{ whoLabel(m) }}</text>
          <image
            v-if="imgOf(m)"
            class="bubble-img"
            :src="imgOf(m)"
            mode="widthFix"
            @click="previewImg(imgOf(m))"
            @load="scrollToLatest"
          />
          <view v-else-if="prodOf(m)" class="prod-card" @click="openProduct(prodOf(m))">
            <image v-if="prodOf(m).image" class="prod-img" :src="csMediaUrl(prodOf(m).image || '')" mode="aspectFill" />
            <view class="prod-body">
              <text class="prod-name">{{ prodOf(m).name || prodOf(m).sku }}</text>
              <text class="prod-price">{{ prodOf(m).price }}</text>
              <text v-if="prodOf(m).option" class="prod-opt">{{ prodOf(m).option }}</text>
              <text class="prod-tip">{{ lab.prodTip }}</text>
            </view>
          </view>
          <view v-else-if="orderOf(m)" class="order-card">
            <text class="order-title">{{ lab.orderCard }} #{{ orderOf(m).id || orderOf(m).submit_id }}</text>
            <text class="order-status">{{ lab.status }}: {{ orderOf(m).status || '—' }}</text>
            <text v-if="orderItemsText(orderOf(m))" class="order-items">{{ orderItemsText(orderOf(m)) }}</text>
            <text v-if="orderOf(m).tracking" class="order-track">{{ orderOf(m).tracking }}</text>
          </view>
          <text v-else class="body">{{ m.body }}</text>
        </view>
      </view>
      <view v-if="typingHint" class="typing-row">
        <text class="typing">{{ typingHint }}</text>
      </view>
      <view id="m-end" class="tail" />
    </scroll-view>

    <!-- Taobao-style optional send for product entered from PDP -->
    <view v-if="entryOffer && entryOffer.sku" class="offer-bar">
      <image v-if="entryOffer.image" class="offer-img" :src="csMediaUrl(entryOffer.image)" mode="aspectFill" />
      <view class="offer-body">
        <text class="offer-name">{{ entryOffer.name || entryOffer.sku }}</text>
        <text class="offer-meta">{{ entryOffer.price || entryOffer.sku }}</text>
      </view>
      <view class="offer-send" @click="sendEntryProduct">{{ lab.send }}</view>
      <view class="offer-x" @click="dismissEntry">×</view>
    </view>

    <view class="composer">
      <view v-if="emojiOpen" class="emoji-panel">
        <text
          v-for="e in stickers"
          :key="e"
          class="emoji"
          @click="insertEmoji(e)"
        >{{ e }}</text>
      </view>

      <view class="tool-row">
        <view class="tool" @click="openBrowseSheet">
          <text class="tool-ico">👁</text>
          <text class="tool-lab">{{ lab.visits }}</text>
        </view>
        <view class="tool" @click="openOrderSheet">
          <text class="tool-ico">📦</text>
          <text class="tool-lab">{{ lab.orders }}</text>
        </view>
      </view>

      <view class="composer-row">
        <view class="emoji-btn" :class="{ on: emojiOpen }" @click.stop="toggleEmoji">😊</view>
        <view class="emoji-btn" @click.stop="pickImage">🖼</view>
        <input
          class="inp"
          v-model="draft"
          :placeholder="t('chat_placeholder')"
          confirm-type="send"
          @confirm="send"
          @focus="emojiOpen = false"
        />
        <view class="send" :class="{ on: canSend }" @click="send">{{ t('chat_send') }}</view>
      </view>
    </view>

    <!-- Visit history sheet -->
    <view v-if="sheet === 'browse'" class="sheet-mask" @click="sheet = ''">
      <view class="sheet" @click.stop>
        <view class="sheet-head">
          <text class="sheet-title">{{ lab.visits }}</text>
          <text class="sheet-close" @click="sheet = ''">×</text>
        </view>
        <scroll-view scroll-y class="sheet-list">
          <view v-if="!browseList.length" class="sheet-empty">{{ lab.noVisits }}</view>
          <view v-for="item in browseList" :key="item.sku + String(item.ts)" class="sheet-item">
            <image v-if="item.image" class="sheet-img" :src="csMediaUrl(item.image)" mode="aspectFill" />
            <view class="sheet-body">
              <text class="sheet-name">{{ item.name || item.sku }}</text>
              <text class="sheet-meta">{{ item.price || item.sku }}</text>
            </view>
            <view class="sheet-btn" @click="sendBrowseItem(item)">{{ lab.send }}</view>
          </view>
        </scroll-view>
      </view>
    </view>

    <!-- Orders sheet -->
    <view v-if="sheet === 'orders'" class="sheet-mask" @click="sheet = ''">
      <view class="sheet" @click.stop>
        <view class="sheet-head">
          <text class="sheet-title">{{ lab.orders }}</text>
          <text class="sheet-close" @click="sheet = ''">×</text>
        </view>
        <scroll-view scroll-y class="sheet-list">
          <view v-if="ordersLoading" class="sheet-empty">…</view>
          <view v-else-if="!orderList.length" class="sheet-empty">{{ lab.noOrders }}</view>
          <view v-for="o in orderList" :key="String(o.id || o.submit_id)" class="sheet-item order-item">
            <view class="sheet-body">
              <text class="sheet-name">#{{ o.id || o.submit_id }} · {{ o.status || '—' }}</text>
              <text class="sheet-meta">{{ orderItemsText(o) || lab.noItems }}</text>
            </view>
            <view class="sheet-btn" @click="sendOrderItem(o)">{{ lab.send }}</view>
          </view>
        </scroll-view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'
import { onLoad, onUnload, onShow } from '@dcloudio/uni-app'
import { useI18n } from '@/composables/i18n'
import { loadBrowseHistory, type BrowseItem } from '@/composables/browseHistory'
import {
  openSupportChat,
  sendSupportMessage,
  pollSupportMessages,
  fetchCsStickers,
  uploadCsImage,
  sendSupportImage,
  parseImgBody,
  parseProductBody,
  parseOrderBody,
  buildProductBody,
  buildOrderBody,
  fetchCsOrders,
  csMediaUrl,
  type CsMessage,
  type CsProductCtx,
  type CsOrderCard,
} from '@/api/supportApi'

const { t } = useI18n()
const roomId = ref('')
const messages = ref<CsMessage[]>([])
const draft = ref('')
const booting = ref(true)
const online = ref(false)
const productCard = ref<CsProductCtx | null>(null)
const entryOffer = ref<CsProductCtx | null>(null)
const scrollInto = ref('')
const scrollTop = ref(0)
const scrollAnim = ref(false)
let scrollSeq = 0
const sending = ref(false)
const emojiOpen = ref(false)
const stickers = ref<string[]>(['👍','❤️','😊','🙏','✨','🔥','🎉','😅','🤝','✅'])
let pollAlive = false
let lastId = 0
const typingHint = ref('')
const sheet = ref<'' | 'browse' | 'orders'>('')
const browseList = ref<BrowseItem[]>([])
const orderList = ref<CsOrderCard[]>([])
const ordersLoading = ref(false)

const lab = computed(() => {
  const en =
    String(t('chat_title') || '').toLowerCase().includes('support') ||
    String(t('chat_send') || '').toLowerCase() === 'send'
  return en
    ? {
        visits: 'Visits',
        orders: 'Orders',
        send: 'Send',
        noVisits: 'No recent views',
        noOrders: 'No orders yet',
        noItems: 'Items n/a',
        orderCard: 'Order',
        status: 'Status',
        prodTip: 'Specs ready — tap to buy',
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
        prodTip: '已选规格，可直接下单',
      }
})

const canSend = computed(() => !!draft.value.trim() && !!roomId.value && !sending.value)
const statusLabel = computed(() => {
  if (booting.value) return t('chat_connecting')
  return online.value ? t('chat_online') : t('chat_reconnecting')
})

function whoLabel(m: CsMessage) {
  if (m.role === 'user') return t('chat_you')
  if (m.role === 'staff') {
    let name = String(m.staff_user || '').trim()
    name = name.replace(/^AI\s*[·•.\-]?\s*/i, '').replace(/\s*AI$/i, '').replace(/\s+AI\b/gi, '').trim()
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
  uni.previewImage({ urls: [src], current: src })
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

async function pickImage() {
  if (!roomId.value || sending.value) return
  emojiOpen.value = false
  try {
    const chosen = await new Promise<UniApp.ChooseImageSuccessCallbackResult>((resolve, reject) => {
      uni.chooseImage({
        count: 1,
        sizeType: ['compressed'],
        sourceType: ['album', 'camera'],
        success: resolve,
        fail: reject,
      })
    })
    const filePath = (chosen.tempFilePaths || [])[0]
    if (!filePath) return
    sending.value = true
    const up = await uploadCsImage(roomId.value, filePath)
    if (!up.ok || !up.url) {
      uni.showToast({ title: t('chat_fail'), icon: 'none' })
      return
    }
    const res = await sendSupportImage(roomId.value, up.url, productCard.value)
    const data = res.data as any
    if (data?.messages?.length) mergeMessages(data.messages)
    else if (data?.message) mergeMessages([data.message])
    else uni.showToast({ title: t('chat_fail'), icon: 'none' })
  } catch {
    uni.showToast({ title: t('chat_fail'), icon: 'none' })
  } finally {
    sending.value = false
  }
}

function openProduct(p: { sku?: string; option?: string; offer_id?: string; option_key?: string } | null) {
  if (!p?.sku) return
  const q = ['sku=' + encodeURIComponent(p.sku)]
  if (p.option) q.push('option=' + encodeURIComponent(p.option))
  if (p.offer_id || p.option_key) q.push('offer=' + encodeURIComponent(p.offer_id || p.option_key || ''))
  uni.navigateTo({ url: '/pages/pdp/index?' + q.join('&') })
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

function scrollToLatest(animated = false) {
  const last = messages.value.length ? messages.value[messages.value.length - 1] : null
  const target = last ? `m${last.id}` : 'm-end'
  scrollAnim.value = !!animated
  const seq = ++scrollSeq
  const bump = () => {
    if (seq !== scrollSeq) return
    scrollTop.value = scrollTop.value === 999999 ? 999998 : 999999
    scrollInto.value = ''
    nextTick(() => {
      if (seq !== scrollSeq) return
      scrollInto.value = target
      setTimeout(() => {
        if (seq !== scrollSeq) return
        scrollInto.value = 'm-end'
        scrollTop.value = scrollTop.value === 999999 ? 999998 : 999999
      }, 30)
    })
  }
  nextTick(() => {
    bump()
    ;[50, 150, 350, 700, 1200].forEach((ms) => setTimeout(bump, ms))
  })
}

async function boot(ctx: CsProductCtx | null) {
  booting.value = true
  try {
    const res = await openSupportChat(ctx)
    if (res.statusCode >= 400 || !(res.data as any)?.ok) {
      uni.showToast({ title: t('chat_fail'), icon: 'none' })
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
    uni.showToast({ title: t('chat_fail'), icon: 'none' })
  } finally {
    booting.value = false
    nextTick(() => scrollToLatest(false))
  }
}

function applyTyping(data: any) {
  const tp = data?.typing
  if (tp && tp.active && (tp.side === 'staff' || tp.side === 'ai')) {
    const en =
      String(t('chat_title') || '').toLowerCase().includes('support') ||
      String(t('chat_send') || '').toLowerCase() === 'send'
    typingHint.value = en ? 'Typing…' : '对方正在输入…'
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
      uni.showToast({ title: t('chat_fail'), icon: 'none' })
      return false
    }
    return true
  } catch {
    uni.showToast({ title: t('chat_fail'), icon: 'none' })
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
  uni.navigateBack({ fail: () => uni.reLaunch({ url: '/pages/me/index' }) })
}

onLoad((q) => {
  const ctx: CsProductCtx | null = q?.sku
    ? {
        sku: decodeURIComponent(String(q.sku)),
        name: q.name ? decodeURIComponent(String(q.name)) : decodeURIComponent(String(q.sku)),
        image: q.image ? decodeURIComponent(String(q.image)) : '',
        price: q.price ? decodeURIComponent(String(q.price)) : '',
      }
    : null
  productCard.value = ctx
  // Only show Taobao-style tip when entering from a product page
  entryOffer.value = ctx && ctx.sku ? { ...ctx } : null
  boot(ctx)
})

onShow(() => {
  uni.setNavigationBarTitle({ title: t('chat_title') })
  nextTick(() => scrollToLatest(false))
})

onUnload(() => {
  pollAlive = false
})
</script>

<style lang="scss" scoped>
@import '@/styles/theme.scss';
.page {
  min-height: 100vh;
  background: $hb-paper;
  display: flex;
  flex-direction: column;
  padding-top: calc(10px + env(safe-area-inset-top));
}
.head {
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 0 16px 10px;
}
.back {
  width: 36px;
  height: 36px;
  border-radius: 12px;
  background: $hb-white;
  text-align: center;
  line-height: 36px;
  font-size: 22px;
  box-shadow: $hb-shadow-soft;
}
.head-main { flex: 1; min-width: 0; }
.title { display: block; font-size: 20px; font-weight: 720; color: $hb-ink; }
.sub { display: block; font-size: 12px; color: $hb-muted; margin-top: 2px; }
.msgs {
  flex: 1;
  height: 0;
  padding: 8px 16px 12px;
  box-sizing: border-box;
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
.who { display: block; font-size: 11px; color: $hb-muted; margin-bottom: 4px; font-weight: 650; }
.body { display: block; font-size: 14px; line-height: 1.45; color: $hb-ink; white-space: pre-wrap; word-break: break-word; }
.bubble-img { display: block; max-width: 220px; width: 220px; border-radius: 10px; margin-top: 4px; }
.tail { height: 8px; }
.typing-row { padding: 0 4px 8px; }
.typing { font-size: 12px; color: $hb-muted; font-style: italic; }

.offer-bar {
  margin: 0 12px 8px;
  background: $hb-white;
  border-radius: 14px;
  padding: 8px 10px;
  display: flex;
  gap: 8px;
  align-items: center;
  box-shadow: $hb-shadow-soft;
  border: 1px solid $hb-soft;
}
.offer-img { width: 44px; height: 44px; border-radius: 10px; background: $hb-paper; flex: 0 0 auto; }
.offer-body { min-width: 0; flex: 1; }
.offer-name {
  display: block; font-size: 12px; font-weight: 680; color: $hb-ink;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.offer-meta { display: block; font-size: 11px; color: $hb-muted; margin-top: 2px; }
.offer-send {
  padding: 6px 12px; border-radius: 999px; background: $hb-coral; color: #fff;
  font-size: 12px; font-weight: 700; flex: 0 0 auto;
}
.offer-x {
  width: 28px; height: 28px; border-radius: 10px; text-align: center; line-height: 28px;
  color: $hb-muted; font-size: 18px; flex: 0 0 auto;
}

.tool-row {
  display: flex; gap: 8px; padding: 0 2px 8px;
}
.tool {
  display: flex; align-items: center; gap: 4px;
  padding: 6px 10px; border-radius: 999px; background: $hb-paper;
  border: 1px solid $hb-line;
}
.tool-ico { font-size: 13px; }
.tool-lab { font-size: 12px; color: $hb-ink; font-weight: 650; }

.emoji-panel {
  display: flex; flex-wrap: wrap; gap: 4px; padding: 8px 4px 10px;
  background: $hb-white; border-radius: 14px; margin-bottom: 8px;
  max-height: 160px; overflow: auto;
}
.emoji-btn {
  width: 40px; height: 40px; border-radius: 12px; background: $hb-white;
  text-align: center; line-height: 40px; font-size: 22px;
  box-shadow: $hb-shadow-soft; flex: 0 0 auto;
}
.emoji-btn.on { outline: 2px solid rgba(15, 90, 60, 0.25); }
.emoji { display: inline-block; font-size: 22px; padding: 4px 8px; }
.composer-row {
  display: flex; gap: 10px; align-items: center; width: 100%;
}
.composer {
  display: flex; flex-direction: column; gap: 0; align-items: stretch;
  padding: 10px 16px calc(10px + env(safe-area-inset-bottom));
  background: rgba(255, 255, 255, 0.94);
  border-top: 1px solid $hb-line;
  backdrop-filter: blur(12px);
}
.inp {
  flex: 1; background: $hb-paper; border-radius: 14px; padding: 12px 14px; font-size: 14px;
}
.send {
  min-width: 64px; height: 44px; border-radius: 14px; background: $hb-line; color: $hb-muted;
  display: flex; align-items: center; justify-content: center; font-weight: 720; font-size: 14px;
  &.on { background: $hb-coral; color: $hb-white; }
}

.prod-card {
  display: flex; gap: 10px; align-items: center; max-width: 260px;
  background: rgba(255,255,255,0.7); border-radius: 12px; padding: 8px;
  border: 1px solid rgba(0,0,0,0.06);
}
.prod-img { width: 64px; height: 64px; border-radius: 10px; flex: 0 0 auto; background: $hb-paper; }
.prod-body { min-width: 0; flex: 1; display: flex; flex-direction: column; gap: 2px; }
.prod-name { font-size: 13px; font-weight: 650; color: $hb-ink; }
.prod-price { font-size: 13px; color: $hb-coral; font-weight: 700; }
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
  background: $hb-white; border-radius: 18px 18px 0 0;
  padding: 12px 14px calc(14px + env(safe-area-inset-bottom));
  box-shadow: 0 -8px 30px rgba(0,0,0,0.12);
}
.sheet-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.sheet-title { font-size: 16px; font-weight: 720; color: $hb-ink; }
.sheet-close { font-size: 22px; color: $hb-muted; padding: 4px 8px; }
.sheet-list { max-height: 46vh; }
.sheet-empty { text-align: center; color: $hb-muted; padding: 28px 8px; font-size: 13px; }
.sheet-item {
  display: flex; gap: 10px; align-items: center;
  padding: 10px 4px; border-bottom: 1px solid $hb-line;
}
.sheet-img { width: 48px; height: 48px; border-radius: 10px; background: $hb-paper; flex: 0 0 auto; }
.sheet-body { min-width: 0; flex: 1; }
.sheet-name {
  display: block; font-size: 13px; font-weight: 650; color: $hb-ink;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.sheet-meta { display: block; font-size: 11px; color: $hb-muted; margin-top: 2px; }
.sheet-btn {
  padding: 6px 12px; border-radius: 999px; background: $hb-forest; color: #fff;
  font-size: 12px; font-weight: 700; flex: 0 0 auto;
}
.order-item .sheet-btn { background: $hb-coral; }
.page { background: #F7F4EF; padding-top: env(safe-area-inset-top); }
.price { color: #B45309 !important; }

/* Function layout deepen */

.fn-page { background: #F7F4EF; color: #0F2744; min-height: 100vh; }
.fn-card { background: #fff; border: 1px solid #E8E4DC; border-radius: 16px; padding: 14px; margin-bottom: 10px; }
.fn-title { font-size: 17px; font-weight: 700; color: #0F2744; }
.fn-muted { font-size: 12px; color: #6B7280; }
.fn-btn { display: flex; align-items: center; justify-content: center; height: 40px; border-radius: 12px; background: #0F2744; color: #fff; font-weight: 600; }
.fn-btn.outline { background: #fff; color: #0F2744; border: 1px solid #E8E4DC; }
.fn-amber { color: #B45309; font-weight: 700; }

/* A20 chrome */
.status { display: flex; justify-content: space-between; padding: 14px 16px 0; font-size: 12px; font-weight: 700; color: #0F2744; }
.page { background: #F7F4EF !important; color: #0F2744; min-height: 100vh; }
.head { background: #fff; border-bottom: 1px solid #E2E6EE; padding: 10px 16px !important; }
.head .title { font-size: 16px !important; font-weight: 700 !important; color: #0F2744 !important; }
.head .sub { font-size: 11px !important; color: #5C6570 !important; }
.composer .field, .composer input, .inp, .msg-input, .input {
  border-radius: 20px !important;
  background: #F7F4EF !important;
}

/* A20 bubbles */
.msgs { background: #F7F4EF !important; padding: 12px 16px 90px !important; }
.bubble-row { display: flex; margin: 8px 0; }
.bubble-row.user, .bubble-row.me, .bubble-row.buyer { justify-content: flex-end; }
.bubble-row.agent, .bubble-row.staff, .bubble-row.system { justify-content: flex-start; }
.bubble {
  max-width: 78%; padding: 10px 12px; border-radius: 14px; font-size: 13px; line-height: 1.4;
  background: #fff; border: 1px solid #E2E6EE; color: #0F2744;
}
.bubble-row.user .bubble, .bubble-row.me .bubble, .bubble-row.buyer .bubble {
  background: #E0F2FE; border-color: transparent; border-bottom-right-radius: 4px;
}
.bubble-row.agent .bubble, .bubble-row.staff .bubble {
  border-bottom-left-radius: 4px;
}
.bubble .who { display: block; font-size: 10px; color: #5C6570; margin-bottom: 4px; font-weight: 600; }
.empty {
  text-align: center; padding: 48px 16px; color: #0F2744;
}
.empty::before {
  content: "How can we help?"; display: block; font-size: 16px; font-weight: 700; margin-bottom: 8px;
}
.composer, .input-bar, .send-row, .foot {
  background: #fff !important; border-top: 1px solid #E2E6EE !important;
  padding: 10px 12px calc(10px + env(safe-area-inset-bottom)) !important;
}
.composer input, .composer .inp, .msg-input, .input-pill {
  border-radius: 20px !important; background: #F7F4EF !important; border: 0 !important;
  padding: 10px 14px !important; font-size: 13px !important;
}
</style>


