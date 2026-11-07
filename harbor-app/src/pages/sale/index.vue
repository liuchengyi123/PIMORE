<template>
  <view class="page">
    <view class="status hb-status"><text>9:41</text><text>●●● 5G</text></view>
    <view class="nav">
      <text class="back" @click="goBack">‹</text>
      <text class="title">Sale</text>
    </view>
    <view class="hero">
      <text class="hl">Kitchen deals</text>
      <text class="sub">Real sale items</text>
      <view v-if="saleEnds" class="clock"><HbDealClock :label="t('deal_ends_in')" :ends-at="saleEnds" light /></view>
    </view>
    <view v-if="loading" class="state">Loading…</view>
    <view v-else-if="!products.length" class="state">No sale items right now.</view>
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
import { onShow } from '@dcloudio/uni-app'
import { useI18n } from '@/composables/i18n'
import { ref, onMounted } from 'vue'
import { listSaleProducts, type Product, fetchDealEnds } from '@/api/products'
import HbDealClock from '@/components/HbDealClock.vue'
const { t } = useI18n()
const products = ref<Product[]>([])
const loading = ref(true)
const saleEnds = ref('')
onMounted(async () => {
  try { saleEnds.value = (await fetchDealEnds()) || '' } catch { /* */ }
  try { products.value = await listSaleProducts() } finally { loading.value = false }
})
function money(p: Product) {
  const n = Number(p.price || 0)
  return n ? `$${n.toFixed(2)}` : ''
}
function ph(p: Product) {
  if (p.image) return {}
  return { backgroundImage: 'linear-gradient(154deg, #fcd34d 6%, #b45309 94%)' }
}
function open(p: Product) {
  uni.navigateTo({ url: '/pages/pdp/index?sku=' + encodeURIComponent(String(p.sku || p.id)) })
}
function goBack() { uni.navigateBack({ fail: () => uni.reLaunch({ url: '/pages/home/index' }) }) }
onShow(() => uni.setNavigationBarTitle({ title: t('sale_title') }))
</script>
<style scoped>
.page { min-height: 100vh; background: #F7F4EF; color: #0F2744; padding: 0 16px 40px; padding-top: env(safe-area-inset-top); }
.status { display: flex; justify-content: space-between; padding: 14px 12px 0; font-size: 12px; font-weight: 700; }
.nav { display: flex; align-items: center; gap: 10px; padding: 8px 0 12px; }
.back { font-size: 18px; font-weight: 700; }
.title { font-size: 17px; font-weight: 700; }
.hero {
  border-radius: 16px; padding: 16px; color: #fff; margin-bottom: 12px;
  background-image: linear-gradient(154deg, #0F2744 8%, #B45309 92%);
}
.hl { display: block; font-size: 18px; font-weight: 800; }
.sub { display: block; margin-top: 4px; font-size: 12px; opacity: 0.85; }
.clock { margin-top: 8px; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.card { background: #fff; border: 1px solid #E2E6EE; border-radius: 16px; overflow: hidden; }
.thumb { height: 100px; background: #e8e4dc; }
.img { width: 100%; height: 100%; }
.body { padding: 10px; }
.nm { display: block; font-size: 13px; font-weight: 600; min-height: 34px; }
.price { display: block; margin-top: 4px; font-size: 16px; font-weight: 700; color: #B45309; }
.state { text-align: center; color: #6B7280; padding: 28px 8px; }
</style>
