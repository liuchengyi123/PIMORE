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
      <div class="ok" aria-hidden="true"><Check :size="30" :stroke-width="2.75" /></div>
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
  padding: calc(8px + env(safe-area-inset-top)) 16px 96px; text-align: center;
}
.head { display: grid; grid-template-columns: 32px 1fr 32px; align-items: start; }
.brand { grid-column: 2; }
.mark {
  width: 24px; height: 24px; margin: 0 auto 1px; border-radius: 7px; background: $hb-coral; color: #fff;
  display: grid; place-items: center;
}
.brand b { display: block; color: $hb-coral; font-size: 22px; font-weight: 800; letter-spacing: -0.04em; line-height: 1; }
.brand small { display: block; margin-top: 2px; color: $hb-muted; font-size: 9px; letter-spacing: 0.12em; font-weight: 700; }
.bag { grid-column: 3; color: $hb-ink; display: grid; place-items: center; height: 28px; }
.hero { position: relative; margin-top: 14px; }
.ok {
  width: 68px; height: 68px; margin: 0 auto 8px; border-radius: 50%; background: $hb-coral; color: #fff;
  display: grid; place-items: center; box-shadow: 0 8px 18px rgba(249, 97, 65, 0.32);
  position: relative; z-index: 1;
}
h1 { margin: 0; font-size: 26px; font-weight: 800; letter-spacing: -0.03em; line-height: 1.15; position: relative; z-index: 1; }
.sub { margin: 6px auto 0; max-width: 30ch; color: #5C6570; font-size: 13px; line-height: 1.35; position: relative; z-index: 1; }
.pill {
  position: relative; z-index: 1; display: inline-flex; flex-direction: column; margin-top: 10px;
  background: #FFF1EC; color: $hb-coral; border-radius: 999px; padding: 5px 16px;
}
.pill span { font-size: 9px; letter-spacing: 0.12em; font-weight: 750; line-height: 1.2; }
.pill b { font-size: 14px; line-height: 1.2; }
.card {
  position: relative; z-index: 1; margin-top: 12px; background: #fff; border-radius: 16px;
  padding: 10px 12px 4px; text-align: left; box-shadow: $hb-shadow-soft;
}
.kicker { font-size: 10px; letter-spacing: 0.12em; color: $hb-muted; font-weight: 750; margin-bottom: 2px; }
.line {
  display: flex; align-items: center; gap: 10px; padding: 7px 0; color: inherit; text-decoration: none;
}
.line + .line { border-top: 1px solid $hb-line; }
.bubble {
  width: 30px; height: 30px; border-radius: 50%; background: $hb-coral-soft; color: $hb-coral;
  display: grid; place-items: center; flex: 0 0 auto;
}
.copy { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.copy small { color: $hb-muted; font-size: 9px; letter-spacing: 0.08em; font-weight: 750; line-height: 1.2; }
.copy b { font-size: 14px; margin-top: 1px; line-height: 1.2; }
.copy em { font-style: normal; color: $hb-muted; font-size: 11px; margin-top: 1px; line-height: 1.2; }
.line :deep(svg:last-child), .line > svg:last-child { color: $hb-muted; }
.btn {
  position: relative; z-index: 1; margin-top: 8px; height: 46px; border-radius: 999px; background: $hb-coral; color: #fff;
  display: flex; align-items: center; justify-content: center; gap: 6px; font-weight: 750; font-size: 15px; text-decoration: none;
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
  position: absolute; left: 0; right: 0; bottom: 0; height: 84px; pointer-events: none;
  background:
    radial-gradient(80% 90% at 15% 120%, #FFE4DA 0%, transparent 70%),
    radial-gradient(70% 90% at 85% 130%, #FFD0C2 0%, transparent 68%);
}
.waves p {
  position: absolute; right: 16px; bottom: 16px; margin: 0; color: $hb-coral;
  font-family: "Segoe Script", "Comic Sans MS", cursive; font-size: 14px; transform: rotate(-8deg);
}
</style>
