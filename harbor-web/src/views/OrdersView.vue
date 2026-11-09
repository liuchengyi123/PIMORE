<template>
  <div class="page" data-figma="M14">
    <header class="head">
      <button type="button" class="back" @click="$router.back()" aria-label="back"><ChevronLeft :size="22" :stroke-width="1.75" /></button>
      <h1>My orders</h1>
    </header>
    <div class="tabs">
      <button type="button" class="tab" :class="{ on: filter === '' }" @click="filter=''">All</button>
      <button type="button" class="tab" :class="{ on: filter === 'pending' }" @click="filter='pending'">To pay</button>
      <button type="button" class="tab" :class="{ on: filter === 'paid' }" @click="filter='paid'">Paid</button>
      <button type="button" class="tab" :class="{ on: filter === 'shipped' }" @click="filter='shipped'">Shipped</button>
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
          <div v-else class="ph">Item</div>
        </div>
        <div class="row between meta">
          <span class="tiny">{{ o.itemCount ? o.itemCount + ' items' : 'Order' }}{{ o.tracking ? ' · ' + o.tracking : '' }}</span>
          <span class="price">{{ o.due }}</span>
        </div>
        <div class="actions">
          <button v-if="/ship/i.test(o.status)" type="button" class="btn soft" @click.stop="track(o)">Track</button>
          <button v-else type="button" class="btn soft" @click.stop="again(o)">Buy again</button>
          <button type="button" class="btn" @click="$router.push('/orders/' + encodeURIComponent(o.id))">Details</button>
        </div>
      </article>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ChevronLeft } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import { fetchOrders, type OrderRow } from '@/api/accountApi'
import { useI18n } from '@/composables/i18n'

const { t } = useI18n()
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
function track(o: OrderRow) {
  // details page shows tracking
  location.assign('/orders/' + encodeURIComponent(o.id))
}
function again(_o: OrderRow) {
  location.assign('/home')
}
</script>

<style lang="scss" scoped>
@import '@/styles/theme.scss';
.page { min-height: 100vh; background: $hb-paper; padding: 8px 16px 40px; padding-top: calc(8px + env(safe-area-inset-top)); }
.head { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
.back { width: 36px; height: 36px; border: 0; border-radius: 12px; background: #fff; display: inline-flex; align-items: center; justify-content: center; box-shadow: $hb-shadow-soft; color: $hb-ink; }
h1 { margin: 0; font-size: 17px; font-weight: 800; color: $hb-ink; }
.tabs { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 12px; }
.tab {
  height: 31px; padding: 0 12px; border-radius: 999px; border: 1px solid #E7ECF3; background: #fff;
  font-size: 12px; color: $hb-ink; cursor: pointer;
  &.on { background: $hb-ink; color: #fff; border-color: $hb-ink; }
}
.list { display: flex; flex-direction: column; gap: 10px; }
.card { background: #fff; border: 1px solid #E7ECF3; border-radius: 16px; padding: 14px; }
.row { display: flex; align-items: center; gap: 8px; }
.between { justify-content: space-between; }
.oid { font-size: 11px; color: #6B7280; }
.pill { font-size: 11px; font-weight: 600; padding: 4px 10px; border-radius: 999px; background: #F3F4F6; color: $hb-ink; }
.pill.paid { background: #ECFDF5; color: #047857; }
.pill.ship { background: #E0F2FE; color: #FF6B4A; }
.pill.pend { background: #FEF3C7; color: #B45309; }
.thumbs { display: flex; gap: 10px; margin-top: 10px; }
.thumbs img, .ph { width: 64px; height: 64px; border-radius: 10px; object-fit: cover; background: linear-gradient(145deg,#bae6fd,#0369a1); }
.ph { display: flex; align-items: flex-end; padding: 12px; color: #fff; font-size: 11px; font-weight: 600; box-sizing: border-box; }
.meta { margin-top: 10px; }
.tiny { font-size: 11px; color: #6B7280; }
.price { font-size: 16px; font-weight: 800; color: $hb-price; }
.actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 12px; }
.btn {
  height: 33px; padding: 0 12px; border-radius: 12px; border: 0; background: $hb-ink; color: #fff;
  font-size: 12px; font-weight: 600; cursor: pointer; text-decoration: none; display: inline-flex; align-items: center;
}
.btn.soft { background: #fff; color: $hb-ink; border: 1px solid #E7ECF3; }
.state { text-align: center; color: $hb-muted; padding: 40px 8px; }
</style>
