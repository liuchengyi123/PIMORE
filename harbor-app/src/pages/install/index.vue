<template>
  <view class="page">
    <view class="head">
      <view class="back" @click="goBack">←</view>
      <view>
        <text class="title">{{ t('install_title') }}</text>
        <text class="sub">{{ t('install_sub') }}</text>
      </view>
    </view>
    <view class="card">
      <text class="kicker">{{ t('install_pwa') }}</text>
      <text class="t2">{{ t('install_add') }}</text>
      <text class="note">On iPhone: Share → Add to Home Screen. Android: browser menu → Install app. Then reopen from the icon to unlock the install coupon when signed in.</text>
      <view class="btn" @click="openSite">{{ t('install_open') }}</view>
    </view>
  </view>
</template>
<script setup lang="ts">
import { onShow } from '@dcloudio/uni-app'
import { useI18n } from '@/composables/i18n'
import { openHarborWeb } from '@/api/accountApi'
const { t } = useI18n()
function openSite() { openHarborWeb('/install', 'Install') }
function goBack() { uni.navigateBack({ fail: () => uni.reLaunch({ url: '/pages/me/index' }) }) }

onShow(() => {
  uni.setNavigationBarTitle({ title: t('install_title') })
})
</script>
<style lang="scss" scoped>
@import '@/styles/theme.scss';
.page { min-height: 100vh; background: $hb-paper; padding: 12px 16px 40px; padding-top: calc(12px + env(safe-area-inset-top)); }
.head { display: flex; gap: 12px; align-items: center; margin-bottom: 16px; }
.back { width: 36px; height: 36px; border-radius: 12px; background: $hb-white; text-align: center; line-height: 36px; box-shadow: $hb-shadow-soft; }
.title { display: block; font-size: 24px; font-weight: 720; }
.sub { display: block; font-size: 12px; color: $hb-muted; margin-top: 2px; }
.card { border-radius: 24px; padding: 20px; background: $hb-soft; }
.kicker { display: block; font-size: 11px; letter-spacing: 1px; text-transform: uppercase; color: $hb-forest; font-weight: 700; }
.t2 { display: block; font-size: 20px; font-weight: 760; margin-top: 8px; color: $hb-forest; }
.note { display: block; margin-top: 10px; font-size: 13px; color: $hb-muted; line-height: 1.45; }
.btn { margin-top: 16px; display: inline-flex; background: $hb-forest; color: #fff; padding: 12px 16px; border-radius: 999px; font-weight: 720; }
</style>
