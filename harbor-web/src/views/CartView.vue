<template>
  <div class="fn-page page" data-figma="1:7">
    <header class="head">
      <div>
        <h1>{{ zh ? '购物车' : 'Your Cart' }}</h1>
        <p class="count">{{ zh ? `${lines.length} 件商品` : `${lines.length} items` }}</p>
      </div>
      <button type="button" class="later-link" @click="openLater">
        <Heart :size="16" :stroke-width="1.75" />
        <span>{{ zh ? '稍后再买' : 'Saved for later' }}</span>
        <ChevronRight :size="16" :stroke-width="1.75" />
      </button>
    </header>

    <div v-if="!lines.length && !saved.length" class="empty">
      <ShoppingBag :size="40" :stroke-width="1.5" class="empty-ico" />
      <p>{{ zh ? '购物车是空的' : t('cart_empty') }}</p>
      <router-link class="go-shop" to="/home">{{ zh ? '去逛逛' : 'Keep shopping' }}</router-link>
    </div>

    <template v-else>
      <section v-if="lines.length" class="ship">
        <div class="ship-top">
          <Truck :size="16" :stroke-width="1.85" />
          <div>
            <b>{{ shipTitle }}</b>
            <p>{{ shipSub }}</p>
          </div>
        </div>
        <div class="bar" role="progressbar" :aria-valuenow="shipPct" aria-valuemin="0" aria-valuemax="100">
          <i :style="{ width: shipPct + '%' }" />
        </div>
        <div class="ship-ends">
          <span>{{ money(subtotal) }}</span>
          <span>{{ goal > 0 ? money(goal) : (zh ? '包邮' : 'Free') }}</span>
        </div>
      </section>

      <section v-if="lines.length" class="sheet">
        <article v-for="line in lines" :key="line.sku + '|' + line.offer" class="row">
          <button type="button" class="thumb" @click="open(line.sku)">
            <img v-if="line.image" :src="line.image" alt="" />
            <span v-else class="ph">{{ (line.name || '').slice(0, 1) }}</span>
          </button>
          <div class="mid">
            <button type="button" class="name" @click="open(line.sku)">{{ line.name }}</button>
            <div class="meta">{{ line.size || line.offer || (zh ? '默认' : 'default') }}</div>
            <div class="price">{{ money(line.price) }}</div>
            <div class="qty">
              <button type="button" @click="bump(line, -1)" :aria-label="zh ? '减少' : 'minus'"><Minus :size="13" :stroke-width="2" /></button>
              <span>{{ line.qty }}</span>
              <button type="button" @click="bump(line, 1)" :aria-label="zh ? '增加' : 'plus'"><Plus :size="13" :stroke-width="2" /></button>
              <button type="button" class="hold" @click="saveForLater(line)">{{ zh ? '稍后再买' : 'Save for later' }}</button>
            </div>
          </div>
          <div class="acts">
            <button type="button" class="act" :class="{ hot: wished.has(line.sku) }" @click="toggleWish(line.sku)">
              <Heart :size="15" :stroke-width="1.75" :fill="wished.has(line.sku) ? 'currentColor' : 'none'" />
              <span v-if="zh">{{ wished.has(line.sku) ? '移出' : '加入' }}<br>心愿单</span>
              <span v-else>{{ wished.has(line.sku) ? 'Remove from wishlist' : 'Save to wishlist' }}</span>
            </button>
            <button type="button" class="act" @click="askRemove(line)">
              <Trash2 :size="15" :stroke-width="1.75" />
              <span>{{ zh ? '移除' : 'Remove' }}</span>
            </button>
          </div>
        </article>
      </section>

      <button id="later" type="button" class="later" @click="laterOpen = !laterOpen">
        <span class="bm"><Bookmark :size="16" :stroke-width="1.75" /></span>
        <span class="later-copy">
          <b>{{ zh ? '稍后再买' : 'Save for later' }}</b>
          <small>{{ zh ? '先放一边，回头再买' : "Move items you're not ready for yet." }}</small>
        </span>
        <span class="later-n">{{ saved.length }} {{ zh ? '件' : 'items' }} <ChevronRight :size="14" /></span>
      </button>
      <div v-if="laterOpen" class="later-list">
        <p v-if="!saved.length" class="later-empty">{{ zh ? '还没有稍后再买的商品' : 'Nothing saved yet' }}</p>
        <article v-for="line in saved" :key="'s-' + line.sku + line.offer" class="srow">
          <div class="sthumb">
            <img v-if="line.image" :src="line.image" alt="" />
            <span v-else>{{ (line.name || '').slice(0, 1) }}</span>
          </div>
          <div class="sbody">
            <div class="name">{{ line.name }}</div>
            <div class="price">{{ money(line.price) }}</div>
          </div>
          <button type="button" class="back-btn" @click="restore(line)">{{ zh ? '加回' : 'Add back' }}</button>
        </article>
      </div>

      <section v-if="picks.length" class="upsell">
        <div class="up-head">
          <Zap :size="16" :stroke-width="2" />
          <div>
            <b>{{ zh ? '凑齐这单' : 'Complete Your Order' }}</b>
            <p>{{ zh ? '加几件热门商品，更快包邮' : 'Add these popular items and get closer to free shipping!' }}</p>
          </div>
        </div>
        <div class="picks">
          <article v-for="p in picks" :key="p.sku" class="pick">
            <button type="button" class="pthumb" @click="open(p.sku)">
              <img v-if="p.image" :src="p.image" alt="" />
              <span v-else class="ph">{{ (p.name || '').slice(0, 1) }}</span>
            </button>
            <div class="pname">{{ p.name }}</div>
            <div class="pprice">{{ money(p.price) }}</div>
            <button type="button" class="padd" @click="addPick(p)">
              {{ zh ? '加入' : 'Add' }} <Plus :size="14" :stroke-width="2.25" />
            </button>
          </article>
        </div>
      </section>
    </template>

    <div v-if="lines.length" class="dock">
      <div class="dock-bar">
        <div>
          <div class="dmeta">{{ zh ? `小计（${lines.length} 件）` : `Subtotal (${lines.length} items)` }}</div>
          <div class="dsum">{{ money(subtotal) }}</div>
        </div>
        <button type="button" class="checkout" @click="$router.push('/checkout')">
          {{ zh ? '去结算' : 'Checkout' }} <ChevronRight :size="16" :stroke-width="2.25" />
        </button>
      </div>
    </div>
    <AppTabBar active="cart" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Bookmark, ChevronRight, Heart, Minus, Plus, ShoppingBag, Trash2, Truck, Zap } from 'lucide-vue-next'
import { listProducts, money, type Product } from '@/api/products'
import { harborRequest } from '@/api/http'
import { useCart, type LocalCartLine } from '@/composables/cart'
import { useI18n } from '@/composables/i18n'
import AppTabBar from '@/components/AppTabBar.vue'

const LATER_KEY = 'harbor_web_cart_later'
const { t, lang } = useI18n()
const zh = computed(() => String(lang.value).startsWith('zh'))
const cart = useCart()
const router = useRouter()
const lines = computed(() => cart.lines.value)
const subtotal = computed(() => cart.subtotal.value)
const goal = computed(() => Number(cart.freeShipThreshold?.value || cart.minOrderAmount?.value || 0) || 0)
const shipPct = computed(() => {
  if (goal.value <= 0) return 100
  return Math.max(6, Math.min(100, Math.round((subtotal.value / goal.value) * 100)))
})
const shipTitle = computed(() => {
  if (goal.value > 0 && subtotal.value < goal.value) {
    const gap = money(Math.max(0, goal.value - subtotal.value))
    return zh.value ? `还差 ${gap} 即可包邮` : `You're ${gap} away from free shipping!`
  }
  return zh.value ? '已享包邮' : 'Free shipping unlocked'
})
const shipSub = computed(() => {
  if (goal.value > 0) {
    return zh.value ? `订单满 ${money(goal.value)} 包邮` : `Free shipping on orders over ${money(goal.value)}`
  }
  return zh.value ? '本单包邮 · 可追踪配送' : 'Free tracked shipping on this order'
})

const saved = ref<LocalCartLine[]>([])
const laterOpen = ref(false)
const picks = ref<Product[]>([])
const wished = ref<Set<string>>(new Set())

function loadSaved() {
  try {
    const raw = localStorage.getItem(LATER_KEY)
    const list = raw ? JSON.parse(raw) : []
    saved.value = Array.isArray(list) ? list : []
  } catch {
    saved.value = []
  }
}
function persistSaved() {
  try { localStorage.setItem(LATER_KEY, JSON.stringify(saved.value)) } catch { /* ignore */ }
}
function loadWish() {
  const m = document.cookie.match(/(?:^|; )wishlist=([^;]*)/)
  const raw = m ? decodeURIComponent(m[1]) : ''
  wished.value = new Set(raw.split(',').map((s) => s.trim()).filter(Boolean))
}
function openLater() {
  laterOpen.value = true
  requestAnimationFrame(() => document.getElementById('later')?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
}
function bump(line: LocalCartLine, delta: number) {
  cart.setQty(line.sku, line.offer || '', line.qty + delta)
}
function askRemove(line: LocalCartLine) {
  cart.setQty(line.sku, line.offer || '', 0)
}
function saveForLater(line: LocalCartLine) {
  const hit = saved.value.find((s) => s.sku === line.sku && (s.offer || '') === (line.offer || ''))
  if (hit) hit.qty += line.qty
  else saved.value.push({ ...line })
  persistSaved()
  cart.setQty(line.sku, line.offer || '', 0)
}
function restore(line: LocalCartLine) {
  const exists = cart.lines.value.find((l) => l.sku === line.sku && (l.offer || '') === (line.offer || ''))
  if (exists) cart.setQty(exists.sku, exists.offer || '', exists.qty + (line.qty || 1))
  else cart.setLines([...cart.lines.value, { ...line }])
  saved.value = saved.value.filter((s) => !(s.sku === line.sku && (s.offer || '') === (line.offer || '')))
  persistSaved()
}
async function toggleWish(sku: string) {
  const next = new Set(wished.value)
  if (next.has(sku)) next.delete(sku)
  else next.add(sku)
  wished.value = next
  try {
    await harborRequest('/wishlist', {
      method: 'POST',
      form: true,
      data: { sku, ajax: '1', country: 'US' },
      headers: { 'X-Harbor-Ajax': '1', Accept: 'application/json' },
    })
    loadWish()
  } catch { /* optimistic */ }
}
function open(sku: string) {
  router.push({ path: '/pdp', query: { sku } })
}
function addPick(p: Product) {
  cart.add(p, p.sizes?.[0] || 'default', 1)
}

onMounted(async () => {
  loadSaved()
  loadWish()
  cart.refreshFromServer()
  try {
    const rows = await listProducts('recommended', 1)
    const have = new Set(cart.lines.value.map((l) => l.sku))
    picks.value = rows.filter((p) => p.sku && !have.has(p.sku)).slice(0, 8)
  } catch {
    picks.value = []
  }
})
</script>

<style lang="scss" scoped>
@import '@/styles/theme.scss';
.page { min-height: 100vh; background: $hb-paper; padding: 0 16px 150px; color: $hb-ink; }
.head {
  display: flex; justify-content: space-between; align-items: flex-end; gap: 12px;
  padding: calc(16px + env(safe-area-inset-top)) 0 12px;
}
h1 { margin: 0; font-size: 28px; font-weight: 800; letter-spacing: -0.03em; color: $hb-ink; }
.count { margin: 2px 0 0; font-size: 14px; color: $hb-muted; }
.later-link {
  display: inline-flex; align-items: center; gap: 4px; border: 0; background: transparent;
  color: $hb-muted; font-size: 13px; font-weight: 650; cursor: pointer; padding: 6px 0;
}
.empty { text-align: center; padding: 88px 16px; color: $hb-muted; }
.empty-ico { color: $hb-muted; opacity: 0.5; margin-bottom: 10px; }
.go-shop {
  display: inline-flex; margin-top: 16px; height: 44px; padding: 0 18px; align-items: center;
  border-radius: 999px; background: $hb-coral; color: #fff; font-weight: 750;
}
.ship {
  background: #FFF1EC; border-radius: 14px; padding: 9px 12px 7px; margin-bottom: 10px;
}
.ship-top { display: flex; gap: 8px; align-items: center; color: $hb-coral; }
.ship-top b { display: block; color: $hb-ink; font-size: 13.5px; font-weight: 760; line-height: 1.2; }
.ship-top p { margin: 1px 0 0; color: #8B919A; font-size: 11.5px; font-weight: 500; line-height: 1.25; }
.bar { margin-top: 7px; height: 6px; border-radius: 99px; background: #F6D4CB; overflow: hidden; }
.bar > i { display: block; height: 100%; background: $hb-coral; border-radius: 99px; }
.ship-ends {
  display: flex; justify-content: space-between; margin-top: 3px;
  font-size: 11px; font-weight: 650; color: #8B919A; font-variant-numeric: tabular-nums;
}
.sheet { background: #fff; border-radius: 16px; padding: 2px 10px; box-shadow: $hb-shadow-soft; }
.row { display: flex; gap: 10px; align-items: center; padding: 10px 0; border-bottom: 1px solid $hb-line; }
.row:last-child { border-bottom: 0; }
.thumb, .pthumb {
  border: 0; padding: 0; overflow: hidden; background: #F6F3EF; flex: 0 0 auto; cursor: pointer;
}
.thumb { width: 72px; height: 72px; border-radius: 12px; }
.thumb img, .pthumb img, .sthumb img { width: 100%; height: 100%; object-fit: cover; display: block; }
.ph, .sthumb span, .pthumb .ph {
  width: 100%; height: 100%; display: grid; place-items: center; color: $hb-muted; font-weight: 750;
}
.mid { flex: 1; min-width: 0; }
.name {
  display: block; width: 100%; border: 0; background: transparent; padding: 0; text-align: left;
  font-size: 14px; font-weight: 750; line-height: 1.25; color: $hb-ink; cursor: pointer;
}
.meta { margin-top: 0; font-size: 11px; line-height: 1.2; color: $hb-muted; }
.price { margin-top: 2px; font-size: 15px; font-weight: 800; line-height: 1.2; color: $hb-ink; }
.qty { display: flex; align-items: center; gap: 8px; margin-top: 4px; }
.qty button {
  width: 26px; height: 26px; border-radius: 50%; border: 1px solid #E4DFD8; background: #fff;
  display: inline-flex; align-items: center; justify-content: center; color: $hb-ink; cursor: pointer;
}
.qty span { min-width: 10px; text-align: center; font-weight: 700; font-size: 13px; }
.qty .hold {
  width: auto; height: auto; margin-left: 2px; border: 0; border-radius: 0; background: transparent;
  color: $hb-muted; font-size: 11px; font-weight: 650; cursor: pointer; padding: 0; white-space: nowrap;
}
.acts { display: flex; gap: 2px; flex: 0 0 auto; }
.act {
  width: 46px; border: 0; background: transparent; color: $hb-muted; cursor: pointer;
  display: flex; flex-direction: column; align-items: center; gap: 2px; font-size: 10px; line-height: 1.15; padding: 0;
}
.act.hot { color: $hb-coral; }
.later {
  width: 100%; margin-top: 12px; border: 1px solid $hb-line; background: #fff; border-radius: 16px;
  padding: 14px; display: flex; align-items: center; gap: 12px; text-align: left; cursor: pointer;
}
.bm {
  width: 36px; height: 36px; border-radius: 12px; background: #F6F3EF; color: $hb-ink;
  display: grid; place-items: center; flex: 0 0 auto;
}
.later-copy { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.later-copy b { font-size: 14px; }
.later-copy small { color: $hb-muted; font-size: 12px; margin-top: 2px; }
.later-n { color: $hb-muted; font-size: 13px; display: inline-flex; align-items: center; gap: 2px; white-space: nowrap; }
.later-list { background: #fff; border-radius: 16px; margin-top: 8px; padding: 4px 12px; border: 1px solid $hb-line; }
.later-empty { margin: 12px 0; color: $hb-muted; font-size: 13px; }
.srow { display: flex; gap: 10px; align-items: center; padding: 10px 0; border-bottom: 1px solid $hb-line; }
.srow:last-child { border-bottom: 0; }
.sthumb {
  width: 52px; height: 52px; border-radius: 12px; overflow: hidden; background: #F6F3EF;
  display: grid; place-items: center; flex: 0 0 auto;
}
.sbody { flex: 1; min-width: 0; }
.sbody .name { cursor: default; }
.back-btn {
  border: 0; height: 32px; padding: 0 12px; border-radius: 999px; background: $hb-coral; color: #fff;
  font-weight: 700; font-size: 12px; cursor: pointer;
}
.upsell { margin-top: 18px; }
.up-head { display: flex; gap: 8px; align-items: flex-start; color: $hb-coral; margin-bottom: 10px; }
.up-head b { display: block; color: $hb-ink; font-size: 16px; }
.up-head p { margin: 2px 0 0; color: $hb-muted; font-size: 12px; }
.picks { display: flex; gap: 10px; overflow-x: auto; padding-bottom: 6px; }
.pick {
  flex: 0 0 148px; background: #fff; border-radius: 16px; padding: 8px; border: 1px solid $hb-line;
}
.pthumb { width: 100%; height: 108px; border-radius: 12px; }
.pname {
  margin-top: 8px; font-size: 13px; font-weight: 700; line-height: 1.3; min-height: 34px;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.pprice { margin: 4px 0 8px; font-weight: 800; font-size: 14px; }
.padd {
  width: 100%; height: 32px; border: 0; border-radius: 999px; background: $hb-coral; color: #fff;
  font-weight: 750; display: inline-flex; align-items: center; justify-content: center; gap: 4px; cursor: pointer;
}
.dock {
  position: fixed; left: 50%; transform: translateX(-50%); width: min(100vw, 768px);
  bottom: calc(58px + env(safe-area-inset-bottom)); z-index: 90; padding: 0 10px 6px;
}
.dock-bar {
  background: $hb-coral; color: #fff; border-radius: 16px; min-height: 56px;
  padding: 8px 10px 8px 14px; display: flex; align-items: center; gap: 8px;
  box-shadow: 0 8px 18px rgba(249, 97, 65, 0.24);
}
.dmeta { font-size: 11px; line-height: 1.15; opacity: 0.92; }
.dsum { font-size: 20px; font-weight: 800; letter-spacing: -0.03em; line-height: 1.05; }
.checkout {
  margin-left: auto; height: 36px; padding: 0 14px; border: 0; border-radius: 999px;
  background: #fff; color: $hb-coral; font-weight: 800; font-size: 14px; cursor: pointer;
  display: inline-flex; align-items: center; gap: 2px;
}
</style>
