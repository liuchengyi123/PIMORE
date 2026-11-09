<template>
  <div class="page" data-figma="1:14">
    <h1>{{ zh ? '搜索' : 'Search' }}</h1>
    <p class="sub">{{ zh ? '找可爱的家居好物和日常必需，还有更多，低至 $1–$10。' : 'Find cute home goods, everyday essentials and more — all $1 to $10.' }}</p>
    <form class="search-row" @submit.prevent="onSearch">
      <label class="field">
        <Search :size="18" :stroke-width="1.8" />
        <input v-model="q" type="search" enterkeyhint="search" :placeholder="zh ? '搜索家居好物' : 'Search home finds'" />
      </label>
      <button type="button" class="cancel" @click="cancel">{{ zh ? '取消' : 'Cancel' }}</button>
    </form>

    <template v-if="!searched">
      <section v-if="shownRecent.length" class="block">
        <div class="sec">
          <h2>{{ zh ? '最近搜索' : 'Recent searches' }}</h2>
          <button type="button" class="link" @click="clearRecent">{{ zh ? '清空' : 'Clear all' }}</button>
        </div>
        <div class="chips">
          <button v-for="h in shownRecent" :key="h" type="button" class="chip" @click="quick(h)">
            <Clock :size="14" /> {{ h }}
          </button>
        </div>
      </section>

      <section class="block">
        <h2 class="trend-title"><Flame :size="16" /> {{ zh ? '正在热搜' : 'Trending now' }}</h2>
        <div class="trends">
          <button v-for="h in trending" :key="h" type="button" class="trend" @click="quick(h)">
            <Flame :size="14" /> {{ h }}
          </button>
        </div>
      </section>

      <section class="block">
        <div class="sec">
          <h2>{{ zh ? '为你推荐' : 'Suggested for you' }}</h2>
          <router-link class="link" to="/browse">{{ zh ? '查看全部' : 'See all' }}</router-link>
        </div>
        <div class="grid">
          <article v-for="p in picks" :key="p.sku" class="card" @click="go(p)">
            <div class="shot"><img v-if="p.image" :src="p.image" :alt="p.name" /></div>
            <div class="meta">
              <div class="nm">{{ p.name }}</div>
              <div class="pr">
                <b>{{ money(p.price) }}</b>
                <button type="button" class="bag" :aria-label="zh ? '加入购物车' : 'Add'" @click.stop="add(p)">
                  <ShoppingCart :size="14" />
                </button>
              </div>
            </div>
          </article>
        </div>
      </section>

      <div class="foot">
        <span class="mark" aria-hidden="true"><Home :size="18" /></span>
        <b>{{ zh ? '好物，从一次搜索开始' : 'Good things are just a search away' }}</b>
        <p>{{ zh ? '试试关键词、分类，或上面的热搜。' : 'Try a keyword, a category, or one of the trending finds above.' }}</p>
      </div>
    </template>

    <div v-else-if="loading" class="state">{{ t('search_searching') }}</div>
    <div v-else-if="!products.length" class="empty-block">
      <h2>{{ t('search_no_results') }} “{{ q }}”</h2>
      <p>{{ zh ? '试试厨房、收纳或清洁' : 'Try kitchen, storage, or cleaning' }}</p>
      <div class="chips center">
        <button v-for="h in trending.slice(0, 4)" :key="'e'+h" type="button" class="chip" @click="quick(h)">{{ h }}</button>
      </div>
    </div>
    <template v-else>
      <div class="sorts">
        <button v-for="s in sorts" :key="s.id" type="button" :class="{ on: sort === s.id }" @click="sort = s.id">{{ s.label }}</button>
      </div>
      <div class="grid">
        <article v-for="p in shown" :key="p.sku" class="card" @click="go(p)">
          <div class="shot"><img v-if="p.image" :src="p.image" :alt="p.name" /></div>
          <div class="meta">
            <div class="nm">{{ p.name }}</div>
            <div class="pr">
              <b>{{ money(p.price) }}</b>
              <button type="button" class="bag" :aria-label="zh ? '加入购物车' : 'Add'" @click.stop="add(p)">
                <ShoppingCart :size="14" />
              </button>
            </div>
          </div>
        </article>
      </div>
      <button v-if="hasMore" type="button" class="more" @click="loadMore">{{ t('search_load_more') }}</button>
    </template>
    <AppTabBar active="home" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Clock, Flame, Home, Search, ShoppingCart } from 'lucide-vue-next'
import { listProducts, money, searchProducts, type Product } from '@/api/products'
import { useCart } from '@/composables/cart'
import { useI18n } from '@/composables/i18n'
import { shelfFallback } from '@/catalog/shelf'
import AppTabBar from '@/components/AppTabBar.vue'

const RECENT_KEY = 'harbor_web_recent_search'
const { t, lang } = useI18n()
const zh = computed(() => String(lang.value).startsWith('zh'))
const route = useRoute()
const router = useRouter()
const cart = useCart()

const q = ref('')
const products = ref<Product[]>([])
const picks = ref<Product[]>([])
const loading = ref(false)
const searched = ref(false)
const page = ref(1)
const hasMore = ref(false)
const sort = ref<'best' | 'up' | 'down' | 'new'>('best')
const recent = ref<string[]>(loadRecent())
const cleared = ref(false)

const defaults = computed(() => zh.value
  ? ['收纳盒', '花盆', '浴巾', '厨房收纳', '台灯']
  : ['storage bins', 'plant pots', 'bath towels', 'kitchen organizers', 'desk lamp'])
const trending = computed(() => zh.value
  ? ['墙面置物', '收纳篮', '柔软毯子', '厨房小物', '花盆', '浴室收纳', '小夜灯', '抱枕']
  : ['wall shelves', 'storage baskets', 'cozy blankets', 'kitchen gadgets', 'plant pots', 'bathroom organizers', 'LED lights', 'throw pillows'])
const sorts = computed(() => zh.value
  ? [
      { id: 'best' as const, label: '综合' },
      { id: 'up' as const, label: '价格↑' },
      { id: 'down' as const, label: '价格↓' },
      { id: 'new' as const, label: '最新' },
    ]
  : [
      { id: 'best' as const, label: 'Best' },
      { id: 'up' as const, label: 'Price ↑' },
      { id: 'down' as const, label: 'Price ↓' },
      { id: 'new' as const, label: 'Newest' },
    ])
const shownRecent = computed(() => {
  if (recent.value.length) return recent.value.slice(0, 6)
  if (cleared.value) return []
  return defaults.value
})
const shown = computed(() => {
  const list = [...products.value]
  if (sort.value === 'up') list.sort((a, b) => a.price - b.price)
  else if (sort.value === 'down') list.sort((a, b) => b.price - a.price)
  else if (sort.value === 'new') list.sort((a, b) => (a.tag === 'New' ? -1 : 1) - (b.tag === 'New' ? -1 : 1))
  return list
})

function loadRecent() {
  try {
    const raw = JSON.parse(localStorage.getItem(RECENT_KEY) || '[]')
    return Array.isArray(raw) ? raw.map(String).filter(Boolean) : []
  } catch {
    return []
  }
}
function remember(text: string) {
  const list = [text, ...recent.value.filter((x) => x !== text)].slice(0, 8)
  recent.value = list
  cleared.value = false
  try { localStorage.setItem(RECENT_KEY, JSON.stringify(list)) } catch { /* */ }
}
function clearRecent() {
  recent.value = []
  cleared.value = true
  try { localStorage.removeItem(RECENT_KEY) } catch { /* */ }
}

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
  remember(text)
  try {
    const res = await searchProducts(text, 1)
    products.value = res.items || []
    hasMore.value = !!res.hasMore
    if (!products.value.length) {
      const local = shelfFallback([], 8).filter((p) => p.name.includes(text) || p.category.includes(text) || p.sku.includes(text))
      if (local.length) products.value = local
    }
    if (route.query.q !== text) router.replace({ path: '/search', query: { q: text } })
  } catch {
    products.value = []
    hasMore.value = false
  } finally {
    loading.value = false
  }
}
function onSearch() { runSearch(q.value) }
function quick(h: string) { runSearch(h) }
function cancel() {
  if (q.value || searched.value) {
    q.value = ''
    searched.value = false
    products.value = []
    if (route.query.q) router.replace({ path: '/search' })
    return
  }
  router.back()
}
async function loadMore() {
  page.value += 1
  const res = await searchProducts(q.value.trim(), page.value)
  products.value = products.value.concat(res.items || [])
  hasMore.value = !!res.hasMore
}
function go(p: Product) {
  router.push({ path: '/pdp', query: { sku: p.sku } })
}
function add(p: Product) { cart.add(p) }

watch(() => route.query.q, (v) => {
  const next = v ? String(v) : ''
  if (next && next !== q.value) runSearch(next)
})
onMounted(async () => {
  try {
    picks.value = shelfFallback(await listProducts(), 4).slice(0, 4)
  } catch {
    picks.value = shelfFallback([], 4)
  }
  const initial = route.query.q ? String(route.query.q) : ''
  if (initial) runSearch(initial)
})
</script>

<style lang="scss" scoped>
.page {
  min-height: 100vh; background: #FCFAF8; color: #1C2430;
  padding: calc(12px + env(safe-area-inset-top)) 16px 8px;
  font-family: "Plus Jakarta Sans", "PingFang SC", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
h1 { margin: 0; font-size: 30px; font-weight: 800; letter-spacing: -0.04em; color: #F96141; line-height: 1; }
.sub { margin: 6px 0 0; max-width: 260px; color: #8B919A; font-size: 13px; line-height: 1.35; }
.search-row { display: flex; align-items: center; gap: 8px; margin-top: 12px; }
.field {
  flex: 1; display: flex; align-items: center; gap: 8px; height: 42px; padding: 0 14px;
  background: #fff; border: 1px solid #EFEAE4; border-radius: 999px; color: #8B919A;
}
.field input { flex: 1; border: 0; outline: none; background: transparent; color: #1C2430; font-size: 14px; min-width: 0; }
.cancel { border: 0; background: transparent; color: #F96141; font-weight: 700; font-size: 15px; cursor: pointer; padding: 0; }
.block { margin-top: 14px; }
.sec { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; }
h2 { margin: 0; font-size: 15px; font-weight: 800; letter-spacing: -0.02em; }
.trend-title { display: flex; align-items: center; gap: 4px; color: #1C2430; }
.trend-title :deep(svg), .trend :deep(svg) { color: #F96141; }
.link { border: 0; background: transparent; color: #F96141; font-weight: 700; font-size: 13px; cursor: pointer; padding: 0; }
.chips { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
.chips.center { justify-content: center; }
.chip {
  display: inline-flex; align-items: center; gap: 4px; height: 30px; padding: 0 10px;
  border: 0; border-radius: 999px; background: #F3F1EF; color: #1C2430; font-size: 13px; font-weight: 650; cursor: pointer;
}
.chip :deep(svg) { color: #8B919A; }
.trends { display: grid; grid-template-columns: 1fr 1fr; gap: 4px 8px; margin-top: 6px; }
.trend {
  display: flex; align-items: center; gap: 5px; border: 0; background: transparent;
  text-align: left; font-size: 13px; font-weight: 650; color: #1C2430; cursor: pointer; padding: 3px 0; line-height: 1.2;
}
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 8px; }
.card { background: #fff; border-radius: 14px; overflow: hidden; border: 1px solid #F3F0EC; cursor: pointer; }
.shot { aspect-ratio: 1.18; background: #F6F4F2; }
.shot img { width: 100%; height: 100%; object-fit: cover; display: block; }
.meta { padding: 6px 8px 8px; }
.nm {
  font-size: 13px; font-weight: 700; line-height: 1.3; min-height: 2.6em;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.pr { display: flex; align-items: center; margin-top: 2px; }
.pr b { color: #F96141; font-size: 15px; letter-spacing: -0.02em; }
.bag {
  margin-left: auto; width: 28px; height: 28px; border: 0; border-radius: 999px;
  background: #F96141; color: #fff; display: inline-flex; align-items: center; justify-content: center; cursor: pointer;
}
.foot { margin: 14px 0 4px; text-align: center; color: #8B919A; }
.mark {
  width: 36px; height: 36px; margin: 0 auto 8px; border-radius: 12px; background: #FFF1EC; color: #F96141;
  display: grid; place-items: center;
}
.foot b { display: block; color: #1C2430; font-size: 14px; }
.foot p { margin: 6px auto 0; max-width: 240px; font-size: 12px; line-height: 1.45; }
.state, .empty-block { text-align: center; color: #8B919A; padding: 36px 8px; }
.empty-block h2 { font-size: 18px; }
.sorts { display: flex; gap: 8px; margin-top: 16px; overflow-x: auto; }
.sorts button {
  border: 0; background: #F3F1EF; color: #1C2430; height: 32px; padding: 0 12px; border-radius: 999px;
  font-size: 13px; font-weight: 700; cursor: pointer; white-space: nowrap;
}
.sorts button.on { background: #F96141; color: #fff; }
.more {
  display: block; margin: 16px auto 0; border: 0; background: #fff; color: #F96141;
  height: 40px; padding: 0 18px; border-radius: 999px; font-weight: 700; cursor: pointer;
}
</style>
