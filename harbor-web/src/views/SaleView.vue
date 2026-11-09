<template>
  <div class="page" data-figma="1:15">
    <header class="top">
      <router-link to="/home" class="brand">
        <span class="mark" aria-hidden="true"><Home :size="16" :stroke-width="2.2" /></span>
        <span>
          <span class="logo">Harbor</span>
          <span class="tag">{{ zh ? '小物见喜' : 'Small finds. Big joy.' }}</span>
        </span>
      </router-link>
      <div class="tools">
        <router-link to="/search" aria-label="搜索"><Search :size="22" /></router-link>
        <router-link to="/cart" class="cart" aria-label="购物车">
          <ShoppingCart :size="22" />
          <i v-if="count">{{ count > 99 ? '99+' : count }}</i>
        </router-link>
      </div>
    </header>

    <section class="hero">
      <div class="copy">
        <div class="script">{{ zh ? '今日' : "Today's" }}</div>
        <div class="deals">{{ zh ? '特惠' : 'DEALS' }}</div>
        <p>{{ zh ? '家居好物，低价入手。限时开抢。' : 'Top home goods. Low prices. Limited time only.' }}</p>
        <div class="ticks" aria-label="countdown">
          <div><b>{{ parts[0] }}</b><small>{{ zh ? '时' : 'HRS' }}</small></div>
          <span>:</span>
          <div><b>{{ parts[1] }}</b><small>{{ zh ? '分' : 'MIN' }}</small></div>
          <span>:</span>
          <div><b>{{ parts[2] }}</b><small>{{ zh ? '秒' : 'SEC' }}</small></div>
        </div>
      </div>
      <img v-if="heroImg" class="hero-photo" :src="heroImg" alt="" />
      <div v-if="maxOff" class="ribbon">
        <small>{{ zh ? '最高' : 'UP TO' }}</small>
        <b>{{ maxOff }}%</b>
        <small>{{ zh ? '立减' : 'OFF' }}</small>
      </div>
    </section>

    <div class="promos">
      <div class="promo">
        <Truck :size="18" />
        <span><b>{{ zh ? '包邮' : 'Free shipping' }}</b><small>{{ shipNote }}</small></span>
      </div>
      <router-link class="promo" to="/coupons">
        <Percent :size="18" />
        <span><b>{{ zh ? '再用券' : 'Extra savings' }}</b><small>{{ zh ? '去领优惠券' : 'Use our coupons' }}</small></span>
        <ChevronRight :size="16" />
      </router-link>
    </div>

    <div class="sec" id="deals">
      <h2>{{ zh ? '热卖' : 'Hot deals' }}</h2>
      <a href="#deals">{{ zh ? '查看全部' : 'See all' }}</a>
    </div>

    <div v-if="loading" class="state">{{ zh ? '加载中…' : 'Loading…' }}</div>
    <div v-else-if="!products.length" class="state">{{ zh ? '暂无特卖' : 'No sale items right now.' }}</div>
    <div v-else class="grid">
      <article v-for="p in products" :key="p.sku" class="card" @click="go(p)">
        <div class="shot">
          <img v-if="p.image" :src="p.image" :alt="p.name" />
          <span v-if="pct(p)" class="badge">-{{ pct(p) }}%</span>
        </div>
        <div class="nm">{{ p.name }}</div>
        <div class="pr">
          <span v-if="p.compareAt && p.compareAt > p.price" class="was">{{ money(p.compareAt) }}</span>
          <b>{{ money(p.price) }}</b>
          <button type="button" class="bag" :aria-label="zh ? '加入购物车' : 'Add'" @click.stop="add(p)">
            <ShoppingCart :size="14" />
          </button>
        </div>
      </article>
    </div>
    <AppTabBar active="home" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ChevronRight, Home, Percent, Search, ShoppingCart, Truck } from 'lucide-vue-next'
import { fetchDealEnds, listSaleProducts, money, type Product } from '@/api/products'
import { useCart } from '@/composables/cart'
import { useI18n } from '@/composables/i18n'
import { shelf } from '@/catalog/shelf'
import AppTabBar from '@/components/AppTabBar.vue'

const { lang } = useI18n()
const zh = computed(() => String(lang.value).startsWith('zh'))
const cart = useCart()
const count = computed(() => cart.count.value)
const router = useRouter()
const products = ref<Product[]>([])
const loading = ref(true)
const saleEnds = ref('')
const now = ref(Date.now())
let timer = 0

const heroImg = computed(() => products.value.find((p) => p.image)?.image || '')
const maxOff = computed(() => products.value.reduce((n, p) => Math.max(n, pct(p)), 0))
const shipNote = computed(() => {
  const th = Number(cart.freeShipThreshold.value || 0)
  if (th > 0) return zh.value ? `订单满 $${th}` : `On orders over $${th}`
  return zh.value ? '可追踪物流' : 'Tracked on every order'
})
const parts = computed(() => {
  const parsed = Date.parse(saleEnds.value)
  const target = Number.isFinite(parsed) && parsed > now.value ? parsed : endOfDay(now.value)
  const s = Math.max(0, Math.floor((target - now.value) / 1000))
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const sec = s % 60
  return [h, m, sec].map((n) => String(n).padStart(2, '0'))
})

function endOfDay(ts: number) {
  const d = new Date(ts)
  d.setHours(24, 0, 0, 0)
  return d.getTime()
}
function pct(p: Product) {
  const a = Number(p.compareAt || 0)
  const b = Number(p.price || 0)
  if (a > b && b > 0) return Math.round((1 - b / a) * 100)
  return p.offPct || 0
}
function go(p: Product) { router.push({ path: '/pdp', query: { sku: p.sku } }) }
function add(p: Product) { cart.add(p) }

onMounted(async () => {
  timer = window.setInterval(() => { now.value = Date.now() }, 1000)
  try { saleEnds.value = (await fetchDealEnds()) || '' } catch { /* live end unknown */ }
  try {
    const rows = await listSaleProducts()
    products.value = rows.length ? rows : shelf.filter((p) => pct(p) > 0)
  } catch {
    products.value = shelf.filter((p) => pct(p) > 0)
  } finally {
    loading.value = false
  }
})
onUnmounted(() => { if (timer) window.clearInterval(timer) })
</script>

<style lang="scss" scoped>
.page {
  min-height: 100vh; background: #FCFAF8; color: #1C2430;
  padding: calc(12px + env(safe-area-inset-top)) 16px 8px;
  font-family: "Plus Jakarta Sans", "PingFang SC", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
.top { display: flex; align-items: center; justify-content: space-between; }
.brand { display: flex; align-items: center; gap: 8px; color: inherit; }
.mark {
  width: 32px; height: 32px; border-radius: 10px; background: #F96141; color: #fff;
  display: inline-flex; align-items: center; justify-content: center;
}
.logo { display: block; font-size: 20px; font-weight: 800; letter-spacing: -0.04em; line-height: 1; color: #F96141; }
.tag { display: block; margin-top: 2px; font-size: 10px; letter-spacing: 0.04em; color: #8B919A; text-transform: uppercase; }
.tools { display: flex; align-items: center; gap: 14px; color: #1C2430; }
.cart { position: relative; color: inherit; }
.cart i {
  position: absolute; top: -6px; right: -8px; min-width: 16px; height: 16px; padding: 0 4px;
  border-radius: 99px; background: #F96141; color: #fff; font-size: 10px; font-style: normal; font-weight: 800;
  display: grid; place-items: center;
}
.hero {
  position: relative; margin-top: 14px; min-height: 168px; border-radius: 18px; overflow: hidden; color: #fff;
  background: linear-gradient(100deg, #FF8A62 0%, #F96141 58%, #FFB199 100%);
}
.copy { position: relative; z-index: 1; padding: 16px 16px 14px; max-width: 62%; }
.script { font-size: 22px; font-weight: 700; font-style: italic; letter-spacing: -0.03em; line-height: 1; }
.deals { margin-top: 2px; font-size: 34px; font-weight: 800; letter-spacing: -0.04em; line-height: 0.95; }
.copy p { margin: 8px 0 0; font-size: 11px; line-height: 1.35; letter-spacing: 0.04em; font-weight: 700; text-transform: uppercase; }
.ticks { display: flex; align-items: flex-end; gap: 4px; margin-top: 12px; }
.ticks div {
  min-width: 36px; background: rgba(90, 24, 12, 0.28); border-radius: 8px; text-align: center; padding: 4px 4px 3px;
}
.ticks b { display: block; font-size: 14px; line-height: 1; }
.ticks small { display: block; font-size: 8px; letter-spacing: 0.06em; opacity: 0.85; }
.ticks span { font-weight: 800; padding-bottom: 10px; }
.hero-photo { position: absolute; right: 0; top: 0; width: 46%; height: 100%; object-fit: cover; }
.ribbon {
  position: absolute; right: 12px; top: 0; z-index: 1; width: 72px; padding: 10px 6px 14px;
  background: #E24B2A; color: #fff; text-align: center;
  clip-path: polygon(0 0, 100% 0, 100% 100%, 50% 86%, 0 100%);
}
.ribbon small { display: block; font-size: 10px; font-weight: 800; letter-spacing: 0.04em; }
.ribbon b { display: block; font-size: 20px; line-height: 1.05; }
.promos { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 12px; }
.promo {
  display: flex; align-items: center; gap: 8px; background: #fff; border: 1px solid #F3F0EC;
  border-radius: 14px; padding: 10px 10px; color: inherit; min-height: 58px;
}
.promo :deep(svg) { color: #F96141; flex: none; }
.promo span { display: flex; flex-direction: column; min-width: 0; }
.promo b { font-size: 13px; }
.promo small { color: #8B919A; font-size: 11px; }
.sec { display: flex; align-items: baseline; justify-content: space-between; margin-top: 14px; }
.sec h2 { margin: 0; font-size: 18px; letter-spacing: -0.03em; }
.sec a { color: #F96141; font-size: 13px; font-weight: 700; }
.state { text-align: center; color: #8B919A; padding: 28px 8px; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 8px; }
.card { cursor: pointer; min-width: 0; }
.shot { position: relative; aspect-ratio: 1.18; border-radius: 14px; overflow: hidden; background: #F6F4F2; }
.shot img { width: 100%; height: 100%; object-fit: cover; display: block; }
.badge {
  position: absolute; left: 8px; top: 8px; height: 22px; display: inline-flex; align-items: center;
  background: #F96141; color: #fff; font-size: 12px; font-weight: 800; letter-spacing: -0.02em;
  border-radius: 999px; padding: 0 8px;
}
.nm {
  margin-top: 6px; font-size: 13px; font-weight: 750; line-height: 1.25; min-height: 2.5em;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.pr { display: flex; align-items: center; gap: 4px; margin-top: 2px; }
.was { color: #B0B6BE; text-decoration: line-through; font-size: 11px; }
.pr b { color: #F96141; font-size: 16px; font-weight: 800; letter-spacing: -0.03em; }
.bag {
  margin-left: auto; width: 28px; height: 28px; border: 0; border-radius: 999px; flex: none;
  background: #F96141; color: #fff; display: inline-flex; align-items: center; justify-content: center; cursor: pointer;
}
</style>
