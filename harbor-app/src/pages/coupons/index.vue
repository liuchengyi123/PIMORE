<template>
  <view class="page">
    <view class="status hb-status"><text>9:41</text><text>●●● 5G</text></view>
    <view class="nav">
      <text class="back" @click="goBack">‹</text>
      <text class="title">Coupons</text>
    </view>
    <view v-if="loginRequired" class="state">
      <text>Sign in to see coupons.</text>
      <view class="cta" @click="login">Sign in</view>
    </view>
    <view v-else-if="loading" class="state">Loading…</view>
    <view v-else-if="!coupons.length" class="state">No coupons yet.</view>
    <view v-else class="list">
      <view v-for="(c, i) in coupons" :key="i" class="ticket">
        <view class="face"><text class="amt">{{ amountOf(c) }}</text></view>
        <view class="info">
          <text class="code">{{ c.name }}</text>
          <text class="meta">{{ c.meta || 'Harbor coupon' }}</text>
        </view>
      </view>
    </view>
  </view>
</template>
<script setup lang="ts">
import { useI18n } from '@/composables/i18n'
import { ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { fetchCoupons, openHarborWeb, accountLinks, type CouponRow } from '@/api/accountApi'
const { t } = useI18n()
const coupons = ref<CouponRow[]>([])
const loading = ref(false)
const loginRequired = ref(false)
async function refresh() {
  loading.value = true
  try {
    const res = await fetchCoupons()
    coupons.value = res.coupons
    loginRequired.value = res.loginRequired && !res.coupons.length
  } finally { loading.value = false }
}
function amountOf(c: CouponRow) {
  const m = `${c.name} ${c.meta}`.match(/\$?\s*(\d+(?:\.\d+)?)\s*%?/)
  if (m) {
    if (/%/.test(`${c.name} ${c.meta}`) || /off/i.test(c.meta)) return `${m[1]}%`
    return `$${m[1]}`
  }
  return '★'
}
function login() { openHarborWeb(accountLinks().login, 'Sign in') }
function goBack() { uni.navigateBack({ fail: () => uni.reLaunch({ url: '/pages/me/index' }) }) }
onShow(() => { uni.setNavigationBarTitle({ title: t('coupons_title') }); refresh() })
</script>
<style scoped>
.page { min-height: 100vh; background: #F7F4EF; color: #0F2744; padding: 0 16px 40px; padding-top: env(safe-area-inset-top); }
.status { display: flex; justify-content: space-between; padding: 14px 12px 0; font-size: 12px; font-weight: 700; }
.nav { display: flex; align-items: center; gap: 10px; padding: 8px 0 12px; }
.back { font-size: 18px; font-weight: 700; }
.title { font-size: 17px; font-weight: 700; }
.list { display: flex; flex-direction: column; gap: 10px; }
.ticket { display: flex; background: #fff; border: 1px solid #E2E6EE; border-radius: 16px; overflow: hidden; min-height: 68px; }
.face { width: 80px; background: #0F2744; color: #fff; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.amt { font-size: 20px; font-weight: 800; }
.info { padding: 14px; display: flex; flex-direction: column; justify-content: center; }
.code { font-size: 16px; font-weight: 700; }
.meta { margin-top: 4px; font-size: 11px; color: #5C6570; }
.state { text-align: center; color: #6B7280; padding: 36px 8px; }
.cta { margin: 14px auto 0; width: 140px; height: 41px; border-radius: 12px; background: #0F2744; color: #fff; font-weight: 600; display: flex; align-items: center; justify-content: center; }
</style>
