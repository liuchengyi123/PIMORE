<template>
  <view class="page">
    <view class="status hb-status"><text>9:41</text><text>●●● 5G</text></view>
    <view class="nav">
      <text class="back" @click="goBack">‹</text>
      <text class="title">Balance</text>
    </view>
    <view class="hero">
      <text class="lab">Available</text>
      <text class="amt">{{ info.balanceText || '—' }}</text>
      <view class="withdraw-btn" @click="withdraw">Withdraw</view>
    </view>
    <view class="card" @click="goCheckin">
      <text class="nm">Daily check-in</text>
      <text class="meta">{{ info.note || 'Tap to claim today’s perk' }}</text>
    </view>
    <view v-if="!info.signedIn" class="cta soft" @click="login">Sign in</view>
  </view>
</template>
<script setup lang="ts">
import { useI18n } from '@/composables/i18n'
import { reactive } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { fetchBalancePanel, openHarborWeb, accountLinks, type BalanceInfo } from '@/api/accountApi'
const { t } = useI18n()
const info = reactive<BalanceInfo>({
  ok: false, live: false, signedIn: false, balanceText: '—', note: '',
})
async function refresh() { Object.assign(info, await fetchBalancePanel()) }
function withdraw() { uni.navigateTo({ url: '/pages/withdraw/index' }) }
function goCheckin() { uni.navigateTo({ url: '/pages/checkin/index' }) }
function login() { openHarborWeb(accountLinks().login, 'Sign in') }
function goBack() { uni.navigateBack({ fail: () => uni.reLaunch({ url: '/pages/me/index' }) }) }
onShow(() => { uni.setNavigationBarTitle({ title: t('balance_title') }); refresh() })
</script>
<style scoped>
.page { min-height: 100vh; background: #F7F4EF; color: #0F2744; padding: 0 16px 40px; padding-top: env(safe-area-inset-top); }
.status { display: flex; justify-content: space-between; padding: 14px 12px 0; font-size: 12px; font-weight: 700; }
.nav { display: flex; align-items: center; gap: 10px; padding: 8px 0 12px; }
.back { font-size: 18px; font-weight: 700; }
.title { font-size: 17px; font-weight: 700; }
.hero {
  border-radius: 18px; padding: 20px; color: #fff; margin-bottom: 12px;
  background-image: linear-gradient(163deg, #0F2744 6%, #1A3A5C 94%);
}
.lab { display: block; font-size: 12px; opacity: 0.8; }
.amt { display: block; margin-top: 4px; font-size: 32px; font-weight: 800; }
.withdraw-btn {
  margin-top: 14px; display: inline-flex; align-items: center; justify-content: center;
  height: 41px; padding: 0 18px; border-radius: 12px; background: #fff; color: #0F2744; font-size: 14px; font-weight: 600;
}
.card { background: #fff; border: 1px solid #E2E6EE; border-radius: 16px; padding: 14px; }
.nm { display: block; font-size: 16px; font-weight: 700; }
.meta { display: block; margin-top: 4px; font-size: 11px; color: #5C6570; }
.cta.soft { margin-top: 14px; height: 41px; border-radius: 12px; border: 1px solid #E8E4DC; background: #fff; display: flex; align-items: center; justify-content: center; font-weight: 600; }
</style>
