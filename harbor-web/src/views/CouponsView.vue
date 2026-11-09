<template>
  <AgShell tabs="me">
    <header class="head ag-top ag-pad">
      <div class="nav">
        <button type="button" class="ag-back ink" @click="router.back()" :aria-label="tx('返回', 'Back')">
          <ChevronLeft :size="26" :stroke-width="2.2" />
        </button>
        <div class="doodle" aria-hidden="true">
          <Home :size="22" color="#F96141" :stroke-width="1.8" />
          <span>{{ tx('家更好\n花更少', 'Better Home\nfor Less') }}</span>
        </div>
      </div>
      <h1 class="ag-h1">{{ tx('我的优惠券', 'My Coupons') }}</h1>
    </header>

    <div class="ag-pad">
      <div class="ag-tabs">
        <button type="button" :class="{ on: tab === 'avail' }" @click="tab = 'avail'">{{ tx('可用', 'Available') }}</button>
        <button type="button" :class="{ on: tab === 'used' }" @click="tab = 'used'">{{ tx('已使用', 'Used') }}</button>
        <button type="button" :class="{ on: tab === 'exp' }" @click="tab = 'exp'">{{ tx('已过期', 'Expired') }}</button>
      </div>

      <div v-if="loginRequired" class="ag-empty">
        <h3>{{ tx('登录后同步优惠券', 'Sign in to sync coupons') }}</h3>
        <router-link class="ag-cta" style="margin-top:14px" :to="{ path: '/login', query: { next: '/coupons' } }">{{ tx('登录', 'Sign in') }}</router-link>
      </div>
      <div v-else-if="loading" class="ag-empty"><p>{{ tx('加载中…', 'Loading…') }}</p></div>
      <div v-else-if="!filtered.length" class="empty ag-card">
        <div class="ticket" aria-hidden="true"><TicketPercent :size="34" color="#F96141" /></div>
        <h3>{{ tx('暂无优惠券', 'No coupons available') }}</h3>
        <p>{{ tx('继续逛逛，新的优惠会出现在这里。', 'Keep shopping! New deals and coupons will show up here.') }}</p>
        <div class="tip">
          <Lightbulb :size="18" color="#F96141" />
          <span><b>{{ tx('小提示：', 'Tip:') }}</b> {{ tx('常回来看看，我们会定期发新券。', 'Check back often — we drop new coupons regularly!') }}</span>
        </div>
      </div>
      <div v-else class="list">
        <article v-for="(c, i) in filtered" :key="i" class="coupon ag-card" :class="{ dim: tab !== 'avail' }">
          <div class="badge">
            <b>{{ face(c).big }}</b>
            <small v-if="face(c).off">{{ face(c).off }}</small>
          </div>
          <div class="info">
            <div class="nm">{{ c.name }}</div>
            <div class="meta">{{ c.meta || tx('全场可用', 'Storewide') }}</div>
            <div class="exp"><Calendar :size="12" /> {{ expiry(c) }}</div>
          </div>
          <router-link v-if="tab === 'avail'" class="use" to="/browse">{{ tx('去使用', 'Use now') }}</router-link>
        </article>
      </div>
    </div>
  </AgShell>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Calendar, ChevronLeft, Home, Lightbulb, TicketPercent } from 'lucide-vue-next'
import AgShell from '@/components/account/AgShell.vue'
import { fetchCoupons, type CouponRow } from '@/api/accountApi'
import { useZh } from '@/composables/zh'

const { tx } = useZh()
const router = useRouter()
const tab = ref<'avail' | 'used' | 'exp'>('avail')
const coupons = ref<CouponRow[]>([])
const loading = ref(true)
const loginRequired = ref(false)

function expired(c: CouponRow) {
  return /过期|expired|invalid/i.test(`${c.name} ${c.meta}`)
}
const filtered = computed(() => coupons.value.filter((c) => {
  if (tab.value === 'exp') return expired(c)
  if (tab.value === 'used') return !c.owned && !expired(c)
  return c.owned && !expired(c)
}))

onMounted(async () => {
  try {
    const res = await fetchCoupons()
    coupons.value = res.coupons
    loginRequired.value = !!res.loginRequired && !res.coupons.length
  } finally { loading.value = false }
})

function face(c: CouponRow) {
  const s = `${c.name} ${c.meta}`
  const pct = s.match(/(\d+)\s*%/)
  if (pct) return { big: `${pct[1]}%`, off: 'OFF' }
  const dol = s.match(/\$\s*(\d+(?:\.\d+)?)/) || s.match(/(\d+(?:\.\d+)?)\s*元/)
  if (dol) return { big: s.includes('元') ? `¥${dol[1]}` : `$${dol[1]}`, off: 'OFF' }
  return { big: tx('券', 'OFF'), off: '' }
}
function expiry(c: CouponRow) {
  const m = `${c.meta}`.match(/(20\d{2}[-/.]\d{1,2}[-/.]\d{1,2}|[A-Za-z]{3,}\s+\d{1,2},?\s+20\d{2}|\d{1,2}月\d{1,2}日)/)
  if (m) return tx(`有效期至 ${m[1]}`, `Expires ${m[1]}`)
  return tab.value === 'used' ? tx('已核销', 'Already redeemed') : tx('请在结算时使用', 'Apply at checkout')
}
</script>

<style scoped>
.head { margin-bottom: 14px; }
.nav { display: flex; align-items: flex-start; justify-content: space-between; }
.doodle { display: flex; align-items: center; gap: 6px; color: #F96141; transform: rotate(-8deg); margin-top: 4px; }
.doodle span { font-family: 'Segoe Script', 'Comic Sans MS', cursive; font-size: 13px; line-height: 1.15; white-space: pre-line; font-weight: 700; }
.list { display: flex; flex-direction: column; gap: 12px; margin-top: 14px; }
.coupon { display: flex; align-items: center; min-height: 92px; overflow: hidden; padding-right: 12px; }
.coupon.dim { opacity: 0.6; }
.badge {
  width: 84px; align-self: stretch; background: #F96141; color: #fff;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
}
.badge b { font-size: 22px; line-height: 1; }
.badge small { font-size: 11px; letter-spacing: 0.06em; margin-top: 2px; }
.info { flex: 1; min-width: 0; padding: 12px; }
.nm { font-size: 14.5px; font-weight: 800; }
.meta, .exp { margin-top: 3px; font-size: 12px; color: #8B919A; display: flex; align-items: center; gap: 4px; }
.use {
  flex: 0 0 auto; height: 32px; padding: 0 12px; border-radius: 999px; background: #F96141; color: #fff;
  font-size: 12.5px; font-weight: 750; display: inline-flex; align-items: center; text-decoration: none;
}
.empty { margin-top: 16px; padding: 28px 18px 16px; text-align: center; }
.ticket {
  width: 74px; height: 74px; margin: 0 auto; border-radius: 20px; background: #FFF1EC;
  display: grid; place-items: center;
}
.empty h3 { margin: 12px 0 6px; font-size: 18px; }
.empty p { margin: 0; color: #8B919A; font-size: 13.5px; line-height: 1.5; }
.tip {
  margin-top: 16px; display: flex; gap: 10px; text-align: left; align-items: flex-start;
  background: #FFF8F5; border-radius: 12px; padding: 12px; color: #5C6570; font-size: 12.5px; line-height: 1.45;
}
.tip b { color: #F96141; }
</style>
