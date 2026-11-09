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
      <router-link class="locale" to="/locale">
        <span>{{ localeFlag }}</span>
        <span>{{ localeCode }}</span>
        <ChevronDown :size="14" :stroke-width="2.2" />
      </router-link>
    </header>

    <button v-if="isHold" type="button" class="cta" style="margin:12px 0" @click="lockHold">{{ holdNote || (zh ? '锁定这件的价格' : 'Lock a price') }}</button>
    <div class="search-wrap">
      <AppSearchBar :placeholder="zh ? '搜索家居好物...' : 'Search home essentials...'" navigate-on-focus />
    </div>

    <section class="hero">
      <div class="hero-copy">
        <div class="kicker">{{ slides[slideIndex].kicker }}</div>
        <h1>{{ slides[slideIndex].title }}</h1>
        <p>{{ slides[slideIndex].body }}</p>
        <router-link class="cta" :to="slides[slideIndex].to">{{ slides[slideIndex].cta }} →</router-link>
        <div class="dots">
          <button v-for="(slide, i) in slides" :key="slide.kicker" type="button" :class="{ on: i === slideIndex }" @click="slideIndex = i" />
        </div>
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
        <router-link class="clock" to="/flash" aria-label="flash">
          <Clock :size="14" :stroke-width="2" />
          <span><b>02</b><small>{{ zh ? '时' : 'HRS' }}</small></span>
          <span><b>18</b><small>{{ zh ? '分' : 'MIN' }}</small></span>
          <span><b>36</b><small>{{ zh ? '秒' : 'SEC' }}</small></span>
        </router-link>
      </div>
      <div class="row">
        <article v-for="item in flash" :key="item.sku" class="mini" @click="openSku(item.sku)">
          <div class="shot">
            <img :src="item.image" alt="" />
            <span class="range">$1-$10</span>
          </div>
          <div class="nm">{{ item.name }}</div>
          <div class="pr">
            <b>{{ money(item.price) }}</b>
            <button type="button" class="bag" aria-label="Add to cart" @click.stop="addSku(item)"><ShoppingCart :size="14" /></button>
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
        <article v-for="item in arrivals" :key="item.sku" class="mini" @click="openSku(item.sku)">
          <div class="shot">
            <img :src="item.image" alt="" />
            <span class="range">$1-$10</span>
          </div>
          <div class="nm">{{ item.name }}</div>
          <div class="pr">
            <b>{{ money(item.price) }}</b>
            <button type="button" class="bag" aria-label="Add to cart" @click.stop="addSku(item)"><ShoppingCart :size="14" /></button>
          </div>
        </article>
      </div>
    </section>

    <section class="block">
      <div class="sec">
        <div>
          <div class="sec-title"><UserRound :size="16" class="who" /> {{ zh ? '为你推荐' : 'Just for You' }}</div>
          <div class="sec-sub">{{ zh ? '按你的喜好挑选。' : 'Based on your interests.' }}</div>
        </div>
      </div>
      <div v-if="error" class="state err">{{ error }}</div>
      <div class="pair">
        <article v-for="item in picks" :key="item.sku" class="wide" @click="openSku(item.sku)">
          <div class="shot tall">
            <img :src="item.image" alt="" />
            <span class="range">$1-$10</span>
            <span class="sold">{{ zh ? '已售' : 'Sold' }}</span>
          </div>
          <div class="nm">{{ item.name }}</div>
          <div class="stars">★★★★★</div>
          <div class="pr">
            <b>{{ money(item.price) }}</b>
            <button type="button" class="bag" aria-label="Add to cart" @click.stop="addSku(item)"><ShoppingCart :size="14" /></button>
          </div>
        </article>
      </div>
    </section>

    <AppTabBar active="home" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Home, ChevronDown, Utensils, Archive, SprayCan, Shirt, Zap, Clock, Sparkles, UserRound, ShoppingCart } from 'lucide-vue-next'
import { listProducts, listByCategory, money, type Product } from '@/api/products'
import { apiRoot } from '@/api/config'
import { useI18n } from '@/composables/i18n'
import { useCart } from '@/composables/cart'
import AppTabBar from '@/components/AppTabBar.vue'
import AppSearchBar from '@/components/AppSearchBar.vue'
import heroPhoto from '@/assets/home/hero-photo.jpg'

const { t, lang } = useI18n()
const zh = computed(() => String(lang.value).startsWith('zh'))
const cart = useCart()
const route = useRoute()
const router = useRouter()
const isHold = computed(() => route.name === 'hold')
const holdNote = ref('')
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

const slideIndex = ref(0)
const slides = computed(() => zh.value
  ? [
      { kicker: '限时', title: '家居好物最高 5 折', body: '把家里刷新一下，少花一点。', cta: '去抢购', to: '/sale' },
      { kicker: '闪购', title: '今天的限时货架', body: '倒计时结束前去看看。', cta: '看闪购', to: '/flash' },
      { kicker: '新品', title: '刚到的家居小物', body: '从新品列表开始逛。', cta: '看新品', to: '/new' },
      { kicker: '搜索', title: '找一件家里用得上的', body: '厨房、收纳、清洁都能搜。', cta: '去搜索', to: '/search' },
    ]
  : [
      { kicker: 'LIMITED TIME', title: 'Up to 50% Off Home Essentials', body: 'Refresh your space, for less.', cta: 'Shop Sale', to: '/sale' },
      { kicker: 'FLASH', title: 'Today’s limited shelf', body: 'Open the flash aisle before the clock ends.', cta: 'Shop flash', to: '/flash' },
      { kicker: 'NEW', title: 'Just landed', body: 'Start with the new arrivals.', cta: 'See new', to: '/new' },
      { kicker: 'SEARCH', title: 'Find something the house uses', body: 'Kitchen, storage, and cleaning.', cta: 'Search', to: '/search' },
    ])
const flash = computed(() => products.value.slice(0, 4))
const arrivals = computed(() => products.value.slice(4, 8))
const picks = computed(() => products.value.slice(8, 10))

function openSku(sku: string) {
  if (sku) router.push({ path: '/pdp', query: { sku } })
}

async function addSku(item: Product) {
  await cart.addServer(item, 'default', 1)
}

async function lockHold() {
  const sku = products.value[0]?.sku || ''
  const body = new URLSearchParams()
  if (sku) body.set('sku', sku)
  const res = await fetch(apiRoot().replace(/\/$/, '') + '/hold', {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded', Accept: 'application/json' },
    body,
  })
  const data = await res.json().catch(() => ({}))
  holdNote.value = data.ok ? (zh.value ? '价格已锁定' : 'Price locked') : (zh.value ? '现在不能锁定' : 'Could not lock a price')
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
  margin-top: 10px; position: relative; min-height: 168px;
  border-radius: 16px; overflow: hidden; color: #fff;
  background: linear-gradient(105deg, #F97855 0%, #F96141 42%, #F7B39A 100%);
}
.hero-copy { position: relative; z-index: 1; padding: 14px 14px 12px; max-width: 58%; }
.kicker { font-size: 10px; font-weight: 800; letter-spacing: 0.12em; text-transform: uppercase; }
.hero h1 { margin: 4px 0 0; font-size: 22px; line-height: 1.1; letter-spacing: -0.03em; font-weight: 800; }
.hero p { margin: 4px 0 0; font-size: 12px; line-height: 1.3; opacity: 0.95; }
.cta {
  display: inline-flex; align-items: center; margin-top: 8px; background: #fff; color: #F96141;
  height: 32px; border-radius: 999px; padding: 0 12px; font-size: 13px; font-weight: 700;
}
.dots { display: flex; gap: 4px; margin-top: 8px; }
.dots button { width: 6px; height: 6px; border: 0; border-radius: 99px; background: rgba(255,255,255,0.45); padding: 0; cursor: pointer; }
.dots button.on { width: 14px; background: #fff; }
.hero-photo {
  position: absolute; right: 0; top: 0; height: 100%; width: auto; max-width: 46%;
  object-fit: contain; object-position: right center;
  mask-image: linear-gradient(90deg, transparent, #000 18%);
}
.cats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-top: 10px; }
.cat {
  background: #fff; border-radius: 14px; padding: 8px 4px 8px;
  display: flex; flex-direction: column; align-items: center; gap: 4px;
  border: 1px solid #F1EEEA; box-shadow: none; color: #1C2430;
  font-size: 11px; font-weight: 700; line-height: 1.2;
}
.bubble {
  width: 36px; height: 36px; border-radius: 999px;
  display: inline-flex; align-items: center; justify-content: center;
}
.block { margin-top: 20px; }
.sec { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.sec-title { display: flex; align-items: center; gap: 4px; font-size: 18px; font-weight: 800; letter-spacing: -0.03em; line-height: 1; }
.sec-sub { margin-top: 3px; font-size: 12px; line-height: 1.3; color: #8E949C; }
.zap, .spark, .who { color: #F96141; }
.see { color: #F96141; font-size: 13px; font-weight: 700; line-height: 1; padding-top: 0; }
.clock {
  display: flex; align-items: center; gap: 3px; color: #F96141;
  background: transparent; padding: 0; text-decoration: none;
}
.clock span {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  line-height: 1; background: #FFF1EC; border-radius: 8px; min-width: 28px; height: 32px; padding: 0 4px;
}
.clock b { font-size: 13px; font-weight: 800; color: #F96141; letter-spacing: -0.03em; }
.clock small { font-size: 7px; letter-spacing: 0.02em; color: #F96141; margin-top: 2px; font-weight: 700; }
.row { display: flex; gap: 12px; overflow-x: auto; margin-top: 10px; padding-bottom: 2px; scrollbar-width: none; }
.row::-webkit-scrollbar { display: none; }
.mini, .wide { flex: 0 0 164px; cursor: pointer; }
.shot { position: relative; border-radius: 16px; overflow: hidden; background: #F4F1EE; aspect-ratio: 1; border: 0; box-shadow: 0 8px 18px rgba(28,36,48,0.06); }
.shot img { width: 100%; height: 100%; object-fit: cover; object-position: center; display: block; }
.range {
  position: absolute; left: 10px; top: 10px; height: 18px; display: inline-flex; align-items: center;
  background: #fff; color: #F96141; font-size: 10px; font-weight: 800; letter-spacing: 0; border-radius: 999px; padding: 0 7px;
}
.sold {
  position: absolute; left: 10px; bottom: 8px; height: 18px; display: inline-flex; align-items: center;
  background: #fff; color: #F96141; font-size: 10px; font-weight: 800; border-radius: 999px; padding: 0 7px;
}
.nm {
  margin-top: 8px; font-size: 13px; font-weight: 650; line-height: 1.3; min-height: 2.6em; color: #1C2430;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.pr { display: flex; align-items: center; margin-top: 4px; min-height: 26px; }
.pr b { color: #F96141; font-size: 16px; font-weight: 800; letter-spacing: -0.03em; }
.bag {
  margin-left: auto; width: 26px; height: 26px; border: 0; border-radius: 999px;
  background: #FFF1EC; color: #F96141; display: inline-flex; align-items: center; justify-content: center; cursor: pointer;
}
.pair { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 10px; }
.wide { flex: none; }
.shot.tall { aspect-ratio: 334 / 130; }
.stars { margin-top: 2px; color: #F5B400; font-size: 11px; letter-spacing: 1px; line-height: 1; }
.stars span { color: #8E949C; letter-spacing: 0; margin-left: 4px; }
.state { color: #8E949C; font-size: 13px; }
.state.err { color: #E11D2E; }
</style>
