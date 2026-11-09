<template>
  <div class="page" data-figma="1:26">
    <header class="hero">
      <div class="brand-row">
        <div class="brand">
          <span class="mark" aria-hidden="true"><Home :size="16" :stroke-width="2.4" /></span>
          <div>
            <div class="logo">Harbor</div>
            <div class="tag">{{ zh ? '每日发现，更开心的家' : 'Everyday finds. Happier homes.' }}</div>
          </div>
        </div>
        <div class="tools">
          <button type="button" class="tool" aria-label="search" @click="$router.push('/search')"><Search :size="22" :stroke-width="1.8" /></button>
          <button type="button" class="tool" aria-label="cart" @click="$router.push('/cart')">
            <ShoppingBag :size="22" :stroke-width="1.8" />
            <i v-if="cartCount" class="badge">{{ cartCount > 9 ? '9+' : cartCount }}</i>
          </button>
        </div>
      </div>
      <h1>{{ zh ? '我的订单' : 'My Orders' }}</h1>
    </header>

    <div class="tabs-wrap">
      <div class="tabs" role="tablist">
        <button v-for="tab in tabs" :key="tab.id" type="button" class="tab" :class="{ on: filter === tab.id }" @click="setFilter(tab.id)">
          {{ tab.label }}
        </button>
      </div>
    </div>

    <div v-if="loading" class="state">{{ t('pdp_loading') }}</div>
    <div v-else-if="loginRequired" class="state">
      <p>{{ t('orders_login') }}</p>
      <router-link class="btn" :to="{ path: '/login', query: { next: '/orders' } }">{{ t('me_sign_in') }}</router-link>
    </div>
    <div v-else-if="!visible.length" class="blank">
      <span class="blank-ico" aria-hidden="true"><Package :size="26" :stroke-width="1.75" /></span>
      <h2>{{ filter ? (zh ? '这里还没有订单' : 'Nothing in this tab') : (zh ? '还没有订单' : 'No orders yet') }}</h2>
      <p>{{ zh ? '下单之后，物流和发票会列在这里。' : 'Tracking and invoices show up here after you order.' }}</p>
      <router-link class="btn" to="/browse">{{ zh ? '去逛逛' : 'Browse' }}</router-link>
    </div>
    <div v-else class="list">
      <article v-for="o in visible" :key="o.id" class="card" @click="open(o)">
        <div class="top">
          <div class="oid">{{ displayId(o.id) }}</div>
          <div class="status-wrap">
            <div class="status" :class="tone(o)">
              <component :is="toneIcon(o)" :size="12" :stroke-width="2.2" />
              <span>{{ statusText(o) }}</span>
            </div>
            <ChevronRight :size="16" :stroke-width="2" class="chev" />
          </div>
        </div>
        <div class="sub">{{ metaLine(o) }}</div>
        <div class="body">
          <div class="thumbs">
            <template v-if="thumbs(o).length">
              <img v-for="(src, i) in thumbs(o)" :key="src + i" :src="src" alt="" />
            </template>
            <div v-else class="ph">{{ zh ? '商品' : 'Item' }}</div>
          </div>
          <div class="sum">
            <div class="sum-lab">{{ zh ? '订单合计' : 'Order Total' }}</div>
            <div class="price">{{ o.due || '—' }}</div>
          </div>
        </div>
        <div class="actions">
          <button type="button" class="btn" @click.stop="act(o)">{{ actionLabel(o) }}</button>
        </div>
      </article>
    </div>
    <AppTabBar active="me" />
  </div>
</template>

<script setup lang="ts">
import { Check, ChevronRight, Clock3, Home, Package, RotateCcw, Search, ShoppingBag, Truck } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { fetchOrders, postBuyAgain, type OrderRow } from '@/api/accountApi'
import { useI18n } from '@/composables/i18n'
import { useCart } from '@/composables/cart'
import AppTabBar from '@/components/AppTabBar.vue'

const { t, lang } = useI18n()
const zh = computed(() => String(lang.value).startsWith('zh'))
const router = useRouter()
const cart = useCart()
const cartCount = computed(() => cart.count.value)
const orders = ref<OrderRow[]>([])
const returns = ref<OrderRow[]>([])
const filter = ref('')
const loading = ref(true)
const loginRequired = ref(false)

const tabs = computed(() => [
  { id: '', label: zh.value ? '全部' : 'All' },
  { id: 'pending', label: zh.value ? '待支付' : 'Unpaid' },
  { id: 'shipped', label: zh.value ? '运输中' : 'Shipping' },
  { id: 'paid', label: zh.value ? '已完成' : 'Completed' },
  { id: 'return', label: zh.value ? '退货' : 'Returns' },
])

const visible = computed(() => {
  if (filter.value === 'return') return returns.value
  if (!filter.value) return orders.value
  return orders.value.filter((o) => tone(o) === filter.value || String(o.status || '').toLowerCase().includes(filter.value))
})

onMounted(load)

async function load() {
  loading.value = true
  const res = await fetchOrders()
  orders.value = res.orders || []
  loginRequired.value = !!res.loginRequired
  loading.value = false
}

async function setFilter(id: string) {
  filter.value = id
  if (id !== 'return' || returns.value.length || loginRequired.value) return
  const res = await fetchOrders('returns')
  returns.value = res.orders || []
}

function displayId(id: string) {
  const raw = String(id || '').trim()
  if (!raw) return '—'
  if (/^#/.test(raw)) return raw
  if (/^h/i.test(raw)) return '#' + raw
  return '#H' + raw
}

function tone(o: OrderRow) {
  const s = String(o.status || o.statusLabel || '').toLowerCase()
  if (s.includes('return') || s.includes('refund') || /退/.test(o.statusLabel || '')) return 'return'
  if (s.includes('ship') || /运输|发货/.test(o.statusLabel || '')) return 'shipped'
  if (s.includes('paid') || s.includes('complete') || /完成|已付/.test(o.statusLabel || '')) return 'paid'
  if (s.includes('pend') || s.includes('await') || /待/.test(o.statusLabel || '')) return 'pending'
  return 'pending'
}

function toneIcon(o: OrderRow) {
  const k = tone(o)
  if (k === 'shipped') return Truck
  if (k === 'paid') return Check
  if (k === 'return') return RotateCcw
  return Clock3
}

function statusText(o: OrderRow) {
  const k = tone(o)
  if (!zh.value) {
    if (k === 'shipped') return 'Shipping'
    if (k === 'paid') return 'Completed'
    if (k === 'return') return 'Return'
    return 'Unpaid'
  }
  if (k === 'shipped') return '运输中'
  if (k === 'paid') return '已完成'
  if (k === 'return') return '退货'
  return '待支付'
}

function metaLine(o: OrderRow) {
  const n = o.itemCount || o.items?.length || (o.image ? 1 : 0)
  const count = n ? (zh.value ? `${n} 件` : `${n} item${n > 1 ? 's' : ''}`) : ''
  return [o.date, count].filter(Boolean).join(' · ') || (zh.value ? '订单' : 'Order')
}

function thumbs(o: OrderRow) {
  const fromItems = (o.items || []).map((it) => it.image).filter(Boolean) as string[]
  const list = fromItems.length ? fromItems : o.image ? [o.image] : []
  return list.slice(0, 3)
}

function actionLabel(o: OrderRow) {
  const k = tone(o)
  if (zh.value) {
    if (k === 'pending') return '去支付'
    if (k === 'paid') return '再买一次'
    return '查看物流'
  }
  if (k === 'pending') return 'Pay'
  if (k === 'paid') return 'Buy again'
  return 'Track'
}

function open(o: OrderRow) {
  router.push('/orders/' + encodeURIComponent(o.id))
}

async function act(o: OrderRow) {
  const k = tone(o)
  if (k === 'paid') {
    try { await postBuyAgain(o.id) } catch { /* still open the cart */ }
    try { await cart.refreshFromServer() } catch { /* local cart remains */ }
    router.push('/cart')
    return
  }
  open(o)
}
</script>

<style lang="scss" scoped>
@import '@/styles/theme.scss';
.page { min-height: 100vh; background: #FCFAF8; padding-bottom: 24px; color: #1C2430; }
.hero {
  background: #F96141; color: #fff;
  padding: 14px 16px 28px;
  padding-top: calc(14px + env(safe-area-inset-top));
}
.brand-row { display: flex; align-items: center; justify-content: space-between; }
.brand { display: flex; align-items: center; gap: 8px; }
.mark {
  width: 28px; height: 28px; border-radius: 8px; background: rgba(255,255,255,0.18);
  display: inline-flex; align-items: center; justify-content: center;
}
.logo { font-size: 20px; font-weight: 800; letter-spacing: -0.03em; line-height: 1; }
.tag { margin-top: 2px; font-size: 11px; opacity: 0.9; }
.tools { display: flex; gap: 4px; }
.tool {
  position: relative; width: 36px; height: 36px; border: 0; background: transparent; color: #fff;
  display: inline-flex; align-items: center; justify-content: center; cursor: pointer;
}
.badge {
  position: absolute; top: 2px; right: 0; min-width: 16px; height: 16px; padding: 0 4px;
  border-radius: 99px; background: #fff; color: #F96141; font-size: 10px; font-weight: 800;
  font-style: normal; display: inline-flex; align-items: center; justify-content: center;
}
h1 { margin: 18px 0 0; font-size: 28px; font-weight: 800; letter-spacing: -0.03em; }
.tabs-wrap { margin: -16px 16px 14px; }
.tabs {
  display: flex; gap: 2px; background: #fff; border-radius: 999px;
  padding: 5px; box-shadow: 0 8px 24px rgba(28, 36, 48, 0.06);
}
.tab {
  flex: 1 1 0; height: 34px; padding: 0 4px; border: 0; border-radius: 999px;
  background: transparent; color: #6B7280; font-size: 12px; font-weight: 700; cursor: pointer;
  white-space: nowrap;
  &.on { background: #F96141; color: #fff; }
}
.list { display: flex; flex-direction: column; gap: 10px; padding: 0 16px; }
.card {
  background: #fff; border-radius: 16px; padding: 12px 12px 10px;
  box-shadow: 0 6px 16px rgba(28, 36, 48, 0.05); cursor: pointer;
}
.top { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.oid { font-size: 15px; font-weight: 800; letter-spacing: -0.02em; line-height: 1.15; }
.status-wrap { display: inline-flex; align-items: center; gap: 1px; flex: 0 0 auto; }
.status {
  display: inline-flex; align-items: center; gap: 3px; height: 24px; padding: 0 8px;
  border-radius: 999px; font-size: 12px; font-weight: 700; letter-spacing: -0.01em;
  background: #FFF1EC; color: #F96141;
}
.status.paid { background: #E7F8EE; color: #1B9A52; }
.status.return { background: #F3F4F6; color: #8B919A; }
.chev { color: #C5CAD1; flex: 0 0 auto; }
.sub { margin-top: 2px; font-size: 12px; line-height: 1.2; color: #9AA1A9; }
.body { display: flex; align-items: center; justify-content: space-between; gap: 10px; margin-top: 8px; }
.thumbs { display: flex; gap: 6px; min-width: 0; }
.thumbs img, .ph {
  width: 56px; height: 56px; border-radius: 10px; object-fit: cover; background: #F6F1EC; flex: 0 0 auto;
}
.ph { display: flex; align-items: flex-end; padding: 6px; color: #8B919A; font-size: 11px; font-weight: 700; }
.sum { text-align: right; flex: 0 0 auto; }
.sum-lab { font-size: 11px; line-height: 1.15; color: #9AA1A9; }
.price { margin-top: 2px; font-size: 18px; font-weight: 800; letter-spacing: -0.03em; line-height: 1; color: #1C2430; }
.actions { display: flex; justify-content: flex-end; margin-top: 8px; }
.btn {
  height: 32px; padding: 0 14px; border: 0; border-radius: 999px; background: #F96141; color: #fff;
  font-size: 13px; font-weight: 700; letter-spacing: -0.01em; cursor: pointer; text-decoration: none;
  display: inline-flex; align-items: center;
}
.blank .btn, .state .btn { height: 40px; padding: 0 22px; font-size: 15px; }
.state { text-align: center; color: #8B919A; padding: 48px 16px; }
.state .btn { margin-top: 12px; }
.blank {
  margin: 28px 16px 0; padding: 36px 22px 28px; text-align: center;
  background: #fff; border-radius: 22px; box-shadow: 0 10px 28px rgba(28, 36, 48, 0.05);
}
.blank-ico {
  width: 64px; height: 64px; margin: 0 auto 14px; border-radius: 20px;
  background: #FFF1EC; color: #F96141;
  display: flex; align-items: center; justify-content: center;
}
.blank h2 { margin: 0; font-size: 20px; font-weight: 800; letter-spacing: -0.03em; color: #1C2430; }
.blank p { margin: 8px auto 0; max-width: 240px; font-size: 14px; line-height: 1.45; color: #8B919A; }
.blank .btn { margin-top: 18px; }
</style>
