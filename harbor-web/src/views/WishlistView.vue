<template>
  <div class="page">
    <header class="head">
      <button type="button" class="back" @click="$router.back()" aria-label="back">‹</button>
      <h1 class="title">{{ t('wishlist_title') || 'Wishlist' }}</h1>
    </header>
    <div v-if="loading" class="state">{{ t('pdp_loading') }}</div>
    <div v-else-if="loginRequired" class="gate">
      <p>{{ t('wishlist_signin') }}</p>
      <router-link class="gate-btn" :to="{ path: '/login', query: { next: '/wishlist' } }">{{ t('me_sign_in') }}</router-link>
    </div>
    <div v-else-if="!products.length" class="state">{{ t('wishlist_empty') }}</div>
    <div v-else class="grid">
      <article v-for="p in products" :key="p.sku" class="card" @click="go(p)">
        <div class="thumb" :style="thumbStyle(p)">
          <img v-if="p.image" :src="p.image" :alt="p.name" />
          <span v-else class="ph">{{ (p.name || '').slice(0, 8) }}</span>
        </div>
        <div class="body">
          <div class="nm">{{ p.name }}</div>
          <div class="price">{{ money(p) }}</div>
          <button type="button" class="add" @click.stop="add(p)">{{ t('common_add') || 'Add to cart' }}</button>
        </div>
      </article>
    </div>
    <AppTabBar active="wishlist" variant="wish" />
  </div>
</template>
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { fetchWishlistHtml } from '@/api/accountApi'
import { parseFeedCards, type Product } from '@/api/products'
import { useCart } from '@/composables/cart'
import { useI18n } from '@/composables/i18n'
import AppTabBar from '@/components/AppTabBar.vue'
const { t } = useI18n()
const cart = useCart()
const router = useRouter()
const products = ref<Product[]>([])
const loading = ref(true)
const loginRequired = ref(false)
onMounted(async () => {
  try {
    const html = await fetchWishlistHtml()
    if (/name=["']password["']/i.test(html) && !/class=["']card["']/i.test(html)) {
      loginRequired.value = true
      return
    }
    products.value = parseFeedCards(html)
  } finally { loading.value = false }
})
function money(p: Product) {
  const n = Number(p.price || 0)
  return n ? `$${n.toFixed(2)}` : ''
}
function thumbStyle(p: Product) {
  if (p.image) return {}
  return { backgroundImage: 'linear-gradient(152deg, #fcd34d 6%, #b45309 94%)' }
}
function go(p: Product) {
  router.push(`/p/${encodeURIComponent(p.sku || p.id)}`)
}
function add(p: Product) {
  cart.addServer(p)
}
</script>
<style scoped>
.page { min-height: 100vh; background: #FCFAF8; color: #1C2430; padding: 12px 16px 40px; padding-top: calc(12px + env(safe-area-inset-top)); }
.head { display: flex; gap: 10px; align-items: center; margin-bottom: 12px; }
.back { border: 0; background: transparent; font-size: 22px; font-weight: 700; color: #1C2430; padding: 0 4px; cursor: pointer; }
.title { font-size: 22px; font-weight: 800; letter-spacing: -0.03em; margin: 0; }
.state, .gate { text-align: center; color: #6B7280; padding: 36px 8px; }
.gate-btn { display: inline-flex; margin-top: 12px; background: #F96141; color: #fff; padding: 12px 18px; border-radius: 999px; font-weight: 600; text-decoration: none; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.card { background: #fff; border: 1px solid #E8E4DC; border-radius: 16px; overflow: hidden; }
.thumb { height: 130px; background: #e8e4dc; display: flex; align-items: flex-end; padding: 12px; position: relative; }
.thumb img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
.ph { position: relative; z-index: 1; color: #fff; font-size: 11px; font-weight: 600; }
.body { padding: 10px; }
.nm { font-size: 13px; font-weight: 600; color: #1C2430; line-height: 1.3; min-height: 34px; }
.price { margin-top: 6px; font-size: 16px; font-weight: 700; color: #F96141; }
.add { margin-top: 8px; width: 100%; height: 34px; border-radius: 999px; border: 0; background: #F96141; color: #fff; font-size: 12px; font-weight: 700; cursor: pointer; }
</style>
