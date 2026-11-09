<template>
  <div class="page" data-figma="1:17">
    <header class="top">
      <h1>{{ zh ? '新品' : 'New In' }}</h1>
      <button type="button" class="filter" @click="open = !open">
        <SlidersHorizontal :size="14" /> {{ zh ? '筛选' : 'Filter' }}
      </button>
      <div v-if="open" class="pop">
        <button v-for="s in sorts" :key="s.id" type="button" :class="{ on: sort === s.id }" @click="pick(s.id)">{{ s.label }}</button>
      </div>
    </header>

    <section class="hero">
      <div>
        <h2>{{ zh ? '本周刚到' : 'Just landed this week' }}</h2>
        <p>{{ zh ? '新鲜家居，日常必备。' : 'Fresh finds. Everyday essentials.' }}</p>
      </div>
      <span class="hero-mark" aria-hidden="true"><Home :size="22" /></span>
    </section>

    <div v-if="loading" class="state">{{ zh ? '加载中…' : 'Loading…' }}</div>
    <div v-else-if="!shown.length" class="state">{{ zh ? '暂无新品' : 'No new arrivals yet.' }}</div>
    <div v-else class="grid">
      <article v-for="p in shown" :key="p.sku" class="card" @click="go(p)">
        <div class="shot">
          <img v-if="p.image" :src="p.image" :alt="p.name" />
          <span class="tag">{{ zh ? '新品' : 'NEW' }}</span>
        </div>
        <div class="nm">{{ p.name }}</div>
        <div class="sub">{{ p.blurb || p.category }}</div>
        <div class="pr">
          <b>{{ money(p.price) }}</b>
          <button type="button" class="bag" :aria-label="zh ? '加入购物车' : 'Add'" @click.stop="add(p)">
            <ShoppingCart :size="14" />
          </button>
        </div>
      </article>
    </div>
    <AppTabBar active="home" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Home, ShoppingCart, SlidersHorizontal } from 'lucide-vue-next'
import { listNewProducts, money, type Product } from '@/api/products'
import { useCart } from '@/composables/cart'
import { useI18n } from '@/composables/i18n'
import { shelf } from '@/catalog/shelf'
import AppTabBar from '@/components/AppTabBar.vue'

const { lang } = useI18n()
const zh = computed(() => String(lang.value).startsWith('zh'))
const cart = useCart()
const router = useRouter()
const products = ref<Product[]>([])
const loading = ref(true)
const open = ref(false)
const sort = ref<'best' | 'low' | 'high'>('best')

const sorts = computed(() => zh.value
  ? [{ id: 'best' as const, label: '综合' }, { id: 'low' as const, label: '价格从低到高' }, { id: 'high' as const, label: '价格从高到低' }]
  : [{ id: 'best' as const, label: 'Featured' }, { id: 'low' as const, label: 'Price: low to high' }, { id: 'high' as const, label: 'Price: high to low' }])
const shown = computed(() => {
  const list = [...products.value]
  if (sort.value === 'low') list.sort((a, b) => a.price - b.price)
  if (sort.value === 'high') list.sort((a, b) => b.price - a.price)
  return list
})

function pick(id: 'best' | 'low' | 'high') {
  sort.value = id
  open.value = false
}
function go(p: Product) { router.push({ path: '/pdp', query: { sku: p.sku } }) }
function add(p: Product) { cart.add(p) }

onMounted(async () => {
  try {
    const rows = await listNewProducts()
    products.value = rows.length ? rows : shelf.filter((p) => p.tag === 'New' || !p.compareAt)
  } catch {
    products.value = shelf.filter((p) => p.tag === 'New')
  } finally {
    loading.value = false
  }
})
</script>

<style lang="scss" scoped>
.page {
  min-height: 100vh; background: #FCFAF8; color: #1C2430;
  padding: calc(14px + env(safe-area-inset-top)) 16px 8px;
  font-family: "Plus Jakarta Sans", "PingFang SC", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
.top { position: relative; display: flex; align-items: center; justify-content: space-between; }
h1 { margin: 0; font-size: 28px; font-weight: 800; letter-spacing: -0.04em; color: #F96141; }
.filter {
  display: inline-flex; align-items: center; gap: 4px; height: 32px; padding: 0 12px;
  border: 0; border-radius: 999px; background: #FFF1EC; color: #F96141; font-weight: 700; font-size: 13px; cursor: pointer;
}
.pop {
  position: absolute; right: 0; top: 40px; z-index: 5; background: #fff; border-radius: 14px;
  box-shadow: 0 10px 28px rgba(28,36,48,0.12); padding: 6px; min-width: 148px;
}
.pop button {
  display: block; width: 100%; text-align: left; border: 0; background: transparent;
  padding: 8px 10px; border-radius: 10px; cursor: pointer; font-weight: 650; color: #1C2430;
}
.pop button.on { background: #FFF1EC; color: #F96141; }
.hero {
  margin-top: 14px; background: #FFF6F1; border-radius: 18px; padding: 16px;
  display: flex; align-items: center; justify-content: space-between; gap: 12px;
}
.hero h2 { margin: 0; font-size: 20px; letter-spacing: -0.03em; line-height: 1.15; }
.hero p { margin: 6px 0 0; color: #8B919A; font-size: 13px; }
.hero-mark {
  width: 54px; height: 54px; border-radius: 16px; background: #fff; color: #F96141;
  display: grid; place-items: center; flex: none; box-shadow: 0 6px 16px rgba(249,97,65,0.12);
}
.state { text-align: center; color: #8B919A; padding: 28px 8px; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 14px; }
.card { cursor: pointer; }
.shot { position: relative; aspect-ratio: 1.05; border-radius: 16px; overflow: hidden; background: #F6F4F2; }
.shot img { width: 100%; height: 100%; object-fit: cover; display: block; }
.tag {
  position: absolute; left: 8px; top: 8px; background: #F96141; color: #fff;
  font-size: 10px; font-weight: 800; letter-spacing: 0.04em; border-radius: 999px; padding: 3px 7px;
}
.nm { margin-top: 8px; font-size: 14px; font-weight: 800; letter-spacing: -0.02em; line-height: 1.25; }
.sub { margin-top: 2px; color: #8B919A; font-size: 12px; }
.pr { display: flex; align-items: center; margin-top: 6px; }
.pr b { color: #F96141; font-size: 16px; }
.bag {
  margin-left: auto; width: 28px; height: 28px; border: 0; border-radius: 999px;
  background: #F96141; color: #fff; display: inline-flex; align-items: center; justify-content: center; cursor: pointer;
}
</style>
