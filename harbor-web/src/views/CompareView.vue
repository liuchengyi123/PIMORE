<template>
  <div class="page">
    <header class="head">
      <button type="button" class="back" @click="$router.back()" aria-label="back">‹</button>
      <h1 class="title">对比</h1>
    </header>
    <div v-if="loading" class="state">{{ zh ? '加载中…' : 'Loading…' }}</div>
    <div v-else-if="!products.length" class="state">
      <div class="mark" aria-hidden="true">↔</div>
      <div>{{ zh ? '还没有可对比的商品' : 'Nothing to compare yet.' }}</div>
      <router-link class="link" to="/home">{{ zh ? '去逛逛' : 'Browse products' }}</router-link>
    </div>
    <div v-else class="grid">
      <article v-for="p in products.slice(0,4)" :key="p.sku || p.id" class="card" @click="$router.push('/p/' + encodeURIComponent(p.sku || p.id))">
        <div class="thumb" :style="ph(p)">
          <img v-if="p.image" :src="p.image" :alt="p.name" />
        </div>
        <div class="nm">{{ p.name }}</div>
        <div class="price">{{ money(p) }}</div>
        <button type="button" class="add" @click.stop="add(p)">{{ zh ? '加入' : 'Add' }}</button>
      </article>
    </div>
    <AppTabBar active="browse" />
  </div>
</template>
<script setup lang="ts">
import { ChevronLeft } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import { listCompareProducts, type Product } from '@/api/products'
import { useCart } from '@/composables/cart'
import { useI18n } from '@/composables/i18n'
import AppTabBar from '@/components/AppTabBar.vue'
const { t, lang } = useI18n()
const zh = computed(() => String(lang.value).startsWith('zh'))
const cart = useCart()
const products = ref<Product[]>([])
const loading = ref(true)
const note = ref('')
onMounted(async () => {
  try {
    const res: any = await listCompareProducts()
    products.value = Array.isArray(res) ? res : (res?.products || [])
    note.value = products.value.length ? t('compare_n', { n: products.value.length }) : t('compare_empty')
  } finally { loading.value = false }
})

function money(p: any) {
  const n = Number(p.price || 0)
  return n ? `$${n.toFixed(2)}` : ''
}
function add(p: Product) { cart.addServer(p) }
function ph(p: any) {
  if (p.image) return {}
  return { backgroundImage: 'linear-gradient(154deg, #bae6fd 6%, #0369a1 94%)' }
}
</script>
<style scoped>
.page { min-height: 100vh; background: #FCFAF8; color: #1C2430; padding: 12px 16px 40px; padding-top: calc(12px + env(safe-area-inset-top)); }
.head { display: flex; gap: 10px; align-items: center; margin-bottom: 12px; }
.back { border: 0; background: transparent; font-size: 22px; font-weight: 700; cursor: pointer; color: #1C2430; }
.title { font-size: 22px; font-weight: 800; letter-spacing: -0.03em; margin: 0; }
.mark { width: 56px; height: 56px; margin: 0 auto 10px; border-radius: 18px; background: #FFF1EC; color: #F96141; display: grid; place-items: center; font-size: 22px; font-weight: 800; }
.link { color: #F96141; font-weight: 700; }
.grid { display: flex; gap: 8px; flex-wrap: wrap; }
.card { width: calc(50% - 4px); background: #fff; border: 1px solid #E2E6EE; border-radius: 16px; padding: 10px; box-sizing: border-box; }
.thumb { height: 90px; border-radius: 10px; overflow: hidden; background: #e8e4dc; position: relative; }
.thumb img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
.nm { margin-top: 8px; font-size: 12px; font-weight: 600; }
.price { margin-top: 2px; font-size: 13px; font-weight: 700; color: #F96141; }
.state { text-align: center; color: #6B7280; padding: 36px 8px; }
.link { display: inline-block; margin-top: 10px; color: #F96141; font-weight: 700; text-decoration: none; }
</style>
