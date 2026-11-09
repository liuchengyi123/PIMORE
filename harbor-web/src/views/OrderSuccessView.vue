<template>
  <div class="page" data-figma="1:25">
    <header class="head">
      <div class="brand">
        <span class="mark" aria-hidden="true"><Home :size="16" :stroke-width="2.25" /></span>
        <b>Harbor</b>
        <small>{{ zh ? '家居好物 · 日常好价' : 'HOME GOODS · EVERYDAY VALUE' }}</small>
      </div>
      <router-link class="bag" to="/cart" :aria-label="zh ? '购物车' : 'cart'"><ShoppingBag :size="20" :stroke-width="1.75" /></router-link>
    </header>

    <div class="hero">
      <span class="confetti c1" /><span class="confetti c2" /><span class="confetti c3" />
      <span class="confetti c4" /><span class="confetti c5" /><span class="confetti c6" />
      <div class="ok" aria-hidden="true"><Check :size="36" :stroke-width="2.75" /></div>
      <h1>{{ zh ? '支付成功' : 'Order placed!' }}</h1>
      <p class="sub">{{ zh ? '感谢购买，订单已收到，正在安排发货。' : 'Thanks for your purchase! Your order has been received and is on its way.' }}</p>
      <div v-if="orderId" class="pill">
        <span>{{ zh ? '订单号' : 'ORDER NUMBER' }}</span>
        <b>#{{ orderId }}</b>
      </div>
    </div>

    <section class="card">
      <div class="kicker">{{ zh ? '订单摘要' : 'ORDER SUMMARY' }}</div>
      <router-link class="line" :to="orderTo">
        <span class="bubble"><ShoppingBag :size="16" /></span>
        <span class="copy"><small>{{ zh ? '商品' : 'ITEMS' }}</small><b>{{ itemLabel }}</b></span>
        <ChevronRight :size="16" />
      </router-link>
      <div class="line">
        <span class="bubble"><Tag :size="16" /></span>
        <span class="copy"><small>{{ zh ? '合计' : 'TOTAL' }}</small><b>{{ amountText }}</b></span>
      </div>
      <div class="line">
        <span class="bubble"><Truck :size="16" /></span>
        <span class="copy">
          <small>{{ zh ? '预计送达' : 'ESTIMATED DELIVERY' }}</small>
          <b>{{ windowLabel }}</b>
          <em>{{ zh ? '标准配送' : 'Standard shipping' }}</em>
        </span>
      </div>
    </section>

    <router-link class="btn" :to="orderTo">
      <Truck :size="16" /> {{ zh ? '查看物流' : 'Track order' }} <ChevronRight :size="16" />
    </router-link>
    <router-link class="btn ghost" to="/home">
      <ShoppingBag :size="16" /> {{ zh ? '继续逛' : 'Continue shopping' }}
    </router-link>

    <div class="waves" aria-hidden="true">
      <p>{{ zh ? '把好物带回家' : 'Good things for your home' }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Check, ChevronRight, Home, ShoppingBag, Tag, Truck } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { fetchOrderDetail } from '@/api/accountApi'
import { useCart } from '@/composables/cart'
import { useI18n } from '@/composables/i18n'

const { lang } = useI18n()
const zh = computed(() => String(lang.value).startsWith('zh'))
const route = useRoute()
const cart = useCart()
const orderId = computed(() => String(route.query.id || ''))
const orderTo = computed(() => (orderId.value ? '/orders/' + encodeURIComponent(orderId.value) : '/orders'))
const amountText = ref('—')
const summaryCount = ref(0)

const itemLabel = computed(() => {
  const n = summaryCount.value || cart.count.value
  if (!n) return zh.value ? '查看订单' : 'View order'
  return zh.value ? `${n} 件商品` : `${n} items`
})

const windowLabel = computed(() => {
  const a = new Date()
  const b = new Date()
  a.setDate(a.getDate() + 7)
  b.setDate(b.getDate() + 12)
  if (!zh.value) {
    const fmt = (d: Date) => d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    return `${fmt(a)} – ${fmt(b)}`
  }
  const fmt = (d: Date) => `${d.getMonth() + 1}月${d.getDate()}日`
  return `${fmt(a)} – ${fmt(b)}`
})

onMounted(async () => {
  const q = String(route.query.amount || route.query.due || '')
  if (q) amountText.value = q
  if (!orderId.value) {
    if (cart.subtotal.value) amountText.value = '$' + cart.subtotal.value.toFixed(2)
    return
  }
  try {
    const detail = await fetchOrderDetail(orderId.value)
    if (detail.due) amountText.value = detail.due
    summaryCount.value = detail.summary.length
  } catch { /* keep fallback */ }
})
</script>

<style lang="scss" scoped>
@import '@/styles/theme.scss';
.page {
  min-height: 100vh; background: #FFF9F6; color: $hb-ink; position: relative; overflow: hidden;
  padding: calc(14px + env(safe-area-inset-top)) 20px 150px; text-align: center;
}
.head { display: grid; grid-template-columns: 36px 1fr 36px; align-items: start; }
.brand { grid-column: 2; }
.mark {
  width: 28px; height: 28px; margin: 0 auto 2px; border-radius: 8px; background: $hb-coral; color: #fff;
  display: grid; place-items: center;
}
.brand b { display: block; color: $hb-coral; font-size: 26px; font-weight: 800; letter-spacing: -0.04em; line-height: 1; }
.brand small { display: block; margin-top: 4px; color: $hb-muted; font-size: 10px; letter-spacing: 0.12em; font-weight: 700; }
.bag { grid-column: 3; color: $hb-ink; display: grid; place-items: center; height: 36px; }
.hero { position: relative; margin-top: 28px; }
.ok {
  width: 84px; height: 84px; margin: 0 auto 16px; border-radius: 50%; background: $hb-coral; color: #fff;
  display: grid; place-items: center; box-shadow: 0 12px 28px rgba(249, 97, 65, 0.35);
  position: relative; z-index: 1;
}
h1 { margin: 0; font-size: 30px; font-weight: 800; letter-spacing: -0.03em; position: relative; z-index: 1; }
.sub { margin: 10px auto 0; max-width: 32ch; color: #5C6570; font-size: 14px; line-height: 1.5; position: relative; z-index: 1; }
.pill {
  position: relative; z-index: 1; display: inline-flex; flex-direction: column; margin-top: 16px;
  background: #FFF1EC; color: $hb-coral; border-radius: 999px; padding: 8px 22px;
}
.pill span { font-size: 10px; letter-spacing: 0.12em; font-weight: 750; }
.pill b { font-size: 16px; }
.card {
  position: relative; z-index: 1; margin-top: 18px; background: #fff; border-radius: 18px;
  padding: 14px; text-align: left; box-shadow: $hb-shadow-soft;
}
.kicker { font-size: 11px; letter-spacing: 0.12em; color: $hb-muted; font-weight: 750; margin-bottom: 6px; }
.line {
  display: flex; align-items: center; gap: 12px; padding: 10px 0; color: inherit; text-decoration: none;
}
.line + .line { border-top: 1px solid $hb-line; }
.bubble {
  width: 36px; height: 36px; border-radius: 50%; background: $hb-coral-soft; color: $hb-coral;
  display: grid; place-items: center; flex: 0 0 auto;
}
.copy { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.copy small { color: $hb-muted; font-size: 10px; letter-spacing: 0.08em; font-weight: 750; }
.copy b { font-size: 15px; margin-top: 2px; }
.copy em { font-style: normal; color: $hb-muted; font-size: 12px; margin-top: 2px; }
.line :deep(svg:last-child), .line > svg:last-child { color: $hb-muted; }
.btn {
  position: relative; z-index: 1; margin-top: 14px; height: 52px; border-radius: 999px; background: $hb-coral; color: #fff;
  display: flex; align-items: center; justify-content: center; gap: 8px; font-weight: 750; text-decoration: none;
}
.btn.ghost { background: #fff; color: $hb-coral; border: 1.5px solid $hb-coral; }
.confetti { position: absolute; width: 10px; height: 16px; border-radius: 2px; }
.c1 { left: 18%; top: 8px; background: $hb-coral; transform: rotate(-28deg); }
.c2 { left: 28%; top: 36px; background: #F7B7A8; width: 8px; height: 12px; transform: rotate(20deg); }
.c3 { right: 22%; top: 6px; background: #F7B7A8; transform: rotate(24deg); }
.c4 { right: 14%; top: 40px; background: $hb-coral; width: 8px; height: 14px; transform: rotate(-18deg); }
.c5 { left: 10%; top: 70px; background: #FFD3C6; transform: rotate(40deg); }
.c6 { right: 8%; top: 78px; background: #F7B7A8; transform: rotate(-36deg); }
.waves {
  position: absolute; left: 0; right: 0; bottom: 0; height: 120px; pointer-events: none;
  background:
    radial-gradient(80% 90% at 15% 120%, #FFE4DA 0%, transparent 70%),
    radial-gradient(70% 90% at 85% 130%, #FFD0C2 0%, transparent 68%);
}
.waves p {
  position: absolute; right: 22px; bottom: 28px; margin: 0; color: $hb-coral;
  font-family: "Segoe Script", "Comic Sans MS", cursive; font-size: 16px; transform: rotate(-8deg);
}
</style>
