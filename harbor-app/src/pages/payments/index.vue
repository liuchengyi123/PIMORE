<template>
  <view class="page">
    <view class="status hb-status"><text>9:41</text><text>●●● 5G</text></view>
    <view class="nav">
      <text class="back" @click="goBack">‹</text>
      <text class="title">Payment methods</text>
    </view>
    <view v-if="loginRequired" class="state">Sign in to manage payment methods.</view>
    <view v-else-if="loading" class="state">Loading…</view>
    <view v-else-if="!rows.length" class="state">No payment methods yet.</view>
    <view v-else class="list">
      <view v-for="(r, i) in rows" :key="i" class="card" :class="{ tall: !!r.last4 }">
        <view class="row">
          <text class="nm">{{ label(r) }}</text>
          <view v-if="i === 0" class="badge"><text>Preferred</text></view>
        </view>
        <text v-if="provider(r)" class="sub">{{ provider(r) }}</text>
      </view>
    </view>
    <view class="cta" @click="manage">Manage on Harbor</view>
  </view>
</template>
<script setup lang="ts">
import { useI18n } from '@/composables/i18n'
import { ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { fetchPayments, openHarborWeb, accountLinks, type PayMethodRow } from '@/api/accountApi'
const { t } = useI18n()
const rows = ref<PayMethodRow[]>([])
const loading = ref(false)
const loginRequired = ref(false)
async function refresh() {
  loading.value = true
  try {
    const res = await fetchPayments()
    rows.value = res.rows
    loginRequired.value = res.loginRequired && !res.rows.length
  } finally { loading.value = false }
}
function label(r: PayMethodRow) {
  const brand = (r as any).brand || (r as any).name || 'Card'
  const last4 = (r as any).last4 || ''
  if (last4) return `Card · ${brand} ••${last4}`
  return String(brand)
}
function provider(r: PayMethodRow) {
  return (r as any).provider || (r as any).meta || ''
}
function login() { openHarborWeb(accountLinks().login, 'Sign in') }
function manage() { openHarborWeb('/account/payments', 'Payments') }
function goBack() { uni.navigateBack({ fail: () => uni.reLaunch({ url: '/pages/me/index' }) }) }
onShow(() => {
  uni.setNavigationBarTitle({ title: t('payments_title') })
  refresh()
})
</script>
<style scoped>
.page { min-height: 100vh; background: #F7F4EF; color: #0F2744; padding: 0 16px 40px; padding-top: env(safe-area-inset-top); }
.status { display: flex; justify-content: space-between; padding: 14px 12px 0; font-size: 12px; font-weight: 700; }
.nav { display: flex; align-items: center; gap: 10px; padding: 8px 0 12px; }
.back { font-size: 18px; font-weight: 700; }
.title { font-size: 17px; font-weight: 700; }
.list { display: flex; flex-direction: column; gap: 8px; }
.card { background: #fff; border: 1px solid #E2E6EE; border-radius: 16px; padding: 14px; }
.row { display: flex; justify-content: space-between; align-items: center; }
.nm { font-size: 16px; font-weight: 700; }
.badge { background: #E0F2FE; color: #0E7490; font-size: 11px; font-weight: 600; padding: 4px 10px; border-radius: 999px; }
.sub { display: block; margin-top: 4px; font-size: 11px; color: #5C6570; }
.cta { margin-top: 14px; height: 41px; border-radius: 12px; background: #0F2744; color: #fff; font-size: 14px; font-weight: 600; display: flex; align-items: center; justify-content: center; }
.state { text-align: center; color: #6B7280; padding: 36px 8px; }
</style>
