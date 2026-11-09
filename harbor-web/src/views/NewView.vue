<template>
  <div class="page">
    <header class="head">
      <button type="button" class="back" @click="$router.back()" aria-label="back">‹</button>
      <h1 class="title">{{ zh ? '新品' : 'New In' }}</h1>
    </header>
    <section class="hero">
      <div class="eyebrow">{{ zh ? '本周刚到' : 'Just landed this week' }}</div>
      <div class="hl">{{ zh ? '新鲜家居小物。' : 'Fresh finds. Everyday essentials.' }}</div>
    </section>
    <div v-if="loading" class="state">{{ zh ? '加载中…' : 'Loading…' }}</div>
    <div v-else-if="!products.length" class="state">{{ zh ? '暂无新品' : 'No new arrivals yet.' }}</div>
    <div v-else class="grid">
      <article v-for="p in products" :key="p.sku" class="card" @click="go(p)">
        <div class="thumb" :style="ph(p)">
          <span class="tag">{{ zh ? '新品' : 'NEW' }}</span>
          <img v-if="p.image" :src="p.image" :alt="p.name" />
        </div>
        <div class="body">
          <div class="nm">{{ p.name }}</div>
          <div class="price-row">
            <div class="price">{{ money(p.price) }}</div>
            <button type="button" class="add" aria-label="Add" @click.stop="add(p)">+</button>
          </div>
        </div>
      </article>
    </div>
    <AppTabBar active="home" />
  </div>
</template>
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { listNewProducts, type Product } from '@/api/products'
import { useCart } from '@/composables/cart'
import AppTabBar from '@/components/AppTabBar.vue'
const cart = useCart()
const zh = computed(() => String(navigator.language || '').toLowerCase().startsWith('zh'))
const router = useRouter()
const products = ref<Product[]>([])
const loading = ref(true)
onMounted(async () => {
  try { products.value = await listNewProducts() } catch { products.value = [] }
  finally { loading.value = false }
})
function money(n: number | string | undefined) {
  const v = Number(n || 0)
  return v ? `$${v.toFixed(2)}` : ''
}
function ph(p: Product) {
  if (p.image) return {}
  return { backgroundImage: 'linear-gradient(154deg, #a7f3d0 6%, #0E7490 94%)' }
}
function go(p: Product) { router.push(`/p/${encodeURIComponent(p.sku || p.id)}`) }
function add(p: Product) { cart.add(p) }
</script>
<style scoped>
.page { min-height: 100vh; background: #FCFAF8; color: #1C2430; padding: 12px 16px 40px; padding-top: calc(12px + env(safe-area-inset-top)); }
.title { color: #1C2430; font-size: 24px; font-weight: 800; letter-spacing: -0.03em; margin: 0; }
.hero { background: #FFF6F1; color: #1C2430; border-radius: 18px; padding: 16px; margin-bottom: 14px; }
.eyebrow { font-weight: 800; font-size: 16px; }
.hl { margin-top: 4px; color: #8B919A; font-size: 13px; font-weight: 500; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.card { background: #fff; border-radius: 18px; overflow: hidden; box-shadow: 0 6px 18px rgba(28,36,48,0.05); cursor: pointer; }
.thumb { position: relative; aspect-ratio: 1; background: #F3F0EC; }
.thumb img { width: 100%; height: 100%; object-fit: cover; }
.tag { position: absolute; left: 8px; top: 8px; background: #F96141; color: #fff; font-size: 10px; font-weight: 800; border-radius: 999px; padding: 3px 7px; }
.body { padding: 8px 10px 12px; }
.nm { font-size: 13px; font-weight: 650; min-height: 2.6em; }
.price-row { display: flex; align-items: center; }
.price { color: #F96141; font-weight: 800; }
.add { margin-left: auto; width: 28px; height: 28px; border: 0; border-radius: 999px; background: #F96141; color: #fff; cursor: pointer; }
.head { display: flex; gap: 10px; align-items: center; margin-bottom: 12px; }
.back { border: 0; background: transparent; font-size: 22px; font-weight: 700; cursor: pointer; color: #1C2430; }
.state { text-align: center; color: #8B919A; padding: 28px 8px; }
</style>
