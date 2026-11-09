<template>
  <div class="fn-page page" data-figma="M26">
    <header class="sticky">
      <div class="brand-row">
        <span class="brand-mark">Pimo</span>
        <span class="brand-sub">Harbor</span>
      </div>
      <AppSearchBar compact navigate-on-focus />
    </header>

    <div class="chips">
      <button type="button" class="chip" :class="{ on: !activeCat }" @click="pick('')">{{ t('cat_all') || 'All' }}</button>
      <button
        v-for="c in categories"
        :key="'chip-'+c.id"
        type="button"
        class="chip"
        :class="{ on: activeCat === c.id }"
        @click="pick(c.id)"
      >{{ catLabel(c.id) || c.name }}</button>
    </div>

    <h2 class="essentials">Everyday essentials</h2>

    <div v-if="loading" class="state">{{ t('pdp_loading') }}</div>
    <div v-else class="grid">
      <ProductCard v-for="p in products" :key="p.sku" :product="p" />
    </div>
    <AppTabBar active="browse" />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ALL_CATEGORIES, listByCategory, type Product } from '@/api/products'
import { useI18n } from '@/composables/i18n'
import ProductCard from '@/components/ProductCard.vue'
import AppTabBar from '@/components/AppTabBar.vue'
import AppSearchBar from '@/components/AppSearchBar.vue'

const { t, catLabel } = useI18n()
const route = useRoute()
const router = useRouter()
const categories = ALL_CATEGORIES
const products = ref<Product[]>([])
const activeCat = ref('')
const loading = ref(false)

const tones: Record<string, { bg: string; fg: string; emoji: string; hint: string }> = {
  kitchen: { bg: '#FFF1EC', fg: '#FF6B4A', emoji: '🍳', hint: 'Tools · prep · gadgets' },
  cleaning: { bg: '#FFF1EC', fg: '#16A34A', emoji: '🧹', hint: 'Cloths · brushes' },
  storage: { bg: '#F4F7FB', fg: '#FF6B4A', emoji: '📦', hint: 'Bins · shelves' },
  pet: { bg: '#FFF1EC', fg: '#F04E32', emoji: '🐾', hint: 'Bowls · care' },
  personal: { bg: '#F4F7FB', fg: '#1B2B4A', emoji: '🧴', hint: 'Oral · bath' },
  office: { bg: '#F4F7FB', fg: '#1B2B4A', emoji: '📎', hint: 'Lamps · organizers' },
}

function tone(id: string) {
  const key = String(id || '').toLowerCase()
  return tones[key] || { bg: '#F4F7FB', fg: '#1B2B4A', emoji: '•', hint: '' }
}

async function load(cat = '') {
  activeCat.value = cat
  loading.value = true
  try {
    products.value = await listByCategory(cat || 'All')
  } finally {
    loading.value = false
  }
}
function pick(id: string) {
  load(id)
}
function openCat(id: string) {
  pick(id)
  router.replace({ path: '/browse', query: { cat: id } })
}
onMounted(() => {
  const cat = route.query.cat ? String(route.query.cat) : ''
  load(cat)
})
</script>

<style lang="scss" scoped>
@import '@/styles/theme.scss';
.page { min-height: 100vh; background: $hb-paper; padding: 0 16px 16px; }
.sticky {
  position: sticky; top: 0; z-index: 20;
  background: rgba(244, 247, 251, 0.94); backdrop-filter: blur(14px);
  padding: calc(12px + env(safe-area-inset-top)) 0 12px;
}
.brand-row { display: flex; align-items: baseline; gap: 8px; margin-bottom: 10px; }
.brand-mark { font-size: 22px; font-weight: 800; color: $hb-coral; letter-spacing: -0.02em; }
.brand-sub { font-size: 13px; font-weight: 650; color: $hb-muted; }
.chips { display: flex; gap: 8px; overflow-x: auto; padding: 4px 0 12px; scrollbar-width: none; }
.chips::-webkit-scrollbar { display: none; }
.chip {
  flex: 0 0 auto; border: 1px solid $hb-line; background: #fff; border-radius: 999px;
  padding: 8px 13px; font-size: 13px; font-weight: 650; cursor: pointer; color: $hb-ink;
  &.on { background: $hb-coral; color: #fff; border-color: $hb-coral; }
}
.essentials { margin: 0 0 12px; font-size: 18px; font-weight: 800; color: $hb-ink; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; padding-bottom: 8px; }
.state { text-align: center; color: $hb-muted; padding: 40px 8px; }

.fn-page { --ink:#1B2B4A; --teal:#FF6B4A; --amber:#FF6B4A; --sand:#F4F7FB; }
</style>
