<template>
  <div class="page">
    <header class="head">
      <button type="button" class="back" @click="$router.back()" aria-label="back">‹</button>
      <h1 class="title">Sale</h1>
    </header>
    <section class="hero">
      <div class="eyebrow">Limited time</div>
      <div class="hl">Flash deals</div>
      <div v-if="saleEnds" class="ends">Ends {{ saleEnds }}</div>
    </section>
    <div v-if="loading" class="state">Loading…</div>
    <div v-else-if="!products.length" class="state">No sale items right now.</div>
    <div v-else class="list">
      <article v-for="p in products" :key="p.sku" class="row" @click="go(p)">
        <div class="thumb" :style="ph(p)">
          <img v-if="p.image" :src="p.image" :alt="p.name" />
          <span v-if="pct(p)" class="badge">-{{ pct(p) }}%</span>
        </div>
        <div class="meta">
          <div class="nm">{{ p.name }}</div>
          <div class="prices">
            <span class="now">{{ money(p.price) }}</span>
            <span v-if="p.compareAt && p.compareAt > p.price" class="was">{{ money(p.compareAt) }}</span>
          </div>
        </div>
      </article>
    </div>
  </div>
</template>
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { listSaleProducts, fetchDealEnds, type Product } from '@/api/products'
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
</script>
<style scoped>
.page { min-height: 100vh; background: #F4F7FB; color: #1B2B4A; padding: 12px 16px 40px; padding-top: calc(12px + env(safe-area-inset-top)); }
.head { display: flex; gap: 10px; align-items: center; margin-bottom: 12px; }
.back { border: 0; background: transparent; font-size: 22px; font-weight: 700; cursor: pointer; color: #1B2B4A; }
.title { font-size: 17px; font-weight: 700; margin: 0; }
.hero {
  border-radius: 18px; padding: 20px; color: #fff; margin-bottom: 14px;
  background-image: linear-gradient(161deg, #B45309 4%, #F59E0B 96%);
}
.eyebrow { font-size: 13px; opacity: 0.9; }
.hl { margin-top: 6px; font-size: 22px; font-weight: 800; }
.ends { margin-top: 8px; font-size: 12px; opacity: 0.9; }
.state { text-align: center; color: #6B7280; padding: 28px 8px; }
.list { display: flex; flex-direction: column; gap: 10px; }
.row {
  display: flex; gap: 12px; background: #fff; border: 1px solid #E7ECF3; border-radius: 16px;
  padding: 10px; align-items: center;
}
.thumb { position: relative; width: 72px; height: 72px; border-radius: 12px; overflow: hidden; flex-shrink: 0; background: #e8e4dc; }
.thumb img { width: 100%; height: 100%; object-fit: cover; }
.badge {
  position: absolute; left: 4px; top: 4px; background: #B45309; color: #fff; font-size: 10px; font-weight: 700;
  padding: 2px 6px; border-radius: 999px;
}
.nm { font-size: 14px; font-weight: 600; line-height: 1.3; }
.prices { margin-top: 6px; display: flex; gap: 8px; align-items: baseline; }
.now { font-size: 16px; font-weight: 700; color: #B45309; }
.was { font-size: 12px; color: #9CA3AF; text-decoration: line-through; }
</style>
