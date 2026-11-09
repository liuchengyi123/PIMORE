<template>
  <div v-if="desk" class="drawer-mask" @click="leaveDrawer"></div>
  <div class="fn-page page" :class="{ desk }" data-figma="M23">
    <header class="sticky">
      <div class="head">
        <div>
          <h1>{{ t('cart_title') }} <small v-if="cart.syncing">…</small></h1>
          <p v-if="lines.length && !desk" class="count">{{ lines.length }}</p>
        </div>
        <button v-if="desk" type="button" class="drawer-x" @click="leaveDrawer" aria-label="关闭">×</button>
        <button v-else-if="lines.length" type="button" class="clear" @click="clear">{{ zhCart ? '清空' : 'Clear' }}</button>
      </div>
      <AppSearchBar v-if="!desk" compact navigate-on-focus />
    </header>

    <div v-if="!lines.length" class="empty">
      <ShoppingBag :size="40" :stroke-width="1.5" class="empty-ico" />
      <p>{{ t('cart_empty') }}</p>
      <router-link class="btn" to="/home">去逛逛</router-link>
    </div>

    <div v-else class="list">
      <div v-for="line in lines" :key="line.sku + '|' + line.offer" class="row">
        <img v-if="line.image" class="img" :src="line.image" alt="" @click="open(line.sku)" />
        <div class="body" @click="open(line.sku)">
          <div class="name">{{ line.name }}</div>
          <div class="meta">{{ zhCart ? '规格' : 'Option' }} · {{ line.size || line.offer || (zhCart ? '默认' : 'default') }}</div>
          <div class="price">{{ zhCart ? '价格' : 'Price' }} {{ money(line.price) }}</div>
        </div>
        <div class="qty">
          <button type="button" @click="bump(line, -1)" aria-label="minus"><Minus :size="14" :stroke-width="2" /></button>
          <span>{{ line.qty }}</span>
          <button type="button" @click="bump(line, 1)" aria-label="plus"><Plus :size="14" :stroke-width="2" /></button>
          <button type="button" class="trash" @click="askRemove(line)" aria-label="remove">×</button>
        </div>
      </div>
    </div>

    <div v-if="lines.length && minOrder > 0 && !desk" class="ship-card">
      <div class="ship-row"><span>{{ zhCart ? '起送金额' : 'Minimum order' }}</span><span class="tiny">{{ zhCart ? '还差 ' : '' }}{{ money(Math.max(0, minOrder - subtotal)) }}{{ zhCart ? '' : ' more' }}</span></div>
      <div class="ship-bar"><i :style="{ width: shipPct + '%' }"></i></div>
      <div class="tiny">{{ subtotal >= minOrder ? (zhCart ? '已满起送 · 包邮' : 'Minimum met · free shipping') : ((zhCart ? '满 ' : 'Minimum order ') + money(minOrder) + (zhCart ? ' 包邮' : ' · free shipping')) }}</div>
    </div>
    <div v-else-if="lines.length && !desk" class="ship-card">
      <div class="tiny">{{ zhCart ? '本单包邮' : 'Free shipping on this order' }}</div>
    </div>
    <div v-if="lines.length && desk" class="drawer-progress">
      <p>{{ shipNote }}</p>
      <div class="ship-meter" aria-hidden="false">
        <span class="track"><i :style="{ width: shipPct + '%' }"></i></span>
        <b>{{ shipPct }}%</b>
      </div>
    </div>
    <div v-if="lines.length" class="footer">
      <div class="sum">{{ zhCart ? '小计' : 'Subtotal' }} <b>{{ money(subtotal) }}</b></div>
      <button type="button" class="checkout" @click="$router.push('/checkout')">{{ zhCart ? '去结算' : 'Checkout' }}</button>
      <button v-if="desk" type="button" class="continue" @click="router.push('/browse')">{{ zhCart ? '继续购物' : 'Continue shopping' }}</button>
    </div>
    <AppTabBar v-if="!desk" active="cart" />
    <div v-if="showGap" class="gap-mask" @click.self="gapOff = true">
      <div class="gap-sheet" role="dialog" data-figma="5:9">
        <div class="grab" aria-hidden="true"></div>
        <div class="added">
          <svg class="tick" viewBox="0 0 22 22" width="22" height="22" aria-hidden="true"><circle cx="11" cy="11" r="9.2" fill="#fff" stroke="#FF6B4A" stroke-width="1.6"/><path d="M6.6 11.2l2.8 2.9 6-6.2" fill="none" stroke="#FF6B4A" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>
          {{ zhCart ? '已加入购物袋' : 'Added to bag' }}
        </div>
        <h2>{{ gapTitle }}</h2>
        <label class="gap-search">
          <svg viewBox="0 0 20 20" width="16" height="16" aria-hidden="true"><circle cx="8.5" cy="8.5" r="5.2" fill="none" stroke="#9AA1A9" stroke-width="1.6"/><path d="M12.4 12.4L17 17" stroke="#9AA1A9" stroke-width="1.6" stroke-linecap="round"/></svg>
          <input v-model="gapQ" :placeholder="zhCart ? '搜索商品…' : 'Search products…'" />
        </label>
        <div class="gap-tabs">
          <button type="button" :class="{ on: gapTab === 'rec' }" @click="gapTab = 'rec'">{{ zhCart ? '推荐' : 'Recommended' }}</button>
          <button type="button" :class="{ on: gapTab === 'deal' }" @click="gapTab = 'deal'">{{ zhCart ? '优惠' : 'Deals' }}</button>
        </div>
        <div class="gap-grid">
          <button v-for="p in shownPicks" :key="p.sku" type="button" class="gap-card" @click="addPick(p)">
            <img v-if="p.image" :src="p.image" alt="" />
            <span class="gap-ph" v-else aria-hidden="true"></span>
            <b>{{ p.name }}</b>
            <em>{{ money(p.price) }}</em>
          </button>
        </div>
        <p v-if="!shownPicks.length" class="tiny">{{ zhCart ? '没有匹配的商品' : 'No matches' }}</p>
        <button type="button" class="gap-go" @click="gapOff = true">{{ zhCart ? '去购物车' : 'Continue to cart' }}</button>
      </div>
    </div>
    <div v-if="pendingRemove" class="confirm-mask" @click.self="pendingRemove = null">
      <div class="confirm-card" role="dialog" data-figma="5:8">
        <div class="confirm-head">
          <h2>{{ zhCart ? '移除' : 'Remove' }}</h2>
          <span class="trash-art" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="22" height="22"><path d="M5 7h14M9 7V5h6v2M8 7l1 12h6l1-12" fill="none" stroke="#FF6B4A" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </span>
        </div>
        <p class="rm-name">{{ pendingRemove.name }}</p>
        <p>{{ zhCart ? '确定要从购物车移除这件商品吗？' : 'Are you sure you want to remove this item from your cart?' }}</p>
        <div class="confirm-actions">
          <button type="button" class="ghost" @click="pendingRemove = null">{{ zhCart ? '取消' : 'Cancel' }}</button>
          <button type="button" class="ok" @click="confirmRemove">{{ zhCart ? '移除' : 'Remove' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Minus, Plus, ShoppingBag } from 'lucide-vue-next'
import { listProducts, listSaleProducts, money, type Product } from '@/api/products'
import { useCart, type LocalCartLine } from '@/composables/cart'
import { useI18n } from '@/composables/i18n'
import AppTabBar from '@/components/AppTabBar.vue'
import AppSearchBar from '@/components/AppSearchBar.vue'
import shotA from '@/assets/home/just-1.jpg'
import shotB from '@/assets/home/just-2.jpg'
import shotC from '@/assets/home/flash-1.jpg'
import shotD from '@/assets/home/new-1.jpg'

const { t, lang } = useI18n()
const zhCart = computed(() => String(lang.value).startsWith('zh'))
const pendingRemove = ref<LocalCartLine | null>(null)
const gapOff = ref(false)
const cart = useCart()
const route = useRoute()
const router = useRouter()
const lines = computed(() => cart.lines.value)
const subtotal = computed(() => cart.subtotal.value)
/** Minimum checkout amount from live cart snapshot; 0 = no minimum. */
const minOrder = computed(() => Number(cart.minOrderAmount?.value ?? cart.freeShipThreshold?.value ?? 0) || 0)
const desk = ref(false)
const forceGap = computed(() => route.name === 'cart-gap' || route.query.gap === '1')
const showGap = computed(() => !gapOff.value && (forceGap.value || (lines.value.length > 0 && minOrder.value > 0 && subtotal.value < minOrder.value)))
const gapRemain = computed(() => Math.max(0, minOrder.value - subtotal.value))
const shipPct = computed(() => {
  if (minOrder.value <= 0) return subtotal.value > 0 ? 100 : 0
  return Math.min(100, Math.round((subtotal.value / minOrder.value) * 100))
})
const shipNote = computed(() => {
  if (minOrder.value <= 0 || subtotal.value >= minOrder.value) return zhCart.value ? '本单已包邮。' : 'This order ships free.'
  const left = money(gapRemain.value)
  return zhCart.value ? `还差 ${left} 即可包邮。` : `Only ${left} away from free shipping.`
})
const gapTitle = computed(() => {
  if (gapRemain.value > 0) {
    const left = money(gapRemain.value)
    return zhCart.value ? `再买 ${left} 即可包邮` : `Add ${left} more for free shipping`
  }
  return zhCart.value ? '再凑一点即可包邮' : 'Add a little more for free shipping'
})

const fallbacks: Product[] = [
  { id: 'pick-a', sku: 'pick-a', name: '家居精选', price: 12, category: 'daily', image: shotA },
  { id: 'pick-b', sku: 'pick-b', name: '日用好物', price: 22, category: 'daily', image: shotB },
  { id: 'pick-c', sku: 'pick-c', name: '限时热卖', price: 9, category: 'daily', image: shotC },
  { id: 'pick-d', sku: 'pick-d', name: '新品推荐', price: 15, category: 'daily', image: shotD },
]
const picks = ref<Product[]>([])
const gapTab = ref<'rec' | 'deal'>('rec')
const gapQ = ref('')
const shownPicks = computed(() => {
  const q = gapQ.value.trim().toLowerCase()
  return picks.value.filter((p) => !q || p.name.toLowerCase().includes(q) || p.sku.toLowerCase().includes(q)).slice(0, 4)
})

function syncDesk() {
  desk.value = window.matchMedia('(min-width: 960px)').matches
}
function leaveDrawer() {
  if (window.history.length > 1) router.back()
  else router.push('/home')
}
async function loadPicks() {
  try {
    const list = gapTab.value === 'deal' ? await listSaleProducts() : await listProducts('recommended')
    picks.value = list.length ? list : fallbacks
  } catch {
    picks.value = fallbacks
  }
}
function addPick(p: Product) {
  cart.add(p, p.offers?.[0]?.label || p.sizes?.[0] || (zhCart.value ? '默认' : 'default'), 1)
}
function askRemove(line: LocalCartLine) { pendingRemove.value = line }
function confirmRemove() {
  const line = pendingRemove.value
  pendingRemove.value = null
  if (line) bump(line, -line.qty)
}
function bump(line: LocalCartLine, delta: number) {
  cart.setQty(line.sku, line.offer || '', line.qty + delta)
}
function clear() {
  cart.clear()
}
function open(sku: string) {
  router.push({ path: '/pdp', query: { sku } })
}
onMounted(() => {
  syncDesk()
  window.addEventListener('resize', syncDesk)
  cart.refreshFromServer()
})
onUnmounted(() => window.removeEventListener('resize', syncDesk))
watch([showGap, gapTab], ([open]) => { if (open) loadPicks() }, { immediate: true })
</script>

<style lang="scss" scoped>
@import '@/styles/theme.scss';
.page { min-height: 100vh; background: $hb-paper; padding: 0 16px 120px; }
.sticky {
  position: sticky; top: 0; z-index: 20;
  background: rgba(247,244,239,0.94); backdrop-filter: blur(14px);
  padding: calc(12px + env(safe-area-inset-top)) 0 10px;
}
.head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
h1 { margin: 0; font-size: 24px; color: $hb-ink; font-weight: 780; }
h1 small { font-size: 12px; color: $hb-muted; font-weight: 600; }
.count { margin: 2px 0 0; font-size: 13px; color: $hb-muted; }
.trash { border: 0; background: transparent; color: #9AA0A8; font-size: 18px; cursor: pointer; }
.drawer-mask { position: fixed; inset: 0; z-index: 30; background: rgba(28,36,48,0.28); }
.drawer-x { border: 0; background: transparent; font-size: 28px; line-height: 1; color: #1C2430; cursor: pointer; }
.confirm-mask, .gap-mask {
  position: fixed; inset: 0; z-index: 140; background: rgba(28,36,48,0.45);
  display: flex; justify-content: center;
}
.confirm-mask { align-items: center; padding: 24px 16px; }
.gap-mask { align-items: flex-end; }
.confirm-card {
  width: min(100%, 420px); background: #fff; border-radius: 18px; padding: 18px 16px 16px;
  box-shadow: 0 18px 40px rgba(28,36,48,0.16); text-align: center;
}
.confirm-head { display: flex; align-items: center; justify-content: space-between; text-align: left; border-bottom: 1px solid #F1EEEA; padding-bottom: 8px; }
.confirm-card h2 { margin: 0; font-size: 24px; font-weight: 750; }
.confirm-card p { margin: 10px 0 0; color: #5C6570; font-size: 16px; line-height: 1.45; }
.rm-name { color: #1C2430 !important; font-size: 18px !important; font-weight: 700; }
.confirm-actions { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 16px; }
.confirm-actions button { height: 46px; border-radius: 12px; font-weight: 750; font-size: 16px; cursor: pointer; }
.confirm-actions .ghost { background: #fff; border: 1.5px solid #FF6B4A; color: #FF6B4A; }
.confirm-actions .ok { background: #FF6B4A; border: 0; color: #fff; }
.gap-sheet {
  width: min(100%, 440px); max-height: 88vh; overflow: auto; background: #fff;
  border-radius: 28px 28px 0 0; padding: 8px 18px calc(18px + env(safe-area-inset-bottom));
}
.grab { width: 42px; height: 4px; border-radius: 99px; background: #E6E2DC; margin: 4px auto 14px; }
.added { display: flex; align-items: center; justify-content: center; gap: 8px; color: #FF6B4A; font-weight: 700; font-size: 14px; }
.added .tick { display: block; flex: 0 0 auto; }
.gap-sheet h2 { margin: 10px 0 14px; text-align: center; font-size: 22px; line-height: 1.3; font-weight: 800; letter-spacing: -0.03em; color: #1C2430; }
.gap-search {
  display: flex; align-items: center; gap: 8px; height: 44px; border-radius: 12px;
  border: 1px solid #E6E2DC; padding: 0 12px; color: #8B919A; background: #fff;
}
.gap-search input { border: 0; flex: 1; outline: none; font-size: 14px; background: transparent; color: #1C2430; }
.gap-search input::placeholder { color: #A0A6AE; }
.gap-tabs { display: flex; gap: 22px; margin: 16px 0 12px; border-bottom: 1px solid #F3F0EC; }
.gap-tabs button { border: 0; background: transparent; padding: 8px 0 10px; font-size: 15px; font-weight: 650; color: #8B919A; cursor: pointer; }
.gap-tabs button.on { color: #1C2430; font-weight: 800; box-shadow: inset 0 -2px 0 #FF6B4A; }
.gap-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px 12px; }
.gap-card { border: 0; background: transparent; text-align: left; cursor: pointer; padding: 0; color: inherit; }
.gap-card img, .gap-ph { width: 100%; aspect-ratio: 1; object-fit: cover; border-radius: 12px; background: #F6F4F2; display: block; }
.gap-card b { display: block; margin-top: 10px; font-size: 14px; font-weight: 650; line-height: 1.35; letter-spacing: -0.01em; color: #1C2430; }
.gap-card em { display: block; margin-top: 4px; font-style: normal; color: #1C2430; font-weight: 800; font-size: 16px; }
.gap-go {
  width: 100%; height: 50px; margin-top: 18px; border: 0; border-radius: 12px;
  background: #FF6B4A; color: #fff; font-weight: 750; font-size: 16px; cursor: pointer;
}
@media (min-width: 960px) {
  .page.desk {
    position: fixed; top: 0; right: 0; width: min(420px, 100vw); height: 100vh;
    overflow: auto; z-index: 40; background: #fff; padding-bottom: 24px;
    border-left: 1px solid #EFEAE4; box-shadow: -12px 0 40px rgba(28,36,48,0.12);
  }
  .page.desk .sticky { background: #fff; }
  .page.desk h1 { font-size: 20px; }
  .page.desk .row { box-shadow: none; border-radius: 0; border-bottom: 1px solid #F1EEEA; background: transparent; padding: 14px 0; }
  .page.desk .footer {
    position: static; transform: none; width: auto; left: auto; bottom: auto;
    display: flex; flex-direction: column; align-items: stretch; gap: 10px;
    border-top: 1px solid #F1EEEA; margin-top: 12px; padding: 14px 0 0;
  }
  .page.desk .sum { display: flex; justify-content: space-between; align-items: baseline; font-size: 16px; color: #1C2430; }
  .page.desk .checkout, .page.desk .continue { width: 100%; height: 48px; border-radius: 10px; }
  .page.desk .continue { background: #fff; color: #1C2430; border: 1px solid #1C2430; font-weight: 750; cursor: pointer; }
  .drawer-progress { margin: 4px 0 2px; }
  .drawer-progress p { margin: 0 0 6px; font-size: 13px; line-height: 1.35; font-weight: 650; color: #1C2430; }
  .ship-meter { display: flex; align-items: center; gap: 8px; }
  .ship-meter .track { flex: 1; height: 12px; background: #E6E2DC; border-radius: 99px; overflow: hidden; }
  .ship-meter .track > i { display: block; height: 100%; background: #FF6B4A; border-radius: 99px; }
  .ship-meter b { min-width: 36px; text-align: right; font-size: 12px; line-height: 1; color: #5C6570; font-weight: 750; }
}
.clear { border: 0; background: transparent; color: $hb-muted; cursor: pointer; font-weight: 650; }
.empty { text-align: center; padding: 72px 16px; color: $hb-muted; }
.empty .btn { border-radius: 999px; background: #F96141; }
.empty-ico { color: $hb-muted; opacity: 0.55; margin-bottom: 10px; }
.btn {
  display: inline-block; margin-top: 14px; padding: 11px 18px; border-radius: 14px;
  background: $hb-coral; color: #fff; font-weight: 720;
}
.list { display: flex; flex-direction: column; gap: 10px; margin-top: 12px; }
.row {
  display: flex; gap: 12px; align-items: center; background: #fff; border-radius: 16px;
  padding: 12px; box-shadow: 0 8px 18px rgba(28,36,48,0.05);
}
.img { width: 74px; height: 74px; border-radius: 14px; object-fit: cover; background: $hb-soft; }
.body { flex: 1; min-width: 0; }
.name { font-weight: 680; font-size: 14px; color: $hb-ink; }
.meta { font-size: 12px; color: $hb-muted; margin-top: 2px; }
.price { margin-top: 6px; color: #F96141; font-weight: 760; }
.qty { display: flex; align-items: center; gap: 8px; }
.qty button {
  width: 30px; height: 30px; border: 0; border-radius: 10px; background: $hb-paper; cursor: pointer;
  display: inline-flex; align-items: center; justify-content: center; color: $hb-ink;
}
.footer {
  position: fixed; left: 50%; transform: translateX(-50%);
  width: min(100vw, 768px);
  bottom: calc(58px + env(safe-area-inset-bottom));
  background: #fff; border-top: 1px solid #F1EEEA; padding: 10px 16px;
  display: flex; align-items: center; gap: 10px; z-index: 90; color: #1C2430;
}
.sum { flex: 1; font-size: 13px; color: #8B919A; }
.sum b { color: #F96141; font-size: 20px; }
.checkout {
  border: 0; height: 44px; padding: 0 18px; border-radius: 999px; background: #F96141; color: #fff;
  font-weight: 740; cursor: pointer;
}
.ship-card {
  margin: 12px 0; background: #fff; border: 1px solid $hb-line; border-radius: 16px; padding: 14px;
}
.ship-row { display: flex; justify-content: space-between; font-size: 13px; font-weight: 600; color: $hb-ink; }
.ship-bar { margin-top: 8px; height: 8px; background: #E8E4DC; border-radius: 4px; overflow: hidden; }
.ship-bar > i { display: block; height: 100%; background: #F96141; }
.tiny { font-size: 11px; color: $hb-muted; margin-top: 6px; }
.price { color: #F96141 !important; }
.empty { padding: 80px 24px; text-align: center; }
.empty .btn { background: #F96141; color: #fff; border-radius: 999px; padding: 10px 18px; text-decoration: none; font-weight: 700; display: inline-block; margin-top: 16px; }

.fn-page { --ink:#1C2430; --teal:#0E7490; --amber:#F96141; --sand:#FCFAF8; }
</style>
