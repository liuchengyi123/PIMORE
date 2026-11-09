<template>
  <view class="page" data-figma="1:2" :data-deal="dealEnds">
    <view class="top">
      <view>
        <text class="word"><text class="coral">Harbor</text> / Pimo</text>
        <text class="kicker">HOME GOODS FOR A BRIGHTER EVERYDAY</text>
      </view>
      <view class="tools">
        <view class="tool" @click="goSearch">
          <view class="mag" />
        </view>
        <view class="tool" @click="goCart">
          <view class="bag" />
          <text v-if="cartCount" class="badge">{{ cartCount > 9 ? '9+' : cartCount }}</text>
        </view>
      </view>
    </view>
    <view class="search" @click="goSearch">
      <view class="mag sm" />
      <text>Search home goods, decor, kitchen...</text>
    </view>
    <scroll-view scroll-x class="chips" :show-scrollbar="false">
      <view
        v-for="c in chipList"
        :key="c"
        class="chip"
        :class="{ on: activeCat === c || (!activeCat && c === 'All') }"
        @click="pick(c)"
      >
        {{ c === 'All' ? 'All' : labelFor(c) }}
      </view>
    </scroll-view>

    <view class="sec">
      <text class="title">Everyday essentials</text>
      <text class="sub">Thoughtful home goods. Better living.{{ liveSource ? '' : '' }}</text>
    </view>

    <view class="grid">
      <HbProductCard v-for="p in products" :key="p.id" :product="p" variant="browse" plain />
    </view>
    <HbTabBar active="browse" />
  </view>
</template>

<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { onLoad, onShow } from '@dcloudio/uni-app'
import { ALL_CATEGORIES, listByCategory, fetchDealEnds, type Product } from '@/api/products'
import HbProductCard from '@/components/HbProductCard.vue'
import HbTabBar from '@/components/HbTabBar.vue'
import { useI18n } from '@/composables/i18n'
import { useCart } from '@/composables/cart'

const { t, catLabel } = useI18n()
const { count } = useCart()
const cartCount = computed(() => count.value)
function goSearch() { uni.navigateTo({ url: '/pages/search/index' }) }
function goCart() { uni.reLaunch({ url: '/pages/cart/index' }) }

const chipList = ['All', ...ALL_CATEGORIES.map((c) => c.id)]
const activeCat = ref('')
const products = ref<Product[]>([])
const liveSource = ref(false)
const dealEnds = ref('')

function labelFor(id: string) {
  return catLabel(id)
}

async function load(cat?: string) {
  activeCat.value = cat && cat !== 'All' ? cat : ''
  const rows = await listByCategory(activeCat.value || 'All')
  products.value = rows
  liveSource.value = rows.some((p) => p.live)
}

function pick(c: string) {
  load(c === 'All' ? '' : c)
}

onLoad((q) => {
  load(q?.cat ? decodeURIComponent(q.cat) : '')
})

onMounted(async () => {
  if (!products.value.length) load('')
  try {
    dealEnds.value = (await fetchDealEnds()) || ''
  } catch { /* ignore */ }
})

onShow(() => {
  uni.setNavigationBarTitle({ title: t('browse_title') })
})
</script>

<style lang="scss" scoped>
@import '@/styles/theme.scss';

.page {
  min-height: 100vh;
  background: $hb-paper;
  padding: 16px;
  padding-top: calc(16px + env(safe-area-inset-top));
}
.head {
  margin-bottom: 14px;
}
.title {
  display: block;
  font-size: 28px;
  font-weight: 720;
  letter-spacing: -0.7px;
}
.sub {
  display: block;
  font-size: 13px;
  color: $hb-muted;
  margin-top: 4px;
}
.chips {
  white-space: nowrap;
  margin: 0 -4px 12px;
  padding: 2px 4px 4px;
}
.chip {
  display: inline-block;
  padding: 8px 14px;
  border-radius: $hb-radius-pill;
  background: $hb-white;
  font-size: 13px;
  font-weight: 560;
  margin-right: 8px;
  color: $hb-ink;
  box-shadow: $hb-shadow-soft;
  &.on {
    background: $hb-forest;
    color: $hb-white;
    font-weight: 680;
    box-shadow: none;
  }
}
.deal-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin: 0 0 14px;
  padding: 10px 12px;
  border-radius: 16px;
  background: $hb-white;
  box-shadow: $hb-shadow-soft;
}
.deal-copy { min-width: 0; flex: 1; }
.deal-kicker {
  display: block;
  font-size: 13px;
  font-weight: 720;
  color: $hb-ink;
}
.deal-hint {
  display: block;
  margin-top: 2px;
  font-size: 11px;
  color: $hb-muted;
}
.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  padding-bottom: 88px;
}
.page { background: #F7F8FB; padding: 12px 16px 0; padding-top: calc(10px + env(safe-area-inset-top)); }
.top { display: flex; justify-content: space-between; align-items: flex-start; }
.word { display: block; font-size: 22px; font-weight: 800; letter-spacing: -0.4px; color: #1B2B4A; }
.coral { color: #FF6B4A; }
.kicker { display: block; margin-top: 2px; font-size: 9px; letter-spacing: 0.6px; color: #98A2B3; font-weight: 700; }
.tools { display: flex; gap: 8px; }
.tool { width: 36px; height: 36px; border-radius: 99px; background: #fff; display: flex; align-items: center; justify-content: center; position: relative; }
.mag, .bag { width: 16px; height: 16px; border: 1.8px solid #1B2B4A; border-radius: 99px; }
.mag.sm { width: 14px; height: 14px; border-color: #98A2B3; flex: none; }
.bag { border-radius: 3px 3px 5px 5px; height: 12px; margin-top: 4px; }
.badge {
  position: absolute; top: -2px; right: -2px; min-width: 16px; height: 16px; padding: 0 4px;
  border-radius: 99px; background: #FF6B4A; color: #fff; font-size: 10px; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
}
.search {
  margin-top: 12px; height: 40px; border-radius: 20px; background: #fff;
  border: 1px solid #EEF1F6; display: flex; align-items: center; gap: 8px;
  padding: 0 14px; color: #98A2B3; font-size: 13px;
}
.chips { margin: 12px -16px 8px; padding: 0 16px; }
.chip {
  background: #F1F3F7; box-shadow: none; color: #5C677A; font-weight: 600;
  &.on { background: #FF6B4A; color: #fff; }
}
.sec { margin: 8px 0 12px; }
.title { font-size: 20px; font-weight: 800; letter-spacing: -0.3px; color: #1B2B4A; }
.sub { font-size: 13px; color: #98A2B3; }
.grid { gap: 12px; }
.dept-card {
  display: flex; height: 80px; background: #fff; border: 1px solid #E2E6EE;
  border-radius: 16px; overflow: hidden; margin-bottom: 10px;
}
.dept-swatch { width: 90px; height: 80px; }
h2, .title { color: #1B2B4A; font-weight: 800; }
</style>
