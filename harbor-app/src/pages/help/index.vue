<template>
  <view class="page">
    <view class="status hb-status"><text>9:41</text><text>●●● 5G</text></view>
    <view class="nav">
      <text class="back" @click="goBack">‹</text>
      <text class="title">Help & contact</text>
    </view>
    <view class="card" @click="go('/pages/policy/index?kind=shipping')"><text class="rt">Shipping policy</text></view>
    <view class="card" @click="go('/pages/policy/index?kind=privacy')"><text class="rt">Privacy</text></view>
    <view class="card" @click="go('/pages/contact/index')"><text class="rt">Contact / Chat</text></view>
    <view class="cta" @click="go('/pages/chat/index')">Open chat</view>
  </view>
</template>
<script setup lang="ts">
import { onShow } from '@dcloudio/uni-app'
import { useI18n } from '@/composables/i18n'
const { t } = useI18n()
function go(url: string) { uni.navigateTo({ url }) }
function goBack() { uni.navigateBack({ fail: () => uni.reLaunch({ url: '/pages/me/index' }) }) }
onShow(() => uni.setNavigationBarTitle({ title: t('help_title') }))
</script>
<style scoped>
.page { min-height: 100vh; background: #F7F4EF; color: #0F2744; padding: 0 16px 40px; padding-top: env(safe-area-inset-top); }
.status { display: flex; justify-content: space-between; padding: 14px 12px 0; font-size: 12px; font-weight: 700; }
.nav { display: flex; align-items: center; gap: 10px; padding: 8px 0 12px; }
.back { font-size: 18px; font-weight: 700; }
.title { font-size: 17px; font-weight: 700; }
.card { background: #fff; border: 1px solid #E2E6EE; border-radius: 16px; padding: 14px; margin-bottom: 8px; }
.rt { font-size: 16px; font-weight: 700; }
.cta { margin-top: 14px; height: 41px; border-radius: 12px; background: #0F2744; color: #fff; font-size: 14px; font-weight: 600; display: flex; align-items: center; justify-content: center; }
</style>
