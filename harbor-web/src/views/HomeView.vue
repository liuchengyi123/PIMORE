<template>
  <div class="home" data-figma="1:5">
    <header class="top">
      <div class="brand">
        <span class="mark" aria-hidden="true"><Home :size="18" :stroke-width="2.2" /></span>
        <div>
          <div class="logo">Pimo</div>
          <div class="tagline">{{ zh ? '更好的家，更开心的一天' : 'Better Homes. Happier Days.' }}</div>
        </div>
      </div>
      <router-link class="locale" :to="{ path: '/home', query: { locale: '1' } }">
        <span>{{ localeFlag }}</span>
        <span>{{ localeCode }}</span>
        <ChevronDown :size="14" :stroke-width="2.2" />
      </router-link>
    </header>

    <div class="search-wrap">
      <AppSearchBar :placeholder="zh ? '搜索家居好物...' : 'Search home essentials...'" navigate-on-focus />
    </div>

    <section class="hero">
      <div class="hero-copy">
        <div class="kicker">{{ zh ? '限时' : 'LIMITED TIME' }}</div>
        <h1>{{ zh ? '家居好物最高 5 折' : 'Up to 50% Off Home Essentials' }}</h1>
        <p>{{ zh ? '把家里刷新一下，少花一点。' : 'Refresh your space, for less.' }}</p>
        <router-link class="cta" to="/sale">{{ zh ? '去抢购' : 'Shop Sale' }} →</router-link>
        <div class="dots" aria-hidden="true"><i class="on" /><i /><i /><i /></div>
      </div>
      <img class="hero-photo" :src="heroPhoto" alt="" />
    </section>

    <div class="cats">
      <router-link v-for="q in quickLinks" :key="q.to" class="cat" :to="q.to">
        <span class="bubble" :style="{ background: q.bg, color: q.fg }">
          <component :is="q.icon" :size="18" :stroke-width="1.9" />
        </span>
        <span>{{ q.label }}</span>
      </router-link>
    </div>

    <section class="block">
      <div class="sec">
        <div>
          <div class="sec-title"><Zap :size="16" :stroke-width="2.2" class="zap" /> {{ zh ? '限时特惠' : 'Flash Deals' }}</div>
          <div class="sec-sub">{{ zh ? '省一笔，时间有限。' : 'Big savings. Limited time.' }}</div>
        </div>
        <div class="clock" aria-label="02:18:36">
          <Clock :size="14" :stroke-width="2" />
          <span><b>02</b><small>{{ zh ? '时' : 'HRS' }}</small></span>
          <span><b>18</b><small>{{ zh ? '分' : 'MIN' }}</small></span>
          <span><b>36</b><small>{{ zh ? '秒' : 'SEC' }}</small></span>
        </div>
      </div>
      <div class="row">
        <article v-for="(item, i) in flash" :key="item.name" class="mini" @click="openSlot(i)">
          <div class="shot">
            <img :src="item.image" alt="" />
            <span class="range">$1–$10</span>
          </div>
          <div class="nm">{{ item.name }}</div>
          <div class="pr">
            <b>{{ money(item.price) }}</b>
            <button type="button" class="bag" aria-label="Add to cart" @click.stop="addSlot(item, i)"><ShoppingCart :size="14" /></button>
          </div>
        </article>
      </div>
    </section>

    <section class="block">
      <div class="sec">
        <div>
          <div class="sec-title"><Sparkles :size="16" class="spark" /> {{ zh ? '新品' : 'New Arrivals' }}</div>
          <div class="sec-sub">{{ zh ? '刚到的家居好物。' : 'Fresh finds for your home.' }}</div>
        </div>
        <router-link class="see" to="/new">{{ zh ? '查看全部' : 'See All' }} →</router-link>
      </div>
      <div class="row">
        <article v-for="(item, i) in arrivals" :key="item.name" class="mini" @click="openSlot(i + 4)">
          <div class="shot">
            <img :src="item.image" alt="" />
            <span class="range">$1–$10</span>
          </div>
          <div class="nm">{{ item.name }}</div>
          <div class="pr">
            <b>{{ money(item.price) }}</b>
            <button type="button" class="bag" aria-label="Add to cart" @click.stop="addSlot(item, i + 4)"><ShoppingCart :size="14" /></button>
          </div>
        </article>
      </div>
    </section>

    <section class="block">
      <div class="sec">
        <div>
          <div class="sec-title"><UserRound :size="16" /> {{ zh ? '为你推荐' : 'Just for You' }}</div>
          <div class="sec-sub">{{ zh ? '按你的喜好挑选。' : 'Based on your interests.' }}</div>
        </div>
      </div>
      <div v-if="error" class="state err">{{ error }}</div>
      <div class="pair">
        <article v-for="(item, i) in picks" :key="item.name" class="wide" @click="openSlot(i + 8)">
          <div class="shot tall">
            <img :src="item.image" alt="" />
            <span class="range">$1–$10</span>
          </div>
          <div class="nm">{{ item.name }}</div>
          <div class="stars">★★★★★ <span>({{ item.reviews }})</span></div>
          <div class="pr">
            <b>{{ money(item.price) }}</b>
            <button type="button" class="bag" aria-label="Add to cart" @click.stop="addSlot(item, i + 8)"><ShoppingCart :size="14" /></button>
          </div>
        </article>
      </div>
    </section>

    <AppTabBar active="home" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Home, ChevronDown, Utensils, Archive, SprayCan, Shirt, Zap, Clock, Sparkles, UserRound, ShoppingCart } from 'lucide-vue-next'
import { listProducts, listByCategory, money, type Product } from '@/api/products'
import { useI18n } from '@/composables/i18n'
import { useCart } from '@/composables/cart'
import AppTabBar from '@/components/AppTabBar.vue'
import AppSearchBar from '@/components/AppSearchBar.vue'
import heroPhoto from '@/assets/home/hero-photo.jpg'
import flash1 from '@/assets/home/flash-1.jpg'
import flash2 from '@/assets/home/flash-2.jpg'
import flash3 from '@/assets/home/flash-3.jpg'
import flash4 from '@/assets/home/flash-4.jpg'
import neu1 from '@/assets/home/new-1.jpg'
import neu2 from '@/assets/home/new-2.jpg'
import neu3 from '@/assets/home/new-3.jpg'
import neu4 from '@/assets/home/new-4.jpg'
import just1 from '@/assets/home/just-1.jpg'
import just2 from '@/assets/home/just-2.jpg'

const { t, lang } = useI18n()
const zh = computed(() => String(lang.value).startsWith('zh'))
const cart = useCart()
const router = useRouter()
const products = ref<Product[]>([])
const error = ref('')

const searchPh = computed(() =>
  lang.value === 'en' ? 'Search home essentials...' : (t('home_search_ph') || '搜索家居好物...')
)
const localeFlag = computed(() => ({ en: '🇺🇸', zh: '🇨🇳', 'zh-Hant': '🇹🇼', ja: '🇯🇵', de: '🇩🇪' }[lang.value] || '🇺🇸'))
const localeCode = computed(() => ({ en: 'US', zh: 'CN', 'zh-Hant': 'TW', ja: 'JP', de: 'DE' }[lang.value] || 'US'))

const quickLinks = computed(() => {
  return [
    { to: '/browse?cat=kitchen', label: zh.value ? '厨房' : 'Kitchen', icon: Utensils, bg: '#FFF1EC', fg: '#F96141' },
    { to: '/browse?cat=storage', label: zh.value ? '收纳' : 'Storage', icon: Archive, bg: '#E8F8EF', fg: '#1F9D62' },
    { to: '/browse?cat=cleaning', label: zh.value ? '清洁' : 'Cleaning', icon: SprayCan, bg: '#E7F2FF', fg: '#3B82F6' },
    { to: '/browse?cat=textile', label: zh.value ? '家纺' : 'Textile', icon: Shirt, bg: '#F3EEFF', fg: '#8B5CF6' },
  ]
})

const flash = [
  { sku: 'glass-food-storage', name: 'Glass Food Storage Set', price: 6.99, image: flash1 },
  { sku: 'dish-drying-rack', name: 'Foldable Dish Drying Rack', price: 7.99, image: flash2 },
  { sku: 'spray-bottles', name: 'Multipurpose Spray Bottles (2)', price: 3.99, image: flash3 },
  { sku: 'microfiber-cloths', name: 'Microfiber Cleaning Cloths (5)', price: 4.99, image: flash4 },
]
const arrivals = [
  { sku: 'rolling-cart', name: '3-Tier Rolling Cart', price: 8.99, image: neu1 },
  { sku: 'throw-blanket', name: 'Lightweight Throw Blanket', price: 5.99, image: neu2 },
  { sku: 'storage-bins', name: 'Stackable Storage Bins (3)', price: 7.49, image: neu3 },
  { sku: 'utensil-set', name: 'Silicone Utensil Set (5 pcs)', price: 4.99, image: neu4 },
]
const picks = [
  { sku: 'desk-organizer', name: 'Desk Organizer', price: 6.49, image: just1, reviews: 428 },
  { sku: 'bath-towels', name: 'Quick-Dry Bath Towels', price: 8.99, image: just2, reviews: 612 },
]

function asProduct(item: { sku: string; name: string; price: number; image: string }, live?: Product): Product {
  if (live) return live
  return { id: item.sku, sku: item.sku, name: item.name, price: item.price, category: 'home', image: item.image }
}

function openSlot(index: number) {
  const live = products.value[index]
  if (live) router.push({ path: '/pdp', query: { sku: live.sku } })
  else router.push('/browse')
}

function addSlot(item: { sku: string; name: string; price: number; image: string }, index: number) {
  cart.add(asProduct(item, products.value[index]))
}

onMounted(async () => {
  try {
    products.value = await listProducts()
    if (!products.value.length) products.value = await listByCategory('')
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  }
})
</script>

<style lang="scss" scoped>
.home {
  min-height: 100vh;
  background: #FDFBF9;
  color: #1C2430;
  padding: 16px 16px 8px;
  font-family: "Plus Jakarta Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
.top { display: flex; align-items: center; justify-content: space-between; }
.brand { display: flex; align-items: center; gap: 8px; }
.mark {
  width: 32px; height: 32px; border-radius: 10px; background: #F96141; color: #fff;
  display: inline-flex; align-items: center; justify-content: center;
}
.logo { font-size: 24px; font-weight: 800; letter-spacing: -0.04em; line-height: 1; }
.tagline { margin-top: 2px; font-size: 11px; color: #8E949C; }
.locale {
  display: inline-flex; align-items: center; gap: 4px;
  height: 32px; padding: 0 10px; border-radius: 999px;
  background: #fff; border: 1px solid #EEEAE6; color: #1C2430;
  font-size: 13px; font-weight: 700;
}
.search-wrap { margin-top: 14px; }
.search-wrap :deep(.search-bar) {
  min-height: 44px; border-radius: 999px; background: #fff; border: 1px solid #EFEAE4; box-shadow: none;
}
.hero {
  margin-top: 14px; position: relative; min-height: 196px;
  border-radius: 22px; overflow: hidden; color: #fff;
  background: linear-gradient(105deg, #F97855 0%, #F96141 42%, #F7B39A 100%);
}
.hero-copy { position: relative; z-index: 1; padding: 20px 18px 18px; max-width: 56%; }
.kicker { font-size: 10px; font-weight: 800; letter-spacing: 0.14em; text-transform: uppercase; }
.hero h1 { margin: 6px 0 0; font-size: 28px; line-height: 1.08; letter-spacing: -0.03em; font-weight: 800; }
.hero p { margin: 6px 0 0; font-size: 13px; line-height: 1.35; opacity: 0.95; }
.cta {
  display: inline-flex; align-items: center; margin-top: 12px; background: #fff; color: #1C2430;
  height: 34px; border-radius: 999px; padding: 0 14px; font-size: 13px; font-weight: 700;
}
.dots { display: flex; gap: 5px; margin-top: 12px; }
.dots i { width: 6px; height: 6px; border-radius: 99px; background: rgba(255,255,255,0.45); display: block; }
.dots i.on { width: 14px; background: #fff; }
.hero-photo {
  position: absolute; right: 0; top: 0; height: 100%; width: 50%;
  object-fit: cover; object-position: 70% center;
}
.cats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-top: 14px; }
.cat {
  background: #fff; border-radius: 18px; padding: 14px 4px 12px;
  display: flex; flex-direction: column; align-items: center; gap: 8px;
  border: 0; box-shadow: 0 6px 16px rgba(28,36,48,0.05); color: #1C2430;
  font-size: 12px; font-weight: 650;
}
.bubble {
  width: 40px; height: 40px; border-radius: 999px;
  display: inline-flex; align-items: center; justify-content: center;
}
.block { margin-top: 20px; }
.sec { display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; }
.sec-title { display: flex; align-items: center; gap: 6px; font-size: 17px; font-weight: 800; letter-spacing: -0.02em; }
.sec-sub { margin-top: 2px; font-size: 12px; color: #8E949C; }
.zap, .spark { color: #F96141; }
.see { color: #F96141; font-size: 13px; font-weight: 700; padding-top: 4px; }
.clock {
  display: flex; align-items: center; gap: 4px; color: #F96141;
  background: transparent; padding: 0;
}
.clock span { display: flex; flex-direction: column; align-items: center; line-height: 1; background: #FFF1EC; border-radius: 8px; min-width: 32px; padding: 4px 5px; }
.clock b { font-size: 13px; }
.clock small { font-size: 8px; letter-spacing: 0.04em; color: #C47A68; }
.row { display: flex; gap: 12px; overflow-x: auto; margin-top: 10px; padding-bottom: 4px; scrollbar-width: none; }
.row::-webkit-scrollbar { display: none; }
.mini, .wide { flex: 0 0 164px; cursor: pointer; }
.shot { position: relative; border-radius: 16px; overflow: hidden; background: #F4F1EE; aspect-ratio: 1; border: 0; box-shadow: 0 8px 18px rgba(28,36,48,0.06); }
.shot img { width: 100%; height: 100%; object-fit: cover; object-position: center; display: block; }
.range {
  position: absolute; left: 8px; top: 8px; background: #fff; color: #F96141;
  font-size: 11px; font-weight: 800; border-radius: 999px; padding: 3px 7px;
}
.nm { margin-top: 8px; font-size: 13px; font-weight: 650; line-height: 1.3; min-height: 2.6em; color: #1C2430; }
.pr { display: flex; align-items: center; margin-top: 4px; }
.pr b { color: #F96141; font-size: 15px; }
.bag {
  margin-left: auto; width: 28px; height: 28px; border: 0; border-radius: 999px;
  background: #FFF1EC; color: #F96141; display: inline-flex; align-items: center; justify-content: center; cursor: pointer;
}
.pair { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 12px; }
.wide { flex: none; }
.shot.tall { aspect-ratio: 2.5; }
.stars { margin-top: 4px; color: #F5B400; font-size: 11px; letter-spacing: 1px; }
.stars span { color: #8E949C; letter-spacing: 0; margin-left: 4px; }
.state { color: #8E949C; font-size: 13px; }
.state.err { color: #E11D2E; }
</style>
