<template>
  <div class="fn-page page" v-if="product" data-figma="M05">
    <div class="gallery" :style="galleryBg">
      <img v-if="gallerySrc" class="gallery-img" :src="gallerySrc" alt="" />
      <div class="pills">
        <span class="pill">{{ product.category }}</span>
        <span v-if="discount" class="pill coral">-{{ discount }}%</span>
      </div>
      <button type="button" class="back" @click="goBack" aria-label="back"><ChevronLeft :size="22" :stroke-width="1.75" /></button>
      <div class="gtools">
        <button type="button" @click="doWish" aria-label="save"><Heart :size="18" /></button>
        <button type="button" @click="share" aria-label="share"><Share2 :size="18" /></button>
      </div>
    </div>
    <div v-if="thumbs.length > 1" class="thumbs">
      <button v-for="(src, i) in thumbs" :key="src + i" type="button" :class="{ on: activeShot === i }" @click="activeShot = i">
        <img :src="src" alt="" />
      </button>
    </div>

    <div class="body">
      <h1 class="title">{{ product.name }}</h1>
      <p class="blurb top">{{ product.blurb || t('pdp_blurb_default') }}</p>
      <div class="price-row">
        <span class="price" :class="{ oos: isOos }">{{ money(displayPrice) }}</span>
        <span v-if="displayCompare" class="was">{{ money(displayCompare) }}</span>
        <span v-if="discount" class="off">{{ zh ? ('省' + discount + '%') : (discount + '% OFF') }}</span>
      </div>
      <p v-if="interestCount > 0" class="interest">{{ t('pdp_interest', { n: interestCount }) }}</p>
      <div class="ship-bar">{{ t('pdp_ship_tracked') }} · {{ product.shipsIn || t('pdp_ships_default') }}</div>
      <button type="button" class="sku-row" @click="sheetOpen = true">
        <span class="sku-k">{{ t('common_option') }}</span>
        <span class="sku-v">{{ sizeSummary }} · {{ zh ? '数量' : 'Qty' }} {{ qty }}</span>
        <ChevronRight :size="18" :stroke-width="1.7" class="chev" />
      </button>
      <div v-if="optionLabels.length" class="opt-block">
        <div class="opt-lab">{{ t('common_option') }}</div>
        <div class="opts">
          <button v-for="opt in optionLabels" :key="'p'+opt" type="button" class="opt" :class="{ on: size === opt }" @click="size = opt">{{ opt }}</button>
        </div>
      </div>
      <div class="qty-row page-qty">
        <span class="qty-lab">{{ zh ? '数量' : 'Qty' }}</span>
        <div class="qty-ctrl">
          <button type="button" @click="qty = Math.max(1, qty - 1)">−</button>
          <span>{{ qty }}</span>
          <button type="button" @click="qty = qty + 1">+</button>
        </div>
      </div>
      <div class="reviews-box">
        <div class="rev-head"><strong>{{ t('reviews') || '评价' }}</strong></div>
        <div class="rev-empty">{{ t('reviews_empty') || '暂无评价' }}</div>
      </div>
      <div class="cta-spacer" />
    </div>

    <div class="sticky-cta">
      <button type="button" class="dock wish" @click="doWish" aria-label="wishlist">♡<span class="lab">收藏</span></button>
      <template v-if="isOos">
        <button type="button" class="btn disabled" disabled>{{ t('out_of_stock') || (zh ? '缺货' : 'Sold out') }}</button>
        <button type="button" class="btn outline" @click="notifyMe" :disabled="notifyBusy">{{ notifyBusy ? "…" : (zh ? '到货通知' : 'Notify me') }}</button>
      <p v-if="notifyMsg" class="tiny" style="margin-top:8px">{{ notifyMsg }}</p>
      </template>
      <template v-else>
        <button type="button" class="btn outline" @click="doAdd"><ShoppingCart :size="16" /> {{ t('common_add') }}</button>
        <button type="button" class="btn solid" @click="doBuy"><Zap :size="16" /> {{ t('common_buy_now') }}</button>
      </template>
    </div>

    <div v-if="sheetOpen" class="sheet-mask" @click="sheetOpen = false">
      <div class="sheet" data-figma="1:3" @click.stop>
        <div class="grab" aria-hidden="true"></div>
        <button type="button" class="x" @click="sheetOpen = false" aria-label="close">×</button>
        <div class="sheet-head">
          <img v-if="gallerySrc" :src="gallerySrc" alt="" />
          <span v-else class="sheet-ph" aria-hidden="true"></span>
          <div>
            <div class="brand">Pimo</div>
            <strong>{{ product.name }}</strong>
            <div class="sheet-price">{{ money(displayPrice) }}</div>
            <div class="muted">{{ product.blurb || t('pdp_blurb_default') }}</div>
          </div>
        </div>
        <div v-if="colorOpts.length" class="opt-sec">
          <div class="sheet-title">{{ zh ? '颜色' : 'Color' }}</div>
          <div class="swatches">
            <button v-for="opt in colorOpts" :key="'c'+opt.label" type="button" class="swatch" :class="{ on: size === opt.label }" @click="size = opt.label">
              <span class="dot" :style="opt.hex ? { background: opt.hex } : undefined">
                <img v-if="opt.image && !opt.hex" :src="opt.image" alt="" />
              </span>
              <span>{{ opt.label }}</span>
            </button>
          </div>
        </div>
        <div v-if="sizeOpts.length" class="opt-sec">
          <div class="sheet-title">{{ sizeTitle }}</div>
          <div class="opts">
            <button v-for="opt in sizeOpts" :key="opt.label" type="button" class="opt" :class="{ on: (fitPick || size) === opt.label }" @click="pickFit(opt.label)">
              <img v-if="opt.image" :src="opt.image" alt="" />
              {{ opt.label }}
            </button>
          </div>
        </div>
        <div v-if="!optionLabels.length" class="muted">{{ t('common_default') }}</div>
        <div class="qty-row">
          <span class="qty-lab">{{ zh ? '数量' : 'Quantity' }}</span>
          <div class="qty-pill">
            <button type="button" @click="qty = Math.max(1, qty - 1)">−</button>
            <span>{{ qty }}</span>
            <button type="button" @click="qty = qty + 1">+</button>
          </div>
        </div>
        <button type="button" class="sheet-ok" @click="confirmSheet">{{ zh ? '确认加入购物车' : 'Confirm add to cart' }}</button>
      </div>
    </div>
  </div>
  <div v-else class="empty">
    <p>{{ err || t('pdp_loading') }}</p>
    <router-link v-if="err" class="btn solid" to="/browse">{{ t('tab_browse') }}</router-link>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { ChevronLeft, ChevronRight, Heart, Share2, ShoppingCart, Zap } from 'lucide-vue-next'
import { useRoute, useRouter } from 'vue-router'
import { fetchProductInterest, getProduct, money, type Product } from '@/api/products'
import { useCart } from '@/composables/cart'
import { useI18n } from '@/composables/i18n'
import { trackBrowse } from '@/composables/browseHistory'
import { addToCartServer } from '@/api/cartApi'
import previewShot from '@/assets/home/new-2.jpg'

const { t, lang } = useI18n()
const zh = computed(() => String(lang.value).startsWith('zh'))
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

const activeShot = ref(0)
const thumbs = computed(() => {
  const p = product.value
  const list = (p?.images || []).filter(Boolean)
  if (list.length) return list.slice(0, 5)
  return p?.image ? [p.image] : []
})
const gallerySrc = computed(() => thumbs.value[activeShot.value] || product.value?.image || '')
function share() {
  const url = location.href
  const title = product.value?.name || 'Pimo'
  if (navigator.share) navigator.share({ title, url }).catch(() => {})
  else navigator.clipboard?.writeText(url).catch(() => {})
}
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
const COLOR_RULES: { re: RegExp; hex: string }[] = [
  { re: /\bcoral\b|珊瑚|橙/, hex: '#F96141' },
  { re: /\bblack\b|黑/, hex: '#1C2430' },
  { re: /\bwhite\b|白/, hex: '#F4F4F5' },
  { re: /\bgr[ae]y\b|灰/, hex: '#C5C8CE' },
  { re: /\bnavy\b|藏青|海军/, hex: '#1E3A5F' },
  { re: /\bolive\b|橄榄/, hex: '#5C6B4A' },
  { re: /\bred\b|红/, hex: '#E23D3D' },
  { re: /\bblue\b|蓝/, hex: '#2F6FED' },
  { re: /\bgreen\b|绿/, hex: '#3E7A4D' },
  { re: /\bpink\b|粉/, hex: '#E7A0B0' },
  { re: /\bbrown\b|棕|咖/, hex: '#8C5A3C' },
  { re: /\bbeige\b|卡其/, hex: '#E6D3B3' },
  { re: /\byellow\b|黄/, hex: '#E2B340' },
  { re: /\bpurple\b|紫/, hex: '#6B4C9A' },
]
function swatchHex(label: string) {
  const s = label.trim().toLowerCase()
  return COLOR_RULES.find((rule) => rule.re.test(s))?.hex || ''
}
const optionItems = computed(() => optionLabels.value.map((label) => {
  const offer = product.value?.offers?.find((o) => o.label === label)
  return { label, hex: swatchHex(label), image: offer?.image || '' }
}))
const colorOpts = computed(() => optionItems.value.filter((o) => o.hex))
const fitPick = ref('')
const sizeOpts = computed(() => {
  const sizes = product.value?.sizes || []
  if (colorOpts.value.length && sizes.length) return sizes.map((label) => ({ label, hex: '', image: '' }))
  const taken = new Set(colorOpts.value.map((o) => o.label))
  const rest = optionItems.value.filter((o) => !taken.has(o.label))
  return rest.length ? rest : (colorOpts.value.length ? [] : optionItems.value)
})
const sizeTitle = computed(() => {
  const sized = sizeOpts.value.some((o) => /^(xxs|xs|s|m|l|xl|xxl|xxxl|\d+(\.\d+)?)$/i.test(o.label.trim()))
  if (sized) return zh.value ? '尺码' : 'Size'
  return zh.value ? '规格' : 'Option'
})
const sizeSummary = computed(() => {
  const bits = [size.value, fitPick.value].filter(Boolean)
  return bits.join(' · ') || (optionLabels.value.length ? t('common_choose_n') : t('common_default'))
})
function pickFit(label: string) {
  if (colorOpts.value.length && (product.value?.sizes || []).includes(label)) fitPick.value = label
  else size.value = label
}

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
    const base = size.value || optionLabels.value[0] || 'default'
    size.value = base
    const label = fitPick.value && fitPick.value !== base ? `${base} / ${fitPick.value}` : base
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
async function doAdd() {
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

function applyFitDefault(p: Product) {
  const sizes = p.sizes || []
  const colored = (p.offers || []).some((o) => swatchHex(o.label))
  fitPick.value = colored && sizes.length ? (sizes.includes('M') ? 'M' : sizes[0]) : ''
}

async function load() {
  const sku = String(route.params.sku || route.query.sku || '').trim()
  if (!sku && route.query.preview === 'sheet') {
    const preview: Product = {
      id: 'preview',
      sku: 'preview',
      name: '每日连帽衫',
      price: 68,
      category: 'Pimo',
      image: previewShot,
      images: [previewShot],
      blurb: '柔软耐穿，适合每天穿。',
      offers: [
        { id: 'coral', label: '珊瑚', price: 68 },
        { id: 'black', label: '黑色', price: 68 },
        { id: 'gray', label: '麻灰', price: 68 },
        { id: 'navy', label: '藏青', price: 68 },
        { id: 'olive', label: '橄榄', price: 68 },
      ],
      sizes: ['XS', 'S', 'M', 'L', 'XL', 'XXL'],
    }
    product.value = preview
    size.value = '珊瑚'
    applyFitDefault(preview)
    sheetOpen.value = true
    err.value = ''
    return
  }
  if (!sku) {
    err.value = 'Missing sku'
    interestCount.value = 0
    return
  }
  err.value = ''
  const p = await getProduct(decodeURIComponent(sku))
  product.value = p || null
  activeShot.value = 0
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
  applyFitDefault(p)
  trackBrowse({ sku: p.sku, name: p.name, image: p.image || '', price: p.price })
  interestCount.value = await fetchProductInterest(p.sku)
}

onMounted(load)
watch(() => [route.params.sku, route.query.sku], load)
watch(() => [route.query.sheet, product.value], () => {
  const flag = String(route.query.sheet || '')
  if ((flag === 'add' || flag === 'options') && product.value) sheetOpen.value = true
})

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
.title { margin: 2px 0 4px; font-size: 20px; line-height: 1.25; letter-spacing: -0.03em; color: $hb-ink; font-weight: 800; }
.interest { color: $hb-deep; font-weight: 600; margin: 0 0 8px; font-size: 13px; color: $hb-muted; font-weight: 560; }
.price-row { display: flex; gap: 8px; align-items: baseline; }
.price { font-size: 24px; font-weight: 780; color: $hb-ink; }
.was { color: $hb-muted; text-decoration: line-through; }
.fx { margin-top: 4px; font-size: 12px; color: $hb-muted; }
.sku-row {
  margin-top: 12px; width: 100%; border: 1px solid #F1EEEA; background: #fff; border-radius: 16px;
  padding: 12px 14px; display: flex; gap: 8px; align-items: center; box-shadow: none; cursor: pointer;
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
  position: fixed; left: 50%; transform: translateX(-50%); width: min(100vw, 768px); bottom: 0; z-index: 40;
  box-shadow: 0 -8px 24px rgba(28,36,48,0.06);
  display: flex; gap: 10px; align-items: center;
  padding: 12px 16px calc(12px + env(safe-area-inset-bottom));
  background: #fff; border-top: 1px solid #F1EEEA;
}
.dock { position: relative; width: 46px; height: 46px; border: 0; border-radius: 14px; background: #fff; color: #121816; display: inline-flex; align-items: center; justify-content: center; box-shadow: 0 4px 16px rgba(18,24,22,0.06); cursor: pointer; }
.dock.chat { width: auto; padding: 0 10px; display: flex; align-items: center; gap: 4px; }
.lab { font-size: 12px; font-weight: 700; }
.badge {
  position: absolute; top: -4px; right: -4px; min-width: 16px; height: 16px; border-radius: 999px;
  background: $hb-price; color: #fff; font-size: 10px; font-weight: 700; display: flex; align-items: center; justify-content: center;
}
.gtools { position: absolute; right: 12px; top: calc(12px + env(safe-area-inset-top)); display: flex; gap: 8px; z-index: 2; }
.gtools button { width: 40px; height: 40px; border: 0; border-radius: 14px; background: rgba(255,255,255,0.92); color: #1C2430; display: inline-flex; align-items: center; justify-content: center; cursor: pointer; }
.thumbs { display: flex; gap: 8px; padding: 10px 16px 0; background: #fff; }
.thumbs button { width: 56px; height: 56px; padding: 0; border-radius: 12px; border: 1px solid #E8E4DC; overflow: hidden; background: #F6F4F2; cursor: pointer; }
.thumbs button.on { border: 2px solid #F96141; }
.thumbs img { width: 100%; height: 100%; object-fit: cover; display: block; }
.opt-block { margin-top: 14px; }
.opt-lab { font-size: 13px; font-weight: 700; margin-bottom: 8px; }
.page-qty { margin-top: 14px; }
.btn {
  height: 52px; border-radius: 999px; font-weight: 740; cursor: pointer; flex: 1; font-size: 15px;
  display: inline-flex; align-items: center; justify-content: center; gap: 6px;
  &.outline { background: #fff; color: #F96141; border: 1.5px solid #F96141; }
  &.solid { background: #F96141; color: #fff; border: 0; }
}
.empty { padding: 80px 20px; text-align: center; color: $hb-muted; }
.empty .btn { display: inline-flex; margin-top: 12px; padding: 0 16px; align-items: center; text-decoration: none; }
.sheet-mask { position: fixed; inset: 0; background: rgba(28,36,48,0.45); z-index: 60; display: flex; align-items: flex-end; justify-content: center; }
.sheet { position: relative; width: min(100%, 768px); background: #fff; border-radius: 22px 22px 0 0; padding: 10px 16px calc(16px + env(safe-area-inset-bottom)); }
.grab { width: 36px; height: 4px; border-radius: 99px; background: #E6E2DC; margin: 0 auto 12px; }
.sheet-head { display: grid; grid-template-columns: 84px 1fr; gap: 12px; align-items: start; margin: 4px 28px 16px 0; }
.sheet-head img, .sheet-ph { width: 84px; height: 84px; border-radius: 14px; object-fit: cover; background: #F6F4F2; display: block; }
.brand { font-size: 12px; color: #8B919A; }
.sheet-head strong { display: block; font-size: 18px; letter-spacing: -0.02em; }
.sheet-price { color: #1C2430; font-weight: 800; margin-top: 4px; font-size: 18px; }
.sheet-head .muted { display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; margin-top: 2px; }
.x {
  position: absolute; right: 12px; top: 16px; width: 32px; height: 32px; border: 0; border-radius: 50%;
  background: #F4F1EC; color: #5C6570; font-size: 20px; cursor: pointer; line-height: 1;
}
.opt-sec { margin-top: 8px; }
.sheet-title { font-weight: 800; font-size: 15px; margin-bottom: 10px; color: #1C2430; }
.swatches { display: flex; gap: 14px; overflow-x: auto; padding: 4px 2px 8px; }
.swatch { border: 0; background: transparent; display: flex; flex-direction: column; align-items: center; gap: 6px; min-width: 56px; cursor: pointer; color: #5C6570; font-size: 12px; }
.dot { width: 36px; height: 36px; border-radius: 50%; border: 1px solid rgba(28,36,48,0.08); overflow: hidden; display: block; }
.dot img { width: 100%; height: 100%; object-fit: cover; }
.swatch.on .dot { box-shadow: 0 0 0 2px #fff, 0 0 0 4px #F96141; }
.swatch.on { color: #1C2430; font-weight: 700; }
.opts { display: flex; flex-wrap: wrap; gap: 8px; }
.opt {
  height: 36px; border: 1px solid #E8E4DC; background: #fff; border-radius: 999px; padding: 0 14px; cursor: pointer; font-weight: 650;
  display: inline-flex; align-items: center; gap: 6px;
  &.on { background: #FF6B4A; color: #fff; border-color: #FF6B4A; }
  img { width: 18px; height: 18px; border-radius: 50%; object-fit: cover; }
}
.qty-pill {
  display: inline-flex; align-items: center; border: 1px solid #E6E2DC; border-radius: 999px; overflow: hidden;
  button { width: 36px; height: 36px; border: 0; background: #fff; cursor: pointer; font-size: 18px; }
  span { min-width: 24px; text-align: center; font-weight: 700; }
}
.muted { color: $hb-muted; font-size: 13px; }
.qty-row { display: flex; align-items: center; justify-content: space-between; margin: 18px 0 16px; }
.qty-lab { font-size: 14px; font-weight: 650; color: #5C6570; }
.qty-ctrl { display: flex; align-items: center; gap: 14px; font-size: 16px; font-weight: 700; }
.qty-ctrl button { width: 36px; height: 36px; border: 0; border-radius: 12px; background: #F6F4F2; cursor: pointer; }
.sheet-ok { width: 100%; height: 52px; border: 0; border-radius: 999px; background: #F96141; color: #fff; font-weight: 740; cursor: pointer; }
.body { background: #fff; border-radius: 20px 20px 0 0; margin-top: -16px; position: relative; padding-top: 14px; }
.price { font-size: 28px; font-weight: 800; color: $hb-price; letter-spacing: -0.03em; }
.price.oos { color: #9CA3AF; }
.was { font-size: 13px; color: #9CA3AF; text-decoration: line-through; margin-left: 6px; }
.interest { color: $hb-deep !important; font-size: 12px; font-weight: 600; margin-top: 8px; }
.ship-bar { margin-top: 12px; background: #FFF1EC; color: #C2410C; border-radius: 12px; padding: 10px 12px; font-size: 13px; font-weight: 650; }
.off { background: #FFF1EC; color: #F96141; border-radius: 999px; padding: 2px 8px; font-size: 12px; font-weight: 800; }
.blurb.top { margin-top: 4px; color: #8E949C; }
.pill { display: inline-flex; padding: 4px 10px; border-radius: 999px; font-size: 11px; font-weight: 600; background: #F3F4F6; color: #374151; }
.pill.ok { background: #ECFDF5; color: #047857; }
.pill.info { background: #E0F2FE; color: #0E7490; }
.pill.amber { background: #FEF3C7; color: #F96141; }
.pill.bad, .pill.coral { background: #FEE2E2; color: #B91C1C; }
.reviews-box { margin-top: 16px; padding-top: 14px; border-top: 1px solid #E8E4DC; }
.rev-head { display: flex; justify-content: space-between; align-items: center; font-size: 15px; }
.rev-empty { margin-top: 10px; padding: 14px; background: #FCFAF8; border-radius: 12px; text-align: center; color: #6B7280; font-size: 13px; }
.sticky-cta .btn.solid { background: $hb-price !important; }
.sticky-cta .btn.disabled { background: #E8E4DC !important; color: #9CA3AF !important; }
.dock.wish { flex-direction: column; font-size: 11px; color: $hb-muted; width: auto; padding: 0 6px; background: transparent; box-shadow: none; }
.sheet { width: min(100%, 768px); }
.sheet-ok { background: $hb-price !important; }
.page { background: $hb-paper; }

.fn-page { --ink:#1C2430; --teal:#0E7490; --amber:#F96141; --sand:#FCFAF8; }
</style>
