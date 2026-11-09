<template>
  <view class="page" data-figma="1:19">
    <view class="top">
      <text class="logo">Harbor</text>
      <view class="tools">
        <view class="tool" @click="goSearch"><view class="mag" /></view>
        <view class="tool" @click="goCart">
          <view class="bag" />
          <text v-if="cartCount" class="badge">{{ cartCount > 9 ? '9+' : cartCount }}</text>
        </view>
      </view>
    </view>
    <view class="hero">
      <view class="copy">
        <text class="pill">FREE SHIPPING</text>
        <text class="h">Flash Ship</text>
        <text class="h">Deals</text>
        <text class="s">Top home goods. Fast delivery. Limited time only!</text>
        <text class="cd-k">DEALS END IN</text>
        <view class="clock">
          <view class="cell"><text class="n">{{ hh }}</text><text class="u">HRS</text></view>
          <text class="colon">:</text>
          <view class="cell"><text class="n">{{ mm }}</text><text class="u">MIN</text></view>
          <text class="colon">:</text>
          <view class="cell"><text class="n">{{ ss }}</text><text class="u">SEC</text></view>
        </view>
      </view>
      <view class="seal">FREE SHIPPING</view>
      <image v-if="hero" class="art" :src="hero" mode="aspectFill" />
    </view>
    <view class="ship-bar">
      <view>
        <text class="ship-t">FREE SHIPPING</text>
        <text class="ship-s">on orders $40+</text>
      </view>
      <text class="aside">More home goods. Less shipping costs.</text>
    </view>
    <view class="sec">
      <view>
        <text class="sec-t">Flash Ship Eligible</text>
        <text class="sec-s">Home goods $1 – $10</text>
      </view>
      <text class="chip">FLASH SHIP</text>
    </view>
    <view v-if="loading" class="state">{{ t('flash_loading') }}</view>
    <view v-else-if="!products.length" class="state">{{ t('flash_empty') }}</view>
    <view v-else class="grid">
      <view v-for="p in products" :key="p.id" class="card">
        <view class="thumb" @click="open(p)">
          <image v-if="p.image" class="img" :src="p.image" mode="aspectFill" />
        </view>
        <text class="price">{{ money(p) }}</text>
        <text class="nm">{{ p.name }}</text>
        <view class="shop" @click="open(p)">Shop</view>
      </view>
    </view>
    <view class="enter" @click="goSale">Enter Flash Ship Deals</view>
    <text class="foot">— Great finds. Fast. —</text>
    <HbTabBar active="home" />
  </view>
</template>
<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { useI18n } from '@/composables/i18n'
import { dealEndsAt, fetchFlashEnds, listShipLpProducts, type Product } from '@/api/products'
import { useCart } from '@/composables/cart'
import HbTabBar from '@/components/HbTabBar.vue'

const { t } = useI18n()
const { count } = useCart()
const cartCount = computed(() => count.value)
const products = ref<Product[]>([])
const loading = ref(true)
const flashEnds = ref('')
const hh = ref('00')
const mm = ref('00')
const ss = ref('00')
const hero = computed(() => products.value.find((p) => p.image)?.image || '')
let timer: ReturnType<typeof setInterval> | null = null
function tick() {
  const left = Math.max(0, Math.floor((dealEndsAt(flashEnds.value) - Date.now()) / 1000))
  const z = (n: number) => (n < 10 ? '0' : '') + n
  hh.value = z(Math.floor(left / 3600))
  mm.value = z(Math.floor((left % 3600) / 60))
  ss.value = z(left % 60)
}
onMounted(async () => {
  try { flashEnds.value = (await fetchFlashEnds()) || '' } catch { /* ignore */ }
  tick()
  timer = setInterval(tick, 1000)
  try { products.value = await listShipLpProducts() } finally { loading.value = false }
})
onUnmounted(() => { if (timer) clearInterval(timer) })
function money(p: Product) {
  const n = Number(p.price || 0)
  return n ? `$${Math.round(n)}` : ''
}
function open(p: Product) {
  uni.navigateTo({ url: '/pages/pdp/index?sku=' + encodeURIComponent(String(p.sku || p.id)) })
}
function goSearch() { uni.navigateTo({ url: '/pages/search/index' }) }
function goCart() { uni.reLaunch({ url: '/pages/cart/index' }) }
function goSale() { uni.navigateTo({ url: '/pages/sale/index' }) }
onShow(() => uni.setNavigationBarTitle({ title: t('flash_title') }))
</script>
<style scoped>
.page { min-height: 100vh; background: #FCFBF8; color: #1B2430; padding: 10px 16px 110px; padding-top: calc(10px + env(safe-area-inset-top)); }
.top { display: flex; justify-content: space-between; align-items: center; height: 44px; }
.logo { font-size: 28px; font-weight: 800; color: #FC6444; letter-spacing: -0.4px; }
.tools { display: flex; gap: 6px; }
.tool { width: 32px; height: 32px; position: relative; display: flex; align-items: center; justify-content: center; }
.mag, .bag { width: 16px; height: 16px; border: 1.8px solid #1B2430; border-radius: 99px; }
.bag { border-radius: 3px; height: 13px; margin-top: 3px; }
.badge { position: absolute; top: 0; right: -2px; min-width: 16px; height: 16px; border-radius: 99px; background: #FC6444; color: #fff; font-size: 10px; text-align: center; line-height: 16px; }
.hero { margin-top: 8px; background: #F9F2E8; border-radius: 18px; min-height: 176px; padding: 16px; position: relative; overflow: hidden; }
.copy { position: relative; z-index: 1; max-width: 62%; }
.pill { display: inline-block; background: #FC6444; color: #fff; font-size: 10px; font-weight: 800; border-radius: 8px; padding: 3px 6px; }
.h { display: block; font-size: 28px; font-weight: 900; line-height: 1.02; letter-spacing: -0.5px; }
.s { display: block; margin-top: 6px; font-size: 12px; color: #6B7280; }
.cd-k { display: block; margin-top: 10px; font-size: 10px; letter-spacing: .6px; color: #8B95A7; }
.clock { display: flex; align-items: center; gap: 4px; margin-top: 4px; }
.cell { min-width: 36px; text-align: center; }
.n { display: block; color: #FC6444; font-size: 18px; font-weight: 800; line-height: 1; }
.u { display: block; font-size: 8px; color: #8B95A7; }
.colon { color: #FC6444; font-weight: 800; }
.seal { position: absolute; right: 12px; top: 12px; z-index: 2; width: 64px; height: 64px; border-radius: 99px; background: #FC6444; color: #fff; font-size: 9px; font-weight: 800; display: flex; align-items: center; justify-content: center; text-align: center; }
.art { position: absolute; right: 0; bottom: 0; width: 48%; height: 78%; }
.ship-bar { margin-top: 12px; background: #fff; border-radius: 14px; padding: 12px; display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.ship-t { display: block; color: #FC6444; font-weight: 800; font-size: 13px; }
.ship-s { display: block; font-size: 12px; font-weight: 700; }
.aside { color: #FC6444; font-size: 12px; font-style: italic; max-width: 120px; text-align: right; }
.sec { margin: 16px 0 10px; display: flex; justify-content: space-between; align-items: flex-end; }
.sec-t { display: block; font-size: 18px; font-weight: 800; }
.sec-s { display: block; color: #8B95A7; font-size: 12px; }
.chip { background: #FFF1EC; color: #FC6444; border-radius: 999px; font-size: 11px; font-weight: 800; padding: 4px 8px; }
.grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; }
.card { background: #fff; border-radius: 14px; padding: 8px; }
.thumb { height: 84px; border-radius: 10px; overflow: hidden; background: #F4EFEA; }
.img { width: 100%; height: 100%; }
.price { display: block; margin-top: 6px; font-weight: 800; font-size: 14px; }
.nm { display: block; font-size: 11px; min-height: 28px; line-height: 1.25; }
.shop { margin-top: 6px; height: 28px; border-radius: 8px; background: #FC6444; color: #fff; font-size: 12px; font-weight: 700; display: flex; align-items: center; justify-content: center; }
.enter { margin-top: 16px; height: 48px; border-radius: 24px; background: #FC6444; color: #fff; font-weight: 800; display: flex; align-items: center; justify-content: center; }
.foot { display: block; text-align: center; margin-top: 8px; color: #C5CCD4; font-size: 12px; }
.state { text-align: center; color: #8B95A7; padding: 24px 8px; }
</style>
