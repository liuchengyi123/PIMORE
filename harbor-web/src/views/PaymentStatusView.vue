<template>
  <div class="page" data-figma="1:24">
    <header class="head">
      <button type="button" class="back" @click="$router.push('/orders')" :aria-label="zh ? '返回' : 'back'">
        <ChevronLeft :size="22" :stroke-width="1.75" />
      </button>
      <div class="brand">
        <b>Harbor</b>
        <small>{{ zh ? '家居好物 · 实惠好价' : 'HOME GOODS · GREAT PRICES' }}</small>
      </div>
    </header>

    <section class="panel">
      <div class="glass" aria-hidden="true">
        <span class="ring" />
        <Hourglass :size="34" :stroke-width="1.75" />
      </div>
      <h1>{{ zh ? '支付处理中' : 'Payment processing...' }}</h1>
      <p class="sub">{{ zh ? '正在核对付款信息，请稍候。' : "We're checking your payment details. This may take a moment." }}</p>

      <div class="amt-box">
        <div class="kicker">{{ zh ? '订单金额' : 'ORDER AMOUNT' }}</div>
        <div class="amt">{{ amountText }}</div>
        <p v-if="orderId" class="oid">{{ zh ? '订单' : 'Order' }} {{ orderId }}</p>
      </div>

      <div class="methods">
        <div class="kicker">{{ zh ? '支付方式' : 'PAYMENT METHODS' }}</div>
        <div class="icons">
          <div><CreditCard :size="22" :stroke-width="1.75" /><span>{{ zh ? '银行卡' : 'Card' }}</span></div>
          <div><span class="pp">P</span><span>PayPal</span></div>
          <div><span class="ll">连</span><span>{{ zh ? '连连' : 'LianLian' }}</span></div>
          <div><Wallet :size="22" :stroke-width="1.75" /><span>{{ zh ? '钱包' : 'Wallet' }}</span></div>
        </div>
      </div>

      <button type="button" class="btn" @click="refresh">
        <RefreshCw :size="16" :stroke-width="1.75" /> {{ zh ? '刷新状态' : 'Refresh status' }}
      </button>
      <router-link class="ghost" to="/chat">
        <Headset :size="16" :stroke-width="1.75" /> {{ zh ? '联系客服' : 'Contact support' }}
      </router-link>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ChevronLeft, CreditCard, Headset, Hourglass, RefreshCw, Wallet } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { fetchOrderDetail } from '@/api/accountApi'
import { useI18n } from '@/composables/i18n'

const { lang } = useI18n()
const zh = computed(() => String(lang.value).startsWith('zh'))
const route = useRoute()
const router = useRouter()
const orderId = computed(() => String(route.query.id || route.query.order || ''))
const amountText = ref('—')

onMounted(async () => {
  const q = String(route.query.amount || route.query.due || '')
  if (q) amountText.value = q
  if (!orderId.value) return
  try {
    const detail = await fetchOrderDetail(orderId.value)
    if (detail.due) amountText.value = detail.due
  } catch { /* keep placeholder */ }
})

function refresh() {
  if (orderId.value) router.push('/orders/' + encodeURIComponent(orderId.value))
  else router.push('/orders')
}
</script>

<style lang="scss" scoped>
@import '@/styles/theme.scss';
.page {
  min-height: 100vh; background: #fff; color: $hb-ink;
  padding: calc(12px + env(safe-area-inset-top)) 20px 32px;
}
.head { display: grid; grid-template-columns: 36px 1fr 36px; align-items: center; }
.back { width: 36px; height: 36px; border: 0; background: transparent; color: $hb-ink; cursor: pointer; display: grid; place-items: center; }
.brand { text-align: center; }
.brand b { display: block; color: $hb-coral; font-size: 28px; letter-spacing: -0.04em; font-weight: 800; }
.brand small { display: block; margin-top: 2px; color: $hb-muted; font-size: 10px; letter-spacing: 0.14em; font-weight: 700; }
.panel {
  margin-top: 22px; background: #FFF6F2; border-radius: 28px; padding: 28px 16px 16px; text-align: center;
}
.glass {
  width: 108px; height: 108px; margin: 0 auto 16px; position: relative; display: grid; place-items: center; color: $hb-coral;
}
.ring {
  position: absolute; inset: 0; border-radius: 50%;
  background: conic-gradient(from 200deg, $hb-coral 0 68%, #F8D2C8 68% 100%);
  -webkit-mask: radial-gradient(circle, transparent 58%, #000 60%);
  mask: radial-gradient(circle, transparent 58%, #000 60%);
}
h1 { margin: 0; font-size: 26px; font-weight: 800; letter-spacing: -0.03em; }
.sub { margin: 8px auto 0; max-width: 28ch; color: #5C6570; font-size: 14px; line-height: 1.45; }
.amt-box { margin-top: 18px; background: #FFF9F6; border-radius: 16px; padding: 16px 12px 12px; }
.kicker { font-size: 11px; letter-spacing: 0.12em; color: $hb-muted; font-weight: 750; }
.amt { margin-top: 4px; color: $hb-coral; font-size: 32px; font-weight: 800; letter-spacing: -0.03em; }
.oid { margin: 4px 0 0; color: $hb-muted; font-size: 12px; }
.methods { margin-top: 14px; padding-top: 12px; border-top: 1px solid #F3E4DC; }
.icons { margin-top: 12px; display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; color: $hb-ink; }
.icons div { display: flex; flex-direction: column; align-items: center; gap: 6px; font-size: 11px; color: #5C6570; }
.pp, .ll {
  width: 22px; height: 22px; display: grid; place-items: center; font-weight: 800; font-size: 13px;
}
.pp { color: #003087; }
.ll { color: #1F4BFF; }
.btn, .ghost {
  display: flex; align-items: center; justify-content: center; gap: 8px; height: 52px; margin-top: 14px;
  width: 100%; border-radius: 16px; font-weight: 750; font-size: 15px; text-decoration: none;
}
.btn { border: 0; background: $hb-coral; color: #fff; cursor: pointer; }
.ghost { border: 1.5px solid $hb-coral; color: $hb-coral; background: #fff; }
</style>
