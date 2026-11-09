<template>
  <div class="fn-page page" data-figma="M01">
    <header class="sticky-top">
      <div class="brand-row">
        <div class="brand">
          <span class="brand-ico" aria-hidden="true"><Home :size="22" :stroke-width="2" /></span>
          <div>
            <div class="logo">Pimo</div>
            <div class="tagline">Better Homes. Happier Days.</div>
          </div>
        </div>
        <router-link class="locale-pill" to="/locale">{{ localeLabel }}</router-link>
      </div>
      <div class="search-wrap">
        <AppSearchBar :placeholder="searchPh" navigate-on-focus />
      </div>
    </header>

    <section class="hero">
      <div class="hero-kicker">LIMITED TIME</div>
      <div class="hero-title">Up to 50% Off Home Essentials</div>
      <router-link class="hero-cta" to="/sale">Shop Sale</router-link>
    </section>

    <div class="body">
      <div class="cat-tiles">
        <router-link class="tile" :to="{ path: '/browse', query: { cat: 'kitchen' } }">
          <span class="tile-ico">🍳</span>
          <span class="tile-lab">Kitchen</span>
        </router-link>
        <router-link class="tile" :to="{ path: '/browse', query: { cat: 'storage' } }">
          <span class="tile-ico">📦</span>
          <span class="tile-lab">Storage</span>
        </router-link>
        <router-link class="tile" :to="{ path: '/browse', query: { cat: 'cleaning' } }">
          <span class="tile-ico">🧹</span>
          <span class="tile-lab">Cleaning</span>
        </router-link>
        <router-link class="tile" :to="{ path: '/browse', query: { cat: 'textile' } }">
          <span class="tile-ico">🛏️</span>
          <span class="tile-lab">Textile</span>
        </router-link>
      </div>

      <div v-if="flashStrip.length" class="flash-block">
        <div class="sec-head">
          <div class="section-title">Flash deals</div>
          <router-link class="see-all" to="/ship-lp">See all</router-link>
        </div>
        <div class="strip">
          <router-link v-for="p in flashStrip" :key="'f'+p.sku" class="strip-card" :to="{ path: '/pdp', query: { sku: p.sku } }">
            <div class="strip-thumb" :style="stripBg(p)">
              <img v-if="p.image" :src="p.image" alt="" />
            </div>
            <div class="strip-name">{{ p.name }}</div>
            <div class="strip-price">{{ money(p.price) }}</div>
          </router-link>
        </div>
      </div>

      <div class="sec-head">
        <div class="section-title">New arrivals</div>
        <router-link class="see-all" to="/new">See all</router-link>
      </div>
      <div v-if="newStrip.length" class="strip new-strip">
        <router-link v-for="p in newStrip" :key="'n'+p.sku" class="strip-card" :to="{ path: '/pdp', query: { sku: p.sku } }">
          <div class="strip-thumb" :style="stripBg(p)">
            <img v-if="p.image" :src="p.image" alt="" />
            <span class="new-tag">New</span>
          </div>
          <div class="strip-name">{{ p.name }}</div>
          <div class="strip-price">{{ money(p.price) }}</div>
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
        <div class="section-title">Just for you</div>
        <div class="tiny">{{ t('personalized_note') || 'Personalized picks' }}</div>
      </div>

      <div v-if="loading" class="state">{{ t('pdp_loading') }}</div>
      <div v-else-if="error" class="state err">{{ error }}</div>
      <div v-else-if="!products.length" class="state">{{ t('no_products') || 'No products' }}</div>
      <div v-else class="grid">
        <ProductCard v-for="p in products" :key="p.sku" :product="p" />
      </div>
    </div>
    <AppTabBar active="home" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Home, Percent, Sparkles, Zap, CalendarCheck, Ticket, Wallet, Gift, Heart, Package, LifeBuoy } from 'lucide-vue-next'
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

const flashStrip = computed(() => {
  const src = shopStrip.value.length ? shopStrip.value : products.value
  const flash = src.filter((p) => p.tag === 'Flash' || (p.offPct && p.offPct > 0))
  return (flash.length ? flash : src).slice(0, 8)
})

const newStrip = computed(() => {
  const src = shopStrip.value.length ? shopStrip.value : products.value
  const fresh = src.filter((p) => p.tag === 'New')
  return (fresh.length ? fresh : src.slice().reverse()).slice(0, 8)
})

const quickLinks = computed(() => {
  const en = lang.value === 'en'
  return [
    { to: '/sale', label: en ? 'Sale' : '特卖', icon: Percent, bg: '#FFF1EC', fg: '#FF6B4A' },
    { to: '/new', label: en ? 'New' : '新品', icon: Sparkles, bg: '#FFF1EC', fg: '#F04E32' },
    { to: '/ship-lp', label: en ? 'Flash' : '闪购', icon: Zap, bg: '#F4F7FB', fg: '#FF6B4A' },
    { to: '/coupons', label: en ? 'Coupons' : '优惠券', icon: Ticket, bg: '#FFF1EC', fg: '#1B2B4A' },
    { to: '/checkin', label: en ? 'Check-in' : '签到', icon: CalendarCheck, bg: '#F4F7FB', fg: '#1B2B4A' },
    { to: '/balance', label: en ? 'Balance' : '余额', icon: Wallet, bg: '#FFF1EC', fg: '#FF6B4A' },
    { to: '/invite', label: en ? 'Invite' : '邀请', icon: Gift, bg: '#F4F7FB', fg: '#16A34A' },
    { to: '/wishlist', label: en ? 'Wishlist' : '愿望单', icon: Heart, bg: '#F4F7FB', fg: '#1B2B4A' },
    { to: '/orders', label: en ? 'Orders' : '订单', icon: Package, bg: '#FFF1EC', fg: '#F04E32' },
    { to: '/help', label: en ? 'Help' : '帮助', icon: LifeBuoy, bg: '#F4F7FB', fg: '#1B2B4A' },
  ]
})

function stripBg(p: Product) {
  if (p.image) return {}
  return { background: 'linear-gradient(145deg,#FFF1EC,#FF6B4A)' }
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
  background: rgba(244, 247, 251, 0.94); backdrop-filter: blur(14px);
  padding: calc(8px + env(safe-area-inset-top)) 16px 12px;
}
.brand-row { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
.brand { display: flex; align-items: center; gap: 10px; }
.brand-ico {
  width: 40px; height: 40px; border-radius: 12px;
  background: $hb-coral-soft; color: $hb-coral;
  display: inline-flex; align-items: center; justify-content: center;
}
.logo { font-size: 20px; font-weight: 800; color: $hb-ink; letter-spacing: -0.02em; line-height: 1.1; }
.tagline { font-size: 11px; color: $hb-muted; margin-top: 2px; }
.locale-pill {
  background: $hb-white; color: $hb-ink; border: 1px solid $hb-line; border-radius: 999px;
  padding: 6px 10px; font-size: 11px; font-weight: 700; text-decoration: none; white-space: nowrap;
}
.search-wrap { margin-top: 12px; }
.hero {
  margin: 12px 16px 0; border-radius: $hb-radius-md; overflow: hidden;
  background: linear-gradient(125deg, $hb-coral 0%, $hb-coral-deep 100%);
  color: #fff; padding: 20px 18px;
  box-shadow: $hb-shadow-soft;
}
.hero-kicker { font-size: 11px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; opacity: 0.92; }
.hero-title { font-size: 22px; font-weight: 800; margin-top: 8px; line-height: 1.25; }
.hero-cta {
  display: inline-flex; margin-top: 16px; background: #fff; color: $hb-ink;
  padding: 10px 18px; border-radius: 999px; font-size: 13px; font-weight: 700; text-decoration: none;
}
.body { padding: 16px 16px 0; }
.cat-tiles {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 20px;
}
.tile {
  display: flex; flex-direction: column; align-items: center; gap: 8px;
  background: $hb-white; border-radius: $hb-radius-sm; padding: 12px 6px;
  border: 1px solid $hb-line; text-decoration: none; color: inherit;
  box-shadow: $hb-shadow-soft;
}
.tile-ico { font-size: 22px; line-height: 1; }
.tile-lab { font-size: 11px; font-weight: 700; color: $hb-ink; text-align: center; }
.sec-head { display: flex; justify-content: space-between; align-items: end; margin-bottom: 10px; gap: 8px; }
.section-title { font-size: 16px; font-weight: 800; color: $hb-ink; }
.see-all { font-size: 12px; font-weight: 650; color: $hb-coral; text-decoration: none; flex-shrink: 0; }
.tiny { font-size: 11px; color: $hb-muted; }
.flash-block { margin-bottom: 18px; }
.strip { display: flex; gap: 10px; overflow-x: auto; padding-bottom: 8px; margin-bottom: 18px; -webkit-overflow-scrolling: touch; scrollbar-width: none; }
.strip::-webkit-scrollbar { display: none; }
.strip-card { width: 120px; flex-shrink: 0; text-decoration: none; color: inherit; }
.strip-thumb {
  height: 100px; border-radius: $hb-radius-sm; overflow: hidden; background: $hb-coral-soft; position: relative;
  img { width: 100%; height: 100%; object-fit: cover; display: block; }
}
.new-tag {
  position: absolute; left: 6px; top: 6px; font-size: 10px; font-weight: 700;
  background: $hb-coral; color: #fff; padding: 3px 7px; border-radius: 999px;
}
.strip-name { font-size: 12px; font-weight: 600; margin-top: 6px; color: $hb-ink; line-height: 1.3; height: 32px; overflow: hidden; }
.strip-price { font-size: 13px; font-weight: 700; color: $hb-price; margin-top: 2px; }
.cats {
  display: flex; gap: 8px; overflow-x: auto; padding: 4px 0 12px;
  -webkit-overflow-scrolling: touch; scrollbar-width: none;
}
.cats::-webkit-scrollbar { display: none; }
.cat-pill {
  flex: 0 0 auto; border: 1px solid $hb-line; background: $hb-white;
  border-radius: 999px; padding: 8px 13px; font-size: 13px; font-weight: 650; color: $hb-ink; cursor: pointer;
  &.on { background: $hb-coral; color: #fff; border-color: $hb-coral; }
}
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.state { text-align: center; color: $hb-muted; padding: 40px 8px; font-size: 14px; }
.state.err { color: $hb-coral-deep; }

.fn-page { --ink:#1B2B4A; --teal:#FF6B4A; --amber:#FF6B4A; --sand:#F4F7FB; }
</style>
