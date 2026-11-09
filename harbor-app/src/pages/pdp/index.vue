<template>
  <view class="page" data-figma="1:4">
    <view v-if="!ready" class="empty"><text>Loading…</text></view>
    <template v-else>
      <!-- Hero -->
      <view class="hero-wrap">
        <view class="status">
          <text class="time">9:41</text>
          <view class="status-right">
            <view class="sig"><view /><view /><view /><view /></view>
            <view class="wifi" />
            <view class="batt"><view class="batt-fill" /></view>
          </view>
        </view>

        <view class="nav">
          <view class="nav-btn" @click="goBack"><view class="chev-l" /></view>
          <view class="nav-right">
            <view class="nav-btn" @click="toggleWish">
              <view class="ico-heart" :class="{ on: wished }" />
            </view>
            <view class="nav-btn" @click="goCompare">
              <view class="ico-compare" />
            </view>
            <view class="nav-btn" @click="goNotify">
              <view class="ico-bell" />
              <view class="dot" />
            </view>
          </view>
        </view>

        <view class="hero">
          <image class="hero-img" :src="gallery[imageIndex]" mode="aspectFill" />
          <view class="badge-bought"><text class="fire">🔥</text><text>1.2K bought today</text></view>
          <view class="badge-watch"><text class="eye">👁</text><text>24 watching</text></view>
          <view class="pager"><text>{{ imageIndex + 1 }} / {{ gallery.length }}</text></view>
          <view class="next" @click="nextImage"><view class="chev-r" /></view>
        </view>

        <scroll-view scroll-x class="thumbs" :show-scrollbar="false">
          <view
            v-for="(src, i) in thumbs"
            :key="i"
            class="thumb"
            :class="{ on: i === imageIndex }"
            @click="imageIndex = i"
          >
            <image class="thumb-img" :src="src" mode="aspectFill" />
          </view>
        </scroll-view>
      </view>

      <view class="body">
        <text class="title">{{ view.name }}</text>
        <text class="tagline">{{ view.tagline }}</text>

        <view class="price-row">
          <text class="price">${{ view.price.toFixed(2) }}</text>
          <text class="was">${{ view.compareAt.toFixed(2) }}</text>
          <view class="off"><text>{{ view.offPct }}% OFF</text></view>
        </view>

        <view class="ship" @click="onShip">
          <view class="ship-ico">🚚</view>
          <view class="ship-copy">
            <text class="ship-t">Free shipping on orders over $25</text>
            <text class="ship-s">Arrives in 2–5 business days</text>
          </view>
          <text class="ship-chev">›</text>
        </view>

        <view class="rating">
          <view class="stars">
            <text v-for="n in 5" :key="n" class="star" :class="starClass(view.rating, n)">★</text>
          </view>
          <text class="rating-t">{{ view.rating.toFixed(1) }} ({{ formatCount(view.reviews) }} reviews)</text>
        </view>

        <view class="tiles">
          <view class="tile" @click="onQa">
            <view class="tile-ico chat" />
            <view class="tile-copy">
              <text class="tile-t">Q&amp;A</text>
              <text class="tile-s">28 questions · 56 answers</text>
            </view>
            <text class="tile-chev">›</text>
          </view>
          <view class="tile-div" />
          <view class="tile" @click="onReviews">
            <view class="tile-ico doc" />
            <view class="tile-copy">
              <text class="tile-t">Reviews</text>
              <text class="tile-s">{{ formatCount(view.reviews) }} customer reviews</text>
            </view>
            <text class="tile-chev">›</text>
          </view>
        </view>

        <view class="feats">
          <view v-for="f in features" :key="f.title" class="feat">
            <view class="feat-circle"><text class="feat-emoji">{{ f.icon }}</text></view>
            <text class="feat-t">{{ f.title }}</text>
            <text class="feat-s">{{ f.sub }}</text>
          </view>
        </view>

        <view class="color-row">
          <text class="lab">Color</text>
          <view class="swatches">
            <view
              v-for="c in colors"
              :key="c.id"
              class="swatch"
              :class="{ on: color === c.id }"
              :style="{ background: c.hex }"
              @click="color = c.id"
            />
          </view>
          <text class="color-name" @click="openSheet('add')">{{ colorLabel }} ›</text>
        </view>

        <view class="qty-row">
          <text class="lab">Qty</text>
          <view class="stepper">
            <view class="step" @click="qty = Math.max(1, qty - 1)">−</view>
            <text class="qty">{{ qty }}</text>
            <view class="step" @click="qty = Math.min(99, qty + 1)">+</view>
          </view>
        </view>

        <view class="cta-spacer" />
      </view>

      <view class="sticky">
        <template v-if="isOos">
          <view class="btn-outline disabled">Sold out</view>
          <view class="btn-solid" :class="{ busy: notifyBusy }" @click="notifyMe">{{ notifyBusy ? '...' : 'Notify me' }}</view>
        </template>
        <template v-else>
          <view class="btn-outline" @click="addDirect">
            <view class="cart-mini" />
            <text>Add to Cart</text>
          </view>
          <view class="btn-solid" @click="buyDirect">
            <text class="bolt">⚡</text>
            <text>Buy Now</text>
          </view>
        </template>
      </view>

      <HbSkuSheet
        v-model:open="sheetOpen"
        v-model="size"
        :mode="sheetMode"
        :product="product || fixtureProduct"
        @confirm="onSheetConfirm"
      />
    </template>
    <HbLucky />
  </view>
</template>

<script setup lang="ts">
import { ref, computed, reactive } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { getProduct, type Product } from '@/api/products'
import { useCart } from '@/composables/cart'
import HbSkuSheet from '@/components/HbSkuSheet.vue'
import { trackBrowse } from '@/composables/browseHistory'

const FIGMA_GALLERY = [
  '/static/figma/pdp/g1.png',
  '/static/figma/pdp/g2.png',
  '/static/figma/pdp/g3.png',
  '/static/figma/pdp/g4.png',
  '/static/figma/pdp/g5.png',
]
const FIGMA_THUMBS = [
  '/static/figma/pdp/thumb1.png',
  '/static/figma/pdp/thumb2.png',
  '/static/figma/pdp/thumb3.png',
  '/static/figma/pdp/thumb4.png',
  '/static/figma/pdp/thumb5.png',
]

const features = [
  { icon: '🛡️', title: 'Water Resistant', sub: 'Keeps your stuff dry' },
  { icon: '💻', title: 'Fits 15" Laptop', sub: 'Padded sleeve' },
  { icon: '🍃', title: 'Lightweight', sub: 'Just 0.8 kg' },
  { icon: '♻️', title: 'Eco Friendly', sub: 'Recycled materials' },
]

const colors = [
  { id: 'coral', hex: '#FF6B4A', label: 'Coral' },
  { id: 'black', hex: '#1A1A1A', label: 'Black' },
  { id: 'navy', hex: '#1B2B4A', label: 'Navy' },
  { id: 'olive', hex: '#6B7A3A', label: 'Olive' },
  { id: 'grey', hex: '#C5C9CE', label: 'Grey' },
]

const view = reactive({
  name: 'Nomad Everyday Backpack',
  tagline: 'Stylish. Durable. Ready for Anything.',
  price: 4.99,
  compareAt: 9.99,
  offPct: 50,
  rating: 4.6,
  reviews: 1248,
})

const fixtureProduct: Product = {
  id: 'figma-pdp-nomad',
  sku: 'NOMAD-EVERYDAY-BP',
  name: 'Nomad Everyday Backpack',
  price: 4.99,
  compareAt: 9.99,
  category: 'Bags',
  image: FIGMA_GALLERY[0],
  images: [...FIGMA_GALLERY],
  sizes: ['Coral', 'Black', 'Navy', 'Olive', 'Grey'],
  blurb: 'Stylish. Durable. Ready for Anything.',
  live: false,
}

const product = ref<Product | null>(null)
const ready = ref(false)
const size = ref('Coral')
const color = ref('coral')
const qty = ref(1)
const imageIndex = ref(0)
const wished = ref(false)
const cart = useCart()
const notifyBusy = ref(false)
const sheetOpen = ref(false)
const sheetMode = ref<'add' | 'buy'>('add')
const busy = ref(false)

const gallery = computed(() => FIGMA_GALLERY)
const thumbs = computed(() => FIGMA_THUMBS)
const isOos = computed(() => Number((product.value as any)?.stock ?? 1) <= 0)
const colorLabel = computed(() => colors.find((c) => c.id === color.value)?.label || 'Coral')

function formatCount(n: number) {
  return n.toLocaleString('en-US')
}
function starClass(rating: number, n: number) {
  if (rating >= n) return 'full'
  if (rating >= n - 0.5) return 'half'
  return 'empty'
}
function nextImage() {
  imageIndex.value = (imageIndex.value + 1) % gallery.value.length
}
function goBack() {
  uni.navigateBack({ fail: () => uni.reLaunch({ url: '/pages/home/index' }) })
}
function goCompare() {
  uni.navigateTo({ url: '/pages/compare/index' })
}
function goNotify() {
  uni.showToast({ title: 'Notifications', icon: 'none' })
}
function toggleWish() {
  wished.value = !wished.value
  uni.showToast({ title: wished.value ? 'Saved' : 'Removed', icon: 'none' })
}
function onShip() {
  uni.showToast({ title: 'Shipping info', icon: 'none' })
}
function onQa() {
  goChat()
}
function onReviews() {
  uni.showToast({ title: 'Reviews', icon: 'none' })
}
function goChat() {
  const p = product.value || fixtureProduct
  const q = [
    'sku=' + encodeURIComponent(p.sku),
    'name=' + encodeURIComponent(p.name || p.sku),
    'image=' + encodeURIComponent(p.image || ''),
    'price=' + encodeURIComponent(String(p.price ?? '')),
  ].join('&')
  uni.navigateTo({ url: '/pages/chat/index?' + q })
}

function openSheet(mode: 'add' | 'buy') {
  sheetMode.value = mode
  sheetOpen.value = true
}

function cartTarget(): Product {
  return product.value || fixtureProduct
}

async function addDirect() {
  if (busy.value) return
  const p = cartTarget()
  const hasOpts = (p.offers && p.offers.length > 1) || (p.sizes && p.sizes.length > 1)
  if (hasOpts && product.value?.live) {
    openSheet('add')
    return
  }
  busy.value = true
  try {
    const label = size.value || colorLabel.value || 'default'
    const res = await cart.add(p, label, qty.value)
    uni.showToast({ title: res.message || 'Added', icon: 'none' })
  } finally {
    busy.value = false
  }
}

async function buyDirect() {
  if (busy.value) return
  const p = cartTarget()
  const hasOpts = (p.offers && p.offers.length > 1) || (p.sizes && p.sizes.length > 1)
  if (hasOpts && product.value?.live) {
    openSheet('buy')
    return
  }
  busy.value = true
  try {
    const label = size.value || colorLabel.value || 'default'
    await cart.add(p, label, qty.value)
    uni.navigateTo({ url: '/pages/checkout/index' })
  } finally {
    busy.value = false
  }
}

async function onSheetConfirm(payload: { size: string; qty: number; mode: 'add' | 'buy' }) {
  if (busy.value) return
  busy.value = true
  size.value = payload.size
  qty.value = payload.qty
  try {
    const res = await cart.add(cartTarget(), payload.size || 'default', payload.qty)
    sheetOpen.value = false
    if (payload.mode === 'buy') {
      uni.navigateTo({ url: '/pages/checkout/index' })
    } else {
      uni.showToast({ title: res.message || 'Added', icon: 'none' })
    }
  } finally {
    busy.value = false
  }
}

async function notifyMe() {
  if (notifyBusy.value) return
  notifyBusy.value = true
  try {
    const email = await new Promise<string>((resolve) => {
      uni.showModal({
        title: 'Notify me',
        editable: true,
        placeholderText: 'you@email.com',
        success: (r) => resolve(r.confirm ? String((r as any).content || '') : ''),
      })
    })
    if (!email || !email.includes('@')) return
    const sku = String(cartTarget().sku || '')
    await uni.request({
      url: '/api/notify-me',
      method: 'POST',
      header: { 'Content-Type': 'application/json' },
      data: { email, sku, country: 'US' },
    })
    uni.showToast({ title: 'Saved', icon: 'none' })
  } catch {
    uni.showToast({ title: 'Failed', icon: 'none' })
  } finally {
    notifyBusy.value = false
  }
}

onLoad(async (q) => {
  const sku = q?.sku ? decodeURIComponent(q.sku) : fixtureProduct.sku
  const prefOption = q?.option
    ? decodeURIComponent(String(q.option))
    : q?.size
      ? decodeURIComponent(String(q.size))
      : ''
  const prefOffer = q?.offer ? decodeURIComponent(String(q.offer)) : ''
  try {
    const p = await getProduct(sku)
    product.value = p || null
    let picked = ''
    if (p) {
      const offers = p.offers || []
      const sizes = p.sizes || []
      if (prefOffer && offers.length) {
        const byId = offers.find((o) => o.id === prefOffer || o.label === prefOffer)
        if (byId) picked = byId.label
      }
      if (!picked && prefOption) {
        if (offers.some((o) => o.label === prefOption)) picked = prefOption
        else if (sizes.includes(prefOption)) picked = prefOption
      }
      if (!picked) picked = offers[0]?.label || sizes[0] || colorLabel.value
      trackBrowse({
        sku: p.sku,
        name: p.name,
        image: p.image || '',
        price: p.price,
      })
    }
    size.value = picked || colorLabel.value
  } catch {
    product.value = null
    size.value = colorLabel.value
  } finally {
    ready.value = true
  }
})
</script>

<style lang="scss" scoped>
@import '@/styles/theme.scss';

.page {
  min-height: 100vh;
  background: #fff;
  color: #1f2430;
  padding-bottom: env(safe-area-inset-bottom);
}
.empty {
  padding: 48px 16px;
  text-align: center;
  color: #8b93a1;
}

.hero-wrap {
  padding-top: env(safe-area-inset-top);
  background: #fff;
}
.status {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 18px 0;
  height: 26px;
  box-sizing: border-box;
}
.time { font-size: 14px; font-weight: 600; }
.status-right { display: flex; align-items: center; gap: 6px; }
.sig { display: flex; align-items: flex-end; gap: 1.5px; height: 10px; }
.sig view { width: 3px; background: #1f2430; border-radius: 1px; }
.sig view:nth-child(1) { height: 3px; }
.sig view:nth-child(2) { height: 5px; }
.sig view:nth-child(3) { height: 7px; }
.sig view:nth-child(4) { height: 10px; }
.wifi {
  width: 13px; height: 10px; border: 2px solid #1f2430; border-top: none;
  border-radius: 0 0 8px 8px; box-sizing: border-box; position: relative;
}
.batt {
  width: 22px; height: 11px; border: 1.5px solid #1f2430; border-radius: 3px;
  padding: 1px; box-sizing: border-box; position: relative;
}
.batt-fill { width: 70%; height: 100%; background: #1f2430; border-radius: 1px; }

.nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 10px 8px;
}
.nav-right { display: flex; gap: 4px; }
.nav-btn {
  width: 36px; height: 36px;
  display: flex; align-items: center; justify-content: center;
  position: relative;
}
.chev-l {
  width: 10px; height: 10px;
  border-left: 2.2px solid #1f2430; border-bottom: 2.2px solid #1f2430;
  transform: rotate(45deg); margin-left: 4px;
}
.ico-heart {
  width: 16px; height: 14px; position: relative;
}
.ico-heart::before, .ico-heart::after {
  content: ''; position: absolute; top: 0; width: 9px; height: 14px;
  border: 1.8px solid #1f2430; background: transparent;
  border-radius: 9px 9px 2px 2px; box-sizing: border-box;
}
.ico-heart::before { left: 0; transform: rotate(-45deg); transform-origin: bottom right; }
.ico-heart::after { right: 0; transform: rotate(45deg); transform-origin: bottom left; }
.ico-heart.on::before, .ico-heart.on::after {
  background: $hb-coral; border-color: $hb-coral;
}
.ico-compare {
  width: 16px; height: 14px; position: relative;
}
.ico-compare::before, .ico-compare::after {
  content: ''; position: absolute; width: 5px; height: 5px; border-radius: 99px;
  border: 1.6px solid #1f2430; box-sizing: border-box;
}
.ico-compare::before { left: 0; top: 0; }
.ico-compare::after { right: 0; bottom: 0; }
.ico-compare {
  background: linear-gradient(#1f2430,#1f2430) center / 10px 1.6px no-repeat;
}
.ico-bell {
  width: 14px; height: 14px; border: 1.8px solid #1f2430; border-radius: 7px 7px 3px 3px;
  box-sizing: border-box; position: relative;
}
.ico-bell::after {
  content: ''; position: absolute; left: 3px; bottom: -4px; width: 6px; height: 3px;
  border: 1.6px solid #1f2430; border-top: none; border-radius: 0 0 4px 4px; box-sizing: border-box;
}
.dot {
  position: absolute; top: 6px; right: 6px; width: 7px; height: 7px;
  background: #ef4444; border-radius: 99px; border: 1.5px solid #fff; box-sizing: border-box;
}

.hero {
  margin: 0 16px; position: relative;
  border-radius: 20px; overflow: hidden; background: #f3f1ee;
  height: 320px;
}
.hero-img { width: 100%; height: 100%; display: block; }
.badge-bought {
  position: absolute; left: 12px; top: 12px;
  background: $hb-coral; color: #fff; border-radius: 99px;
  padding: 5px 10px; font-size: 11px; font-weight: 700;
  display: flex; align-items: center; gap: 4px;
}
.badge-watch {
  position: absolute; right: 12px; top: 12px;
  background: #fff; color: #1f2430; border-radius: 99px;
  padding: 5px 10px; font-size: 11px; font-weight: 600;
  display: flex; align-items: center; gap: 4px;
  box-shadow: 0 2px 8px rgba(0,0,0,.06);
}
.fire, .eye { font-size: 11px; line-height: 1; }
.pager {
  position: absolute; left: 12px; bottom: 12px;
  background: rgba(30, 34, 40, 0.55); color: #fff;
  border-radius: 99px; padding: 4px 10px; font-size: 11px; font-weight: 600;
}
.next {
  position: absolute; right: 12px; top: 50%; margin-top: -18px;
  width: 36px; height: 36px; border-radius: 99px; background: #fff;
  box-shadow: 0 4px 14px rgba(0,0,0,.12);
  display: flex; align-items: center; justify-content: center;
}
.chev-r {
  width: 8px; height: 8px;
  border-right: 2.2px solid #1f2430; border-bottom: 2.2px solid #1f2430;
  transform: rotate(-45deg); margin-left: -2px;
}

.thumbs {
  white-space: nowrap; padding: 12px 16px 4px;
}
.thumb {
  display: inline-block; width: 56px; height: 56px; margin-right: 8px;
  border-radius: 12px; overflow: hidden; border: 2.5px solid transparent;
  box-sizing: border-box; vertical-align: top; background: #f3f1ee;
}
.thumb.on { border-color: $hb-coral; }
.thumb-img { width: 100%; height: 100%; }

.body { padding: 12px 16px 0; }
.title {
  display: block; font-size: 22px; font-weight: 800; letter-spacing: -0.4px; line-height: 1.2;
}
.tagline {
  display: block; margin-top: 6px; font-size: 13px; color: #8b93a1; line-height: 1.35;
}
.price-row {
  display: flex; align-items: center; gap: 8px; margin-top: 12px; flex-wrap: wrap;
}
.price { font-size: 28px; font-weight: 800; color: $hb-coral; letter-spacing: -0.6px; }
.was { font-size: 14px; color: #b0b7c3; text-decoration: line-through; }
.off {
  background: #FFE8E1; color: $hb-coral; border-radius: 99px;
  padding: 3px 8px; font-size: 11px; font-weight: 800;
}

.ship {
  margin-top: 14px; padding: 12px 12px;
  background: #FFF1EC; border-radius: 12px;
  display: flex; align-items: center; gap: 10px;
}
.ship-ico { font-size: 18px; }
.ship-copy { flex: 1; min-width: 0; }
.ship-t { display: block; font-size: 13px; font-weight: 700; color: $hb-coral; }
.ship-s { display: block; margin-top: 2px; font-size: 11px; color: #8b93a1; }
.ship-chev { font-size: 20px; color: #c4c9d2; }

.rating {
  display: flex; align-items: center; gap: 8px; margin-top: 14px;
}
.stars { display: flex; gap: 1px; }
.star { font-size: 14px; color: #e5e7eb; line-height: 1; }
.star.full { color: $hb-coral; }
.star.half { color: $hb-coral; opacity: 0.55; }
.rating-t { font-size: 13px; color: #4b5563; font-weight: 600; }

.tiles {
  margin-top: 14px; display: flex; align-items: stretch;
  border: 1px solid #eceff3; border-radius: 12px; overflow: hidden;
}
.tile {
  flex: 1; display: flex; align-items: center; gap: 8px; padding: 12px 10px;
}
.tile-div { width: 1px; background: #eceff3; }
.tile-ico {
  width: 22px; height: 22px; flex-shrink: 0; position: relative;
}
.tile-ico.chat {
  border: 1.6px solid #9aa3b2; border-radius: 6px 6px 6px 2px; box-sizing: border-box;
}
.tile-ico.doc {
  border: 1.6px solid #9aa3b2; border-radius: 3px; box-sizing: border-box;
}
.tile-copy { flex: 1; min-width: 0; }
.tile-t { display: block; font-size: 13px; font-weight: 700; }
.tile-s { display: block; margin-top: 2px; font-size: 10px; color: #8b93a1; }
.tile-chev { color: #c4c9d2; font-size: 18px; }

.feats {
  margin-top: 18px; display: flex; justify-content: space-between; gap: 6px;
}
.feat { flex: 1; text-align: center; min-width: 0; }
.feat-circle {
  width: 48px; height: 48px; margin: 0 auto;
  border-radius: 99px; border: 1.5px solid #FFD2C4; background: #FFF7F4;
  display: flex; align-items: center; justify-content: center;
}
.feat-emoji { font-size: 18px; line-height: 1; }
.feat-t {
  display: block; margin-top: 8px; font-size: 11px; font-weight: 700; line-height: 1.2;
}
.feat-s {
  display: block; margin-top: 2px; font-size: 10px; color: #8b93a1; line-height: 1.25;
}

.color-row {
  margin-top: 20px; display: flex; align-items: center; gap: 10px;
}
.lab { font-size: 14px; font-weight: 700; width: 48px; }
.swatches { flex: 1; display: flex; gap: 10px; justify-content: center; }
.swatch {
  width: 28px; height: 28px; border-radius: 99px;
  box-sizing: border-box; border: 2px solid transparent;
}
.swatch.on {
  box-shadow: 0 0 0 1.5px #1f2430;
  border-color: #fff;
}
.color-name { font-size: 13px; font-weight: 600; color: #1f2430; }

.qty-row {
  margin-top: 16px; display: flex; align-items: center; justify-content: space-between;
}
.stepper {
  display: flex; align-items: center;
  border: 1px solid #e5e7eb; border-radius: 12px; overflow: hidden;
}
.step {
  width: 40px; height: 36px;
  display: flex; align-items: center; justify-content: center;
  font-size: 18px; color: #1f2430; font-weight: 500;
}
.qty {
  min-width: 36px; text-align: center; font-size: 15px; font-weight: 700;
}

.cta-spacer { height: 96px; }

.sticky {
  position: fixed; left: 0; right: 0; bottom: 0;
  padding: 10px 16px calc(10px + env(safe-area-inset-bottom));
  background: rgba(255,255,255,.96);
  display: flex; gap: 10px;
  box-shadow: 0 -6px 20px rgba(27,43,74,.06);
  z-index: 50;
}
.btn-outline, .btn-solid {
  flex: 1; height: 48px; border-radius: 14px;
  display: flex; align-items: center; justify-content: center; gap: 6px;
  font-size: 15px; font-weight: 750;
}
.btn-outline {
  background: #fff; color: $hb-coral; border: 1.6px solid $hb-coral;
}
.btn-solid {
  background: $hb-coral; color: #fff; border: 1.6px solid $hb-coral;
}
.btn-outline.disabled, .btn-solid.busy { opacity: 0.55; }
.cart-mini {
  width: 16px; height: 14px; position: relative;
  border: 1.6px solid $hb-coral; border-top: none; border-radius: 0 0 3px 3px;
  box-sizing: border-box;
}
.cart-mini::before {
  content: ''; position: absolute; left: -3px; top: -5px; width: 20px; height: 1.6px;
  background: $hb-coral;
}
.bolt { font-size: 14px; line-height: 1; }
</style>
