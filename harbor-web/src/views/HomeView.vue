<template>
  <div class="fn-page page" data-figma="M01">
    <header class="sticky-top">
      <div class="brand-row">
        <div>
          <div class="logo">Pimo</div>
          <div class="tagline">{{ t('home_tagline') || 'Better Homes. Happier Days.' }}</div>
        </div>
        <div class="right-actions">
          <router-link class="locale-pill" to="/locale">{{ localeLabel }}</router-link>
          <router-link class="icon-btn cart" to="/cart" aria-label="cart">
            <ShoppingBag :size="18" :stroke-width="1.7" />
            <span v-if="cartCount > 0" class="badge">{{ cartCount > 99 ? '99+' : cartCount }}</span>
          </router-link>
        </div>
      </div>
      <div class="search-wrap">
        <AppSearchBar :placeholder="searchPh" navigate-on-focus />
      </div>
    </header>

    <section class="hero">
      <div class="hero-kicker">{{ t('home_curated') || 'LIMITED TIME' }}</div>
      <div class="hero-title">{{ t('home_for_you') || 'Up to 50% Off Home Essentials' }}</div>
      <p class="hero-sub">{{ t('home_hero_sub') || 'Refresh your space, for less.' }}</p>
      <router-link class="hero-cta" to="/sale">{{ t('sale_shop') || 'Shop Sale' }} →</router-link>
    </section>

    <div class="body">
      <div class="quick">
        <router-link v-for="q in quickLinks" :key="q.to" class="quick-item" :to="q.to">
          <span class="q-ico" :style="{ background: q.bg, color: q.fg }">
            <component :is="q.icon" :size="18" :stroke-width="1.7" />
          </span>
          <span class="q-lab">{{ q.label }}</span>
        </router-link>
      </div>

      <div class="cats">
        <button type="button" class="cat-pill" :class="{ on: !activeCat }" @click="filterCat('')">{{ t('cat_all') || 'For you' }}</button>
        <button
          v-for="c in categories"
          :key="c.id"
          type="button"
          class="cat-pill"
          :class="{ on: activeCat === c.id }"
          @click="filterCat(c.id)"
        >{{ catLabel(c.id) }}</button>
      </div>

      <div class="sec-head">
        <div class="section-title">{{ t('recommended') || 'Recommended' }}</div>
        <div class="tiny">{{ t('personalized_note') || 'Personalized' }}</div>
      </div>

      <div v-if="loading" class="state">{{ t('pdp_loading') }}</div>
      <div v-else-if="error" class="state err">{{ error }}</div>
      <div v-else-if="!products.length" class="state">{{ t('no_products') || 'No products' }}</div>
      <div v-else class="grid">
        <ProductCard v-for="p in products" :key="p.sku" :product="p" />
      </div>

      <div v-if="shopStrip.length" class="shop-strip">
        <div class="section-title">{{ t('in_the_shop') || 'In the shop' }}</div>
        <div class="strip">
          <router-link v-for="p in shopStrip" :key="'s'+p.sku" class="strip-card" :to="'/p/' + p.sku">
            <div class="strip-thumb" :style="stripBg(p)">
              <img v-if="p.image" :src="p.image" alt="" />
            </div>
            <div class="strip-name">{{ p.name }}</div>
            <div class="strip-price">{{ money(p.price) }}</div>
          </router-link>
        </div>
      </div>
    </div>
    <AppTabBar active="home" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ShoppingBag, Utensils, Archive, SprayCan, Shirt } from 'lucide-vue-next'
import { CATEGORIES, listProducts, listByCategory, money, type Product } from '@/api/products'
import { useI18n } from '@/composables/i18n'
import { useCart } from '@/composables/cart'
import ProductCard from '@/components/ProductCard.vue'
import AppTabBar from '@/components/AppTabBar.vue'
import AppSearchBar from '@/components/AppSearchBar.vue'

const { t, catLabel, lang } = useI18n()
const cart = useCart()
const cartCount = computed(() => cart.count.value)
const categories = CATEGORIES
const products = ref<Product[]>([])
const shopStrip = ref<Product[]>([])
const activeCat = ref('')
const loading = ref(false)
const error = ref('')

const searchPh = computed(() =>
  lang.value === 'en' ? 'Search kitchen, storage, cleaning…' : (t('home_search_ph') || '搜索厨房、收纳、清洁…')
)

const localeLabel = computed(() => {
  const map: Record<string, string> = {
    en: '🇺🇸 US · USD',
    zh: '🇨🇳 CN · CNY',
    ja: '🇯🇵 JP · JPY',
    de: '🇩🇪 DE · EUR',
  }
  return map[lang.value] || '🇺🇸 US · USD'
})

const quickLinks = computed(() => {
  const en = lang.value === 'en'
  return [
    { to: '/browse?cat=kitchen', label: en ? 'Kitchen' : '厨房', icon: Utensils, bg: '#FFF1E8', fg: '#F96141' },
    { to: '/browse?cat=storage', label: en ? 'Storage' : '收纳', icon: Archive, bg: '#E7F8EF', fg: '#128A5E' },
    { to: '/browse?cat=cleaning', label: en ? 'Cleaning' : '清洁', icon: SprayCan, bg: '#E7F3FF', fg: '#2563EB' },
    { to: '/browse?cat=textile', label: en ? 'Textile' : '家纺', icon: Shirt, bg: '#F3EEFF', fg: '#7C3AED' },
  ]
})

function stripBg(p: Product) {
  if (p.image) return {}
  return { background: 'linear-gradient(145deg,#BAE6FD,#0369A1)' }
}

async function loadFeed(cat = '') {
  loading.value = true
  error.value = ''
  try {
    products.value = cat ? await listByCategory(cat) : await listProducts()
    if (!shopStrip.value.length) {
      const all = products.value.length ? products.value : await listProducts()
      shopStrip.value = all.slice(0, 8)
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
    products.value = []
  } finally {
    loading.value = false
  }
}

function filterCat(id: string) {
  activeCat.value = id
  loadFeed(id)
}

onMounted(() => loadFeed(''))
</script>

<style lang="scss" scoped>
@import '@/styles/theme.scss';
.page { min-height: 100vh; background: $hb-paper; padding-bottom: 28px; }
.sticky-top {
  position: sticky; top: 0; z-index: 20;
  background: rgba(247,244,239,0.94); backdrop-filter: blur(14px);
  padding: calc(8px + env(safe-area-inset-top)) 16px 4px;
}
.brand-row { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
.logo { font-size: 20px; font-weight: 800; color: $hb-ink; letter-spacing: -0.02em; }
.sg { font-size: 11px; font-weight: 600; color: $hb-deep; vertical-align: super; }
.tagline { font-size: 11px; color: $hb-muted; margin-top: 2px; }
.right-actions { display: flex; gap: 8px; align-items: center; }
.locale-pill {
  background: #E0F2FE; color: $hb-deep; border-radius: 999px;
  padding: 6px 10px; font-size: 11px; font-weight: 700; text-decoration: none; white-space: nowrap;
}
.icon-btn {
  position: relative;
  width: 36px; height: 36px; border-radius: 18px;
  background: $hb-white; color: $hb-ink; border: 1px solid #E8E4DC;
  display: inline-flex; align-items: center; justify-content: center;
  text-decoration: none;
}
.badge {
  position: absolute; top: -2px; right: -2px;
  min-width: 16px; height: 16px; border-radius: 999px; padding: 0 4px;
  background: $hb-price; color: #fff; font-size: 10px; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
}
.search-wrap { margin-top: 12px; }
.hero {
  margin: 12px 16px 0; border-radius: 22px; overflow: hidden;
  background: linear-gradient(115deg, #FF8A62 0%, #F96141 55%, #FFB199 100%);
  color: #fff; padding: 22px 20px 20px;
}
.hero-kicker { font-size: 11px; font-weight: 700; letter-spacing: 0.12em; }
.hero-title { font-size: 28px; font-weight: 800; margin-top: 8px; line-height: 1.15; letter-spacing: -0.03em; max-width: 16ch; }
.hero-sub { margin: 8px 0 0; font-size: 14px; opacity: 0.92; }
.hero-cta {
  display: inline-flex; margin-top: 16px; background: #fff; color: #1C2430;
  padding: 10px 16px; border-radius: 999px; font-size: 14px; font-weight: 700; text-decoration: none;
}
.body { padding: 14px 16px 0; }
.quick {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 8px;
}
.quick-item {
  display: flex; flex-direction: column; align-items: center; gap: 6px;
  color: inherit; text-decoration: none;
}
.q-ico {
  width: 56px; height: 56px; border-radius: 18px;
  display: inline-flex; align-items: center; justify-content: center;
  box-shadow: 0 6px 16px rgba(28, 36, 48, 0.04);
}
.q-lab { font-size: 10px; font-weight: 600; color: $hb-ink; text-align: center; }
.cats {
  display: flex; gap: 8px; overflow-x: auto; padding: 8px 0 12px;
  -webkit-overflow-scrolling: touch; scrollbar-width: none;
}
.cats::-webkit-scrollbar { display: none; }
.cat-pill {
  flex: 0 0 auto; border: 1px solid $hb-line; background: $hb-white;
  border-radius: 999px; padding: 8px 13px; font-size: 13px; font-weight: 650; color: $hb-ink; cursor: pointer;
  &.on { background: $hb-coral; color: #fff; border-color: $hb-coral; }
}
.sec-head { display: flex; justify-content: space-between; align-items: end; margin-bottom: 10px; }
.section-title { font-size: 16px; font-weight: 800; color: $hb-ink; }
.tiny { font-size: 11px; color: $hb-muted; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.state { text-align: center; color: $hb-muted; padding: 40px 8px; font-size: 14px; }
.state.err { color: $hb-coral; }
.shop-strip { margin-top: 18px; }
.shop-strip .section-title { margin-bottom: 10px; }
.strip { display: flex; gap: 10px; overflow-x: auto; padding-bottom: 8px; -webkit-overflow-scrolling: touch; scrollbar-width: none; }
.strip::-webkit-scrollbar { display: none; }
.strip-card { width: 120px; flex-shrink: 0; text-decoration: none; color: inherit; }
.strip-thumb {
  height: 100px; border-radius: 12px; overflow: hidden; background: #E2E6EE;
  img { width: 100%; height: 100%; object-fit: cover; display: block; }
}
.strip-name { font-size: 12px; font-weight: 600; margin-top: 6px; color: $hb-ink; line-height: 1.3; height: 32px; overflow: hidden; }
.strip-price { font-size: 13px; font-weight: 700; color: $hb-price; margin-top: 2px; }

.fn-page { --ink:#0F2744; --teal:#0E7490; --amber:#B45309; --sand:#F7F4EF; }
</style>
