<template>
  <view class="page">
    <view class="status hb-status"><text>9:41</text><text>●●● 5G</text></view>
    <view class="nav">
      <text class="back" @click="goBack">‹</text>
      <text class="title">Rewards</text>
    </view>
    <view class="tiles">
      <view class="tile" @click="go('/pages/balance/index')"><text class="tt">Balance</text><text class="td">Rewards wallet</text></view>
      <view class="tile" @click="go('/pages/withdraw/index')"><text class="tt">Withdraw</text><text class="td">Cash out</text></view>
      <view class="tile" @click="go('/pages/checkin/index')"><text class="tt">Check-in</text><text class="td">Daily perk</text></view>
      <view class="tile" @click="go('/pages/invite/index')"><text class="tt">Invite</text><text class="td">Earn rewards</text></view>
    </view>
    <view class="cta" @click="openSite">Open on Harbor</view>
  </view>
</template>
<script setup lang="ts">
import { onShow } from '@dcloudio/uni-app'
import { useI18n } from '@/composables/i18n'
import { openHarborWeb } from '@/api/accountApi'
const { t } = useI18n()
function go(url: string) { uni.navigateTo({ url }) }
function openSite() { openHarborWeb('/rewards', 'Rewards') }
function goBack() { uni.navigateBack({ fail: () => uni.reLaunch({ url: '/pages/me/index' }) }) }
onShow(() => uni.setNavigationBarTitle({ title: t('rewards_title') }))
</script>
<style scoped>
.page { min-height: 100vh; background: #F7F4EF; color: #0F2744; padding: 0 16px 40px; padding-top: env(safe-area-inset-top); }
.status { display: flex; justify-content: space-between; padding: 14px 12px 0; font-size: 12px; font-weight: 700; }
.nav { display: flex; align-items: center; gap: 10px; padding: 8px 0 12px; }
.back { font-size: 18px; font-weight: 700; }
.title { font-size: 17px; font-weight: 700; }
.tiles { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.tile { background: #fff; border: 1px solid #E8E4DC; border-radius: 16px; padding: 16px; min-height: 88px; }
.tt { display: block; font-size: 15px; font-weight: 700; }
.td { display: block; margin-top: 6px; font-size: 12px; color: #6B7280; }
.cta { margin-top: 14px; height: 41px; border-radius: 12px; background: #0F2744; color: #fff; font-weight: 600; display: flex; align-items: center; justify-content: center; }
</style>
