<template>
  <div class="page">
    <header class="head">
      <button type="button" class="back" @click="$router.back()" aria-label="back">‹</button>
      <h1 class="title">Browsing history</h1>
      <button v-if="products.length" type="button" class="clear" @click="clearLocal">Clear</button>
    </header>
    <div v-if="loading" class="state">Loading…</div>
    <div v-else-if="!products.length" class="state">{{ note || 'No browsing history yet.' }}</div>
    <div v-else class="grid">
      <article v-for="p in products" :key="p.sku" class="card" @click="go(p)">
        <div class="thumb" :style="ph(p)">
          <img v-if="p.image" :src="p.image" :alt="p.name" />
        </div>
        <div class="body">
          <div class="nm">{{ p.name }}</div>
          <div class="price">{{ money(p) }}</div>
        </div>
      </article>
    </div>
  </div>
</template>
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { fetchHistoryHtml } from '@/api/accountApi'
import { parseFeedCards, type Product } from '@/api/products'
import { loadBrowseHistory, clearBrowseHistory } from '@/composables/browseHistory'
import { useI18n } from '@/composables/i18n'
const { t } = useI18n()
const router = useRouter()
const products = ref<Product[]>([])
const loading = ref(true)
const note = ref(t('history_recent'))
function mapLocal() {
  return loadBrowseHistory().map((b) => ({
    id: b.sku, sku: b.sku, name: b.name, price: Number(b.price) || 0,
    category: 'Harbor', image: b.image || '', images: b.image ? [b.image] : [], live: false,
  }))
}
onMounted(async () => {
  try {
    const html = await fetchHistoryHtml()
    products.value = parseFeedCards(html)
    if (!products.value.length) products.value = mapLocal()
    note.value = products.value.length ? t('history_n', { n: products.value.length }) : t('history_empty_note')
  } catch {
    products.value = mapLocal()
    note.value = products.value.length ? t('history_local') : t('history_offline')
  } finally { loading.value = false }
})
function money(p: Product) {
  const n = Number(p.price || 0)
  return n ? `$${n.toFixed(2)}` : ''
}
function ph(p: Product) {
  if (p.image) return {}
  return { backgroundImage: 'linear-gradient(154deg, #bae6fd 6%, #0369a1 94%)' }
}
function go(p: Product) { router.push(`/p/${encodeURIComponent(p.sku || p.id)}`) }
function clearLocal() {
  try { clearBrowseHistory() } catch { /* */ }
  products.value = []
  note.value = t('history_empty_note') || 'No browsing history yet.'
}
</script>
<style scoped>
.page { min-height: 100vh; background: #F4F7FB; color: #1B2B4A; padding: 12px 16px 40px; padding-top: calc(12px + env(safe-area-inset-top)); }
.head { display: flex; gap: 10px; align-items: center; margin-bottom: 12px; }
.back { border: 0; background: transparent; font-size: 22px; font-weight: 700; color: #1B2B4A; cursor: pointer; }
.title { flex: 1; font-size: 17px; font-weight: 700; margin: 0; }
.clear { border: 0; background: transparent; font-size: 11px; color: #5C6570; cursor: pointer; }
.state { text-align: center; color: #6B7280; padding: 36px 8px; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.card { background: #fff; border: 1px solid #E2E6EE; border-radius: 16px; overflow: hidden; }
.thumb { height: 120px; background: #e8e4dc; position: relative; }
.thumb img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
.body { padding: 10px; }
.nm { font-size: 13px; font-weight: 600; color: #1B2B4A; min-height: 34px; line-height: 1.3; }
.price { margin-top: 6px; font-size: 16px; font-weight: 700; color: #B45309; }
</style>
