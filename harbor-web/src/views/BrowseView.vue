<template>
  <div class="fn-page page" data-figma="M26">
    <header class="sticky">
      <h1>{{ t('browse_title') || 'Departments' }}</h1>
      <p class="sub">{{ t('browse_all_categories') || 'Shop by category' }}</p>
      <AppSearchBar compact navigate-on-focus />
    </header>

    <div class="dept-grid">
      <button
        v-for="c in categories"
        :key="c.id"
        type="button"
        class="dept-card"
        @click="openCat(c.id)"
      >
        <span class="dept-ico" :style="{ background: tone(c.id).bg, color: tone(c.id).fg }">{{ tone(c.id).emoji }}</span>
        <span class="dept-copy">
          <strong>{{ catLabel(c.id) || c.name }}</strong>
          <small>{{ tone(c.id).hint }}</small>
        </span>
      </button>
    </div>

    <div class="chips">
      <button type="button" class="chip" :class="{ on: !activeCat }" @click="pick('')">{{ t('cat_all') || 'For you' }}</button>
      <button
        v-for="c in categories"
        :key="'chip-'+c.id"
        type="button"
        class="chip"
        :class="{ on: activeCat === c.id }"
        @click="pick(c.id)"
      >{{ catLabel(c.id) || c.name }}</button>
    </div>

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
  kitchen: { bg: '#FEF3C7', fg: '#B45309', emoji: '🍳', hint: 'Tools · prep · gadgets' },
  cleaning: { bg: '#D1FAE5', fg: '#047857', emoji: '🧹', hint: 'Cloths · brushes' },
  storage: { bg: '#E0F2FE', fg: '#0E7490', emoji: '📦', hint: 'Bins · shelves' },
  pet: { bg: '#FCE7F3', fg: '#9D174D', emoji: '🐾', hint: 'Bowls · care' },
  personal: { bg: '#EDE9FE', fg: '#5B21B6', emoji: '🧴', hint: 'Oral · bath' },
  office: { bg: '#E2E8F0', fg: '#334155', emoji: '📎', hint: 'Lamps · organizers' },
}

function tone(id: string) {
  const key = String(id || '').toLowerCase()
  return tones[key] || { bg: '#F3F4F6', fg: '#0F2744', emoji: '•', hint: '' }
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
.page { min-height: 100vh; background: $hb-paper; padding: 0 16px; }
.sticky {
  position: sticky; top: 0; z-index: 20;
  background: rgba(247,244,239,0.94); backdrop-filter: blur(14px);
  padding: calc(12px + env(safe-area-inset-top)) 0 10px;
}
h1 { margin: 0; font-size: 28px; font-weight: 800; color: #1C2430; letter-spacing: -0.03em; }
.sub { margin: 4px 0 10px; color: $hb-muted; font-size: 13px; }
.dept-grid { display: grid; grid-template-columns: 1fr; gap: 10px; margin-bottom: 14px; }
.dept-card {
  display: flex; gap: 12px; align-items: center; text-align: left;
  background: #fff; border: 1px solid $hb-line; border-radius: 16px; padding: 12px;
  cursor: pointer; width: 100%;
}
.dept-ico {
  width: 52px; height: 52px; border-radius: 14px; flex-shrink: 0;
  display: inline-flex; align-items: center; justify-content: center; font-size: 22px;
}
.dept-copy { display: flex; flex-direction: column; gap: 2px; }
.dept-copy strong { font-size: 15px; color: $hb-ink; }
.dept-copy small { font-size: 12px; color: $hb-muted; }
.chips { display: flex; gap: 8px; overflow-x: auto; padding: 4px 0 12px; scrollbar-width: none; }
.chips::-webkit-scrollbar { display: none; }
.chip {
  flex: 0 0 auto; border: 1px solid $hb-line; background: #fff; border-radius: 999px;
  padding: 8px 13px; font-size: 13px; font-weight: 650; cursor: pointer; color: $hb-ink;
  &.on { background: #F96141; color: #fff; border-color: #F96141; }
}
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; padding-bottom: 8px; }
.state { text-align: center; color: $hb-muted; padding: 40px 8px; }

.fn-page { --ink:#0F2744; --teal:#0E7490; --amber:#B45309; --sand:#F7F4EF; }
</style>
