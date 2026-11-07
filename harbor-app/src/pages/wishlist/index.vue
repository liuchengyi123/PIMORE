<template>
  <view class="page">
    <view class="status hb-status"><text>9:41</text><text>●●● 5G</text></view>
    <view class="nav">
      <text class="back" @click="goBack">‹</text>
      <text class="title">Wishlist</text>
    </view>
    <view v-if="loginRequired" class="state">
      <text>Sign in to see saved items.</text>
      <view class="cta" @click="login">Sign in</view>
    </view>
    <view v-else-if="loading" class="state">Loading…</view>
    <view v-else-if="!products.length" class="state">Wishlist is empty.</view>
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
import { fetchWishlistHtml, openHarborWeb, accountLinks } from '@/api/accountApi'
import { parseFeedCards, type Product } from '@/api/products'
const { t } = useI18n()
const products = ref<Product[]>([])
const loading = ref(false)
const loginRequired = ref(false)
async function refresh() {
  loading.value = true
  try {
    const html = await fetchWishlistHtml()
    if (/name=["']password["']/i.test(html) && !/class=["']card["']/i.test(html)) {
      loginRequired.value = true
      products.value = []
      return
    }
    loginRequired.value = false
    products.value = parseFeedCards(html)
  } catch { products.value = [] }
  finally { loading.value = false }
}
function money(p: Product) {
  const n = Number(p.price || 0)
  return n ? `$${n.toFixed(2)}` : ''
}
function ph(p: Product) {
  if (p.image) return {}
  return { backgroundImage: 'linear-gradient(155deg, #fcd34d 6%, #b45309 94%)' }
}
function open(p: Product) {
  uni.navigateTo({ url: '/pages/pdp/index?sku=' + encodeURIComponent(String(p.sku || p.id)) })
}
function login() { openHarborWeb(accountLinks().login, 'Sign in') }
function goBack() { uni.navigateBack({ fail: () => uni.reLaunch({ url: '/pages/me/index' }) }) }
onShow(() => { uni.setNavigationBarTitle({ title: t('wishlist_title') }); refresh() })
</script>
<style scoped>
.page { min-height: 100vh; background: #F7F4EF; color: #0F2744; padding: 0 16px 40px; padding-top: env(safe-area-inset-top); }
.status { display: flex; justify-content: space-between; padding: 14px 12px 0; font-size: 12px; font-weight: 700; }
.nav { display: flex; align-items: center; gap: 10px; padding: 8px 0 12px; }
.back { font-size: 18px; font-weight: 700; }
.title { font-size: 17px; font-weight: 700; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.card { background: #fff; border: 1px solid #E2E6EE; border-radius: 16px; overflow: hidden; }
.thumb { height: 110px; background: #e8e4dc; }
.img { width: 100%; height: 100%; }
.body { padding: 10px; }
.nm { display: block; font-size: 13px; font-weight: 600; min-height: 34px; }
.price { display: block; margin-top: 6px; font-size: 16px; font-weight: 700; color: #B45309; }
.state { text-align: center; color: #6B7280; padding: 36px 8px; }
.cta { margin: 14px auto 0; width: 140px; height: 41px; border-radius: 12px; background: #0F2744; color: #fff; font-weight: 600; display: flex; align-items: center; justify-content: center; }
</style>
