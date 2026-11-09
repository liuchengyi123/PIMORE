<template>
  <div class="pdp" v-if="product" data-figma="1:4">
    <div class="gallery">
      <img v-if="gallerySrc" class="gallery-img" :src="gallerySrc" alt="" />
      <button type="button" class="icon back" @click="goBack" aria-label="返回">
        <ChevronLeft :size="22" :stroke-width="1.75" />
      </button>
      <div class="gtools">
        <button type="button" class="icon" :class="{ on: wished }" @click="doWish" aria-label="收藏">
          <Heart :size="18" :fill="wished ? 'currentColor' : 'none'" />
        </button>
        <button type="button" class="icon" @click="share" aria-label="分享">
          <Share2 :size="18" />
        </button>
        <button type="button" class="icon bell" @click="goReviews" aria-label="评价">
          <Bell :size="18" />
          <i v-if="interestCount > 0" />
        </button>
      </div>
      <div v-if="interestCount > 0" class="live bought">
        <Flame :size="14" /> {{ zh ? ('今日 ' + people(interestCount) + ' 人关注') : (people(interestCount) + ' interested') }}
      </div>
      <div v-if="interestCount > 0" class="live watch">
        <Eye :size="14" /> {{ zh ? (people(interestCount) + ' 人在看') : (people(interestCount) + ' watching') }}
      </div>
      <div v-if="thumbs.length" class="counter">{{ activeShot + 1 }}/{{ thumbs.length }}</div>
      <button v-if="thumbs.length > 1" type="button" class="next" @click="nextShot" aria-label="下一张">
        <ChevronRight :size="18" />
      </button>
    </div>

    <div v-if="thumbs.length > 1" class="thumbs">
      <button v-for="(src, i) in thumbs" :key="src + i" type="button" :class="{ on: activeShot === i }" @click="activeShot = i">
        <img :src="src" alt="" />
      </button>
    </div>

    <div class="body">
      <h1 class="title">{{ product.name }}</h1>
      <p class="blurb">{{ product.blurb || t('pdp_blurb_default') }}</p>
      <div class="price-row">
        <span class="price" :class="{ oos: isOos }">{{ money(displayPrice) }}</span>
        <span v-if="displayCompare" class="was">{{ money(displayCompare) }}</span>
        <span v-if="discount" class="off">{{ zh ? ('立减 ' + discount + '%') : (discount + '% OFF') }}</span>
      </div>

      <button type="button" class="ship" @click="goShip">
        <Truck :size="18" />
        <span>
          <b>{{ shipTitle }}</b>
          <small>{{ shipSub }}</small>
        </span>
        <ChevronRight :size="18" class="chev" />
      </button>

      <div class="split">
        <button type="button" class="cell" @click="goChat">
          <MessageCircle :size="18" />
          <span>
            <b>{{ zh ? '问答' : 'Q&A' }}</b>
            <small>{{ zh ? '问问客服' : 'Ask support' }}</small>
          </span>
          <ChevronRight :size="16" />
        </button>
        <button type="button" class="cell" @click="goReviews">
          <FileText :size="18" />
          <span>
            <b>{{ zh ? '评价' : 'Reviews' }}</b>
            <small>{{ interestCount > 0 ? (zh ? (people(interestCount) + ' 人关注') : (people(interestCount) + ' interested')) : (zh ? '暂无评价' : 'No reviews yet') }}</small>
          </span>
          <ChevronRight :size="16" />
        </button>
      </div>

      <div class="perks">
        <div v-for="perk in perks" :key="perk.title" class="perk">
          <span class="bubble"><component :is="perk.icon" :size="16" /></span>
          <b>{{ perk.title }}</b>
          <small>{{ perk.sub }}</small>
        </div>
      </div>

      <div v-if="colorLabels.length" class="opt-row">
        <span class="opt-k">{{ zh ? '颜色' : 'Color' }}</span>
        <div class="swatches">
          <button
            v-for="opt in colorLabels"
            :key="opt"
            type="button"
            class="swatch"
            :class="{ on: size === opt }"
            :style="{ background: swatch(opt) }"
            :aria-label="opt"
            @click="size = opt"
          />
        </div>
        <button type="button" class="opt-more" @click="sheetOpen = true">
          {{ size || (zh ? '请选择' : 'Choose') }} <ChevronRight :size="14" />
        </button>
      </div>
      <div v-if="specLabels.length" class="opt-row specs">
        <span class="opt-k">{{ zh ? '规格' : 'Size' }}</span>
        <div class="pills">
          <button
            v-for="opt in specLabels"
            :key="opt"
            type="button"
            class="pill"
            :class="{ on: pickedSpec === opt }"
            @click="pickSpec(opt)"
          >{{ opt }}</button>
        </div>
      </div>

      <div class="qty-row">
        <span class="qty-lab">{{ zh ? '数量' : 'Qty' }}</span>
        <div class="qty-ctrl">
          <button type="button" @click="qty = Math.max(1, qty - 1)" aria-label="减少">−</button>
          <span>{{ qty }}</span>
          <button type="button" @click="qty = qty + 1" aria-label="增加">+</button>
        </div>
      </div>

      <div class="reviews-box" ref="reviewsEl">
        <div class="rev-head"><strong>{{ zh ? '评价' : 'Reviews' }}</strong></div>
        <div class="rev-empty">{{ zh ? '暂无评价' : 'No reviews yet' }}</div>
      </div>
    </div>

    <div class="sticky-cta">
      <template v-if="isOos">
        <button type="button" class="btn disabled" disabled>{{ t('out_of_stock') || (zh ? '缺货' : 'Sold out') }}</button>
        <button type="button" class="btn outline" @click="notifyMe" :disabled="notifyBusy">{{ notifyBusy ? '…' : (zh ? '到货通知' : 'Notify me') }}</button>
      </template>
      <template v-else>
        <button type="button" class="btn outline" @click="doAdd"><ShoppingCart :size="16" /> {{ zh ? '加入购物车' : 'Add to Cart' }}</button>
        <button type="button" class="btn solid" @click="doBuy"><Zap :size="16" /> {{ zh ? '立即购买' : 'Buy Now' }}</button>
      </template>
    </div>
    <p v-if="notifyMsg" class="notify">{{ notifyMsg }}</p>

    <div v-if="sheetOpen" class="sheet-mask" @click="sheetOpen = false">
      <div class="sheet" @click.stop data-figma="1:3">
        <div class="grab" aria-hidden="true"></div>
        <div class="sheet-head">
          <img v-if="gallerySrc" :src="gallerySrc" alt="" />
          <div>
            <strong>{{ product.name }}</strong>
            <div class="sheet-price">{{ money(displayPrice) }}</div>
            <div class="muted">{{ product.blurb || t('pdp_blurb_default') }}</div>
          </div>
          <button type="button" class="x" @click="sheetOpen = false" aria-label="关闭">×</button>
        </div>
        <template v-if="colorLabels.length">
          <div class="sheet-title">{{ zh ? '颜色' : 'Color' }}</div>
          <div class="sheet-colors">
            <button v-for="opt in colorLabels" :key="'c'+opt" type="button" class="cdot" :class="{ on: size === opt }" @click="size = opt">
              <i :style="{ background: swatch(opt) }" />
              <span>{{ opt }}</span>
            </button>
          </div>
        </template>
        <template v-if="specLabels.length">
          <div class="sheet-title">{{ zh ? '规格' : 'Size' }}</div>
          <div class="opts">
            <button v-for="opt in specLabels" :key="'s'+opt" type="button" class="opt" :class="{ on: pickedSpec === opt }" @click="pickSpec(opt)">{{ opt }}</button>
          </div>
        </template>
        <div class="qty-row sheet-qty">
          <span class="qty-lab">{{ zh ? '数量' : 'Quantity' }}</span>
          <div class="qty-ctrl">
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
import { Bell, ChevronLeft, ChevronRight, Eye, FileText, Flame, Heart, MessageCircle, Share2, ShieldCheck, ShoppingCart, Sparkles, Truck, Zap } from 'lucide-vue-next'
import { useRoute, useRouter } from 'vue-router'
import { fetchProductInterest, getProduct, money, type Product } from '@/api/products'
import { useCart } from '@/composables/cart'
import { useI18n } from '@/composables/i18n'
import { trackBrowse } from '@/composables/browseHistory'
import { addToCartServer } from '@/api/cartApi'
import { shelfProduct } from '@/catalog/shelf'

const { t, lang } = useI18n()
const zh = computed(() => String(lang.value).startsWith('zh'))
const route = useRoute()
const router = useRouter()
const cart = useCart()

const product = ref<Product | null>(null)
const isOos = computed(() => Number((product.value as { stock?: number } | null)?.stock ?? 1) <= 0)
const interestCount = ref(0)
const size = ref('')
const spec = ref('')
const qty = ref(1)
const sheetOpen = ref(false)
const busy = ref(false)
const err = ref('')
const wished = ref(false)
const reviewsEl = ref<HTMLElement | null>(null)

const SWATCHES: [RegExp, string][] = [
  [/珊瑚|coral/i, '#F96141'],
  [/黑|black/i, '#1A1A1A'],
  [/海军|navy/i, '#243E73'],
  [/蓝|blue/i, '#3B6FD8'],
  [/绿|olive|green/i, '#3E5C45'],
  [/灰|gray|grey|heather/i, '#C5C8CE'],
  [/白|white/i, '#F4F4F5'],
  [/米|beige|奶油|cream/i, '#E6D3BE'],
  [/粉|pink/i, '#F3B6C4'],
]

function swatch(label: string) {
  for (const [re, hex] of SWATCHES) if (re.test(label)) return hex
  return ''
}

function people(n: number) {
  if (n >= 10000) return (n / 10000).toFixed(1).replace(/\.0$/, '') + (zh.value ? '万' : 'w')
  if (n >= 1000) return (n / 1000).toFixed(1).replace(/\.0$/, '') + (zh.value ? '千' : 'k')
  return String(n)
}

const discount = computed(() => {
  const price = displayPrice.value
  const compare = displayCompare.value
  if (!compare || compare <= price) return 0
  return Math.round((1 - price / compare) * 100)
})

const activeShot = ref(0)
const thumbs = computed(() => {
  const p = product.value
  const list = (p?.images || []).filter(Boolean)
  if (list.length) return list.slice(0, 5)
  return p?.image ? [p.image] : []
})
const gallerySrc = computed(() => thumbs.value[activeShot.value] || product.value?.image || '')

function nextShot() {
  if (thumbs.value.length < 2) return
  activeShot.value = (activeShot.value + 1) % thumbs.value.length
}

function share() {
  const url = location.href
  const title = product.value?.name || 'Harbor'
  if (navigator.share) navigator.share({ title, url }).catch(() => {})
  else navigator.clipboard?.writeText(url).catch(() => {})
}

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
const colorLabels = computed(() => optionLabels.value.filter((label) => !!swatch(label)))
const specLabels = computed(() => {
  const colors = new Set(colorLabels.value)
  const fromOffers = optionLabels.value.filter((label) => !colors.has(label))
  const fromSizes = (product.value?.sizes || []).filter((label) => !colors.has(label) && !fromOffers.includes(label))
  return [...fromOffers, ...fromSizes]
})
const pickedSpec = computed(() => (colorLabels.value.length ? spec.value : size.value))
function pickSpec(opt: string) {
  if (colorLabels.value.length) spec.value = opt
  else size.value = opt
}

const shipTitle = computed(() => {
  const th = Number(cart.freeShipThreshold.value || 0)
  if (th > 0) return zh.value ? `满 $${th} 包邮` : `Free shipping over $${th}`
  return zh.value ? '可追踪物流' : 'Tracked shipping'
})
const shipSub = computed(() => {
  const raw = product.value?.shipsIn || ''
  if (!raw || /tracked shipping/i.test(raw)) return t('pdp_ships_default')
  return raw
})

const perks = computed(() => {
  const p = product.value
  return [
    { icon: ShieldCheck, title: zh.value ? '物流可追踪' : 'Tracked', sub: zh.value ? '下单后可查' : 'Follow the parcel' },
    { icon: Truck, title: zh.value ? '跨境直邮' : 'Ships direct', sub: p?.shipsIn || (zh.value ? '尽快发出' : 'Ships soon') },
    { icon: Sparkles, title: p?.material || (zh.value ? '日常好物' : 'Everyday'), sub: p?.care || (zh.value ? '家里用得上' : 'Made for home') },
    { icon: ShieldCheck, title: zh.value ? '精选上架' : 'Harbor pick', sub: p?.hub || (zh.value ? '小物见喜' : 'Small finds') },
  ]
})

function goBack() {
  if (window.history.length > 1) router.back()
  else router.push('/home')
}

function goShip() {
  router.push('/policy/shipping')
}

function goReviews() {
  reviewsEl.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
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

function doWish() { wished.value = !wished.value }

async function doAdd() {
  if (optionLabels.value.length && !size.value) {
    sheetOpen.value = true
    return
  }
  await addLocalAndMaybeServer()
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
}

async function load() {
  const sku = String(route.params.sku || route.query.sku || '').trim()
  if (!sku) {
    err.value = zh.value ? '缺少商品' : 'Missing sku'
    interestCount.value = 0
    product.value = null
    return
  }
  err.value = ''
  const decoded = decodeURIComponent(sku)
  const p = (await getProduct(decoded)) || shelfProduct(decoded) || null
  product.value = p
  activeShot.value = 0
  wished.value = false
  if (!p) {
    err.value = zh.value ? '没有找到这个商品' : 'Not found'
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
  else size.value = ''
  const colorSet = new Set((p.offers || []).map((o) => o.label).filter((label) => swatch(label)))
  spec.value = colorSet.size ? ((p.sizes || []).find((label) => !colorSet.has(label)) || '') : ''
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
    const email = window.prompt(zh.value ? '留下邮箱，到货后通知你' : 'Email for back-in-stock notice') || ''
    if (!email || !email.includes('@')) {
      notifyMsg.value = zh.value ? '需要有效邮箱' : 'Email required'
      return
    }
    const sku = String(product.value?.sku || product.value?.id || route.params.sku || '')
    const res = await fetch('/api/notify-me', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ email, sku, offer: '', country: 'US' }),
    })
    const data = await res.json().catch(() => ({}))
    notifyMsg.value = data.ok
      ? (zh.value ? '到货后会发邮件给你。' : "We'll email you when this is back.")
      : (data.error || (zh.value ? '没有提交成功' : 'Failed'))
  } catch {
    notifyMsg.value = zh.value ? '网络异常' : 'Network error'
  } finally {
    notifyBusy.value = false
  }
}
</script>

<style lang="scss" scoped>
@import '@/styles/theme.scss';

.pdp {
  min-height: 100vh;
  background: #fff;
  color: $hb-ink;
  padding-bottom: 108px;
  font-family: "Plus Jakarta Sans", "PingFang SC", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
.gallery {
  position: relative;
  height: 248px;
  background: #F4F5F7;
}
.gallery-img { width: 100%; height: 100%; object-fit: cover; display: block; }
.icon {
  width: 36px; height: 36px; border: 0; border-radius: 999px;
  background: rgba(255,255,255,0.94); color: #1C2430;
  display: inline-flex; align-items: center; justify-content: center; cursor: pointer;
}
.back { position: absolute; left: 14px; top: calc(12px + env(safe-area-inset-top)); z-index: 2; }
.gtools {
  position: absolute; right: 14px; top: calc(12px + env(safe-area-inset-top));
  display: flex; gap: 8px; z-index: 2;
}
.icon.on { color: #F96141; }
.bell { position: relative; }
.bell i {
  position: absolute; top: 6px; right: 7px; width: 7px; height: 7px; border-radius: 99px;
  background: #F96141; box-shadow: 0 0 0 2px #fff;
}
.live {
  position: absolute; z-index: 2; display: inline-flex; align-items: center; gap: 4px;
  height: 28px; padding: 0 10px; border-radius: 999px; font-size: 12px; font-weight: 700;
}
.bought { left: 14px; top: calc(58px + env(safe-area-inset-top)); background: #F96141; color: #fff; }
.watch { right: 14px; top: calc(58px + env(safe-area-inset-top)); background: rgba(255,255,255,0.94); color: #1C2430; }
.counter {
  position: absolute; left: 14px; bottom: 14px; z-index: 2;
  background: rgba(28,36,48,0.55); color: #fff; border-radius: 999px;
  font-size: 12px; font-weight: 700; padding: 4px 8px;
}
.next {
  position: absolute; right: 12px; top: 50%; transform: translateY(-50%); z-index: 2;
  width: 32px; height: 32px; border: 0; border-radius: 999px; background: #fff; color: #1C2430;
  display: inline-flex; align-items: center; justify-content: center; cursor: pointer;
  box-shadow: 0 4px 14px rgba(28,36,48,0.12);
}
.thumbs { display: flex; gap: 8px; padding: 12px 16px 0; overflow-x: auto; }
.thumbs button {
  flex: 0 0 56px; width: 56px; height: 56px; padding: 0; border-radius: 12px;
  border: 1.5px solid #E8E4DC; overflow: hidden; background: #F6F4F2; cursor: pointer;
}
.thumbs button.on { border: 2px solid #F96141; }
.thumbs img { width: 100%; height: 100%; object-fit: cover; display: block; }
.body { padding: 16px 16px 8px; }
.title { margin: 2px 0 0; font-size: 22px; line-height: 1.2; letter-spacing: -0.03em; font-weight: 800; }
.blurb { margin: 6px 0 0; color: #8B919A; font-size: 14px; line-height: 1.4; }
.price-row { display: flex; align-items: baseline; gap: 8px; margin-top: 12px; }
.price { font-size: 28px; font-weight: 800; letter-spacing: -0.04em; color: #F96141; line-height: 1; }
.price.oos { color: #9CA3AF; }
.was { font-size: 14px; color: #B0B6BE; text-decoration: line-through; }
.off { background: #FFF1EC; color: #F96141; border-radius: 8px; padding: 3px 8px; font-size: 12px; font-weight: 800; }
.ship {
  margin-top: 14px; width: 100%; border: 0; background: #FFF6F3; color: #1C2430;
  border-radius: 16px; padding: 12px 14px; display: flex; gap: 10px; align-items: center;
  text-align: left; cursor: pointer;
}
.ship :deep(svg) { color: #F96141; flex: none; }
.ship span { flex: 1; display: flex; flex-direction: column; gap: 2px; }
.ship b { font-size: 14px; }
.ship small { color: #8B919A; font-size: 12px; }
.chev { color: #C4C8CE; }
.split { display: grid; grid-template-columns: 1fr 1fr; margin-top: 16px; border-top: 1px solid #F1EEEA; border-bottom: 1px solid #F1EEEA; }
.cell {
  border: 0; background: transparent; display: flex; align-items: center; gap: 8px;
  padding: 12px 4px; cursor: pointer; text-align: left; color: #1C2430;
}
.cell + .cell { border-left: 1px solid #F1EEEA; padding-left: 12px; }
.cell span { flex: 1; display: flex; flex-direction: column; }
.cell b { font-size: 14px; }
.cell small { color: #8B919A; font-size: 12px; margin-top: 2px; }
.cell :deep(svg) { color: #F96141; flex: none; }
.perks { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-top: 16px; text-align: center; }
.perk { display: flex; flex-direction: column; align-items: center; gap: 4px; }
.bubble {
  width: 40px; height: 40px; border-radius: 999px; background: #FFF1EC; color: #F96141;
  display: inline-flex; align-items: center; justify-content: center;
}
.perk b { font-size: 11px; line-height: 1.25; }
.perk small { color: #8B919A; font-size: 10px; line-height: 1.3; }
.opt-row { display: flex; align-items: center; gap: 8px; margin-top: 12px; min-height: 36px; }
.opt-row.specs { margin-top: 8px; }
.opt-k { font-size: 14px; font-weight: 800; flex: none; }
.swatches { display: flex; align-items: center; gap: 8px; flex: 1; min-width: 0; }
.pills { display: flex; gap: 6px; flex: 1; min-width: 0; overflow-x: auto; scrollbar-width: none; }
.pills::-webkit-scrollbar { display: none; }
.swatch {
  width: 22px; height: 22px; border-radius: 999px; border: 0; padding: 0; cursor: pointer; flex: none;
  box-shadow: inset 0 0 0 2px #fff, 0 0 0 1px #E4E0DA;
}
.swatch.on { box-shadow: inset 0 0 0 2px #fff, 0 0 0 2px #F96141; }
.pill {
  height: 32px; border: 1px solid #E6E1DA; background: #fff; border-radius: 999px;
  padding: 0 12px; cursor: pointer; font-weight: 700; font-size: 13px; color: #1C2430; flex: none;
}
.pill.on { background: #F96141; color: #fff; border-color: #F96141; }
.opt-more {
  margin-left: auto; border: 0; background: transparent; color: #8B919A; flex: none;
  display: inline-flex; align-items: center; gap: 1px; cursor: pointer; font-size: 13px; font-weight: 650;
}
.qty-row { display: flex; align-items: center; justify-content: space-between; margin-top: 16px; }
.qty-lab { font-size: 14px; font-weight: 700; }
.qty-ctrl {
  display: flex; align-items: center; gap: 0; background: #F6F5F4; border-radius: 999px; padding: 4px;
}
.body .qty-ctrl { margin-right: 76px; }
.qty-ctrl button {
  width: 32px; height: 32px; border: 0; border-radius: 999px; background: transparent; cursor: pointer; font-size: 18px;
}
.qty-ctrl span { min-width: 28px; text-align: center; font-weight: 700; }
.reviews-box { margin-top: 18px; padding-top: 14px; border-top: 1px solid #F1EEEA; }
.rev-head { font-size: 16px; }
.rev-empty { margin-top: 10px; color: #8B919A; font-size: 13px; }
.sticky-cta {
  position: fixed; left: 50%; transform: translateX(-50%); width: min(100vw, 768px); bottom: 0; z-index: 40;
  display: flex; gap: 10px; align-items: center;
  padding: 12px 16px calc(12px + env(safe-area-inset-bottom));
  background: #fff; border-top: 1px solid #F1EEEA;
}
.btn {
  height: 48px; border-radius: 999px; font-weight: 750; cursor: pointer; flex: 1; font-size: 15px;
  display: inline-flex; align-items: center; justify-content: center; gap: 6px;
}
.btn.outline { background: #fff; color: #F96141; border: 1.5px solid #F96141; }
.btn.solid { background: #F96141; color: #fff; border: 0; text-decoration: none; }
.btn.disabled { background: #E8E4DC; color: #9CA3AF; border: 0; }
.notify { position: fixed; left: 16px; right: 16px; bottom: 84px; z-index: 41; text-align: center; color: #8B919A; font-size: 12px; }
.empty { padding: 80px 20px; text-align: center; color: $hb-muted; }
.empty .btn { display: inline-flex; margin-top: 12px; padding: 0 18px; }
.sheet-mask {
  position: fixed; inset: 0; background: rgba(28,36,48,0.45); z-index: 60;
  display: flex; align-items: flex-end; justify-content: center;
}
.sheet {
  width: min(100%, 768px); background: #fff; border-radius: 22px 22px 0 0;
  padding: 10px 16px calc(16px + env(safe-area-inset-bottom));
}
.grab { width: 36px; height: 4px; border-radius: 99px; background: #E6E2DC; margin: 0 auto 12px; }
.sheet-head { display: grid; grid-template-columns: 72px 1fr auto; gap: 12px; align-items: start; }
.sheet-head img { width: 72px; height: 72px; border-radius: 12px; object-fit: cover; background: #F6F4F2; }
.sheet-head strong { display: block; font-size: 16px; letter-spacing: -0.02em; }
.sheet-price { color: #F96141; font-weight: 800; font-size: 18px; margin-top: 2px; }
.muted { color: #8B919A; font-size: 13px; margin-top: 2px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.x { border: 0; background: transparent; font-size: 22px; color: #8B919A; cursor: pointer; line-height: 1; }
.sheet-title { margin: 14px 0 8px; font-size: 14px; font-weight: 800; color: #1C2430; }
.sheet-colors { display: flex; justify-content: space-between; gap: 4px; }
.cdot {
  flex: 1; min-width: 0; border: 0; background: transparent; padding: 0;
  display: flex; flex-direction: column; align-items: center; gap: 6px; cursor: pointer; color: #5C6570; font-size: 11px;
}
.cdot i {
  width: 30px; height: 30px; border-radius: 999px;
  box-shadow: inset 0 0 0 2px #fff, 0 0 0 1px #E4E0DA;
}
.cdot span { max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cdot.on i { box-shadow: inset 0 0 0 2px #fff, 0 0 0 2px #F96141; }
.cdot.on { color: #F96141; font-weight: 800; }
.opts { display: flex; flex-wrap: wrap; gap: 8px; }
.opt {
  height: 34px; min-width: 52px; border: 1px solid #E6E1DA; background: #fff; border-radius: 999px;
  padding: 0 14px; cursor: pointer; font-weight: 700; font-size: 13px; color: #1C2430;
}
.opt.on { background: #F96141; color: #fff; border-color: #F96141; }
.sheet-qty { margin: 14px 0 14px; }
.sheet-ok { width: 100%; height: 48px; border: 0; border-radius: 999px; background: #F96141; color: #fff; font-weight: 750; cursor: pointer; font-size: 16px; }
</style>
