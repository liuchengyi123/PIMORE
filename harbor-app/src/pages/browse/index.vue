<template>
  <view class="page">
    <view class="head">
      <text class="title">{{ t('browse_title') }}</text>
      <text class="sub">{{ labelFor(activeCat) || t('browse_all_categories') }}{{ liveSource ? t('browse_live_suffix') : '' }}</text>
    </view>
    <scroll-view scroll-x class="chips" :show-scrollbar="false">
      <view
        v-for="c in chipList"
        :key="c"
        class="chip"
        :class="{ on: activeCat === c || (!activeCat && c === 'All') }"
        @click="pick(c)"
      >
        {{ labelFor(c) }}
      </view>
    </scroll-view>

    <view class="deal-bar">
      <view class="deal-copy">
        <text class="deal-kicker">{{ t('home_sale') }}</text>
        <text class="deal-hint">{{ t('deal_clock_hint') }}</text>
      </view>
      <HbDealClock :label="t('deal_ends_in')" :ends-at="dealEnds" compact />
    </view>

    <view class="grid">
      <HbProductCard v-for="p in products" :key="p.id" :product="p" />
    </view>
    <HbTabBar active="browse" />
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { onLoad, onShow } from '@dcloudio/uni-app'
import { ALL_CATEGORIES, listByCategory, fetchDealEnds, type Product } from '@/api/products'
import HbProductCard from '@/components/HbProductCard.vue'
import HbTabBar from '@/components/HbTabBar.vue'
import HbDealClock from '@/components/HbDealClock.vue'
import { useI18n } from '@/composables/i18n'

const { t, catLabel } = useI18n()

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
.page { background: #F7F4EF; padding-top: env(safe-area-inset-top); }
.dept-card {
  display: flex; height: 80px; background: #fff; border: 1px solid #E2E6EE;
  border-radius: 16px; overflow: hidden; margin-bottom: 10px;
}
.dept-swatch { width: 90px; height: 80px; }
h2, .title { color: #0F2744; font-weight: 800; }
</style>
