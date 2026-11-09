<template>
  <view class="page" data-figma="1:5">
    <view class="sticky-top">
      <view class="brand-row">
        <view class="brand">
          <view class="mark" aria-hidden="true" />
          <view>
            <text class="logo">Pimo</text>
            <text class="tagline">Better Homes. Happier Days.</text>
          </view>
        </view>
        <view class="locale" @click="goLocale">
          <text class="flag">🇺🇸</text>
          <text>{{ localeNative || 'US' }}</text>
          <text class="chev">▾</text>
        </view>
      </view>
      <view class="search" @click="goSearch">
        <view class="search-ico">
          <view class="ring" />
          <view class="handle" />
        </view>
        <text class="search-ph">{{ t('home_search_ph') || 'Search home essentials...' }}</text>
      </view>
    </view>

    <view class="hero">
      <view class="hero-copy">
        <text class="hero-kicker">LIMITED TIME</text>
        <text class="hero-title">Up to 50% Off</text>
        <text class="hero-title">Home Essentials</text>
        <text class="hero-sub">Refresh your space, for less.</text>
        <view class="hero-cta" @click="scrollDeals">Shop Sale →</view>
      </view>
      <view class="hero-art">
        <image v-if="heroShot" class="hero-photo" :src="heroShot" mode="aspectFill" />
        <view v-else class="hero-fallback" />
      </view>
      <view class="dots">
        <view class="dot on" />
        <view class="dot" />
        <view class="dot" />
        <view class="dot" />
      </view>
    </view>

    <view class="tiles">
      <view v-for="tile in tiles" :key="tile.id" class="tile" @click="filterCat(tile.id)">
        <view class="tile-ico" :style="{ background: tile.bg, color: tile.fg }">
          <view class="glyph" :class="tile.id" />
        </view>
        <text>{{ tile.label }}</text>
      </view>
    </view>

    <view class="body">
      <view class="section-head">
        <view>
          <text class="section-title"><text class="bolt">⚡</text> Flash Deals</text>
          <text class="section-sub">Big savings. Limited time.</text>
        </view>
        <view class="clock-pill">
          <HbDealClock :ends-at="dealEnds" compact />
        </view>
      </view>
      <scroll-view scroll-x class="hscroll" :show-scrollbar="false">
        <view class="hrow">
          <HbProductCard v-for="p in flashProducts" :key="'f'+p.id" class="hcard" :product="p" plain />
        </view>
      </scroll-view>

      <view class="section-head">
        <view>
          <text class="section-title">✦ New Arrivals</text>
          <text class="section-sub">Fresh finds for your home.</text>
        </view>
        <text class="see-all" @click="goNew">See All →</text>
      </view>
      <scroll-view scroll-x class="hscroll" :show-scrollbar="false">
        <view class="hrow">
          <HbProductCard v-for="p in newProducts" :key="'n'+p.id" class="hcard" :product="p" plain />
        </view>
      </scroll-view>

      <view class="section-head">
        <view>
          <text class="section-title">Just for You</text>
          <text class="section-sub">Based on your interests.</text>
        </view>
      </view>
      <view class="grid">
        <HbProductCard v-for="p in forYou" :key="'y'+p.id" :product="p" plain />
      </view>
    </view>

    <HbTabBar active="home" />
  </view>
</template>

<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { useI18n } from '@/composables/i18n'
import { CATEGORIES, listProducts, listByCategory, fetchDealEnds, type Product } from '@/api/products'
import HbProductCard from '@/components/HbProductCard.vue'
import HbTabBar from '@/components/HbTabBar.vue'
import HbDealClock from '@/components/HbDealClock.vue'

const { t, localeNative, catLabel } = useI18n()
const categories = CATEGORIES
const products = ref<Product[]>([])
const liveSource = ref(false)
const activeCat = ref('')
const loadingFeed = ref(false)
const dealEnds = ref('')
const tiles = [
  { id: 'kitchen', label: 'Kitchen', bg: '#FFF1EC', fg: '#FF6B4A' },
  { id: 'storage', label: 'Storage', bg: '#E7F8EE', fg: '#2FBF71' },
  { id: 'cleaning', label: 'Cleaning', bg: '#E6F7FA', fg: '#2BB3C7' },
  { id: 'textile', label: 'Textile', bg: '#F0EEFF', fg: '#7C6BF2' },
]
const flashProducts = computed(() => products.value.slice(0, 4))
const newProducts = computed(() => products.value.slice(4, 8))
const forYou = computed(() => {
  const rest = products.value.slice(8, 12)
  return rest.length ? rest : products.value.slice(0, 2)
})
const heroShot = computed(() => products.value[0]?.image || '')

async function loadFeed(cat = '') {
  loadingFeed.value = true
  try {
    const rows = cat ? await listByCategory(cat) : await listProducts()
    products.value = rows
    liveSource.value = rows.some((p) => p.live)
  } finally {
    loadingFeed.value = false
  }
}

onMounted(async () => {
  loadFeed('')
  try { dealEnds.value = (await fetchDealEnds()) || '' } catch { /* ignore */ }
})

function goMe() {
  uni.reLaunch({ url: '/pages/me/index' })
}
function goLocale() {
  uni.navigateTo({ url: '/pages/locale/index' })
}
function goSearch() {
  uni.navigateTo({ url: '/pages/search/index' })
}
function goBrowse() {
  uni.reLaunch({ url: '/pages/browse/index' })
}
function goCategories() {
  uni.navigateTo({ url: '/pages/categories/index' })
}
function goCoupons() { uni.navigateTo({ url: '/pages/coupons/index' }) }
function goCheckin() { uni.navigateTo({ url: '/pages/checkin/index' }) }
function goSale() {
  uni.navigateTo({ url: '/pages/sale/index' })
}
function goShip() {
  uni.navigateTo({ url: '/pages/ship-lp/index' })
}
function goCompare() {
  uni.navigateTo({ url: '/pages/compare/index' })
}
function goHelp() {
  uni.navigateTo({ url: '/pages/help/index' })
}

function goNew() {
  uni.navigateTo({ url: '/pages/new/index' })
}
function filterCat(id: string) {
  // Same page: refresh the curated grid only (do not open category page).
  activeCat.value = id || ''
  loadFeed(activeCat.value)
}
function scrollDeals() {
  goSale()
}

</script>

<style lang="scss" scoped>
@import '@/styles/theme.scss';

.page {
  min-height: 100vh;
  background: #F7F8FB;
  color: $hb-ink;
  padding-top: env(safe-area-inset-top);
}
.sticky-top {
  position: sticky;
  top: 0;
  z-index: 40;
  padding: 14px 16px 12px;
  padding-top: calc(14px + env(safe-area-inset-top));
  background: rgba(247, 246, 243, 0.88);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
}
.brand-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.logo {
  display: block;
  font-size: 26px;
  font-weight: 720;
  color: $hb-ink;
  letter-spacing: -0.8px;
}
.tagline {
  display: block;
  font-size: 12px;
  color: $hb-muted;
  margin-top: 2px;
  letter-spacing: 0.1px;
}
.locale {
  background: rgba(255, 255, 255, 0.9);
  border-radius: $hb-radius-pill;
  padding: 8px 12px;
  font-size: 11px;
  font-weight: 650;
  color: $hb-ink;
  box-shadow: $hb-shadow-soft;
}
.search {
  height: 46px;
  border-radius: 14px;
  background: $hb-white;
  display: flex;
  align-items: center;
  padding: 0 14px;
  gap: 10px;
  box-shadow: $hb-shadow-soft;
}
.search-ico {
  position: relative;
  width: 16px;
  height: 16px;
  flex: none;
}
.ring {
  width: 11px;
  height: 11px;
  border: 1.8px solid $hb-muted;
  border-radius: 99px;
  opacity: 0.7;
}
.handle {
  position: absolute;
  right: 0;
  bottom: 0;
  width: 6px;
  height: 1.8px;
  background: $hb-muted;
  opacity: 0.7;
  transform: rotate(45deg);
  transform-origin: left center;
}
.search-ph {
  font-size: 14px;
  color: $hb-muted;
}
.hero {
  margin: 4px 16px 0;
  border-radius: 28px;
  min-height: 210px;
  background: linear-gradient(120deg, #0F2744 0%, #1A3A5C 45%, #0E7490 100%);
  color: $hb-white;
  position: relative;
  overflow: hidden;
  box-shadow: $hb-shadow-lift;
}
.hero-veil {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, transparent 30%, rgba(20, 53, 40, 0.35) 100%);
}
.hero-inner {
  position: relative;
  padding: 22px 20px 20px;
}
.hero-kicker {
  display: block;
  font-size: 11px;
  font-weight: 650;
  letter-spacing: 1.4px;
  text-transform: uppercase;
  opacity: 0.72;
}
.hero-title {
  display: block;
  font-size: 26px;
  font-weight: 720;
  line-height: 1.18;
  margin-top: 10px;
  letter-spacing: -0.7px;
  max-width: 280px;
}
.hero-sub {
  display: block;
  font-size: 13px;
  opacity: 0.78;
  margin-top: 10px;
  line-height: 1.4;
}
.hero-actions {
  display: flex;
  gap: 8px;
  margin-top: 18px;
}
.btn-primary {
  background: $hb-white;
  color: $hb-forest;
  font-weight: 720;
  font-size: 13px;
  padding: 11px 18px;
  border-radius: $hb-radius-pill;
}
.btn-ghost {
  background: rgba(255, 255, 255, 0.1);
  color: $hb-white;
  font-weight: 600;
  font-size: 13px;
  padding: 11px 16px;
  border-radius: $hb-radius-pill;
  border: 1px solid rgba(255, 255, 255, 0.22);
}
.body {
  padding: 18px 16px 8px;
}
.cats {
  white-space: nowrap;
  margin-bottom: 14px;
}
.quick {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  margin-bottom: 22px;
}
.quick-item {
  text-align: center;
  padding: 12px 6px;
  border-radius: 16px;
  background: $hb-white;
  font-size: 12px;
  font-weight: 700;
  color: $hb-forest;
  box-shadow: $hb-shadow-soft;
}
.cat-pill {
  &.on {
    background: $hb-forest;
    color: $hb-white;
    font-weight: 680;
  }

  display: inline-flex;
  align-items: center;
  padding: 10px 16px;
  margin-right: 8px;
  border-radius: $hb-radius-pill;
  background: $hb-white;
  color: $hb-ink;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: -0.1px;
  box-shadow: $hb-shadow-soft;
}
.section-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 14px;
}
.section-kicker {
  display: block;
  font-size: 11px;
  font-weight: 650;
  letter-spacing: 1.2px;
  text-transform: uppercase;
  color: $hb-muted;
  margin-bottom: 4px;
}
.section-title {
  display: block;
  font-size: 22px;
  font-weight: 720;
  letter-spacing: -0.5px;
}
.see-all {
  font-size: 13px;
  color: $hb-forest;
  font-weight: 680;
  padding-bottom: 2px;
}
.sponsored {
  border-radius: 18px;
  padding: 12px 14px;
  margin-bottom: 14px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: $hb-white;
  box-shadow: $hb-shadow-soft;
}
.sponsored-text {
  font-size: 12px;
  color: $hb-muted;
  flex: 1;
  padding-right: 8px;
}
.sponsored-mark {
  font-weight: 700;
  color: $hb-forest;
}
.sponsored-open {
  font-size: 12px;
  color: $hb-forest;
  font-weight: 700;
}
.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.sg { font-size: 11px; font-weight: 600; color: #0E7490; }
.locale {
  background: #E0F2FE !important; color: #0E7490 !important; border-radius: 999px;
  padding: 6px 10px; font-size: 11px; font-weight: 700;
}
.cat-pill.on { background: #0F2744 !important; border-color: #0F2744 !important; }
.fn-app-home { }
.quick-grid-5 {
  display: grid !important;
  grid-template-columns: repeat(5, 1fr);
  gap: 8px;
  padding: 14px 10px;
}
.quick-grid-5 .quick-item {
  display: flex; flex-direction: column; align-items: center; gap: 4px;
  font-size: 10px; font-weight: 600; color: #0F2744;
}
.q-ico { width: 40px; height: 40px; border-radius: 12px; }
.page { background: #F7F8FB; padding-top: env(safe-area-inset-top); }

.sticky-top {
  background: rgba(247, 248, 251, 0.94);
  padding: 8px 16px 10px;
  padding-top: calc(8px + env(safe-area-inset-top));
}
.brand { display: flex; align-items: center; gap: 8px; }
.mark {
  width: 28px; height: 28px; border-radius: 8px;
  background: $hb-coral;
  position: relative;
}
.mark::before {
  content: '';
  position: absolute; left: 6px; top: 6px;
  width: 0; height: 0;
  border-left: 8px solid transparent;
  border-right: 8px solid transparent;
  border-bottom: 7px solid #fff;
}
.mark::after {
  content: '';
  position: absolute; left: 9px; top: 13px;
  width: 10px; height: 8px;
  background: #fff;
  border-radius: 1px;
}
.logo { font-size: 22px; font-weight: 800; letter-spacing: -0.4px; line-height: 1; }
.tagline { font-size: 11px; color: #98A2B3; margin-top: 2px; }
.locale {
  display: flex; align-items: center; gap: 4px;
  background: #fff !important; color: $hb-ink !important;
  border: 1px solid #EEF1F6; border-radius: 999px;
  padding: 6px 10px; font-size: 12px; font-weight: 700;
  box-shadow: none;
}
.chev { color: #98A2B3; font-size: 10px; }
.search {
  height: 40px; border-radius: 20px; background: #fff;
  border: 1px solid #EEF1F6; box-shadow: none;
}
.hero {
  margin: 8px 16px 0;
  min-height: 156px;
  border-radius: 18px;
  background: linear-gradient(105deg, #FF7A5C 0%, #FF6B4A 55%, #FF8F6E 100%);
  display: flex;
  overflow: hidden;
  position: relative;
  box-shadow: 0 12px 28px rgba(255, 107, 74, 0.22);
}
.hero-copy { position: relative; z-index: 1; padding: 16px 14px 28px; width: 62%; }
.hero-kicker {
  font-size: 10px; letter-spacing: 1.2px; font-weight: 700; opacity: 0.9; margin: 0;
}
.hero-title {
  font-size: 22px; line-height: 1.15; font-weight: 800; letter-spacing: -0.4px;
  margin-top: 4px; max-width: none;
}
.hero-sub { font-size: 12px; opacity: 0.95; margin-top: 6px; }
.hero-cta {
  display: inline-flex; margin-top: 12px;
  background: #fff; color: #1B2B4A;
  font-size: 13px; font-weight: 700;
  border-radius: 999px; padding: 7px 14px;
}
.hero-art {
  position: absolute; right: 0; top: 0; bottom: 0; width: 46%;
}
.hero-photo, .hero-fallback { width: 100%; height: 100%; display: block; }
.hero-fallback { background: linear-gradient(160deg, rgba(255,255,255,.35), rgba(255,255,255,0)); }
.dots {
  position: absolute; left: 16px; bottom: 10px; display: flex; gap: 5px; z-index: 2;
}
.dot { width: 5px; height: 5px; border-radius: 99px; background: rgba(255,255,255,.55); }
.dot.on { width: 14px; background: #fff; }
.tiles {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px;
  padding: 14px 16px 4px;
}
.tile {
  background: #fff; border-radius: 16px; padding: 12px 4px 10px;
  text-align: center; font-size: 12px; font-weight: 600; color: #1B2B4A;
  box-shadow: 0 6px 16px rgba(27, 43, 74, 0.04);
}
.tile-ico {
  width: 36px; height: 36px; border-radius: 99px; margin: 0 auto 8px;
  display: flex; align-items: center; justify-content: center;
}
.glyph { width: 16px; height: 16px; border: 2px solid currentColor; border-radius: 4px; }
.section-head { align-items: center; margin: 18px 0 10px; }
.section-title { font-size: 16px; font-weight: 800; letter-spacing: -0.2px; }
.section-sub { display: block; margin-top: 2px; font-size: 12px; color: #98A2B3; font-weight: 500; }
.see-all { color: #98A2B3; font-size: 13px; font-weight: 600; }
.clock-pill {
  background: #fff; border-radius: 12px; padding: 6px 8px;
  box-shadow: 0 4px 12px rgba(27,43,74,.05);
}
.hscroll { margin: 0 -16px; }
.hrow { display: flex; gap: 10px; padding: 0 16px 4px; }
.hcard { width: 148px; flex: none; }
.grid { gap: 10px; }
.body { padding-top: 6px; }
</style>
