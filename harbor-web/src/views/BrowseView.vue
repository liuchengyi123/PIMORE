<template>
  <div class="browse" data-figma="1:2">
    <header class="top">
      <div>
        <div class="logo"><span class="ink">Harbor</span> <span class="slash">/</span> <span class="pimo">Pimo</span></div>
        <div class="tag">{{ zh ? '家居好物，照亮每一天' : 'HOME GOODS FOR A BRIGHTER EVERYDAY' }}</div>
      </div>
      <div class="tools">
        <router-link to="/search" aria-label="Search"><Search :size="22" /></router-link>
        <router-link class="bag" to="/cart" aria-label="Cart">
          <ShoppingBag :size="22" />
          <i v-if="count">{{ count > 9 ? '9+' : count }}</i>
        </router-link>
      </div>
    </header>

    <div class="search-wrap">
      <AppSearchBar :placeholder="zh ? '搜索家居、装饰、厨房...' : 'Search home goods, decor, kitchen...'" navigate-on-focus />
    </div>

    <div class="chips">
      <button type="button" class="chip" :class="{ on: !activeCat }" @click="pick('')"><Home :size="14" /> {{ zh ? '全部' : 'All' }}</button>
      <button v-for="c in chips" :key="c.id" type="button" class="chip" :class="{ on: activeCat === c.id }" @click="pick(c.id)">
        <component :is="c.icon" :size="14" /> {{ zh ? c.zh : c.label }}
      </button>
    </div>
    <div class="sorts">
      <button type="button" class="sort" :class="{ on: sort === 'featured' }" @click="sort = 'featured'">{{ zh ? '综合' : 'Featured' }}</button>
      <button type="button" class="sort" :class="{ on: sort === 'low' }" @click="sort = 'low'">{{ zh ? '低价' : 'Low price' }}</button>
      <button type="button" class="sort" :class="{ on: sort === 'high' }" @click="sort = 'high'">{{ zh ? '高价' : 'High price' }}</button>
    </div>

    <h1>{{ zh ? '日常好物' : 'Everyday essentials' }}</h1>
    <p class="sub">{{ zh ? '用心的家居小物，生活更好一点。' : 'Thoughtful home goods. Better living.' }}</p>

    <div v-if="isTree" class="chips" style="flex-wrap:wrap">
      <button v-for="c in departments" :key="c.id" type="button" class="chip" :class="{ on: activeCat === c.id }" @click="pick(c.id)">{{ c.name }}</button>
    </div>
    <div v-if="loading" class="state">{{ t('pdp_loading') }}</div>
    <div v-else-if="!shown.length" class="state">{{ zh ? '这个分类还没有商品' : 'No products in this aisle yet.' }}</div>
    <div v-else class="grid">
      <article v-for="(item, i) in shown" :key="item.sku" class="card">
        <div class="shot" @click="open(item, i)">
          <img :src="item.image" alt="" />
          <span class="sold">{{ zh ? '已售' : 'Sold' }}</span>
          <button type="button" class="heart" aria-label="Save" @click.stop="wish(item)"><Heart :size="16" :stroke-width="1.75" /></button>
        </div>
        <div class="nm" @click="open(item, i)">{{ item.name }}</div>
        <div class="cat">{{ item.cat }}</div>
        <div class="pr">
          <b>{{ priceLabel(item.price) }}</b>
          <button type="button" class="add" @click.stop="add(item)">{{ zh ? '加入' : 'Add' }} +</button>
        </div>
      </article>
    </div>
    <AppTabBar active="browse" variant="wish" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Bath, Bed, Coffee, Heart, Home, Lamp, Search, ShoppingBag } from 'lucide-vue-next'
import { listByCategory, money, type Product } from '@/api/products'
import { useI18n } from '@/composables/i18n'
import { useCart } from '@/composables/cart'
import AppTabBar from '@/components/AppTabBar.vue'
import AppSearchBar from '@/components/AppSearchBar.vue'
import { ALL_CATEGORIES } from '@/api/products'
import { toggleWishlist } from '@/api/cartApi'

const { t, lang } = useI18n()
const zh = computed(() => String(lang.value).startsWith('zh'))
const route = useRoute()
const router = useRouter()
const cart = useCart()
const count = computed(() => cart.count.value)
const live = ref<Product[]>([])
const activeCat = ref('')
const sort = ref<'featured' | 'low' | 'high'>('featured')
const loading = ref(false)

const chips = [
  { id: 'bedding', label: 'Bedding', zh: '床品', icon: Bed },
  { id: 'decor', label: 'Decor', zh: '装饰', icon: Lamp },
  { id: 'kitchen', label: 'Kitchen', zh: '厨房', icon: Coffee },
  { id: 'bath', label: 'Bath', zh: '卫浴', icon: Bath },
]
function priceLabel(n: number) {
  if (!Number.isFinite(n)) return '$0'
  return Number.isInteger(n) ? `$${n}` : money(n)
}

const isTree = computed(() => route.name === 'categories')
const departments = ALL_CATEGORIES

const shown = computed(() => applySort(live.value.map((p) => ({
  sku: p.sku,
  name: p.name,
  cat: p.category || activeCat.value,
  price: p.price,
  image: p.image || '',
  live: p,
}))))

function applySort<T extends { price: number }>(rows: T[]) {
  if (sort.value === 'low') return [...rows].sort((a, b) => a.price - b.price)
  if (sort.value === 'high') return [...rows].sort((a, b) => b.price - a.price)
  return rows
}

async function pick(id: string) {
  activeCat.value = id
  loading.value = true
  try {
    live.value = await listByCategory(id || '')
  } catch {
    live.value = []
  } finally {
    loading.value = false
  }
  if (route.name !== 'categories') {
    router.replace({ path: '/browse', query: id ? { cat: id } : {} })
  }
}

function open(item: { sku: string; live?: Product }, _i: number) {
  const sku = item.live?.sku || item.sku
  if (sku) router.push({ path: '/pdp', query: { sku } })
}

async function add(item: { live?: Product }) {
  if (item.live) await cart.addServer(item.live)
}

async function wish(item: { sku: string }) {
  await toggleWishlist(item.sku)
}

onMounted(() => {
  const cat = route.query.cat ? String(route.query.cat) : ''
  pick(cat)
})
</script>

<style lang="scss" scoped>
.browse {
  min-height: 100vh; background: #fff; color: #1C2430;
  padding: 12px 16px 0; padding-top: calc(12px + env(safe-area-inset-top));
  font-family: "Plus Jakarta Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
.top { display: flex; justify-content: space-between; align-items: center; }
.logo { font-size: 24px; font-weight: 800; letter-spacing: -0.04em; line-height: 1; }
.logo .ink { color: #1C2430; }
.logo .slash { color: #C5C9CE; font-weight: 600; margin: 0 2px; }
.logo .pimo { color: #F96141; }
.tag { margin-top: 4px; font-size: 10px; letter-spacing: 0.04em; color: #9AA0A8; font-weight: 650; }
.tools { display: flex; gap: 16px; align-items: center; color: #1C2430; }
.bag { position: relative; }
.bag i {
  position: absolute; top: -6px; right: -8px; min-width: 16px; height: 16px; border-radius: 99px;
  background: #F96141; color: #fff; font-style: normal; font-size: 10px; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
}
.search-wrap { margin-top: 14px; }
.search-wrap :deep(.search-bar) { border-radius: 999px; background: #F4F1EE; border: 0; box-shadow: none; min-height: 46px; }
.chips, .sorts { display: flex; gap: 6px; overflow-x: auto; margin-top: 8px; padding-bottom: 2px; scrollbar-width: none; }
.chips::-webkit-scrollbar, .sorts::-webkit-scrollbar { display: none; }
.chips { margin-top: 10px; }
.chip, .sort {
  flex: 0 0 auto; display: inline-flex; align-items: center; gap: 4px;
  height: 32px; padding: 0 10px; border-radius: 999px; border: 0; background: #F3F1EE;
  color: #1C2430; font-weight: 700; font-size: 12px; cursor: pointer;
}
.chip.on { background: #F96141; color: #fff; }
.sort { height: 30px; background: #fff; border: 1px solid #F1EEEA; color: #5C6570; }
.sort.on { background: #FFF1EC; color: #F96141; border-color: #F96141; }
h1 { margin: 14px 0 0; font-size: 24px; letter-spacing: -0.03em; font-weight: 800; line-height: 1.15; }
.sub { margin: 2px 0 14px; color: #8E949C; font-size: 13px; line-height: 1.35; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.shot { position: relative; border-radius: 16px; overflow: hidden; background: #F6F3F0; aspect-ratio: 4 / 3; cursor: pointer; border: 0; box-shadow: 0 8px 18px rgba(28,36,48,0.06); }
.shot img { width: 100%; height: 100%; object-fit: cover; object-position: center; display: block; }
.heart {
  position: absolute; top: 8px; right: 8px; width: 32px; height: 32px; border: 0; border-radius: 99px;
  background: rgba(255,255,255,0.94); color: #1C2430; cursor: pointer;
  display: inline-flex; align-items: center; justify-content: center;
}
.sold {
  position: absolute; left: 8px; bottom: 8px; height: 18px; display: inline-flex; align-items: center;
  background: #fff; color: #F96141; font-size: 10px; font-weight: 800; border-radius: 999px; padding: 0 7px;
}
.nm { margin-top: 6px; font-size: 14px; font-weight: 750; line-height: 1.3; }
.cat { margin-top: 2px; font-size: 12px; color: #9AA0A8; }
.pr { display: flex; align-items: center; margin-top: 6px; }
.pr b { font-size: 16px; font-weight: 800; color: #F96141; letter-spacing: -0.03em; }
.add {
  margin-left: auto; height: 34px; padding: 0 14px; border: 0; border-radius: 999px;
  background: #F96141; color: #fff; font-weight: 700; cursor: pointer;
}
.state { text-align: center; color: #8E949C; padding: 24px 0; }
</style>
