<template>
  <view class="page" data-figma="1:13" :data-live="live ? '1' : '0'">
    <view class="nav">
      <view class="back" @click="goBack">‹</view>
      <text class="title">{{ subLabel || title }}</text>
      <view class="nav-tools">
        <view class="tool" @click="cycleFilter"><view class="funnel" /></view>
        <view class="tool" @click="toggleSort"><view class="sort" :class="sort" /></view>
      </view>
    </view>
    <scroll-view scroll-x class="chips" :show-scrollbar="false">
      <view class="chip" :class="{ on: filter === 'all' && !sub }" @click="setFilter('all')">All</view>
      <view class="chip" :class="{ on: filter === 'under' }" @click="setFilter('under')">Under $5</view>
      <view class="chip" :class="{ on: filter === 'best' }" @click="setFilter('best')">Best Sellers</view>
      <view class="chip" :class="{ on: filter === 'new' }" @click="setFilter('new')">New</view>
      <view
        v-for="s in subs"
        :key="s.id"
        class="chip"
        :class="{ on: sub === s.id }"
        @click="pickSub(s.id)"
      >{{ subcatLabel(s.id) }}</view>
    </scroll-view>
    <view v-if="loading" class="state">{{ t('nav_loading') }}</view>
    <view v-else-if="!shown.length" class="state">{{ t('nav_empty_aisle') }}</view>
    <view v-else class="grid">
      <HbProductCard v-for="p in shown" :key="p.id" :product="p" variant="plp" />
    </view>
    <view v-if="products.length && hasMore" class="more" @click="loadMore">{{ t('nav_load_more') }}</view>
    <HbTabBar active="browse" />
  </view>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { handleLuckyBack } from '@/composables/lucky'
import { onLoad, onShow } from '@dcloudio/uni-app'
import {
  SUBCATEGORIES,
  listCategoryPage,
  type Product,
} from '@/api/products'
import HbProductCard from '@/components/HbProductCard.vue'
import HbTabBar from '@/components/HbTabBar.vue'
import { useI18n } from '@/composables/i18n'

const { t, catLabel, subcatLabel } = useI18n()
const cat = ref('')
const sub = ref('')
const products = ref<Product[]>([])
const loading = ref(false)
const live = ref(false)
const page = ref(1)
const hasMore = ref(false)

const filter = ref<'all' | 'under' | 'best' | 'new'>('all')
const sort = ref<'none' | 'asc' | 'desc'>('none')
const title = computed(() => catLabel(cat.value) || t('nav_category'))
const shown = computed(() => {
  let rows = products.value.slice()
  if (filter.value === 'under') rows = rows.filter((p) => p.price <= 5)
  if (filter.value === 'best') rows = rows.filter((p) => p.tag === 'Deal' || p.tag === 'Flash' || p.tag === 'Staff')
  if (filter.value === 'new') rows = rows.filter((p) => p.tag === 'New')
  if (sort.value === 'asc') rows.sort((a, b) => a.price - b.price)
  if (sort.value === 'desc') rows.sort((a, b) => b.price - a.price)
  return rows
})
function setFilter(id: 'all' | 'under' | 'best' | 'new') {
  filter.value = id
  if (id === 'all') pickSub('')
}
function cycleFilter() {
  const order = ['all', 'under', 'best', 'new'] as const
  const i = order.indexOf(filter.value)
  setFilter(order[(i + 1) % order.length])
}
function toggleSort() {
  sort.value = sort.value === 'none' ? 'asc' : sort.value === 'asc' ? 'desc' : 'none'
}
const subs = computed(() => SUBCATEGORIES[cat.value] || [])
const subLabel = computed(() => (sub.value ? subcatLabel(sub.value) : ''))

async function load(reset = true) {
  if (!cat.value) return
  loading.value = true
  if (reset) page.value = 1
  try {
    const res = await listCategoryPage(cat.value, sub.value, page.value)
    products.value = reset ? res.items : products.value.concat(res.items)
    hasMore.value = res.hasMore
    live.value = res.live || res.items.some((p) => p.live)
  } finally {
    loading.value = false
  }
}

function pickSub(id: string) {
  sub.value = id
  load(true)
}

async function loadMore() {
  page.value += 1
  await load(false)
}

function goBack() {
  if (handleLuckyBack()) return
  uni.navigateBack({ fail: () => uni.navigateTo({ url: '/pages/categories/index' }) })
}

function syncNavTitle() {
  uni.setNavigationBarTitle({ title: title.value })
}

watch(title, () => syncNavTitle())

onLoad((q) => {
  cat.value = q?.cat ? decodeURIComponent(q.cat) : ''
  sub.value = q?.sub ? decodeURIComponent(q.sub) : ''
  load(true)
  syncNavTitle()
})

onShow(() => syncNavTitle())
</script>

<style lang="scss" scoped>
@import '@/styles/theme.scss';
.page {
  min-height: 100vh; background: #F7F8FB; padding: 8px 16px 24px;
  padding-top: calc(8px + env(safe-area-inset-top));
}
.nav { display: grid; grid-template-columns: 36px 1fr auto; align-items: center; margin-bottom: 12px; }
.back { font-size: 28px; line-height: 36px; color: #1B2B4A; }
.title { text-align: center; font-size: 18px; font-weight: 800; color: #1B2B4A; }
.nav-tools { display: flex; gap: 8px; }
.tool { width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; }
.funnel {
  width: 14px; height: 14px; border: 1.6px solid #1B2B4A; border-radius: 2px 2px 7px 7px;
}
.sort { width: 14px; height: 14px; border-top: 2px solid #1B2B4A; border-bottom: 2px solid #1B2B4A; }
.chips { white-space: nowrap; margin-bottom: 14px; }
.chip {
  display: inline-block; padding: 8px 14px; margin-right: 8px; border-radius: 999px;
  background: #fff; font-size: 13px; font-weight: 600; color: #1B2B4A;
}
.chip.on { background: #FF6B4A; color: #fff; }
.state { text-align: center; color: #8B95A7; padding: 40px 8px; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; padding-bottom: 88px; }
.more {
  margin: 8px auto 88px; width: 140px; text-align: center; padding: 12px; border-radius: 999px;
  background: #fff; color: #FF6B4A; font-weight: 700;
}
</style>
