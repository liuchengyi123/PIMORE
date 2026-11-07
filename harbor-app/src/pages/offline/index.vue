<template>
  <view class="page fn-page" data-figma="A27">
    <view class="card">
      <text class="emoji">offline</text>
      <text class="title">{{ t('offline_title') || 'You are offline' }}</text>
      <text class="muted">{{ t('offline_body') || 'Check your connection, then try again.' }}</text>
      <view class="btn-solid" @click="retry">{{ t('common_retry') || 'Retry' }}</view>
      <view class="btn-outline" @click="goHome">{{ t('nav_home') || 'Home' }}</view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { useI18n } from '@/i18n'

const { t } = useI18n()

function retry() {
  try {
    // @ts-ignore
    if (typeof getCurrentPages === 'function') {
      const stack = getCurrentPages()
      const cur = stack[stack.length - 1] as any
      if (cur?.onLoad) cur.onLoad(cur.options || {})
    }
  } catch {}
  uni.reLaunch({ url: '/pages/home/index' })
}
function goHome() {
  uni.switchTab?.({ url: '/pages/home/index' }) || uni.reLaunch({ url: '/pages/home/index' })
}
</script>

<style scoped>
.page { min-height: 100vh; background: #F7F4EF; color: #0F2744; display: flex; align-items: center; justify-content: center; padding: 24px; }
.card { width: 100%; max-width: 360px; background: #fff; border: 1px solid #E2E6EE; border-radius: 16px; padding: 28px 20px; text-align: center; }
.title { display: block; font-size: 18px; font-weight: 700; margin: 8px 0; }
.muted { display: block; font-size: 13px; color: #64748B; margin-bottom: 20px; }
.btn-solid, .btn-outline { display: flex; align-items: center; justify-content: center; height: 44px; border-radius: 999px; font-weight: 600; margin-top: 10px; }
.btn-solid { background: #0E7490; color: #fff; }
.btn-outline { border: 1px solid #0F2744; color: #0F2744; }
.emoji { display: block; font-size: 12px; font-weight: 700; color: #B45309; letter-spacing: 0.08em; text-transform: uppercase; }
</style>
