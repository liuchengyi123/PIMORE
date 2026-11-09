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

    <h1>{{ zh ? '日常好物' : 'Everyday essentials' }}</h1>
    <p class="sub">{{ zh ? '用心的家居小物，生活更好一点。' : 'Thoughtful home goods. Better living.' }}</p>

    <div v-if="loading" class="state">{{ t('pdp_loading') }}</div>
    <div v-else class="grid">
      <article v-for="(item, i) in shown" :key="item.sku" class="card">
        <div class="shot" @click="open(item, i)">
          <img :src="item.image" alt="" />
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
import b1 from '@/assets/browse/b1.jpg'
import b2 from '@/assets/browse/b2.jpg'
import b3 from '@/assets/browse/b3.jpg'
import b4 from '@/assets/browse/b4.jpg'
import b5 from '@/assets/browse/b5.jpg'
import b6 from '@/assets/browse/b6.jpg'

const { t, lang } = useI18n()
const zh = computed(() => String(lang.value).startsWith('zh'))
const route = useRoute()
const router = useRouter()
const cart = useCart()
const count = computed(() => cart.count.value)
const live = ref<Product[]>([])
const activeCat = ref('')
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

const catalog = [
  { sku: 'stoneware-mug', name: 'Stoneware Mug', cat: 'Kitchen', price: 8, image: b1 },
  { sku: 'linen-pillow', name: 'Linen Throw Pillow', cat: 'Decor', price: 12, image: b2 },
  { sku: 'waffle-throw', name: 'Waffle Weave Throw', cat: 'Bedding', price: 15, image: b3 },
  { sku: 'ceramic-planter', name: 'Ceramic Planter', cat: 'Decor', price: 10, image: b4 },
  { sku: 'bamboo-board', name: 'Bamboo Cutting Board', cat: 'Kitchen', price: 6, image: b5 },
  { sku: 'bath-towels', name: 'Bath Towel Set', cat: 'Bath', price: 13, image: b6 },
]

const shown = computed(() => {
  if (activeCat.value && live.value.length) {
    return live.value.slice(0, 8).map((p) => ({
      sku: p.sku,
      name: p.name,
      cat: p.category || activeCat.value,
      price: Math.round(p.price),
      image: p.image || b1,
      live: p,
    }))
  }
  const id = activeCat.value
  const rows = id ? catalog.filter((c) => c.cat.toLowerCase() === id) : catalog
  return rows.map((c) => ({ ...c, live: undefined as Product | undefined }))
})

async function pick(id: string) {
  activeCat.value = id
  loading.value = true
  try {
    live.value = id ? await listByCategory(id) : []
  } catch {
    live.value = []
  } finally {
    loading.value = false
  }
  router.replace({ path: '/browse', query: id ? { cat: id } : {} })
}

function open(item: { sku: string; live?: Product }, _i: number) {
  const sku = item.live?.sku || ''
  if (sku && live.value.length) router.push({ path: '/pdp', query: { sku } })
  else router.push('/pdp')
}

function add(item: { sku: string; name: string; price: number; image: string; live?: Product }) {
  if (item.live) cart.add(item.live)
  else cart.add({ id: item.sku, sku: item.sku, name: item.name, price: item.price, category: 'home', image: item.image })
}

function wish(item: { sku: string }) {
  router.push({ path: '/wishlist', query: { sku: item.sku } })
}

onMounted(() => {
  const cat = route.query.cat ? String(route.query.cat) : ''
  if (cat) pick(cat)
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
.chips { display: flex; gap: 8px; overflow-x: auto; margin-top: 12px; padding-bottom: 2px; scrollbar-width: none; }
.chips::-webkit-scrollbar { display: none; }
.chip {
  flex: 0 0 auto; display: inline-flex; align-items: center; gap: 6px;
  height: 34px; padding: 0 12px; border-radius: 999px; border: 0; background: #F3F1EE;
  color: #1C2430; font-weight: 650; font-size: 13px; cursor: pointer;
  &.on { background: #F96141; color: #fff; }
}
h1 { margin: 14px 0 0; font-size: 24px; letter-spacing: -0.03em; font-weight: 800; line-height: 1.15; }
.sub { margin: 2px 0 14px; color: #8E949C; font-size: 13px; line-height: 1.35; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px 12px; }
.shot { position: relative; border-radius: 16px; overflow: hidden; background: #F6F3F0; aspect-ratio: 4 / 3; cursor: pointer; border: 0; box-shadow: 0 8px 18px rgba(28,36,48,0.06); }
.shot img { width: 100%; height: 100%; object-fit: cover; object-position: center; display: block; }
.heart {
  position: absolute; top: 8px; right: 8px; width: 32px; height: 32px; border: 0; border-radius: 99px;
  background: rgba(255,255,255,0.94); color: #1C2430; cursor: pointer;
  display: inline-flex; align-items: center; justify-content: center;
}
.nm { margin-top: 8px; font-size: 14px; font-weight: 750; line-height: 1.3; }
.cat { margin-top: 2px; font-size: 12px; color: #9AA0A8; }
.pr { display: flex; align-items: center; margin-top: 8px; }
.pr b { font-size: 16px; }
.add {
  margin-left: auto; height: 34px; padding: 0 14px; border: 0; border-radius: 999px;
  background: #F96141; color: #fff; font-weight: 700; cursor: pointer;
}
.state { text-align: center; color: #8E949C; padding: 24px 0; }
</style>
