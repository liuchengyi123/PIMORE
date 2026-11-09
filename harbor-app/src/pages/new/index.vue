<template>
  <view class="page" data-figma="1:17">
    <view class="nav">
      <text class="title">New In</text>
      <view class="filter" :class="{ on: under }" @click="under = !under">
        <view class="funnel" />
        <text>Filter</text>
      </view>
    </view>
    <view class="banner">
      <view>
        <text class="ban-k">Just landed this week</text>
        <text class="ban-s">Fresh finds. Everyday essentials.</text>
      </view>
      <view class="house" />
    </view>
    <view v-if="loading" class="state">Loading…</view>
    <view v-else-if="!shown.length" class="state">No new arrivals yet.</view>
    <view v-else class="grid">
      <view v-for="p in shown" :key="p.id" class="card" @click="open(p)">
        <view class="thumb">
          <text class="tag">NEW</text>
          <image v-if="p.image" class="img" :src="p.image" mode="aspectFill" />
        </view>
        <text class="nm">{{ p.name }}</text>
        <text class="meta">{{ p.blurb || p.category }}</text>
        <view class="row">
          <text class="price">{{ money(p) }}</text>
          <view class="add" @click.stop="addOne(p)" />
        </view>
      </view>
    </view>
    <HbTabBar active="home" />
  </view>
</template>
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { useI18n } from '@/composables/i18n'
import { listNewProducts, type Product } from '@/api/products'
import { handleLuckyBack } from '@/composables/lucky'
import { useCart } from '@/composables/cart'
import HbTabBar from '@/components/HbTabBar.vue'

const { t } = useI18n()
const { add } = useCart()
const products = ref<Product[]>([])
const loading = ref(true)
const under = ref(false)
const shown = computed(() => (under.value ? products.value.filter((p) => p.price > 0 && p.price <= 5) : products.value))
onMounted(async () => {
  try { products.value = await listNewProducts() } finally { loading.value = false }
})
function money(p: Product) {
  const n = Number(p.price || 0)
  return n ? `$${n.toFixed(2)}` : ''
}
function open(p: Product) {
  uni.navigateTo({ url: '/pages/pdp/index?sku=' + encodeURIComponent(String(p.sku || p.id)) })
}
async function addOne(p: Product) {
  const size = p.sizes?.[0] || p.offers?.[0]?.label || 'default'
  const res = await add(p, size, 1)
  uni.showToast({ title: res.message || 'Added', icon: 'none' })
}
function goBack() {
  if (handleLuckyBack()) return
  uni.navigateBack({ fail: () => uni.reLaunch({ url: '/pages/home/index' }) })
}
onShow(() => uni.setNavigationBarTitle({ title: t('new_title') }))
void goBack
</script>
<style scoped>
.page { min-height: 100vh; background: #FCF3E7; color: #1B2B4A; padding: 12px 16px 96px; padding-top: calc(12px + env(safe-area-inset-top)); }
.nav { display: flex; align-items: center; justify-content: space-between; height: 40px; }
.title { font-size: 28px; font-weight: 800; color: #FD6844; letter-spacing: -0.4px; }
.filter { display: flex; align-items: center; gap: 4px; background: #fff; border-radius: 999px; padding: 6px 12px; font-size: 13px; font-weight: 700; color: #FD6844; }
.filter.on { background: #FD6844; color: #fff; }
.funnel { width: 12px; height: 12px; border: 1.6px solid currentColor; border-radius: 1px 1px 6px 6px; }
.banner { margin-top: 10px; background: #FFF6EE; border-radius: 16px; padding: 16px; display: flex; justify-content: space-between; align-items: center; }
.ban-k { display: block; font-size: 20px; font-weight: 800; letter-spacing: -0.3px; }
.ban-s { display: block; margin-top: 4px; font-size: 13px; color: #8B95A7; }
.house { width: 42px; height: 36px; border: 2px solid #FD6844; border-radius: 4px 4px 2px 2px; position: relative; }
.house::before { content: ''; position: absolute; left: 6px; top: -8px; border-left: 14px solid transparent; border-right: 14px solid transparent; border-bottom: 10px solid #FD6844; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 12px; }
.card { background: #fff; border-radius: 16px; padding: 8px; box-shadow: 0 8px 18px rgba(49,63,75,.05); }
.thumb { height: 132px; border-radius: 12px; overflow: hidden; background: #F4EFEA; position: relative; }
.img { width: 100%; height: 100%; }
.tag { position: absolute; left: 8px; top: 8px; z-index: 1; background: #FC714A; color: #fff; font-size: 10px; font-weight: 800; border-radius: 8px; padding: 3px 6px; }
.nm { display: block; margin-top: 8px; font-size: 13px; font-weight: 800; line-height: 1.25; min-height: 32px; }
.meta { display: block; margin-top: 2px; font-size: 11px; color: #8B95A7; min-height: 14px; }
.row { display: flex; align-items: center; margin-top: 6px; }
.price { color: #FD6844; font-size: 16px; font-weight: 800; }
.add { margin-left: auto; width: 28px; height: 28px; border-radius: 99px; background: #FD6844; }
.state { text-align: center; color: #8B95A7; padding: 28px 8px; }
</style>
