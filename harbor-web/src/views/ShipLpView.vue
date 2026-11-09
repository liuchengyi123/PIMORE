<template>
  <div class="fn-page page" data-figma="M42">
    <div class="hero">
      <button type="button" class="back" @click="$router.back()" aria-label="back"><ChevronLeft :size="22" :stroke-width="1.75" /></button>
      <div class="kicker">{{ t('badge_flash') }}</div>
      <div class="htitle">闪购 / 加速发货</div>
      <div class="line">限时场次 · 尽快发货</div>
      <div v-if="flashEnds" class="ends">{{ t('ends_prefix') }} · {{ flashEnds }}</div>
    </div>
    <div v-if="loading" class="state">加载中…</div>
    <div v-else-if="!products.length" class="state">暂无闪购商品</div>
    <div v-else class="grid">
      <ProductCard v-for="p in products" :key="p.sku" :product="p" />
    </div>
  </div>
</template>
<script setup lang="ts">
import { ChevronLeft } from 'lucide-vue-next'
import { onMounted, ref } from 'vue'
import { listShipLpProducts, fetchFlashEnds, type Product } from '@/api/products'
import { useI18n } from '@/composables/i18n'
import ProductCard from '@/components/ProductCard.vue'
const products = ref<Product[]>([])
const loading = ref(true)
const { t } = useI18n()
const flashEnds = ref('')
onMounted(async () => {
  try { flashEnds.value = (await fetchFlashEnds()) || '' } catch { /* */ }
  try { products.value = await listShipLpProducts() } finally { loading.value = false }
})
</script>
<style lang="scss" scoped>
@import '@/styles/theme.scss';
.page { min-height: 100vh; background: $hb-paper; padding-bottom: 40px; }
.hero {
  margin: 12px 16px 16px; margin-top: calc(12px + env(safe-area-inset-top));
  border-radius: 22px; padding: 18px; color: #1C2430;
  background: #FFF6F1;
}
.kicker, .htitle { color: #F96141; }
.back { width: 34px; height: 34px; border: 0; border-radius: 12px; background: #fff; color: #1C2430; font-size: 20px; margin-bottom: 12px; cursor: pointer; }
.kicker { font-size: 11px; letter-spacing: 1px; text-transform: uppercase; opacity: 0.85; font-weight: 650; }
.htitle { font-size: 26px; font-weight: 760; margin-top: 8px; }
.line { margin-top: 8px; font-size: 13px; opacity: 0.9; }
.ends { margin-top: 10px; font-size: 12px; }
.state { text-align: center; color: $hb-muted; padding: 40px 16px; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; padding: 0 16px; }

.fn-page { --ink:#1C2430; --teal:#0E7490; --amber:#F96141; --sand:#FCFAF8; }
</style>
