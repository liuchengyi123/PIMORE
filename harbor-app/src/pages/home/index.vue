<template>
  <view class="page">
    <view class="sticky-top">
      <view class="brand-row">
        <view>
          <text class="logo">Harbor <text class="sg">small goods</text></text>
          <text class="tagline">{{ t('home_tagline') }}</text>
        </view>
        <view class="locale" @click="goLocale">{{ localeNative }} · USD</view>
      </view>
      <view class="search" @click="goSearch">
        <view class="search-ico">
          <view class="ring" />
          <view class="handle" />
        </view>
        <text class="search-ph">{{ t('home_search_ph') }}</text>
      </view>
    </view>

    <view class="hero">
      <view class="hero-veil" />
      <view class="hero-inner">
        <text class="hero-kicker">{{ t('home_hero_kicker') }}</text>
        <text class="hero-title">{{ t('home_hero_title') }}</text>
        <text class="hero-sub">{{ t('home_hero_sub') }}</text>
        <view class="hero-actions">
          <view class="btn-primary" @click="scrollDeals">{{ t('home_shop_now') }}</view>
          <view class="btn-ghost" @click="goShip">{{ t('home_how_shipping') }}</view>
        </view>
      </view>
    </view>

    <view class="body">
      <scroll-view scroll-x class="cats" :show-scrollbar="false">
        <view
          class="cat-pill"
          :class="{ on: !activeCat }"
          @click="filterCat('')"
        >{{ t('cat_all') }}</view>
        <view
          v-for="c in categories"
          :key="c.id"
          class="cat-pill"
          :class="{ on: activeCat === c.id }"
          @click="filterCat(c.id)"
        >
          {{ catLabel(c.id) }}
        </view>
      </scroll-view>

      <view class="quick quick-grid-5">
        <view class="quick-item" @click="goSale"><view class="q-ico" style="background:#FEF3C7" /><text>{{ t('home_sale') }}</text></view>
        <view class="quick-item" @click="goNew"><view class="q-ico" style="background:#D1FAE5" /><text>{{ t('home_new') }}</text></view>
        <view class="quick-item" @click="goShip"><view class="q-ico" style="background:#E0F2FE" /><text>{{ t('home_flash') }}</text></view>
        <view class="quick-item" @click="goCoupons"><view class="q-ico" style="background:#FCE7F3" /><text>{{ t('home_coupons') || 'Coupons' }}</text></view>
        <view class="quick-item" @click="goCheckin"><view class="q-ico" style="background:#EDE9FE" /><text>{{ t('home_checkin') || 'Check-in' }}</text></view>
      </view>

      <view class="section-head">
        <view>
          <text class="section-kicker">{{ t('home_curated') }}</text>
          <text class="section-title">{{ activeCat ? catLabel(activeCat) : t('home_for_you') }}</text>
        </view>
        <HbDealClock :label="t('deal_ends')" :ends-at="dealEnds" compact />
      </view>

      <view class="sponsored" v-if="false">
        <text class="sponsored-text">
          <text class="sponsored-mark">Sponsored</text>
          · Storage edit for small apartments
        </text>
        <text class="sponsored-open">Open</text>
      </view>

      <view class="grid">
        <HbProductCard v-for="p in products" :key="p.id" :product="p" />
      </view>
    </view>

    <HbTabBar active="home" />
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
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
  background: $hb-paper;
  color: $hb-ink;
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
.page { background: #F7F4EF; padding-top: env(safe-area-inset-top); }
</style>
