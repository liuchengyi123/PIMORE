<template>
  <div class="page">
    <header class="head">
      <button type="button" class="back" @click="$router.back()" aria-label="back">‹</button>
      <h1 class="title">Coupons</h1>
    </header>
    <div v-if="loginRequired" class="gate">
      <p>Sign in to sync coupons</p>
      <router-link class="gate-btn" :to="{ path: '/login', query: { next: '/coupons' } }">Sign in</router-link>
    </div>
    <div v-else-if="loading" class="state">Loading…</div>
    <div v-else-if="!coupons.length" class="state">No coupons yet</div>
    <div v-else class="list">
      <div v-for="(c, i) in coupons" :key="i" class="coupon" :class="{ used: !c.owned }">
        <div class="badge">
          <div class="amt">{{ amountOf(c) }}</div>
          <div v-if="c.owned" class="off">OFF</div>
        </div>
        <div class="info">
          <div class="code">{{ c.owned ? c.name : ('Used · ' + c.name) }}</div>
          <div class="meta">{{ c.meta || (c.owned ? '' : 'Already redeemed') }}</div>
        </div>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { fetchCoupons, type CouponRow } from '@/api/accountApi'
const coupons = ref<CouponRow[]>([])
const loading = ref(true)
const loginRequired = ref(false)
onMounted(async () => {
  try {
    const res = await fetchCoupons()
    coupons.value = res.coupons
    loginRequired.value = !!res.loginRequired && !res.coupons.length
  } finally { loading.value = false }
})
function amountOf(c: CouponRow) {
  const m = String(c.name || c.meta || '').match(/(\$?\d+(?:\.\d+)?%?)/)
  return m ? m[1] : (c.owned ? '$' : '—')
}
</script>
<style scoped>
.page { min-height: 100vh; background: #FCFAF8; color: #1C2430; padding: 12px 16px 40px; padding-top: calc(12px + env(safe-area-inset-top)); }
.head { display: flex; gap: 10px; align-items: center; margin-bottom: 14px; }
.back { border: 0; background: transparent; font-size: 22px; font-weight: 700; color: #1C2430; cursor: pointer; }
.title { font-size: 17px; font-weight: 700; margin: 0; }
.state, .gate { text-align: center; color: #6B7280; padding: 36px 8px; }
.gate-btn { display: inline-flex; margin-top: 12px; background: #F96141; color: #fff; padding: 12px 18px; border-radius: 999px; font-weight: 600; text-decoration: none; }
.list { display: flex; flex-direction: column; gap: 10px; }
.coupon { display: flex; height: 68px; background: #fff; border: 1px solid #E8E4DC; border-radius: 16px; overflow: hidden; }
.coupon.used { opacity: 0.55; }
.badge { width: 88px; background: #F96141; color: #fff; display: flex; flex-direction: column; align-items: center; justify-content: center; }
.coupon.used .badge { background: #6B7280; }
.amt { font-size: 22px; font-weight: 800; line-height: 1; }
.off { font-size: 10px; margin-top: 2px; }
.info { flex: 1; padding: 14px; display: flex; flex-direction: column; justify-content: center; }
.code { font-size: 16px; font-weight: 700; color: #1C2430; }
.meta { margin-top: 4px; font-size: 11px; color: #6B7280; }
</style>
