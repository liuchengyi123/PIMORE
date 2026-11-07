<template>
  <div class="page">
    <header class="head">
      <button type="button" class="back" @click="$router.back()" aria-label="back">‹</button>
      <h1 class="title">New arrivals</h1>
    </header>
    <section class="hero">
      <div class="eyebrow">This week</div>
      <div class="hl">JUST LANDED</div>
    </section>
    <div v-if="loading" class="state">Loading…</div>
    <div v-else-if="!products.length" class="state">No new arrivals yet.</div>
    <div v-else class="grid">
      <article v-for="p in products" :key="p.sku" class="card" @click="go(p)">
        <div class="thumb" :style="ph(p)">
          <span class="tag">NEW</span>
          <img v-if="p.image" :src="p.image" :alt="p.name" />
        </div>
        <div class="body">
          <div class="nm">{{ p.name }}</div>
          <div class="price">{{ money(p.price) }}</div>
        </div>
      </article>
    </div>
  </div>
</template>
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { listNewProducts, type Product } from '@/api/products'
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
</script>
<style scoped>
.page { min-height: 100vh; background: #F7F4EF; color: #0F2744; padding: 12px 16px 40px; padding-top: calc(12px + env(safe-area-inset-top)); }
.head { display: flex; gap: 10px; align-items: center; margin-bottom: 12px; }
.back { border: 0; background: transparent; font-size: 22px; font-weight: 700; cursor: pointer; color: #0F2744; }
.title { font-size: 17px; font-weight: 700; margin: 0; }
.hero {
  border-radius: 18px; padding: 20px; color: #fff; margin-bottom: 14px;
  background-image: linear-gradient(161deg, #0F2744 4%, #0E7490 96%);
}
.eyebrow { font-size: 13px; opacity: 0.9; }
.hl { margin-top: 6px; font-size: 22px; font-weight: 800; letter-spacing: 0.04em; }
.state { text-align: center; color: #6B7280; padding: 28px 8px; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.card { background: #fff; border: 1px solid #E2E6EE; border-radius: 16px; overflow: hidden; }
.thumb { height: 120px; background: #e8e4dc; position: relative; }
.thumb img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
.tag {
  position: absolute; z-index: 1; left: 8px; top: 8px; background: #0E7490; color: #fff;
  font-size: 10px; font-weight: 700; padding: 2px 7px; border-radius: 999px;
}
.body { padding: 10px; }
.nm { font-size: 13px; font-weight: 600; min-height: 34px; line-height: 1.3; }
.price { margin-top: 6px; font-size: 16px; font-weight: 700; color: #B45309; }
</style>
