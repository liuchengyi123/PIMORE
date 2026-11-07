<template>
  <view class="page" data-figma="A19">
    <view class="status hb-status"><text>9:41</text><text>●●●</text></view>
    <view class="hero">
      <view class="back" @click="goBack">←</view>
      <text class="kicker">{{ t('flash_title') }}</text>
      <text class="title">{{ t('flash_sub') }}</text>
      <text class="line">{{ t('flash_hint') }}</text>
      <view class="cd-wrap">
        <HbDealClock :label="t('deal_ends_in')" :ends-at="flashEnds" light />
      </view>
    </view>
    <view v-if="loading" class="state">{{ t('flash_loading') }}</view>
    <view v-else-if="!products.length" class="state">{{ t('flash_empty') }}</view>
    <view v-else class="grid">
      <HbProductCard v-for="p in products" :key="p.id" :product="p" />
    </view>
  </view>
</template>
<script setup lang="ts">
import { onShow } from '@dcloudio/uni-app'
import { useI18n } from '@/composables/i18n'
import { ref, onMounted } from 'vue'
import { listShipLpProducts, type Product, fetchFlashEnds } from '@/api/products'
import HbProductCard from '@/components/HbProductCard.vue'
import HbDealClock from '@/components/HbDealClock.vue'
const { t } = useI18n()
const products = ref<Product[]>([])
const loading = ref(true)
const flashEnds = ref('')
onMounted(async () => {
  try { flashEnds.value = (await fetchFlashEnds()) || '' } catch { /* ignore */ }

  try { products.value = await listShipLpProducts() }
  finally { loading.value = false }
})
function goBack() { uni.navigateBack({ fail: () => uni.reLaunch({ url: '/pages/home/index' }) }) }

onShow(() => {
  uni.setNavigationBarTitle({ title: t('flash_title') })
})
</script>
<style lang="scss" scoped>
.hb-status,.status{display:flex;justify-content:space-between;padding:10px 4px 0;font-size:12px;font-weight:700;color:#0F2744;}
@import '@/styles/theme.scss';
.page { min-height: 100vh; background: $hb-paper; padding-bottom: 40px; }
.hero {
  margin: 12px 16px 16px; margin-top: calc(12px + env(safe-area-inset-top));
  border-radius: 26px; padding: 18px; color: #fff;
  background: linear-gradient(155deg, #5a1d12 0%, $hb-coral 68%, #f07a4f 100%);
  box-shadow: $hb-shadow-lift;
}
.back { width: 34px; height: 34px; border-radius: 12px; background: rgba(255,255,255,0.18); text-align: center; line-height: 34px; margin-bottom: 12px; }
.kicker { display: block; font-size: 11px; letter-spacing: 1px; text-transform: uppercase; opacity: 0.8; font-weight: 650; }
.title { display: block; font-size: 26px; font-weight: 760; margin-top: 8px; letter-spacing: -0.5px; }
.line { display: block; margin-top: 8px; font-size: 13px; opacity: 0.85; }
.state { text-align: center; color: $hb-muted; padding: 40px 16px; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; padding: 0 16px; }

.cd-wrap { margin-top: 12px; }
</style>
