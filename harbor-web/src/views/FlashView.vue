<template>
  <div class="page" data-figma="1:16">
    <header class="hero">
      <div class="title-row">
        <div>
          <div class="name"><Zap :size="22" :stroke-width="2.4" /> {{ zh ? '闪购' : 'Flash Sale' }}</div>
          <p>{{ zh ? '超值。限时。库存有限。' : 'Big value. Short time. Limited stock.' }}</p>
        </div>
        <div class="ticks">
          <div><b>{{ parts[0] }}</b><small>{{ zh ? '时' : 'HRS' }}</small></div>
          <div><b>{{ parts[1] }}</b><small>{{ zh ? '分' : 'MIN' }}</small></div>
          <div><b>{{ parts[2] }}</b><small>{{ zh ? '秒' : 'SEC' }}</small></div>
        </div>
      </div>
    </header>

    <div class="slots">
      <button
        v-for="(slot, i) in slots"
        :key="slot.key"
        type="button"
        class="slot"
        :class="{ on: activeSlot === i }"
        @click="activeSlot = i"
      >
        <b>{{ slot.title }}</b>
        <small>{{ slot.range }}</small>
      </button>
    </div>

    <div v-if="loading" class="state">{{ zh ? '加载中…' : 'Loading…' }}</div>
    <div v-else-if="!products.length" class="state">{{ zh ? '这一场还没有商品' : 'Nothing in this round.' }}</div>
    <div v-else class="grid">
      <article v-for="p in products" :key="p.sku" class="card">
        <div class="shot" @click="go(p)">
          <img v-if="p.image" :src="p.image" :alt="p.name" />
          <span class="claimed"><Flame :size="12" /> {{ meter(p).label }}</span>
          <span v-if="p.onlyLeft" class="stock">{{ zh ? '库存紧张' : 'Limited stock' }}</span>
        </div>
        <div class="body" @click="go(p)">
          <div class="nm">{{ p.name }}</div>
          <div class="sub">{{ p.blurb || p.category }}</div>
          <div class="pr">
            <b>{{ money(p.price) }}</b>
            <s v-if="p.compareAt && p.compareAt > p.price">{{ money(p.compareAt) }}</s>
          </div>
          <div class="bar"><i :style="{ width: meter(p).width }" /></div>
          <div class="meta">
            <span>{{ meter(p).left }}</span>
            <span>{{ meter(p).right }}</span>
          </div>
        </div>
        <button type="button" class="grab" :disabled="activeSlot !== 0" @click="add(p)">
          <ShoppingCart :size="15" /> {{ activeSlot === 0 ? (zh ? '马上抢' : 'Grab') : (zh ? '即将开抢' : 'Soon') }}
        </button>
      </article>
    </div>
    <AppTabBar active="home" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Flame, ShoppingCart, Zap } from 'lucide-vue-next'
import { fetchFlashEnds, listSaleProducts, money, type Product } from '@/api/products'
import { useCart } from '@/composables/cart'
import { useI18n } from '@/composables/i18n'
import { shelf } from '@/catalog/shelf'
import AppTabBar from '@/components/AppTabBar.vue'

const { lang } = useI18n()
const zh = computed(() => String(lang.value).startsWith('zh'))
const cart = useCart()
const router = useRouter()
const products = ref<Product[]>([])
const loading = ref(true)
const flashEnd = ref('')
const now = ref(Date.now())
const activeSlot = ref(0)
let timer = 0

const parts = computed(() => {
  const parsed = Date.parse(flashEnd.value)
  let target = Number.isFinite(parsed) && parsed > now.value ? parsed : 0
  if (!target) {
    const d = new Date(now.value)
    const end = new Date(d)
    end.setHours(Math.floor(d.getHours() / 3) * 3 + 3, 0, 0, 0)
    target = end.getTime()
  }
  const s = Math.max(0, Math.floor((target - now.value) / 1000))
  return [Math.floor(s / 3600), Math.floor((s % 3600) / 60), s % 60].map((n) => String(n).padStart(2, '0'))
})

const slots = computed(() => {
  const start = Math.floor(new Date(now.value).getHours() / 3) * 3
  return [0, 1, 2, 3].map((i) => {
    const h = (start + i * 3) % 24
    const endH = (h + 3) % 24
    const last = endH === 0 ? 23 : endH - 1
    return {
      key: `${h}-${i}`,
      title: i === 0 ? (zh.value ? '进行中' : 'Ongoing') : (zh.value ? '即将开始' : 'Upcoming'),
      range: i === 0
        ? (zh.value ? `现在–${last}:59` : `Now–${last}:59`)
        : `${h}:00–${last}:59`,
    }
  })
})

function off(p: Product) {
  const a = Number(p.compareAt || 0)
  const b = Number(p.price || 0)
  if (a > b && b > 0) return Math.round((1 - b / a) * 100)
  return p.offPct || 0
}
function meter(p: Product) {
  if (p.onlyLeft && p.onlyLeft > 0) {
    const claimed = Math.round(Math.min(92, Math.max(52, 100 - p.onlyLeft * 0.85)))
    const label = zh.value ? `已抢 ${claimed}%` : `${claimed}% claimed`
    return {
      label,
      width: claimed + '%',
      left: label,
      right: zh.value ? `仅剩 ${p.onlyLeft}` : `Only ${p.onlyLeft} left`,
    }
  }
  const cut = off(p)
  if (cut > 0) {
    const label = zh.value ? `已降 ${cut}%` : `${cut}% off`
    return {
      label,
      width: Math.max(18, Math.min(92, cut)) + '%',
      left: label,
      right: zh.value ? '限时' : 'Limited time',
    }
  }
  return {
    label: zh.value ? '闪购中' : 'On flash',
    width: '36%',
    left: zh.value ? '闪购中' : 'On flash',
    right: zh.value ? '限时' : 'Limited time',
  }
}
function go(p: Product) { router.push({ path: '/pdp', query: { sku: p.sku } }) }
function add(p: Product) {
  if (activeSlot.value !== 0) return
  cart.add(p)
}

onMounted(async () => {
  timer = window.setInterval(() => { now.value = Date.now() }, 1000)
  try { flashEnd.value = (await fetchFlashEnds()) || '' } catch { /* */ }
  try {
    const rows = await listSaleProducts()
    const live = rows.length ? rows : shelf.filter((p) => p.tag === 'Flash' || p.tag === 'Deal' || !!p.onlyLeft)
    products.value = live.slice(0, 8)
  } catch {
    products.value = shelf.filter((p) => !!p.onlyLeft || p.tag === 'Flash').slice(0, 4)
  } finally {
    loading.value = false
  }
})
onUnmounted(() => { if (timer) window.clearInterval(timer) })
</script>

<style lang="scss" scoped>
.page {
  min-height: 100vh; background: #FCFAF8; color: #1C2430;
  font-family: "Plus Jakarta Sans", "PingFang SC", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
.hero {
  background: linear-gradient(180deg, #FF7A59 0%, #F96141 100%);
  color: #fff; padding: calc(14px + env(safe-area-inset-top)) 16px 12px;
}
.title-row { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
.name { display: flex; align-items: center; gap: 6px; font-size: 28px; font-weight: 800; letter-spacing: -0.04em; line-height: 1; }
.hero p { margin: 6px 0 0; font-size: 12px; opacity: 0.95; }
.ticks { display: flex; gap: 4px; }
.ticks div { min-width: 36px; background: rgba(255,255,255,0.18); border-radius: 8px; text-align: center; padding: 4px 4px 3px; }
.ticks b { display: block; font-size: 14px; line-height: 1; }
.ticks small { display: block; font-size: 8px; letter-spacing: 0.04em; opacity: 0.9; }
.slots {
  display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 6px;
  padding: 8px 12px 0;
}
.slot {
  border: 1px solid #F1EEEA; background: #fff; border-radius: 14px; padding: 7px 2px 6px;
  cursor: pointer; color: #1C2430; min-height: 48px;
}
.slot b { display: block; font-size: 12px; font-weight: 800; white-space: nowrap; line-height: 1.15; }
.slot small { display: block; margin-top: 3px; color: #8B919A; font-size: 9px; white-space: nowrap; letter-spacing: -0.03em; }
.slot.on { background: #F96141; color: #fff; border-color: #F96141; }
.slot.on small { color: rgba(255,255,255,0.92); }
.state { text-align: center; color: #8B919A; padding: 28px 8px; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; padding: 10px 12px 8px; }
.card { background: #fff; border-radius: 16px; overflow: hidden; border: 1px solid #F3F0EC; display: flex; flex-direction: column; }
.shot { position: relative; aspect-ratio: 1.05; background: #F6F4F2; cursor: pointer; }
.shot img { width: 100%; height: 100%; object-fit: cover; display: block; }
.claimed, .stock {
  position: absolute; top: 8px; display: inline-flex; align-items: center; gap: 3px;
  border-radius: 999px; font-size: 10px; font-weight: 800; padding: 3px 7px; line-height: 1;
}
.claimed { left: 8px; background: #FFF1EC; color: #F96141; }
.stock { right: 8px; background: #F96141; color: #fff; }
.body { padding: 8px 10px 0; cursor: pointer; }
.nm { font-size: 14px; font-weight: 800; letter-spacing: -0.02em; line-height: 1.25; }
.sub { margin-top: 2px; color: #8B919A; font-size: 11px; line-height: 1.3; min-height: 1.3em; }
.pr { display: flex; align-items: baseline; gap: 6px; margin-top: 4px; }
.pr b { color: #F96141; font-size: 18px; letter-spacing: -0.03em; }
.pr s { color: #B0B6BE; font-size: 12px; }
.bar { margin-top: 6px; height: 7px; border-radius: 99px; background: #F8E3DC; overflow: hidden; }
.bar i { display: block; height: 100%; background: #F96141; border-radius: 99px; }
.meta { display: flex; justify-content: space-between; gap: 6px; margin-top: 3px; font-size: 11px; font-weight: 750; }
.meta span:first-child { color: #F96141; }
.meta span:last-child { color: #C45B48; }
.grab {
  margin: 6px 10px 10px; height: 34px; border: 0; border-radius: 999px; background: #F96141; color: #fff;
  font-weight: 750; font-size: 13px; display: inline-flex; align-items: center; justify-content: center; gap: 6px; cursor: pointer;
}
.grab:disabled { background: #F3D2C8; cursor: default; }
</style>
