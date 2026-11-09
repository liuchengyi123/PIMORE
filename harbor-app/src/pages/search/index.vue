<template>
  <view class="page">
    <view class="top">
      <view class="back" @click="goBack">←</view>
      <view class="search-box">
        <input
          class="input"
          type="text"
          confirm-type="search"
          :value="q"
          :focus="true"
          :placeholder="t('search_placeholder')"
          @input="onInput"
          @confirm="runSearch"
        />
        <text class="go" @click="runSearch">{{ t('search_action') }}</text>
      </view>
    </view>

    <view v-if="!q && !loading" class="hints">
      <text class="hint-title">{{ t('search_try') }}</text>
      <view class="hint-row">
        <view v-for="h in hints" :key="h" class="hint" @click="quick(h)">{{ h }}</view>
      </view>
    </view>

    <view v-if="loading" class="state">{{ t('search_searching') }}</view>
    <view v-else-if="searched && !products.length" class="state">{{ t('search_no_results', { q }) }}</view>
    <view v-else class="grid">
      <HbProductCard v-for="p in products" :key="p.id" :product="p" />
    </view>
    <view v-if="products.length && hasMore" class="more" @click="loadMore">{{ t('search_load_more') }}</view>
    <HbLucky />
  </view>
</template>

<script setup lang="ts">
import { useI18n } from '@/composables/i18n'
import { ref } from 'vue'
import { onLoad, onShow } from '@dcloudio/uni-app'
import { searchProducts, type Product } from '@/api/products'
import { handleLuckyBack } from '@/composables/lucky'
import HbProductCard from '@/components/HbProductCard.vue'

const { t } = useI18n()
const q = ref('')
const products = ref<Product[]>([])
const loading = ref(false)
const searched = ref(false)
const page = ref(1)
const hasMore = ref(false)
const hints = ['kitchen', 'storage', 'cleaning', 'pet', 'desk', 'towel']

function onInput(e: any) {
  q.value = e?.detail?.value ?? ''
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

function goBack() {
  if (handleLuckyBack()) return
  uni.navigateBack({ fail: () => uni.reLaunch({ url: '/pages/home/index' }) })
}

onLoad((query) => {
  if (query?.q) {
    q.value = decodeURIComponent(query.q)
    runSearch()
  }
})

onShow(() => {
  uni.setNavigationBarTitle({ title: t('search_action') })
})
</script>

<style lang="scss" scoped>
@import '@/styles/theme.scss';
.page { min-height: 100vh; background: $hb-paper; padding: 12px 16px 40px; padding-top: calc(12px + env(safe-area-inset-top)); }
.top { display: flex; align-items: center; gap: 10px; margin-bottom: 16px; }
.back { width: 36px; height: 36px; border-radius: 12px; background: $hb-white; text-align: center; line-height: 36px; font-size: 18px; box-shadow: $hb-shadow-soft; }
.search-box { flex: 1; height: 46px; border-radius: 14px; background: $hb-white; display: flex; align-items: center; padding: 0 8px 0 14px; box-shadow: $hb-shadow-soft; }
.input { flex: 1; font-size: 14px; color: $hb-ink; }
.go { font-size: 13px; font-weight: 720; color: $hb-forest; padding: 8px 10px; }
.hints { margin-top: 8px; }
.hint-title { display: block; font-size: 12px; color: $hb-muted; font-weight: 650; letter-spacing: 0.8px; text-transform: uppercase; margin-bottom: 10px; }
.hint-row { display: flex; flex-wrap: wrap; gap: 8px; }
.hint { background: $hb-white; padding: 10px 14px; border-radius: 999px; font-size: 13px; font-weight: 600; box-shadow: $hb-shadow-soft; }
.state { text-align: center; color: $hb-muted; padding: 48px 12px; font-size: 14px; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.more { margin: 18px auto 0; width: 140px; text-align: center; padding: 12px; border-radius: 999px; background: $hb-white; color: $hb-forest; font-weight: 700; box-shadow: $hb-shadow-soft; }
</style>
