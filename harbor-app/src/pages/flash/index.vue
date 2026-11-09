<template>
  <view class="page" data-figma="1:16">
    <view class="hero">
      <view class="blob a" />
      <view class="blob b" />
      <view class="hero-row">
        <view class="title-block">
          <view class="bolt" />
          <view>
            <text class="title">Flash Sale</text>
            <text class="sub">Big value. Short time. Limited stock.</text>
          </view>
        </view>
        <view class="clock">
          <view class="cell"><text class="n">{{ hh }}</text><text class="u">HRS</text></view>
          <view class="cell"><text class="n">{{ mm }}</text><text class="u">MIN</text></view>
          <view class="cell"><text class="n">{{ ss }}</text><text class="u">SEC</text></view>
        </view>
      </view>
    </view>

    <scroll-view scroll-x class="sessions" :show-scrollbar="false">
      <view
        v-for="s in sessions"
        :key="s.id"
        class="sess"
        :class="{ on: session === s.id }"
        @click="session = s.id"
      >
        <text class="sess-k">{{ s.k }}</text>
        <text class="sess-s">{{ s.s }}</text>
      </view>
    </scroll-view>

    <view v-if="session !== 'now'" class="state">This window has not started.</view>
    <view v-else-if="loading" class="state">Loading…</view>
    <view v-else-if="!shown.length" class="state">No flash items right now.</view>
    <view v-else class="grid">
      <view v-for="p in shown" :key="p.id" class="card" @click="open(p)">
        <view class="thumb">
          <image v-if="p.image" class="img" :src="p.image" mode="aspectFill" />
          <text v-if="claimed(p) != null" class="claim">{{ claimed(p) }}% claimed</text>
          <text v-if="p.onlyLeft" class="limited">Limited stock</text>
        </view>
        <text class="nm">{{ p.name }}</text>
        <text class="meta">{{ p.blurb || p.category }}</text>
        <view class="price-row">
          <text class="price">{{ money(p) }}</text>
          <text v-if="p.compareAt" class="was">${{ Number(p.compareAt).toFixed(2) }}</text>
        </view>
        <view v-if="claimed(p) != null" class="bar"><view class="fill" :style="{ width: claimed(p) + '%' }" /></view>
        <view v-if="p.onlyLeft" class="left-row">
          <text>{{ claimed(p) }}% claimed</text>
          <text>Only {{ p.onlyLeft }} left</text>
        </view>
        <view class="grab" @click.stop="addOne(p)">Grab</view>
      </view>
    </view>
    <HbTabBar active="home" />
  </view>
</template>
<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { dealEndsAt, fetchFlashEnds, listSaleProducts, type Product } from '@/api/products'
import { useCart } from '@/composables/cart'
import HbTabBar from '@/components/HbTabBar.vue'

const { add } = useCart()
const products = ref<Product[]>([])
const loading = ref(true)
const ends = ref('')
const hh = ref('00')
const mm = ref('00')
const ss = ref('00')
const session = ref('now')
const sessions = [
  { id: 'now', k: 'Ongoing', s: 'Now – 11:59 AM' },
  { id: 'noon', k: 'Upcoming', s: '12:00–2:59 PM' },
  { id: 'aft', k: 'Upcoming', s: '3:00–5:59 PM' },
  { id: 'eve', k: 'Upcoming', s: '6:00–8:59 PM' },
]
let timer: ReturnType<typeof setInterval> | null = null
const shown = computed(() => {
  const flash = products.value.filter((p) => p.tag === 'Flash')
  return flash.length ? flash : products.value
})

function tick() {
  const left = Math.max(0, Math.floor((dealEndsAt(ends.value) - Date.now()) / 1000))
  const z = (n: number) => (n < 10 ? '0' : '') + n
  hh.value = z(Math.floor(left / 3600))
  mm.value = z(Math.floor((left % 3600) / 60))
  ss.value = z(left % 60)
}
function claimed(p: Product) {
  if (!p.onlyLeft || p.onlyLeft <= 0) return null
  return Math.min(95, Math.max(15, 100 - p.onlyLeft))
}
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
onMounted(async () => {
  try { ends.value = (await fetchFlashEnds()) || '' } catch { /* */ }
  tick()
  timer = setInterval(tick, 1000)
  try { products.value = await listSaleProducts() } finally { loading.value = false }
})
onUnmounted(() => { if (timer) clearInterval(timer) })
</script>
<style scoped>
.page { min-height: 100vh; background: #FBF8F2; padding-bottom: 96px; color: #313F4B; }
.hero {
  position: relative; overflow: hidden; background: #F77051; color: #fff;
  padding: 14px 16px 22px; padding-top: calc(14px + env(safe-area-inset-top));
  border-radius: 0 0 22px 22px;
}
.blob { position: absolute; border-radius: 99px; background: rgba(255,255,255,.14); }
.blob.a { width: 140px; height: 140px; right: -30px; top: -40px; }
.blob.b { width: 90px; height: 90px; left: 40%; top: 8px; }
.hero-row { position: relative; z-index: 1; display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; }
.title-block { display: flex; gap: 8px; align-items: flex-start; }
.bolt { width: 18px; height: 26px; margin-top: 4px; background: #fff; clip-path: polygon(45% 0, 100% 0, 55% 46%, 100% 46%, 20% 100%, 48% 54%, 0 54%); }
.title { display: block; font-size: 28px; font-weight: 800; letter-spacing: -0.4px; line-height: 1; }
.sub { display: block; margin-top: 4px; font-size: 12px; opacity: .95; }
.clock { display: flex; gap: 6px; }
.cell { min-width: 42px; background: #E94D2D; border-radius: 8px; text-align: center; padding: 6px 4px 4px; }
.n { display: block; font-size: 16px; font-weight: 800; line-height: 1; }
.u { display: block; margin-top: 2px; font-size: 8px; letter-spacing: .4px; opacity: .9; }
.sessions { white-space: nowrap; margin-top: -16px; padding: 0 12px 4px; position: relative; z-index: 2; }
.sess {
  display: inline-flex; flex-direction: column; justify-content: center;
  min-width: 108px; height: 52px; margin-right: 8px; padding: 0 10px;
  border-radius: 12px; background: #fff; color: #8B95A7;
  box-shadow: 0 6px 16px rgba(49,63,75,.06);
}
.sess.on { color: #F55C3F; }
.sess-k { font-size: 13px; font-weight: 800; }
.sess-s { font-size: 10px; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; padding: 12px 16px 0; }
.card { background: #fff; border-radius: 16px; padding: 8px; box-shadow: 0 8px 18px rgba(49,63,75,.05); }
.thumb { height: 132px; border-radius: 12px; overflow: hidden; background: #F3EFE8; position: relative; }
.img { width: 100%; height: 100%; }
.claim, .limited {
  position: absolute; top: 8px; z-index: 1; border-radius: 8px;
  font-size: 10px; font-weight: 800; padding: 3px 6px;
}
.claim { left: 8px; background: #F55C3F; color: #fff; }
.limited { right: 8px; background: #fff; color: #F55C3F; }
.nm { display: block; margin-top: 8px; font-size: 14px; font-weight: 800; line-height: 1.25; }
.meta { display: block; margin-top: 2px; font-size: 11px; color: #8B95A7; min-height: 16px; }
.price-row { display: flex; align-items: baseline; gap: 6px; margin-top: 6px; }
.price { color: #F55C3F; font-size: 18px; font-weight: 800; }
.was { color: #B0B7C3; font-size: 12px; text-decoration: line-through; }
.bar { margin-top: 8px; height: 4px; border-radius: 99px; background: #F9D2C1; overflow: hidden; }
.fill { height: 100%; background: #F55C3F; }
.left-row { display: flex; justify-content: space-between; margin-top: 4px; font-size: 10px; color: #8B95A7; }
.grab {
  margin-top: 8px; height: 36px; border-radius: 12px; background: #F55C3F; color: #fff;
  font-weight: 800; font-size: 14px; display: flex; align-items: center; justify-content: center;
}
.state { text-align: center; color: #8B95A7; padding: 36px 16px; }
</style>
