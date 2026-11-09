<template>
  <div class="page">
    <header class="head">
      <button type="button" class="back" @click="$router.back()" aria-label="back">‹</button>
      <h1 class="title">{{ zh ? '特卖' : 'Sale' }}</h1>
    </header>
    <section class="hero">
      <div class="eyebrow">{{ zh ? '限时' : 'Limited time' }}</div>
      <div class="hl">{{ zh ? '闪购' : 'Flash deals' }}</div>
      <div v-if="saleEnds" class="ends">{{ zh ? '截止 ' : 'Ends ' }}{{ saleEnds }}</div>
    </section>
    <div v-if="loading" class="state">{{ zh ? '加载中…' : 'Loading…' }}</div>
    <div v-else-if="!products.length" class="state">{{ zh ? '暂无特卖' : 'No sale items right now.' }}</div>
    <div v-else class="grid">
      <article v-for="p in products" :key="p.sku" class="card" @click="go(p)">
        <div class="thumb" :style="ph(p)">
          <img v-if="p.image" :src="p.image" :alt="p.name" />
          <span v-if="pct(p)" class="badge">-{{ pct(p) }}%</span>
        </div>
        <div class="nm">{{ p.name }}</div>
        <div class="prices">
          <span v-if="p.compareAt && p.compareAt > p.price" class="was">{{ money(p.compareAt) }}</span>
          <span class="now">{{ money(p.price) }}</span>
          <button type="button" class="add" aria-label="Add" @click.stop="add(p)">+</button>
        </div>
      </article>
    </div>
    <AppTabBar active="home" />
  </div>
</template>
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { listSaleProducts, fetchDealEnds, type Product } from '@/api/products'
import { useCart } from '@/composables/cart'
import AppTabBar from '@/components/AppTabBar.vue'
const cart = useCart()
const zh = computed(() => String(navigator.language || '').toLowerCase().startsWith('zh'))
const router = useRouter()
const products = ref<Product[]>([])
const loading = ref(true)
const saleEnds = ref('')
onMounted(async () => {
  try { saleEnds.value = (await fetchDealEnds()) || '' } catch { /* */ }
  try { products.value = await listSaleProducts() } finally { loading.value = false }
})
function money(n: number | string | undefined) {
  const v = Number(n || 0)
  return v ? `$${v.toFixed(2)}` : ''
}
function pct(p: Product) {
  const a = Number((p as any).compareAt || 0)
  const b = Number(p.price || 0)
  if (a > b && b > 0) return Math.round((1 - b / a) * 100)
  return 0
}
function ph(p: Product) {
  if (p.image) return {}
  return { backgroundImage: 'linear-gradient(154deg, #fda4af 6%, #be123c 94%)' }
}
function go(p: Product) { router.push(`/p/${encodeURIComponent(p.sku || p.id)}`) }
function add(p: Product) { cart.add(p) }
</script>
<style scoped>
.page { min-height: 100vh; background: #F7F8FA; color: #1C2430; padding: 12px 16px 40px; padding-top: calc(12px + env(safe-area-inset-top)); }
.head { display: flex; gap: 10px; align-items: center; margin-bottom: 12px; }
.back { border: 0; background: transparent; font-size: 22px; font-weight: 700; cursor: pointer; color: #1C2430; }
.title { font-size: 22px; font-weight: 800; margin: 0; color: #F96141; }
.hero {
  border-radius: 22px; padding: 22px 20px; color: #fff; margin-bottom: 16px;
  background: linear-gradient(120deg, #FF8A62 0%, #F96141 70%);
}
.eyebrow { font-size: 12px; letter-spacing: 0.12em; font-weight: 700; }
.hl { margin-top: 6px; font-size: 28px; font-weight: 800; letter-spacing: -0.03em; }
.ends { margin-top: 8px; font-size: 13px; opacity: 0.95; }
.state { text-align: center; color: #8B919A; padding: 28px 8px; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.card { background: #fff; border-radius: 18px; padding: 8px 8px 12px; box-shadow: 0 6px 18px rgba(28,36,48,0.05); cursor: pointer; }
.thumb { position: relative; aspect-ratio: 1; border-radius: 14px; overflow: hidden; background: #F7F8FA; }
.thumb img { width: 100%; height: 100%; object-fit: cover; }
.badge { position: absolute; left: 8px; top: 8px; background: #F96141; color: #fff; font-size: 11px; font-weight: 800; border-radius: 999px; padding: 3px 8px; }
.nm { margin-top: 8px; font-size: 13px; font-weight: 650; line-height: 1.3; min-height: 2.6em; }
.prices { display: flex; align-items: center; gap: 6px; margin-top: 4px; }
.now { color: #F96141; font-weight: 800; font-size: 15px; }
.was { color: #9AA0A8; text-decoration: line-through; font-size: 12px; }
.add { margin-left: auto; width: 28px; height: 28px; border: 0; border-radius: 999px; background: #F96141; color: #fff; font-weight: 700; cursor: pointer; }
</style>
