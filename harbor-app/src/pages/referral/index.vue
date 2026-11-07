<template>
  <view class="page">
    <view class="head">
      <view class="back" @click="goBack">←</view>
      <view>
        <text class="title">{{ t('referral_title') }}</text>
        <text class="sub">{{ code || 'Invite link' }}</text>
      </view>
    </view>
    <view class="card">
      <text class="kicker">{{ t('referral_code') }}</text>
      <text class="code">{{ code || '—' }}</text>
      <text class="note">Open the claim page on Harbor to attach this invite to your account.</text>
      <view class="btn" @click="claim">{{ t('referral_claim') }}</view>
      <view class="btn soft" @click="goInvite">{{ t('referral_link') }}</view>
    </view>
  </view>
</template>
<script setup lang="ts">
import { useI18n } from '@/composables/i18n'
import { ref } from 'vue'
import { onLoad, onShow } from '@dcloudio/uni-app'
import { openHarborWeb } from '@/api/accountApi'
const { t } = useI18n()
const code = ref('')
onLoad((q) => { code.value = q?.code ? decodeURIComponent(q.code) : '' })
function claim() {
  if (!code.value) return
  openHarborWeb('/r/' + encodeURIComponent(code.value), 'Referral')
}
function goInvite() { uni.navigateTo({ url: '/pages/invite/index' }) }
function goBack() { uni.navigateBack({ fail: () => uni.reLaunch({ url: '/pages/home/index' }) }) }

onShow(() => {
  uni.setNavigationBarTitle({ title: t('referral_title') })
})
</script>
<style lang="scss" scoped>
@import '@/styles/theme.scss';
.page { min-height: 100vh; background: $hb-paper; padding: 12px 16px 40px; padding-top: calc(12px + env(safe-area-inset-top)); }
.head { display: flex; gap: 12px; align-items: center; margin-bottom: 16px; }
.back { width: 36px; height: 36px; border-radius: 12px; background: $hb-white; text-align: center; line-height: 36px; box-shadow: $hb-shadow-soft; }
.title { display: block; font-size: 24px; font-weight: 720; }
.sub { display: block; font-size: 12px; color: $hb-muted; margin-top: 2px; }
.card { background: $hb-white; border-radius: 22px; padding: 20px; box-shadow: $hb-shadow-soft; }
.kicker { display: block; font-size: 11px; color: $hb-muted; letter-spacing: 1px; text-transform: uppercase; font-weight: 650; }
.code { display: block; margin-top: 10px; font-size: 28px; font-weight: 780; color: $hb-forest; letter-spacing: 1px; }
.note { display: block; margin-top: 10px; font-size: 13px; color: $hb-muted; line-height: 1.4; }
.btn { margin-top: 14px; text-align: center; padding: 14px; border-radius: 16px; background: $hb-coral; color: #fff; font-weight: 720; }
.btn.soft { background: $hb-soft; color: $hb-forest; }
</style>
