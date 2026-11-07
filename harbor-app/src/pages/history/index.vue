<template>
  <view class="page">
    <view class="status hb-status"><text>9:41</text><text>●●● 5G</text></view>
    <view class="nav">
      <text class="back" @click="goBack">‹</text>
      <text class="title">Browsing history</text>
    </view>
    <view v-if="loading" class="state">Loading…</view>
    <view v-else-if="!products.length" class="state">No browsing history yet.</view>
    <view v-else class="grid">
      <view v-for="p in products" :key="p.id" class="card" @click="open(p)">
        <view class="thumb" :style="ph(p)">
          <image v-if="p.image" class="img" :src="p.image" mode="aspectFill" />
        </view>
        <view class="body">
          <text class="nm">{{ p.name }}</text>
          <text class="price">{{ money(p) }}</text>
        </view>
      </view>
    </view>
  </view>
</template>
<script setup lang="ts">
import { useI18n } from '@/composables/i18n'
import { ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { fetchHistoryHtml } from '@/api/accountApi'
import { parseFeedCards, type Product } from '@/api/products'
const { t } = useI18n()
const products = ref<Product[]>([])
const loading = ref(false)
async function refresh() {
  loading.value = true
  try {
    products.value = parseFeedCards(await fetchHistoryHtml())
  } catch { products.value = [] }
  finally { loading.value = false }
}
function money(p: Product) {
  const n = Number(p.price || 0)
  return n ? `$${n.toFixed(2)}` : ''
}
function ph(p: Product) {
  if (p.image) return {}
  return { backgroundImage: 'linear-gradient(154deg, #bae6fd 6%, #0369a1 94%)' }
}
function open(p: Product) {
  uni.navigateTo({ url: '/pages/pdp/index?sku=' + encodeURIComponent(String(p.sku || p.id)) })
}
function goBack() { uni.navigateBack({ fail: () => uni.reLaunch({ url: '/pages/me/index' }) }) }
onShow(() => {
  uni.setNavigationBarTitle({ title: t('history_title') })
  refresh()
})
</script>
<style scoped>
.page { min-height: 100vh; background: #F7F4EF; color: #0F2744; padding: 0 16px 40px; padding-top: env(safe-area-inset-top); }
.status { display: flex; justify-content: space-between; padding: 14px 12px 0; font-size: 12px; font-weight: 700; }
.nav { display: flex; align-items: center; gap: 10px; padding: 8px 0 12px; }
.back { font-size: 18px; font-weight: 700; }
.title { font-size: 17px; font-weight: 700; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.card { background: #fff; border: 1px solid #E2E6EE; border-radius: 16px; overflow: hidden; }
.thumb { height: 100px; background: #e8e4dc; position: relative; }
.img { width: 100%; height: 100%; }
.body { padding: 10px; }
.nm { display: block; font-size: 12px; font-weight: 600; min-height: 32px; }
.price { display: block; margin-top: 4px; font-size: 16px; font-weight: 700; color: #B45309; }
.state { text-align: center; color: #6B7280; padding: 36px 8px; }
</style>
