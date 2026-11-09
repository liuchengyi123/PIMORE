<template>
  <div class="fn-page page" data-figma="M25">
    <div class="top sticky">
      <button type="button" class="back" @click="$router.back()" aria-label="back">
        <ChevronLeft :size="22" :stroke-width="1.75" />
      </button>
      <AppSearchBar
        v-model="q"
        show-button
        inplace
        autofocus
        class="grow"
        :placeholder="ph"
        @search="onSearch"
      />
    </div>
    <h1 v-if="!searched" class="search-title">{{ zh ? '搜索' : 'Search' }}</h1>
    <p v-if="!searched" class="search-sub">{{ zh ? '找家居好物和日常小物。' : 'Find cute home goods, everyday essentials and more.' }}</p>
    <div v-if="!q && !loading && !searched" class="hints">
      <div class="hint-title">{{ zh ? '最近搜索' : 'Recent searches' }}</div>
      <div class="hint-row">
        <button v-for="h in hints" :key="h" type="button" class="hint" @click="quick(h)">{{ h }}</button>
      </div>
    </div>
    <div v-if="loading" class="state">{{ t('search_searching') }}</div>
    <div v-else-if="searched && !products.length" class="empty-block">
      <h2>{{ t('search_no_results') }} “{{ q }}”</h2>
      <p class="hint-sub">{{ zh ? '试试厨房、收纳或清洁' : 'Try kitchen, storage, or cleaning' }}</p>
      <div class="hint-row" style="justify-content:center;margin-top:16px">
        <button v-for="h in hints" :key="'e'+h" type="button" class="hint" @click="quick(h)">{{ h }}</button>
      </div>
      <router-link class="go-home" to="/home">{{ t('tab_home') || 'Back to Home' }}</router-link>
    </div>
    <div v-else>
      <div class="sort-chips" v-if="products.length">
        <button type="button" class="hint on">{{ zh ? '综合' : 'Best' }}</button>
        <button type="button" class="hint">{{ zh ? '价格↑' : 'Price ↑' }}</button>
        <button type="button" class="hint">{{ zh ? '价格↓' : 'Price ↓' }}</button>
        <button type="button" class="hint">{{ zh ? '最新' : 'Newest' }}</button>
      </div>
      <div class="grid">
        <ProductCard v-for="p in products" :key="p.sku" :product="p" />
      </div>
    </div>
    <button v-if="products.length && hasMore" type="button" class="more" @click="loadMore">{{ t('search_load_more') }}</button>
    <AppTabBar active="home" />
  </div>
</template>
<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ChevronLeft } from 'lucide-vue-next'
import { searchProducts, type Product } from '@/api/products'
import { useI18n } from '@/composables/i18n'
import ProductCard from '@/components/ProductCard.vue'
import AppSearchBar from '@/components/AppSearchBar.vue'
import AppTabBar from '@/components/AppTabBar.vue'

const { t, lang } = useI18n()
const zh = computed(() => String(lang.value).startsWith('zh'))
const route = useRoute()
const router = useRouter()
const q = ref('')
const products = ref<Product[]>([])
const loading = ref(false)
const searched = ref(false)
const page = ref(1)
const hasMore = ref(false)
const hints = computed(() => zh.value
  ? ['收纳盒', '花盆', '浴巾', '厨房收纳', '台灯']
  : ['storage bins', 'plant pots', 'bath towels', 'kitchen organizers', 'desk lamp'])
const ph = computed(() =>
  lang.value === 'en' ? 'Search household goods' : t('search_placeholder')
)

async function runSearch(query = q.value) {
  const text = String(query || '').trim()
  q.value = text
  if (!text) {
    products.value = []
    searched.value = false
    hasMore.value = false
    return
  }
  loading.value = true
  searched.value = true
  page.value = 1
  try {
    const res = await searchProducts(text, 1)
    products.value = res.items || []
    hasMore.value = !!res.hasMore
    if (route.query.q !== text) {
      router.replace({ path: '/search', query: { q: text } })
    }
  } catch {
    products.value = []
    hasMore.value = false
  } finally {
    loading.value = false
  }
}
function onSearch(query: string) {
  runSearch(query)
}
async function loadMore() {
  page.value += 1
  const res = await searchProducts(q.value.trim(), page.value)
  products.value = products.value.concat(res.items || [])
  hasMore.value = !!res.hasMore
}
function quick(h: string) {
  runSearch(h)
}
watch(() => route.query.q, (v) => {
  const next = v ? String(v) : ''
  if (next && next !== q.value) runSearch(next)
})
onMounted(() => {
  const initial = route.query.q ? String(route.query.q) : ''
  if (initial) runSearch(initial)
})
</script>
<style lang="scss" scoped>
@import '@/styles/theme.scss';
.page { min-height: 100vh; background: $hb-paper; padding: 0 16px 40px; }
.search-title { margin: 12px 0 0; font-size: 28px; font-weight: 800; letter-spacing: -0.03em; color: #F96141; }
.search-sub { margin: 4px 0 12px; color: #8B919A; font-size: 14px; }
.sticky {
  position: sticky; top: 0; z-index: 20;
  background: rgba(247,244,239,0.94); backdrop-filter: blur(14px);
  padding: calc(10px + env(safe-area-inset-top)) 0 12px;
  display: flex; align-items: center; gap: 8px;
}
.back {
  width: 40px; height: 40px; border: 0; border-radius: 14px; background: $hb-white; color: $hb-ink;
  display: inline-flex; align-items: center; justify-content: center; box-shadow: $hb-shadow-soft; cursor: pointer;
}
.grow { flex: 1; min-width: 0; }
.hints { padding: 8px 0 16px; }
.hint-title { font-size: 12px; color: $hb-muted; font-weight: 650; margin-bottom: 10px; }
.hint-row { display: flex; flex-wrap: wrap; gap: 8px; }
.hint { border: 0; background: $hb-white; height: 34px; padding: 0 14px; border-radius: 999px; font-size: 13px; font-weight: 650; box-shadow: $hb-shadow-soft; cursor: pointer; }
.state { text-align: center; color: $hb-muted; padding: 48px 12px; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.empty-block { text-align: center; padding: 48px 12px; }
.empty-block h2 { margin: 0; font-size: 18px; font-weight: 800; color: $hb-ink; }
.hint-sub { margin-top: 8px; color: $hb-muted; font-size: 13px; }
.go-home {
  display: inline-flex; margin-top: 20px; padding: 10px 16px; border-radius: 999px;
  background: #F96141; color: #fff; font-weight: 700; text-decoration: none;
}
.sort-chips { display: flex; gap: 8px; flex-wrap: wrap; margin: 4px 0 12px; }
.hint.on { background: #F96141; color: #fff; }
.more { display: block; margin: 18px auto 0; width: 140px; border: 0; padding: 12px; border-radius: 999px; background: $hb-white; color: $hb-forest; font-weight: 700; box-shadow: $hb-shadow-soft; cursor: pointer; }

</style>
