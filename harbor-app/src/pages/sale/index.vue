<template>
  <view class="page" data-figma="1:15">
    <view class="top">
      <view class="brand">
        <view class="house" />
        <view>
          <text class="logo">HomeJoy</text>
          <text class="tag">SMALL FINDS. BIG JOY.</text>
        </view>
      </view>
      <view class="tools">
        <view class="tool" @click="goSearch"><view class="mag" /></view>
        <view class="tool" @click="goCart">
          <view class="bag" />
          <text v-if="cartCount" class="badge">{{ cartCount > 9 ? '9+' : cartCount }}</text>
        </view>
      </view>
    </view>

    <view class="hero">
      <view class="hero-copy">
        <text class="script">Today's</text>
        <text class="deals">DEALS</text>
        <text class="kicker">TOP HOME GOODS. LOW PRICES.</text>
        <text class="kicker">LIMITED TIME ONLY!</text>
        <view class="clock">
          <view class="cell"><text class="n">{{ hh }}</text><text class="u">HRS</text></view>
          <text class="colon">:</text>
          <view class="cell"><text class="n">{{ mm }}</text><text class="u">MIN</text></view>
          <text class="colon">:</text>
          <view class="cell"><text class="n">{{ ss }}</text><text class="u">SEC</text></view>
        </view>
      </view>
      <view class="ribbon">
        <text>UP TO</text>
        <text class="ribbon-n">{{ maxOff || 70 }}%</text>
        <text>OFF</text>
      </view>
      <image v-if="heroShot" class="hero-photo" :src="heroShot" mode="aspectFill" />
    </view>

    <view class="promos">
      <view class="promo" @click="goShip">
        <view class="truck" />
        <view>
          <text class="promo-t">Free Shipping</text>
          <text class="promo-s">on orders over $40</text>
        </view>
      </view>
      <view class="promo" @click="goCoupons">
        <view class="ticket" />
        <view>
          <text class="promo-t">Extra Savings</text>
          <text class="promo-s">Use Our Coupons</text>
        </view>
        <text class="chev">›</text>
      </view>
    </view>

    <view class="sec">
      <text class="sec-t">Hot Deals</text>
      <text class="see" @click="goSearch">See All ›</text>
    </view>

    <view v-if="loading" class="state">Loading…</view>
    <view v-else-if="!products.length" class="state">No sale items right now.</view>
    <view v-else class="grid">
      <view v-for="p in products" :key="p.id" class="card" @click="open(p)">
        <view class="thumb">
          <image v-if="p.image" class="img" :src="p.image" mode="aspectFill" />
          <text v-if="off(p)" class="flag">-{{ off(p) }}%</text>
        </view>
        <text class="nm">{{ p.name }}</text>
        <view class="row">
          <text v-if="p.compareAt" class="was">${{ Number(p.compareAt).toFixed(2) }}</text>
          <text class="price">{{ money(p) }}</text>
          <view class="add" @click.stop="addOne(p)">
            <view class="add-bag" />
          </view>
        </view>
      </view>
    </view>
    <HbTabBar active="home" />
  </view>
</template>
<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { useI18n } from '@/composables/i18n'
import { dealEndsAt, fetchDealEnds, listSaleProducts, type Product } from '@/api/products'
import { handleLuckyBack } from '@/composables/lucky'
import { useCart } from '@/composables/cart'
import HbTabBar from '@/components/HbTabBar.vue'

const { t } = useI18n()
const { add, count } = useCart()
const cartCount = computed(() => count.value)
const products = ref<Product[]>([])
const loading = ref(true)
const saleEnds = ref('')
const hh = ref('00')
const mm = ref('00')
const ss = ref('00')
let timer: ReturnType<typeof setInterval> | null = null
const heroShot = computed(() => products.value.find((p) => p.image)?.image || '')
const maxOff = computed(() => products.value.reduce((n, p) => Math.max(n, off(p)), 0))

function tick() {
  const left = Math.max(0, Math.floor((dealEndsAt(saleEnds.value) - Date.now()) / 1000))
  const z = (n: number) => (n < 10 ? '0' : '') + n
  hh.value = z(Math.floor(left / 3600))
  mm.value = z(Math.floor((left % 3600) / 60))
  ss.value = z(left % 60)
}
onMounted(async () => {
  try { saleEnds.value = (await fetchDealEnds()) || '' } catch { /* */ }
  tick()
  timer = setInterval(tick, 1000)
  try { products.value = await listSaleProducts() } finally { loading.value = false }
})
onUnmounted(() => { if (timer) clearInterval(timer) })
function money(p: Product) {
  const n = Number(p.price || 0)
  return n ? `$${n.toFixed(2)}` : ''
}
function off(p: Product) {
  if (p.offPct && p.offPct > 0) return p.offPct
  if (p.compareAt && p.compareAt > p.price) return Math.round((1 - p.price / p.compareAt) * 100)
  return 0
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
function goSearch() { uni.navigateTo({ url: '/pages/search/index' }) }
function goCart() { uni.reLaunch({ url: '/pages/cart/index' }) }
function goShip() { uni.navigateTo({ url: '/pages/ship-lp/index' }) }
function goCoupons() { uni.navigateTo({ url: '/pages/coupons/index' }) }
onShow(() => uni.setNavigationBarTitle({ title: t('sale_title') }))
void goBack
</script>
<style scoped>
.page { min-height: 100vh; background: #FCFBFA; color: #313F4B; padding: 8px 16px 96px; padding-top: calc(8px + env(safe-area-inset-top)); }
.top { display: flex; align-items: center; justify-content: space-between; height: 48px; }
.brand { display: flex; align-items: center; gap: 8px; }
.house { width: 28px; height: 28px; border-radius: 8px; background: #FD623E; position: relative; }
.house::before { content: ''; position: absolute; left: 6px; top: 6px; border-left: 8px solid transparent; border-right: 8px solid transparent; border-bottom: 7px solid #fff; }
.house::after { content: ''; position: absolute; left: 9px; top: 13px; width: 10px; height: 8px; background: #fff; }
.logo { display: block; font-size: 20px; font-weight: 800; letter-spacing: -0.3px; line-height: 1; }
.tag { display: block; margin-top: 2px; font-size: 8px; letter-spacing: 0.6px; color: #9AA3AE; font-weight: 700; }
.tools { display: flex; gap: 4px; }
.tool { width: 36px; height: 36px; display: flex; align-items: center; justify-content: center; position: relative; }
.mag, .bag { width: 18px; height: 18px; border: 1.8px solid #313F4B; border-radius: 99px; }
.bag { border-radius: 4px 4px 6px 6px; height: 14px; margin-top: 4px; }
.badge { position: absolute; top: 2px; right: 0; min-width: 16px; height: 16px; border-radius: 99px; background: #FD623E; color: #fff; font-size: 10px; font-weight: 700; text-align: center; line-height: 16px; }
.hero { margin-top: 8px; height: 188px; border-radius: 16px; overflow: hidden; position: relative; background: linear-gradient(100deg, #FD623E 0%, #FE6849 58%, #F6E7DC 58%); }
.hero-copy { position: relative; z-index: 1; padding: 16px 14px; width: 62%; }
.script { display: block; font-size: 22px; font-style: italic; font-weight: 700; color: #fff; }
.deals { display: block; font-size: 34px; font-weight: 900; color: #fff; letter-spacing: -0.6px; line-height: 0.95; }
.kicker { display: block; font-size: 9px; font-weight: 700; letter-spacing: 0.4px; color: #fff; }
.clock { display: flex; align-items: center; gap: 4px; margin-top: 10px; }
.cell { min-width: 40px; background: #CE4327; border-radius: 8px; text-align: center; padding: 4px 0 3px; }
.n { display: block; color: #fff; font-size: 16px; font-weight: 800; line-height: 1; }
.u { display: block; color: rgba(255,255,255,.85); font-size: 8px; letter-spacing: 0.4px; }
.colon { color: #fff; font-weight: 800; }
.ribbon { position: absolute; right: 18px; top: 0; z-index: 2; width: 54px; background: #FD623E; color: #fff; text-align: center; padding: 8px 4px 12px; font-size: 9px; font-weight: 800; clip-path: polygon(0 0, 100% 0, 100% 100%, 50% 86%, 0 100%); }
.ribbon-n { display: block; font-size: 16px; line-height: 1.1; }
.hero-photo { position: absolute; right: 0; top: 28px; width: 46%; height: 160px; }
.promos { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 12px; }
.promo { background: #fff; border-radius: 14px; min-height: 64px; padding: 10px 12px; display: flex; align-items: center; gap: 8px; box-shadow: 0 4px 14px rgba(49,63,75,.05); }
.truck, .ticket { width: 28px; height: 28px; border-radius: 8px; background: #FFF1EC; flex: none; }
.promo-t { display: block; font-size: 13px; font-weight: 800; }
.promo-s { display: block; font-size: 11px; color: #8B95A7; }
.chev { margin-left: auto; color: #C5CCD4; font-size: 18px; }
.sec { display: flex; justify-content: space-between; align-items: baseline; margin: 18px 0 10px; }
.sec-t { font-size: 20px; font-weight: 800; }
.see { color: #FD623E; font-size: 13px; font-weight: 700; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.card { background: #fff; border-radius: 16px; padding: 8px 8px 10px; box-shadow: 0 6px 16px rgba(49,63,75,.05); }
.thumb { height: 132px; border-radius: 12px; overflow: hidden; background: #F4EFEA; position: relative; }
.img { width: 100%; height: 100%; }
.flag { position: absolute; left: 8px; top: 8px; background: #FD623E; color: #fff; font-size: 11px; font-weight: 800; border-radius: 8px; padding: 3px 6px; }
.nm { display: block; margin-top: 8px; font-size: 13px; font-weight: 600; line-height: 1.3; min-height: 34px; color: #313F4B; }
.row { display: flex; align-items: center; gap: 6px; margin-top: 4px; }
.was { color: #B0B7C3; text-decoration: line-through; font-size: 12px; }
.price { color: #FD623E; font-weight: 800; font-size: 15px; }
.add { margin-left: auto; width: 28px; height: 28px; border-radius: 99px; background: #FD623E; display: flex; align-items: center; justify-content: center; }
.add-bag { width: 12px; height: 9px; border: 1.5px solid #fff; border-radius: 2px; }
.state { text-align: center; color: #8B95A7; padding: 28px 8px; }
</style>
