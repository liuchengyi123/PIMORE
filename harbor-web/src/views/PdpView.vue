<template>
  <div class="fn-page page" v-if="product" data-figma="M05">
    <div class="gallery" :style="galleryBg">
      <img v-if="gallerySrc" class="gallery-img" :src="gallerySrc" alt="" />
      <div class="pills">
        <span class="pill">{{ product.category }}</span>
        <span v-if="discount" class="pill coral">-{{ discount }}%</span>
      </div>
      <button type="button" class="back" @click="goBack" aria-label="back"><ChevronLeft :size="22" :stroke-width="1.75" /></button>
    </div>

    <div class="body">
      <div class="price-row">
        <span class="price" :class="{ oos: isOos }">{{ money(displayPrice) }}</span>
        <span v-if="displayCompare" class="was">{{ money(displayCompare) }}</span>
        <span v-if="discount" class="pill amber">-{{ discount }}%</span>
      </div>
      <h1 class="title">{{ product.name }}</h1>
      <p v-if="interestCount > 0" class="interest">{{ t('pdp_interest', { n: interestCount }) }}</p>
      <div class="ship-pills">
        <span class="pill ok">{{ t('pdp_ship_tracked') }}</span>
        <span class="pill info">{{ product.shipsIn || t('pdp_ships_default') }}</span>
        <span class="pill" :class="isOos ? 'bad' : ''">{{ isOos ? t('out_of_stock') || 'Sold out' : (t('in_stock') || 'In stock') }}</span>
      </div>
      <button type="button" class="sku-row" @click="sheetOpen = true">
        <span class="sku-k">{{ t('common_option') }}</span>
        <span class="sku-v">{{ sizeSummary }} · Qty {{ qty }}</span>
        <ChevronRight :size="18" :stroke-width="1.7" class="chev" />
      </button>
      <div class="reviews-box">
        <div class="rev-head"><strong>{{ t('reviews') || 'Reviews' }}</strong><span class="tiny">Write a review after delivery</span></div>
        <div class="rev-empty">No reviews yet</div>
      </div>
      <p class="blurb">{{ product.blurb || t('pdp_blurb_default') }}</p>
      <div class="cta-spacer" />
    </div>

    <div class="sticky-cta">
      <button type="button" class="dock wish" @click="doWish" aria-label="wishlist">♡<span class="lab">Save</span></button>
      <template v-if="isOos">
        <button type="button" class="btn disabled" disabled>{{ t('out_of_stock') || 'Sold out' }}</button>
        <button type="button" class="btn outline" @click="notifyMe" :disabled="notifyBusy">{{ notifyBusy ? "…" : "Notify me" }}</button>
      <p v-if="notifyMsg" class="tiny" style="margin-top:8px">{{ notifyMsg }}</p>
      </template>
      <template v-else>
        <button type="button" class="btn outline" @click="doAdd">{{ t('common_add') }}</button>
        <button type="button" class="btn solid" @click="doBuy">{{ t('common_buy_now') }}</button>
      </template>
    </div>

    <div v-if="sheetOpen" class="sheet-mask" @click="sheetOpen = false">
      <div class="sheet" @click.stop>
        <div class="sheet-title">{{ t('common_option') }}</div>
        <div class="opts">
          <button
            v-for="opt in optionLabels"
            :key="opt"
            type="button"
            class="opt"
            :class="{ on: size === opt }"
            @click="size = opt"
          >{{ opt }}</button>
          <div v-if="!optionLabels.length" class="muted">{{ t('common_default') }}</div>
        </div>
        <div class="qty-row">
          <button type="button" @click="qty = Math.max(1, qty - 1)">−</button>
          <span>{{ qty }}</span>
          <button type="button" @click="qty = qty + 1">+</button>
        </div>
        <button type="button" class="sheet-ok" @click="confirmSheet">{{ t('common_add') }}</button>
      </div>
    </div>
  </div>
  <div v-else class="empty">{{ err || t('pdp_loading') }}</div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { ChevronLeft, ChevronRight, ShoppingBag, MessageCircle } from 'lucide-vue-next'
import { useRoute, useRouter } from 'vue-router'
import { fetchProductInterest, getProduct, money, type Product } from '@/api/products'
import { useCart } from '@/composables/cart'
import { useI18n } from '@/composables/i18n'
import { trackBrowse } from '@/composables/browseHistory'
import { addToCartServer } from '@/api/cartApi'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const cart = useCart()
const cartCount = computed(() => cart.count.value)

const product = ref<Product | null>(null)
const isOos = computed(() => Number((product.value as any)?.stock ?? 1) <= 0)
const interestCount = ref(0)
const size = ref('')
const qty = ref(1)
const sheetOpen = ref(false)
const busy = ref(false)
const err = ref('')

const discount = computed(() => {
  const p = product.value
  if (!p?.compareAt || p.compareAt <= p.price) return 0
  return Math.round((1 - p.price / p.compareAt) * 100)
})

const gallerySrc = computed(() => product.value?.images?.[0] || product.value?.image || '')
const galleryBg = computed(() =>
  gallerySrc.value ? {} : { background: 'linear-gradient(160deg, #E8F1EC 0%, #D8E4DC 55%, #EDE8E1 100%)' },
)

const selectedOffer = computed(() => {
  const p = product.value
  if (!p) return null
  return (p.offers || []).find((o) => o.label === size.value) || null
})
const displayPrice = computed(() => selectedOffer.value?.price ?? product.value?.price ?? 0)
const displayCompare = computed(() => {
  const c = selectedOffer.value?.compareAt ?? product.value?.compareAt
  const price = displayPrice.value
  if (!c || c <= price) return 0
  return c
})
const optionLabels = computed(() => {
  const p = product.value
  if (!p) return [] as string[]
  if (p.offers?.length) return p.offers.map((o) => o.label)
  return p.sizes || []
})
const sizeSummary = computed(() => size.value || (optionLabels.value.length ? t('common_choose_n') : t('common_default')))

function goBack() {
  if (window.history.length > 1) router.back()
  else router.push('/home')
}

function goChat() {
  const p = product.value
  if (!p) return
  router.push({
    path: '/chat',
    query: {
      sku: p.sku,
      name: p.name || p.sku,
      image: p.image || '',
      price: String(displayPrice.value ?? p.price ?? ''),
    },
  })
}

async function addLocalAndMaybeServer() {
  if (!product.value || busy.value) return
  busy.value = true
  try {
    const label = size.value || optionLabels.value[0] || 'default'
    size.value = label
    cart.add(product.value, label, qty.value)
    const offer = selectedOffer.value
    try {
      await addToCartServer({
        sku: product.value.sku,
        offer: offer?.id || '',
        qty: qty.value,
      })
    } catch {
      /* local cart still kept */
    }
    sheetOpen.value = false
  } finally {
    busy.value = false
  }
}

async function doWish() { /* wishlist cookie handled server-side via /wishlist when available */ }
function doAdd() {
  if (optionLabels.value.length && !size.value) {
    sheetOpen.value = true
    return
  }
  await addLocalAndMaybeServer()
  alert(t('common_saved_locally'))
}

async function doBuy() {
  if (optionLabels.value.length && !size.value) {
    sheetOpen.value = true
    return
  }
  await addLocalAndMaybeServer()
  router.push('/checkout')
}

async function confirmSheet() {
  await addLocalAndMaybeServer()
  alert(t('common_saved_locally'))
}

async function load() {
  const sku = String(route.params.sku || route.query.sku || '').trim()
  if (!sku) {
    err.value = 'Missing sku'
    interestCount.value = 0
    return
  }
  err.value = ''
  const p = await getProduct(decodeURIComponent(sku))
  product.value = p || null
  if (!p) {
    err.value = 'Not found'
    return
  }
  const prefOffer = route.query.offer ? String(route.query.offer) : ''
  const prefOption = route.query.option ? String(route.query.option) : route.query.size ? String(route.query.size) : ''
  if (prefOffer && p.offers?.length) {
    const byId = p.offers.find((o) => o.id === prefOffer || o.label === prefOffer)
    if (byId) size.value = byId.label
  } else if (prefOption) size.value = prefOption
  else if (p.offers?.[0]) size.value = p.offers[0].label
  else if (p.sizes?.[0]) size.value = p.sizes[0]
  trackBrowse({ sku: p.sku, name: p.name, image: p.image || '', price: p.price })
  interestCount.value = await fetchProductInterest(p.sku)
}

onMounted(load)
watch(() => [route.params.sku, route.query.sku], load)

const notifyBusy = ref(false)
const notifyMsg = ref('')
async function notifyMe() {
  notifyBusy.value = true
  notifyMsg.value = ''
  try {
    const email = window.prompt('Email for back-in-stock notice') || ''
    if (!email || !email.includes('@')) { notifyMsg.value = 'Email required'; return }
    const sku = String((product.value && (product.value.sku || product.value.id)) || route.params.id || '')
    const res = await fetch('/api/notify-me', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ email, sku, offer: '', country: 'US' }),
    })
    const data = await res.json().catch(() => ({}))
    notifyMsg.value = data.ok ? "We'll email you when this is back." : (data.error || 'Failed')
  } catch {
    notifyMsg.value = 'Network error'
  } finally {
    notifyBusy.value = false
  }
}
</script>

<style lang="scss" scoped>
@import '@/styles/theme.scss';
.page { min-height: 100vh; background: $hb-paper; padding-bottom: 90px; }
.gallery { position: relative; aspect-ratio: 1/1; background: $hb-soft; }
.gallery-img { width: 100%; height: 100%; object-fit: cover; display: block; }
.back { position: absolute; left: 14px; top: calc(12px + env(safe-area-inset-top)); width: 40px; height: 40px; border: 0; border-radius: 14px; background: rgba(255,255,255,0.92); color: #121816; display: inline-flex; align-items: center; justify-content: center; box-shadow: 0 4px 20px rgba(18,24,22,0.08); cursor: pointer; z-index: 2; }
.pills { position: absolute; left: 12px; bottom: 12px; display: flex; gap: 6px; }
.pill { background: rgba(255,255,255,0.92); border-radius: 999px; padding: 4px 10px; font-size: 12px; font-weight: 700; }
.pill.coral { background: $hb-price; color: #fff; }
.body { padding: 16px; }
.ships { font-size: 12px; color: $hb-forest; font-weight: 650; }
.title { margin: 8px 0; font-size: 22px; line-height: 1.25; color: $hb-ink; }
.interest { color: $hb-deep; font-weight: 600; margin: 0 0 8px; font-size: 13px; color: $hb-muted; font-weight: 560; }
.price-row { display: flex; gap: 8px; align-items: baseline; }
.price { font-size: 24px; font-weight: 780; color: $hb-ink; }
.was { color: $hb-muted; text-decoration: line-through; }
.fx { margin-top: 4px; font-size: 12px; color: $hb-muted; }
.sku-row {
  margin-top: 14px; width: 100%; border: 0; background: $hb-white; border-radius: 14px;
  padding: 12px 14px; display: flex; gap: 8px; align-items: center; box-shadow: $hb-shadow-soft; cursor: pointer;
}
.sku-k { color: $hb-muted; font-size: 12px; }
.sku-v { flex: 1; text-align: right; font-weight: 680; }
.chev { color: $hb-muted; }
.specs { margin-top: 14px; background: $hb-white; border-radius: 14px; padding: 8px 12px; box-shadow: $hb-shadow-soft; }
.spec { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid $hb-line; font-size: 13px; }
.spec:last-child { border-bottom: 0; }
.k { color: $hb-muted; }
.v { font-weight: 650; }
.blurb { margin-top: 14px; color: $hb-ink; line-height: 1.5; font-size: 14px; }
.cta-spacer { height: 12px; }
.sticky-cta {
  position: fixed; left: 0; right: 0; bottom: 0; z-index: 40;
  display: flex; gap: 8px; align-items: center;
  padding: 10px 12px calc(10px + env(safe-area-inset-bottom));
  background: rgba(255,255,255,0.96); border-top: 1px solid $hb-line;
}
.dock { position: relative; width: 46px; height: 46px; border: 0; border-radius: 14px; background: #fff; color: #121816; display: inline-flex; align-items: center; justify-content: center; box-shadow: 0 4px 16px rgba(18,24,22,0.06); cursor: pointer; }
.dock.chat { width: auto; padding: 0 10px; display: flex; align-items: center; gap: 4px; }
.lab { font-size: 12px; font-weight: 700; }
.badge {
  position: absolute; top: -4px; right: -4px; min-width: 16px; height: 16px; border-radius: 999px;
  background: $hb-price; color: #fff; font-size: 10px; font-weight: 700; display: flex; align-items: center; justify-content: center;
}
.btn {
  height: 44px; border-radius: 14px; border: 0; font-weight: 740; cursor: pointer; flex: 1;
  &.outline { background: $hb-soft; color: $hb-forest; }
  &.solid { background: $hb-price; color: #fff; }
}
.empty { padding: 80px 20px; text-align: center; color: $hb-muted; }
.sheet-mask { position: fixed; inset: 0; background: rgba(0,0,0,0.35); z-index: 60; display: flex; align-items: flex-end; }
.sheet { width: 100%; background: #fff; border-radius: 18px 18px 0 0; padding: 16px 16px calc(16px + env(safe-area-inset-bottom)); }
.sheet-title { font-weight: 740; font-size: 16px; margin-bottom: 10px; }
.opts { display: flex; flex-wrap: wrap; gap: 8px; }
.opt {
  border: 1px solid $hb-line; background: $hb-paper; border-radius: 999px; padding: 8px 12px; cursor: pointer;
  &.on { background: $hb-forest; color: #fff; border-color: $hb-forest; }
}
.muted { color: $hb-muted; font-size: 13px; }
.qty-row { display: flex; align-items: center; gap: 16px; margin: 16px 0; font-size: 18px; font-weight: 700; }
.qty-row button { width: 36px; height: 36px; border: 0; border-radius: 10px; background: $hb-paper; cursor: pointer; }
.sheet-ok { width: 100%; height: 48px; border: 0; border-radius: 14px; background: $hb-price; color: #fff; font-weight: 740; cursor: pointer; }
.body { background: #fff; border-radius: 20px 20px 0 0; margin-top: -16px; position: relative; padding-top: 14px; }
.price { font-size: 26px; font-weight: 800; color: $hb-price; }
.price.oos { color: #9CA3AF; }
.was { font-size: 13px; color: #9CA3AF; text-decoration: line-through; margin-left: 6px; }
.interest { color: $hb-deep !important; font-size: 12px; font-weight: 600; margin-top: 8px; }
.ship-pills { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
.pill { display: inline-flex; padding: 4px 10px; border-radius: 999px; font-size: 11px; font-weight: 600; background: #F3F4F6; color: #374151; }
.pill.ok { background: #ECFDF5; color: #047857; }
.pill.info { background: #E0F2FE; color: #0E7490; }
.pill.amber { background: #FEF3C7; color: #B45309; }
.pill.bad, .pill.coral { background: #FEE2E2; color: #B91C1C; }
.reviews-box { margin-top: 16px; padding-top: 14px; border-top: 1px solid #E8E4DC; }
.rev-head { display: flex; justify-content: space-between; align-items: center; font-size: 15px; }
.rev-empty { margin-top: 10px; padding: 14px; background: #F7F4EF; border-radius: 12px; text-align: center; color: #6B7280; font-size: 13px; }
.sticky-cta .btn.solid { background: $hb-price !important; }
.sticky-cta .btn.disabled { background: #E8E4DC !important; color: #9CA3AF !important; }
.dock.wish { flex-direction: column; font-size: 11px; color: $hb-muted; width: auto; padding: 0 6px; background: transparent; box-shadow: none; }
.sheet { border-radius: 20px 20px 0 0 !important; }
.sheet-ok { background: $hb-price !important; }
.page { background: $hb-paper; }

.fn-page { --ink:#0F2744; --teal:#0E7490; --amber:#B45309; --sand:#F7F4EF; }
</style>
