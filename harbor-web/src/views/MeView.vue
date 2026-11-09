<template>
  <div class="page">
    <section class="hero">
      <div class="top">
        <div class="avatar">{{ initials }}</div>
        <div class="who">
          <div class="name">{{ displayName }}</div>
          <div class="email">{{ acct.email || (lang === 'en' ? 'Sign in to sync orders & balance' : '登录后同步订单与余额') }}</div>
        </div>
        <button type="button" class="locale-pill" @click="go('/locale')">{{ localePill }}</button>
      </div>
      <div class="stats">
        <button type="button" class="stat" @click="go('/balance')"><b>{{ balanceText }}</b><span>{{ lang === 'en' ? 'Balance' : '余额' }}</span></button>
        <button type="button" class="stat" @click="go('/coupons')"><b>{{ couponCount }}</b><span>{{ lang === 'en' ? 'Coupons' : '优惠券' }}</span></button>
        <button type="button" class="stat" @click="go('/wishlist')"><b>{{ wishCount }}</b><span>{{ lang === 'en' ? 'Wishlist' : '心愿单' }}</span></button>
      </div>
      <div v-if="!acct.signedIn" class="login-row">
        <button type="button" class="login" @click="go('/login', { next: '/me' })">{{ lang === 'en' ? 'Sign in' : '登录' }}</button>
      </div>
    </section>

    <section class="orders card">
      <div class="ord-head">
        <span class="h">{{ lang === 'en' ? 'My orders' : '我的订单' }}</span>
        <button type="button" class="all" @click="go('/orders')">{{ lang === 'en' ? 'All' : '全部' }} ›</button>
      </div>
      <div class="ord-row">
        <button type="button" class="ost" @click="go('/orders')"><span class="ic">💳</span><span class="ol">{{ lang === 'en' ? 'To pay' : '待支付' }}</span><b>{{ acct.pending }}</b></button>
        <button type="button" class="ost" @click="go('/orders')"><span class="ic">📦</span><span class="ol">{{ lang === 'en' ? 'Paid' : '已支付' }}</span><b>{{ acct.paid }}</b></button>
        <button type="button" class="ost" @click="go('/orders')"><span class="ic">🚚</span><span class="ol">{{ lang === 'en' ? 'Shipped' : '已发货' }}</span><b>{{ acct.shipped }}</b></button>
        <button type="button" class="ost" @click="go('/return')"><span class="ic">↩</span><span class="ol">{{ lang === 'en' ? 'Returns' : '退货' }}</span><b>0</b></button>
      </div>
    </section>

    <section class="menu card">
      <button v-for="r in menu" :key="r.to" type="button" class="row" @click="go(r.to)">
        <span>{{ r.label }}</span><span class="chev">›</span>
      </button>
    </section>

    <button type="button" class="cs-fab" aria-label="CS" @click="go('/chat')">CS</button>
    <AppTabBar active="me" />
  </div>
</template>
<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from '@/composables/i18n'
import { fetchAccountSummary } from '@/api/accountApi'
import { defaultCountry } from '@/api/countryLocale'
import AppTabBar from '@/components/AppTabBar.vue'

const router = useRouter()
const { lang } = useI18n()
const acct = reactive({ signedIn: false, email: '', pending: 0, paid: 0, shipped: 0 })
const balanceText = ref('$—')
const couponCount = ref('—')
const wishCount = ref('—')

const menu = computed(() => lang.value === 'en'
  ? [
      { to: '/addresses', label: 'Addresses' },
      { to: '/payments', label: 'Payment methods' },
      { to: '/wishlist', label: 'Wishlist' },
      { to: '/history', label: 'Browsing history' },
      { to: '/coupons', label: 'Coupons · Check-in · Rewards' },
      { to: '/invite', label: 'Invite friends' },
      { to: '/locale', label: 'Country / currency' },
      { to: '/install', label: 'Install app' },
      { to: '/help', label: 'Help · Contact · Policies' },
    ]
  : [
      { to: '/orders', label: '我的订单' },
      { to: '/coupons', label: '优惠券' },
      { to: '/balance', label: '余额' },
      { to: '/wishlist', label: '愿望单' },
      { to: '/addresses', label: '收货地址' },
      { to: '/payments', label: '支付方式' },
      { to: '/rewards', label: '奖励' },
      { to: '/invite', label: '邀请好友' },
      { to: '/help', label: '帮助与客服' },
      { to: '/locale', label: '国家与货币' },
    ])

const displayName = computed(() => {
  if (!acct.signedIn) return lang.value === 'en' ? 'Welcome to Harbor' : '欢迎来到 Harbor'
  const e = acct.email || ''
  const local = e.split('@')[0] || 'Harbor'
  return local.replace(/[._]/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
})
const initials = computed(() => {
  const n = displayName.value.trim()
  const parts = n.split(/\s+/).filter(Boolean)
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase()
  return (parts[0] || 'H').slice(0, 2).toUpperCase()
})
const localePill = computed(() => {
  const c = (defaultCountry() || 'US').toUpperCase()
  const map: Record<string, string> = { US: '🇺🇸 US · USD', CN: '🇨🇳 CN · CNY', JP: '🇯🇵 JP · JPY', GB: '🇬🇧 GB · GBP', DE: '🇩🇪 DE · EUR', CA: '🇨🇦 CA · CAD', TW: '🇹🇼 TW · TWD', HK: '🇭🇰 HK · HKD' }
  return map[c] || `${c}`
})

function go(path: string, query?: Record<string, string>) {
  router.push(query ? { path, query } : path)
}

onMounted(async () => {
  try {
    const s = await fetchAccountSummary()
    acct.signedIn = s.signedIn
    acct.email = s.email
    acct.pending = s.pending
    acct.paid = s.paid
    acct.shipped = s.shipped
    // honest counts only — no invented wishlist/coupon numbers
    if ((s as any).balanceText) balanceText.value = String((s as any).balanceText)
    if ((s as any).coupons != null) couponCount.value = String((s as any).coupons)
    if ((s as any).wishlist != null) wishCount.value = String((s as any).wishlist)
  } catch { /* guest */ }
})
</script>
<style scoped>
.page { min-height: 100vh; background: #FCFAF8; color: #1C2430; padding-bottom: 90px; }
.hero {
  padding: 16px 16px 8px; padding-top: calc(16px + env(safe-area-inset-top));
  background: #FCFAF8; color: #1C2430;
}
.top { display: flex; align-items: center; gap: 12px; }
.avatar {
  width: 56px; height: 56px; border-radius: 28px; background: #F96141; color: #fff;
  display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 16px; flex-shrink: 0;
}
.who { flex: 1; min-width: 0; }
.name { font-size: 17px; font-weight: 800; letter-spacing: -0.02em; line-height: 1.15; }
.email { margin-top: 2px; font-size: 12px; color: #8B919A; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.locale-pill {
  border: 0; background: #FFF1EC; color: #F96141; font-size: 11px; font-weight: 700;
  padding: 6px 10px; border-radius: 999px; cursor: pointer; white-space: nowrap;
}
.stats { display: flex; gap: 8px; margin-top: 10px; }
.stat {
  flex: 1; border: 0; background: #fff; color: #1C2430; border-radius: 12px; padding: 8px 6px; cursor: pointer;
  display: flex; flex-direction: column; align-items: center; gap: 2px;
}
.stat b { font-size: 15px; color: #F96141; letter-spacing: -0.02em; }
.stat span { font-size: 10px; color: #8B919A; }
.login-row { margin-top: 10px; }
.login {
  border: 0; background: #F96141; color: #fff; font-weight: 700; font-size: 14px;
  height: 36px; padding: 0 16px; border-radius: 999px; cursor: pointer;
}
.card { margin: 10px 16px 0; background: #fff; border: 1px solid #F1EEEA; border-radius: 14px; overflow: hidden; }
.ord-head { display: flex; justify-content: space-between; align-items: center; padding: 10px 12px 0; }
.h { font-size: 14px; font-weight: 800; }
.all { border: 0; background: transparent; color: #F96141; font-size: 12px; font-weight: 700; cursor: pointer; }
.ord-row { display: flex; padding: 8px 2px 10px; }
.ost {
  flex: 1; border: 0; background: transparent; cursor: pointer; color: inherit;
  display: flex; flex-direction: column; align-items: center; gap: 4px;
}
.ic { font-size: 18px; }
.ol { font-size: 11px; color: #6B7280; }
.ost b { font-size: 12px; color: #F96141; font-weight: 800; }
.menu .row {
  width: 100%; display: flex; justify-content: space-between; align-items: center;
  min-height: 44px; padding: 0 12px; border: 0; border-bottom: 1px solid #F1EEEA; background: #fff; cursor: pointer;
  font-size: 14px; font-weight: 650; color: #1C2430; text-align: left;
}
.menu .row:last-child { border-bottom: 0; }
.chev { color: #F96141; font-size: 16px; }
.cs-fab { display: none; }
</style>
