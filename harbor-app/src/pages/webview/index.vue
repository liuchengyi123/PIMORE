<template>
  <view class="page">
    <view class="bar">
      <text class="back" @click="goBack">← Back</text>
      <text class="title">{{ title }}</text>
      <text class="open" @click="openExternal">{{ t('webview_browser') }}</text>
    </view>
    <view class="actions" v-if="showPayActions">
      <text class="act done" @click="markPaidDone">{{ t('webview_done') }}</text>
      <text class="act cancel" @click="markCancel">Cancel → Cart</text>
    </view>
    <!-- #ifdef H5 -->
    <view class="bridge" v-if="bridging">
      <text class="bridge-title">{{ t('webview_syncing') }}</text>
      <text class="bridge-sub">{{ bridgeNote }}</text>
      <iframe class="hidden-frame" name="harbor_bridge" />
    </view>
    <iframe
      v-else
      class="frame"
      :src="src"
      @load="onIframeLoad"
      ref="frameRef"
    />
    <!-- #endif -->
    <!-- #ifndef H5 -->
    <web-view :src="src" @message="onWebMessage" />
    <!-- #endif -->
  </view>
</template>

<script setup lang="ts">
import { useI18n } from '@/composables/i18n'
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { LIVE_ORIGIN } from '@/api/products'
import { useCart } from '@/composables/cart'
import { classifyHarborUrl, publicStorefrontUrl } from '@/api/urls'
const { t } = useI18n()

const src = ref(LIVE_ORIGIN + '/checkout')
const title = ref('Harbor')
const bridging = ref(false)
const bridgeNote = ref('')
const cart = useCart()
const lastKind = ref('')
const lastOrderId = ref('')
let pollTimer: ReturnType<typeof setInterval> | null = null
let handled = false

const showPayActions = computed(() => {
  const c = classifyHarborUrl(src.value)
  return c.kind === 'checkout' || c.kind === 'payment' || c.kind === 'order-pending'
})

onLoad((q) => {
  if (q?.url) src.value = decodeURIComponent(String(q.url))
  if (q?.title) title.value = decodeURIComponent(String(q.title))
  else {
    const k = classifyHarborUrl(src.value).kind
    if (k === 'checkout' || k === 'payment') title.value = 'Harbor checkout'
    else if (k === 'login') title.value = 'Sign in'
    else if (k === 'account') title.value = 'Account'
    else title.value = 'Harbor'
  }
})

function goBack() {
  uni.navigateBack({ fail: () => uni.reLaunch({ url: '/pages/cart/index' }) })
}

function openExternal() {
  const abs = src.value.startsWith('http') ? src.value : publicStorefrontUrl(src.value.replace(/^\/harbor-api/, ''))
  // #ifdef H5
  window.open(abs, '_blank')
  // #endif
  // #ifndef H5
  try {
    // @ts-expect-error plus on app
    plus.runtime.openURL(abs)
  } catch {
    uni.setClipboardData({ data: abs })
  }
  // #endif
}

function navigateForUrl(url: string) {
  if (handled) return
  const c = classifyHarborUrl(url)
  lastKind.value = c.kind
  if (c.orderId) lastOrderId.value = c.orderId

  if (c.kind === 'order-success') {
    handled = true
    stopPoll()
    uni.reLaunch({
      url: '/pages/order-success/index' + (c.orderId ? '?id=' + encodeURIComponent(c.orderId) : ''),
    })
    return
  }
  if (c.kind === 'cart') {
    handled = true
    stopPoll()
    uni.reLaunch({ url: '/pages/cart/index' })
    return
  }
  // After login, landing on /account — bounce back to Me so summary refreshes
  if (c.kind === 'account' && title.value.toLowerCase().includes('sign')) {
    handled = true
    stopPoll()
    uni.reLaunch({ url: '/pages/me/index' })
  }
}

function markPaidDone() {
  const id = lastOrderId.value
  uni.reLaunch({
    url: '/pages/order-success/index' + (id ? '?id=' + encodeURIComponent(id) : ''),
  })
}

function markCancel() {
  uni.reLaunch({ url: '/pages/cart/index' })
}

function onIframeLoad(e: Event) {
  // Same-origin (local /harbor-api) can read location; cross-origin throws.
  try {
    const el = e.target as HTMLIFrameElement
    const href = el.contentWindow?.location?.href || ''
    if (href && href !== 'about:blank') {
      src.value = href
      navigateForUrl(href)
    }
  } catch {
    /* cross-origin — use toolbar Done / Cancel; native poll below */
  }
}

function onWebMessage(e: { detail?: { data?: unknown } }) {
  const raw = e?.detail?.data
  const first = Array.isArray(raw) ? raw[0] : raw
  if (typeof first === 'string') navigateForUrl(first)
  else if (first && typeof first === 'object' && 'url' in (first as object)) {
    navigateForUrl(String((first as { url: string }).url))
  }
}

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms))
}

function postViaForm(item: { sku: string; offer: string; qty: number; name: string }) {
  return new Promise<void>((resolve) => {
    // #ifdef H5
    const form = document.createElement('form')
    form.method = 'POST'
    form.action = LIVE_ORIGIN + '/cart/add'
    form.target = 'harbor_bridge'
    form.acceptCharset = 'UTF-8'
    const fields: Record<string, string> = {
      sku: item.sku,
      offer: item.offer || '',
      qty: String(item.qty || 1),
      country: 'US',
      next: '/cart',
    }
    Object.entries(fields).forEach(([k, v]) => {
      const input = document.createElement('input')
      input.type = 'hidden'
      input.name = k
      input.value = v
      form.appendChild(input)
    })
    document.body.appendChild(form)
    form.submit()
    setTimeout(() => {
      form.remove()
      resolve()
    }, 300)
    // #endif
    // #ifndef H5
    resolve()
    // #endif
  })
}

async function bridgeThenOpen() {
  // #ifdef H5
  const isCheckout = classifyHarborUrl(src.value).kind === 'checkout'
  if (!isCheckout) {
    bridging.value = false
    return
  }
  if (/harbor-api|127\.0\.0\.1|localhost/.test(src.value)) {
    bridging.value = false
    return
  }
  const items = cart.handoffPayload()
  if (!items.length) {
    bridging.value = false
    return
  }
  bridging.value = true
  bridgeNote.value = `Preparing ${items.length} item(s)…`
  await nextTick()
  for (let i = 0; i < items.length; i++) {
    const item = items[i]
    bridgeNote.value = `Adding ${i + 1}/${items.length}: ${item.name}`
    await postViaForm(item)
    await sleep(350)
  }
  bridgeNote.value = 'Opening checkout…'
  await sleep(400)
  bridging.value = false
  // Prefer public origin for payment providers; local proxy for session pages
  src.value = LIVE_ORIGIN + '/checkout'
  // #endif
}

function startNativeUrlPoll() {
  // #ifndef H5
  try {
    // @ts-expect-error uni app webview
    const pages = getCurrentPages()
    const page = pages[pages.length - 1] as { $getAppWebview?: () => { children: () => { getURL?: () => string; getTitle?: () => string }[] } }
    const wv = page?.$getAppWebview?.()
    pollTimer = setInterval(() => {
      try {
        const kids = wv?.children?.() || []
        const child = kids[0]
        const url = child?.getURL?.() || ''
        if (url) {
          src.value = url
          navigateForUrl(url)
        }
      } catch {
        /* ignore */
      }
    }, 900)
  } catch {
    /* ignore */
  }
  // #endif
}

function stopPoll() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

onMounted(() => {
  // #ifdef H5
  bridgeThenOpen()
  // #endif
  // #ifndef H5
  startNativeUrlPoll()
  // #endif
})

onUnmounted(() => stopPoll())
</script>

<style lang="scss" scoped>
@import '@/styles/theme.scss';
.page {
  min-height: 100vh;
  background: $hb-white;
  display: flex;
  flex-direction: column;
}
.bar {
  height: 48px;
  padding: 0 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid $hb-line;
  background: $hb-paper;
}
.back,
.open {
  font-size: 13px;
  font-weight: 700;
  color: $hb-forest;
  width: 72px;
}
.open {
  text-align: right;
}
.title {
  font-size: 14px;
  font-weight: 760;
}
.actions {
  display: flex;
  gap: 8px;
  padding: 8px 12px;
  background: $hb-soft;
  border-bottom: 1px solid $hb-line;
}
.act {
  flex: 1;
  text-align: center;
  font-size: 12px;
  font-weight: 750;
  padding: 8px;
  border-radius: 10px;
  &.done {
    background: $hb-forest;
    color: $hb-white;
  }
  &.cancel {
    background: $hb-white;
    color: $hb-muted;
    border: 1px solid $hb-line;
  }
}
.frame {
  flex: 1;
  width: 100%;
  border: 0;
  min-height: calc(100vh - 96px);
}
.bridge {
  padding: 40px 20px;
  text-align: center;
}
.bridge-title {
  display: block;
  font-size: 16px;
  font-weight: 760;
  margin-bottom: 8px;
}
.bridge-sub {
  display: block;
  font-size: 13px;
  color: $hb-muted;
}
.hidden-frame {
  width: 0;
  height: 0;
  border: 0;
  position: absolute;
  opacity: 0;
  pointer-events: none;
}
</style>
