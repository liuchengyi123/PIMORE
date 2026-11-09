<template>
  <view class="page" data-figma="A05" v-if="product">
    <view class="gallery" :style="galleryBg">
      <image
        v-if="gallerySrc"
        class="gallery-img"
        :src="gallerySrc"
        mode="aspectFill"
      />
      <view class="pills">
        <HbPill :label="product.category" />
        <HbPill v-if="discount" :label="'-' + discount + '%'" tone="coral" />
      </view>
      <view class="counter">{{ imageIndex + 1 }} / {{ imageCount }}</view>
    </view>

    <view class="body">
      <text class="ships">{{ product.shipsIn || t('pdp_ships_default') }}</text>
      <text class="title">{{ product.name }}</text>
      <view class="price-row">
        <text class="price">{{ money(displayPrice) }}</text>
        <text v-if="displayCompare" class="was">{{ money(displayCompare) }}</text>
      </view>
      <text class="fx">{{ t('pdp_fx') }}</text>

      <view class="sku-row" @click="openSheet('add')">
        <text class="sku-row-k">{{ t('common_option') }}</text>
        <text class="sku-row-v">{{ sizeSummary }}</text>
        <text class="sku-row-chev">›</text>
      </view>

      <view class="specs">
        <view class="spec">
          <text class="k">SKU</text>
          <text class="v">{{ product.sku }}</text>
        </view>
        <view class="spec">
          <text class="k">Hub</text>
          <text class="v">{{ product.hub || 'US / EU' }}</text>
        </view>
        <view class="spec">
          <text class="k">Ship</text>
          <text class="v">{{ t('pdp_ship_tracked') }}</text>
        </view>
      </view>

      <text class="blurb">{{ product.blurb || t('pdp_blurb_default') }}</text>
      <view class="cta-spacer" />
    </view>

    <view class="sticky-cta" data-figma="A28">
      <view class="cart-dock" @click="goCart">
        <view class="cart-ico">
          <view class="bag-body" />
          <view class="bag-handle" />
        </view>
        <view v-if="cartCount > 0" class="cart-badge">
          <text>{{ cartCountLabel }}</text>
        </view>
      </view>
      <view class="chat-dock" @click="goChat">
        <text class="chat-ico">💬</text>
        <text class="chat-lab">{{ t('chat_entry') }}</text>
      </view>
      <template v-if="isOos">
        <view class="btn-outline disabled">{{ t('out_of_stock') || 'Sold out' }}</view>
        <view class="btn-solid" :class="{ busy: notifyBusy }" @click="notifyMe">{{ notifyBusy ? '...' : (t('notify_me') || 'Notify me') }}</view>
      </template>
      <template v-else>
        <view class="btn-outline" @click="openSheet('add')">{{ t('common_add') }}</view>
        <view class="btn-solid" @click="openSheet('buy')">{{ t('common_buy_now') }}</view>
      </template>
    </view>

    <HbSkuSheet
      v-model:open="sheetOpen"
      v-model="size"
      :mode="sheetMode"
      :product="product"
      @confirm="onSheetConfirm"
    />
  </view>
  <view v-else class="empty">
    <text>{{ t('pdp_loading') }}</text>
  </view>
  <HbLucky />
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { getProduct, money, type Product } from '@/api/products'
import { useCart } from '@/composables/cart'
import HbPill from '@/components/HbPill.vue'
import HbSkuSheet from '@/components/HbSkuSheet.vue'
import { useI18n } from '@/composables/i18n'
import { trackBrowse } from '@/composables/browseHistory'

const { t } = useI18n()

const product = ref<Product | null>(null)
const size = ref('')
const imageIndex = ref(0)
const cart = useCart()
const cartCount = computed(() => cart.count.value)
const cartCountLabel = computed(() => (cartCount.value > 99 ? '99+' : String(cartCount.value)))
const isOos = computed(() => Number((product.value as any)?.stock ?? 1) <= 0)
const notifyBusy = ref(false)
const sheetOpen = ref(false)
const sheetMode = ref<'add' | 'buy'>('add')
const busy = ref(false)

const discount = computed(() => {
  const p = product.value
  if (!p?.compareAt || p.compareAt <= p.price) return 0
  return Math.round((1 - p.price / p.compareAt) * 100)
})

const imageCount = computed(() =>
  Math.max(1, product.value?.images?.length || (product.value?.image ? 1 : 1)),
)
const gallerySrc = computed(() => {
  const imgs = product.value?.images
  if (imgs && imgs.length) return imgs[Math.min(imageIndex.value, imgs.length - 1)]
  return product.value?.image || ''
})

const galleryBg = computed(() => {
  if (gallerySrc.value) return {}
  return { background: 'linear-gradient(160deg, #E8F1EC 0%, #D8E4DC 55%, #EDE8E1 100%)' }
})

const selectedOffer = computed(() => {
  const p = product.value
  if (!p) return null
  const label = size.value
  return (p.offers || []).find((o) => o.label === label) || null
})

const displayPrice = computed(() => selectedOffer.value?.price ?? product.value?.price ?? 0)
const displayCompare = computed(() => {
  const c = selectedOffer.value?.compareAt ?? product.value?.compareAt
  const price = displayPrice.value
  if (!c || c <= price) return 0
  return c
})

const sizeSummary = computed(() => {
  if (size.value) return size.value
  const opts = product.value?.offers?.length
    ? product.value.offers.length
    : product.value?.sizes?.length || 0
  if (opts > 0) return t('common_choose_n', { n: opts })
  return t('common_default')
})

function openSheet(mode: 'add' | 'buy') {
  sheetMode.value = mode
  sheetOpen.value = true
}

function goCart() {
  uni.navigateTo({ url: '/pages/cart/index' })
}

function goChat() {
  if (!product.value) return
  const p = product.value
  const q = [
    'sku=' + encodeURIComponent(p.sku),
    'name=' + encodeURIComponent(p.name || p.sku),
    'image=' + encodeURIComponent(p.image || ''),
    'price=' + encodeURIComponent(String(p.price ?? '')),
  ].join('&')
  uni.navigateTo({ url: '/pages/chat/index?' + q })
}

onLoad(async (q) => {
  const sku = q?.sku ? decodeURIComponent(q.sku) : 'SPATULA-5'
  const prefOption = q?.option ? decodeURIComponent(String(q.option)) : (q?.size ? decodeURIComponent(String(q.size)) : '')
  const prefOffer = q?.offer ? decodeURIComponent(String(q.offer)) : ''
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
      else {
        const fuzzy = offers.find((o) => o.label.toLowerCase() === prefOption.toLowerCase())
        if (fuzzy) picked = fuzzy.label
      }
    }
    if (!picked) picked = offers[0]?.label || sizes[0] || ''
  }
  size.value = picked
  imageIndex.value = 0
  if (p) {
    trackBrowse({
      sku: p.sku,
      name: p.name,
      image: p.image || '',
      price: p.price,
    })
  }
})

async function onSheetConfirm(payload: { size: string; qty: number; mode: 'add' | 'buy' }) {
  if (!product.value || busy.value) return
  busy.value = true
  size.value = payload.size
  try {
    const res = await cart.add(product.value, payload.size || 'default', payload.qty)
    sheetOpen.value = false
    if (payload.mode === 'buy') {
      uni.navigateTo({ url: '/pages/checkout/index' })
    } else {
      uni.showToast({
        title: res.message || (res.live ? t('common_added') : t('common_saved_locally')),
        icon: 'none',
      })
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
    const sku = String(product.value?.sku || product.value?.id || '')
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
</script>

<style lang="scss" scoped>
@import '@/styles/theme.scss';

.page {
  min-height: 100vh;
  background: $hb-white;
}
.empty {
  padding: 40px 16px;
  color: $hb-muted;
  font-size: 14px;
}
.gallery {
  height: 72vw;
  max-height: 420px;
  min-height: 280px;
  background: $hb-paper;
  position: relative;
  overflow: hidden;
}
.gallery-img {
  width: 100%;
  height: 100%;
  display: block;
}
.pills {
  position: absolute;
  left: 16px;
  top: 16px;
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  max-width: 70%;
}
.counter {
  position: absolute;
  right: 16px;
  bottom: 16px;
  background: rgba(20, 26, 23, 0.45);
  color: $hb-white;
  font-size: 11px;
  font-weight: 600;
  padding: 6px 10px;
  border-radius: $hb-radius-pill;
  backdrop-filter: blur(8px);
}
.body {
  padding: 20px 16px 8px;
}
.ships {
  display: block;
  font-size: 12px;
  color: $hb-muted;
  margin-bottom: 8px;
  letter-spacing: 0.1px;
}
.title {
  display: block;
  font-size: 24px;
  font-weight: 720;
  letter-spacing: -0.55px;
  line-height: 1.22;
}
.price-row {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-top: 14px;
}
.price {
  font-size: 28px;
  font-weight: 740;
  color: $hb-ink;
  letter-spacing: -0.7px;
}
.was {
  font-size: 14px;
  color: $hb-strike;
  text-decoration: line-through;
}
.fx {
  display: block;
  margin-top: 4px;
  font-size: 12px;
  color: $hb-muted;
}
.sku-row {
  margin-top: 20px;
  margin-bottom: 18px;
  min-height: 48px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 0;
  border-top: 1px solid $hb-line;
  border-bottom: 1px solid $hb-line;
}
.sku-row-k {
  flex: 0 0 auto;
  font-size: 13px;
  font-weight: 680;
  color: $hb-ink;
}
.sku-row-v {
  flex: 1 1 auto;
  min-width: 0;
  text-align: right;
  font-size: 13px;
  font-weight: 500;
  line-height: 1.35;
  color: $hb-muted;
  white-space: normal;
  word-break: break-word;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}
.sku-row-chev {
  flex: 0 0 auto;
  font-size: 22px;
  line-height: 1;
  color: $hb-muted;
  font-weight: 400;
}
.specs {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 8px;
  margin-bottom: 16px;
}
.spec {
  border-radius: 16px;
  background: $hb-paper;
  padding: 12px 8px;
  text-align: center;
}
.k {
  display: block;
  font-size: 10px;
  color: $hb-muted;
  letter-spacing: 0.4px;
  text-transform: uppercase;
}
.v {
  display: block;
  font-size: 12px;
  font-weight: 680;
  margin-top: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.blurb {
  display: block;
  font-size: 14px;
  color: $hb-muted;
  line-height: 1.55;
}
.cta-spacer {
  height: 100px;
}
.sticky-cta {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  padding: 12px 16px calc(12px + env(safe-area-inset-bottom));
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  display: grid;
  grid-template-columns: 40px 40px 1fr 1.25fr;
  gap: 8px;
  align-items: center;
  box-shadow: 0 -8px 28px rgba(20, 26, 23, 0.06);
  z-index: 50;
}
.chat-dock {
  width: 40px;
  height: 44px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1px;
  color: $hb-ink;
}
.chat-ico { font-size: 16px; line-height: 1; }
.chat-lab { font-size: 9px; font-weight: 680; color: $hb-muted; letter-spacing: -0.2px; }
.cart-dock {
  position: relative;
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: $hb-ink;
}
.cart-ico {
  position: relative;
  width: 22px;
  height: 22px;
}
.bag-body {
  position: absolute;
  left: 2px;
  right: 2px;
  top: 7px;
  bottom: 1px;
  border: 1.8px solid currentColor;
  border-radius: 4px 4px 6px 6px;
}
.bag-handle {
  position: absolute;
  left: 6px;
  right: 6px;
  top: 2px;
  height: 8px;
  border: 1.8px solid currentColor;
  border-bottom: 0;
  border-radius: 8px 8px 0 0;
}
.cart-badge {
  position: absolute;
  top: 0;
  right: 0;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  border-radius: $hb-radius-pill;
  background: $hb-coral;
  color: $hb-white;
  font-size: 10px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
  box-sizing: border-box;
}
.btn-outline {
  height: 52px;
  border-radius: $hb-radius-btn-lg;
  border: 1.5px solid $hb-forest;
  color: $hb-forest;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 15px;
  background: $hb-white;
}
.btn-solid {
  height: 52px;
  border-radius: $hb-radius-btn-lg;
  background: $hb-forest;
  color: $hb-white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 15px;
}
.page { background: #F7F4EF; padding-top: env(safe-area-inset-top); }
.price { color: #B45309 !important; }
</style>
