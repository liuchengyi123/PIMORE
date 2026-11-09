<template>
  <div class="page" data-figma="M14">
    <header class="head">
      <button type="button" class="back" @click="$router.back()" aria-label="back"><ChevronLeft :size="22" :stroke-width="1.75" /></button>
      <h1>{{ zh ? '我的订单' : 'My orders' }}</h1>
    </header>
    <div class="tabs">
      <button type="button" class="tab" :class="{ on: filter === '' }" @click="filter=''">{{ zh ? '全部' : 'All' }}</button>
      <button type="button" class="tab" :class="{ on: filter === 'pending' }" @click="filter='pending'">{{ zh ? '待支付' : 'Unpaid' }}</button>
      <button type="button" class="tab" :class="{ on: filter === 'shipped' }" @click="filter='shipped'">{{ zh ? '运输中' : 'Shipping' }}</button>
      <button type="button" class="tab" :class="{ on: filter === 'paid' }" @click="filter='paid'">{{ zh ? '已完成' : 'Completed' }}</button>
      <button type="button" class="tab" :class="{ on: filter === 'return' }" @click="filter='return'">{{ zh ? '退货' : 'Returns' }}</button>
    </div>
    <div v-if="loading" class="state">{{ t('pdp_loading') }}</div>
    <div v-else-if="loginRequired" class="state">
      <p>{{ t('orders_login') }}</p>
      <router-link class="btn" :to="{ path: '/login', query: { next: '/orders' } }">{{ t('me_sign_in') }}</router-link>
    </div>
    <div v-else-if="!visible.length" class="state">{{ t('orders_empty') }}</div>
    <div v-else class="list">
      <article v-for="o in visible" :key="o.id" class="card">
        <div class="row between">
          <span class="oid">HB-{{ o.id }} · {{ o.date || '' }}</span>
          <span class="pill" :class="pillClass(o.status)">{{ o.statusLabel || o.status }}</span>
        </div>
        <div class="thumbs">
          <img v-if="o.image" :src="o.image" alt="" />
          <div v-else class="ph">{{ zh ? '商品' : 'Item' }}</div>
        </div>
        <div class="row between meta">
          <span class="tiny">{{ o.itemCount ? o.itemCount + (zh ? ' 件' : ' items') : (zh ? '订单' : 'Order') }}{{ o.tracking ? ' · ' + o.tracking : '' }}</span>
          <span class="price">{{ o.due }}</span>
        </div>
        <div class="actions">
          <button v-if="/pend|unpaid|await/i.test(o.status)" type="button" class="btn" @click.stop="pay(o)">{{ zh ? '去支付' : 'Pay' }}</button>
          <button v-if="/ship/i.test(o.status)" type="button" class="btn soft" @click.stop="track(o)">{{ zh ? '物流' : 'Track' }}</button>
          <button v-else type="button" class="btn soft" @click.stop="again(o)">{{ zh ? '再买' : 'Buy again' }}</button>
          <button type="button" class="btn" @click="$router.push('/orders/' + encodeURIComponent(o.id))">{{ zh ? '详情' : 'Details' }}</button>
        </div>
      </article>
    </div>
    <AppTabBar active="me" />
  </div>
</template>

<script setup lang="ts">
import { ChevronLeft } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { fetchOrders, type OrderRow } from '@/api/accountApi'
import { useCart } from '@/composables/cart'
import { useI18n } from '@/composables/i18n'
import AppTabBar from '@/components/AppTabBar.vue'

const { t, lang } = useI18n()
const router = useRouter()
const cart = useCart()
const zh = computed(() => String(lang.value).startsWith('zh'))
const orders = ref<OrderRow[]>([])
const filter = ref('')
const visible = computed(() => {
  if (!filter.value) return orders.value
  return orders.value.filter(o => String(o.status || '').toLowerCase().includes(filter.value))
})
const loading = ref(true)
const loginRequired = ref(false)

onMounted(async () => {
  loading.value = true
  const res = await fetchOrders()
  orders.value = res.orders || []
  loginRequired.value = !!res.loginRequired
  loading.value = false
})

function pillClass(status: string) {
  const s = String(status || '').toLowerCase()
  if (s.includes('ship')) return 'ship'
  if (s.includes('paid') || s.includes('pay')) return 'paid'
  if (s.includes('pend') || s.includes('await')) return 'pend'
  return ''
}
function pay(o: OrderRow) {
  router.push('/orders/' + encodeURIComponent(o.id))
}
function track(o: OrderRow) {
  router.push('/orders/' + encodeURIComponent(o.id))
}
async function again(o: OrderRow) {
  const root = (await import('@/api/config')).apiRoot().replace(/\/$/, '')
  await fetch(root + '/orders/' + encodeURIComponent(o.id) + '/again', { method: 'POST', credentials: 'include' })
  await cart.refreshFromServer()
  router.push('/cart')
}
</script>

<style lang="scss" scoped>
@import '@/styles/theme.scss';
.page { min-height: 100vh; background: #FCFAF8; padding: 0 0 24px; }
.head {
  display: flex; align-items: flex-end; gap: 10px; margin-bottom: 12px;
  background: #F96141; color: #fff; padding: 16px 16px 18px; padding-top: calc(16px + env(safe-area-inset-top));
}
.back { width: 36px; height: 36px; border: 0; border-radius: 12px; background: transparent; color: #fff; display: inline-flex; align-items: center; justify-content: center; }
h1 { margin: 0; font-size: 28px; font-weight: 800; color: #fff; }
.tabs { display: flex; gap: 8px; overflow: auto; margin: 0 16px 12px; }
.tab {
  height: 34px; padding: 0 14px; border-radius: 999px; border: 0; background: #fff;
  font-size: 13px; color: #1C2430; cursor: pointer; font-weight: 650;
  &.on { background: #F96141; color: #fff; }
}
.list { padding: 0 16px; }
.list { display: flex; flex-direction: column; gap: 10px; }
.card { background: #fff; border: 1px solid #E8E4DC; border-radius: 16px; padding: 12px; }
.row { display: flex; align-items: center; gap: 8px; }
.between { justify-content: space-between; }
.oid { font-size: 11px; color: #6B7280; }
.pill { font-size: 11px; font-weight: 600; padding: 4px 10px; border-radius: 999px; background: #F3F4F6; color: $hb-ink; }
.pill.paid { background: #ECFDF5; color: #047857; }
.pill.ship { background: #E0F2FE; color: #0E7490; }
.pill.pend { background: #FEF3C7; color: #F96141; }
.thumbs { display: flex; gap: 10px; margin-top: 10px; }
.thumbs img, .ph { width: 64px; height: 64px; border-radius: 10px; object-fit: cover; background: linear-gradient(145deg,#bae6fd,#0369a1); }
.ph { display: flex; align-items: flex-end; padding: 12px; color: #fff; font-size: 11px; font-weight: 600; box-sizing: border-box; }
.meta { margin-top: 10px; }
.tiny { font-size: 11px; color: #6B7280; }
.price { font-size: 16px; font-weight: 800; color: $hb-price; }
.actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 12px; }
.btn {
  height: 36px; padding: 0 14px; border-radius: 999px; border: 0; background: #F96141; color: #fff;
  font-size: 12px; font-weight: 600; cursor: pointer; text-decoration: none; display: inline-flex; align-items: center;
}
.btn.soft { background: #fff; color: $hb-ink; border: 1px solid #E8E4DC; }
.state { text-align: center; color: $hb-muted; padding: 40px 8px; }
</style>
