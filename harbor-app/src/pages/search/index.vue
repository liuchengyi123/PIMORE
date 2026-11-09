<template>
  <view class="page" data-figma="1:14">
    <view class="head">
      <text class="title">Search</text>
      <text class="lead">Find cute home goods, everyday essentials and more — all $1 to $10.</text>
    </view>
    <view class="search-box">
      <view class="mag" />
      <input
        class="input"
        type="text"
        confirm-type="search"
        :value="q"
        :focus="true"
        placeholder="Search home finds"
        @input="onInput"
        @confirm="runSearch"
      />
      <text class="cancel" @click="cancel">Cancel</text>
    </view>

    <template v-if="!searched">
      <view v-if="recent.length" class="block">
        <view class="row-h">
          <text class="h">Recent searches</text>
          <text class="link" @click="clearRecent">Clear all</text>
        </view>
        <view class="pills">
          <view v-for="h in recent" :key="'r'+h" class="pill" @click="quick(h)">{{ h }}</view>
        </view>
      </view>
      <view class="block">
        <text class="h hot-h">Trending now</text>
        <view class="trend">
          <view v-for="h in trending" :key="h" class="pill hot" @click="quick(h)">{{ h }}</view>
        </view>
      </view>
      <view class="row-h">
        <text class="h">Suggested for you</text>
        <text class="link" @click="goSale">See all ›</text>
      </view>
      <view class="grid">
        <HbProductCard v-for="p in suggested" :key="p.id" :product="p" plain />
      </view>
      <view class="empty-note">
        <view class="house" />
        <text class="empty-title">Good things are just a search away</text>
        <text class="empty-sub">Try a keyword, a category, or one of the trending finds above to see what's in store.</text>
      </view>
    </template>

    <view v-else-if="loading" class="state">{{ t('search_searching') }}</view>
    <view v-else-if="!products.length" class="state">{{ t('search_no_results', { q }) }}</view>
    <view v-else class="grid">
      <HbProductCard v-for="p in products" :key="p.id" :product="p" plain />
    </view>
    <view v-if="products.length && hasMore" class="more" @click="loadMore">{{ t('search_load_more') }}</view>
    <HbTabBar active="home" />
  </view>
</template>

<script setup lang="ts">
import { useI18n } from '@/composables/i18n'
import { ref } from 'vue'
import { onLoad, onShow } from '@dcloudio/uni-app'
import { listProducts, searchProducts, type Product } from '@/api/products'
import { handleLuckyBack } from '@/composables/lucky'
import HbProductCard from '@/components/HbProductCard.vue'
import HbTabBar from '@/components/HbTabBar.vue'

const RECENT_KEY = 'hb-recent-searches'
const { t } = useI18n()
const q = ref('')
const products = ref<Product[]>([])
const suggested = ref<Product[]>([])
const loading = ref(false)
const searched = ref(false)
const page = ref(1)
const hasMore = ref(false)
const recent = ref<string[]>([])
const trending = [
  'wall shelves',
  'plant pots',
  'storage baskets',
  'bathroom organizers',
  'cozy blankets',
  'LED lights',
  'kitchen gadgets',
  'throw pillows',
]
const hints = ['kitchen', 'storage', 'cleaning', 'pet', 'desk', 'towel']

function onInput(e: any) {
  q.value = e?.detail?.value ?? ''
}

function readRecent() {
  try {
    const raw = uni.getStorageSync(RECENT_KEY)
    recent.value = raw ? JSON.parse(raw) : []
  } catch {
    recent.value = []
  }
}

function remember(query: string) {
  const next = [query, ...recent.value.filter((item) => item !== query)].slice(0, 8)
  recent.value = next
  uni.setStorageSync(RECENT_KEY, JSON.stringify(next))
}

function clearRecent() {
  recent.value = []
  uni.removeStorageSync(RECENT_KEY)
}

async function runSearch() {
  const query = q.value.trim()
  if (!query) return
  loading.value = true
  searched.value = true
  page.value = 1
  try {
    const res = await searchProducts(query, 1)
    products.value = res.items
    hasMore.value = res.hasMore
    remember(query)
  } finally {
    loading.value = false
  }
}

async function loadMore() {
  const next = page.value + 1
  const res = await searchProducts(q.value.trim(), next)
  products.value = products.value.concat(res.items)
  page.value = next
  hasMore.value = res.hasMore && res.items.length > 0
}

function quick(h: string) {
  q.value = h
  runSearch()
}

function cancel() {
  if (q.value || searched.value) {
    q.value = ''
    products.value = []
    searched.value = false
    return
  }
  goBack()
}

function goSale() {
  uni.navigateTo({ url: '/pages/sale/index' })
}

function goBack() {
  if (handleLuckyBack()) return
  uni.navigateBack({ fail: () => uni.reLaunch({ url: '/pages/home/index' }) })
}

onLoad(async (query) => {
  readRecent()
  try { suggested.value = (await listProducts()).slice(0, 4) } catch { suggested.value = [] }
  if (query?.q) {
    q.value = decodeURIComponent(query.q)
    runSearch()
  }
})

onShow(() => {
  uni.setNavigationBarTitle({ title: t('search_action') })
})

void hints
</script>

<style lang="scss" scoped>
@import '@/styles/theme.scss';
.page {
  min-height: 100vh; background: #F7F8FB; padding: 12px 16px 24px;
  padding-top: calc(12px + env(safe-area-inset-top));
  padding-bottom: calc(88px + env(safe-area-inset-bottom));
}
.head { margin-bottom: 12px; }
.title { display: block; font-size: 32px; font-weight: 800; color: #FF6B4A; letter-spacing: -0.6px; }
.lead { display: block; margin-top: 4px; font-size: 13px; color: #8B95A7; line-height: 1.4; }
.search-box {
  height: 44px; border-radius: 22px; background: #fff; border: 1px solid #EEF1F6;
  display: flex; align-items: center; gap: 8px; padding: 0 12px 0 14px;
}
.mag { width: 14px; height: 14px; border: 1.8px solid #98A2B3; border-radius: 99px; flex: none; }
.input { flex: 1; font-size: 14px; color: #1B2B4A; }
.cancel { color: #8B95A7; font-size: 14px; padding-left: 8px; }
.block { margin-top: 18px; }
.row-h { display: flex; justify-content: space-between; align-items: center; margin: 18px 0 10px; }
.h { font-size: 16px; font-weight: 800; color: #1B2B4A; }
.link { color: #FF6B4A; font-size: 13px; font-weight: 700; }
.pills, .trend { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
.trend { display: grid; grid-template-columns: 1fr 1fr; }
.pill {
  background: #fff; border-radius: 999px; padding: 8px 12px; font-size: 13px; color: #1B2B4A; font-weight: 600;
}
.pill.hot { background: #FFF1EC; color: #1B2B4A; }
.state { text-align: center; color: #8B95A7; padding: 48px 12px; font-size: 14px; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.more { margin: 18px auto 0; text-align: center; color: #FF6B4A; font-weight: 700; }
.empty-note { margin-top: 28px; text-align: center; padding: 8px 24px 12px; }
.house {
  width: 36px; height: 28px; margin: 0 auto 8px; border: 2px solid #FF6B4A; border-radius: 4px 4px 2px 2px;
}
.empty-title { display: block; font-size: 15px; font-weight: 800; color: #1B2B4A; }
.empty-sub { display: block; margin-top: 6px; font-size: 12px; color: #8B95A7; line-height: 1.45; }
</style>
