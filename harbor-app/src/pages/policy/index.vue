<template>
  <view class="page">
    <view class="head">
      <view class="back" @click="goBack">←</view>
      <view>
        <text class="title">{{ title }}</text>
        <text class="sub">{{ t('policy_title') }}</text>
      </view>
    </view>
    <view class="tabs">
      <view class="tab" :class="{ on: kind === 'shipping' }" @click="switchKind('shipping')">{{ t('policy_shipping') }}</view>
      <view class="tab" :class="{ on: kind === 'privacy' }" @click="switchKind('privacy')">{{ t('help_privacy') }}</view>
    </view>
    <view v-if="loading" class="state">{{ t('nav_loading') }}</view>
    <view v-for="(b, i) in blocks" :key="i" class="pd">
      <text class="bt">{{ b.title }}</text>
      <text class="bb">{{ b.body }}</text>
    </view>
  </view>
</template>
<script setup lang="ts">
import { useI18n } from '@/composables/i18n'
import { ref } from 'vue'
import { onLoad, onShow } from '@dcloudio/uni-app'
import { fetchHtmlPath, parsePolicyBlocks } from '@/api/accountApi'
const { t } = useI18n()
const kind = ref('shipping')
const title = ref('Shipping policy')
const blocks = ref<{ title: string; body: string }[]>([])
const loading = ref(false)
async function load() {
  loading.value = true
  title.value = kind.value === 'privacy' ? 'Privacy' : 'Shipping policy'
  try {
    const path = kind.value === 'privacy' ? '/policies/privacy' : '/policies/shipping'
    blocks.value = parsePolicyBlocks(await fetchHtmlPath(path))
  } finally { loading.value = false }
}
function switchKind(k: string) { kind.value = k; load() }
function goBack() { uni.navigateBack({ fail: () => uni.navigateTo({ url: '/pages/help/index' }) }) }
onLoad((q) => {
  kind.value = q?.kind === 'privacy' ? 'privacy' : 'shipping'
  load()
})

onShow(() => {
  uni.setNavigationBarTitle({ title: t('policy_title') })
})
</script>
<style lang="scss" scoped>
@import '@/styles/theme.scss';
.page { min-height: 100vh; background: $hb-paper; padding: 12px 16px 40px; padding-top: calc(12px + env(safe-area-inset-top)); }
.head { display: flex; gap: 12px; align-items: center; margin-bottom: 14px; }
.back { width: 36px; height: 36px; border-radius: 12px; background: $hb-white; text-align: center; line-height: 36px; box-shadow: $hb-shadow-soft; }
.title { display: block; font-size: 24px; font-weight: 720; }
.sub { display: block; font-size: 12px; color: $hb-muted; margin-top: 2px; }
.tabs { display: flex; gap: 8px; margin-bottom: 14px; }
.tab { flex: 1; text-align: center; padding: 12px; border-radius: 999px; background: $hb-white; font-weight: 650; box-shadow: $hb-shadow-soft; }
.tab.on { background: $hb-forest; color: #fff; }
.pd { background: $hb-white; border-radius: 16px; padding: 14px; margin-bottom: 10px; box-shadow: $hb-shadow-soft; }
.bt { display: block; font-weight: 720; color: $hb-forest; margin-bottom: 6px; }
.bb { display: block; font-size: 13px; color: $hb-muted; line-height: 1.45; }
.state { text-align: center; color: $hb-muted; padding: 24px; }
</style>
