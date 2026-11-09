<template>
  <div class="page">
    <button type="button" class="back" @click="$router.push('/orders')">←</button>
    <p class="brand">Harbor</p>
    <h1>{{ zh ? '支付状态' : 'Payment status' }}</h1>
    <p class="sub">{{ zh ? '刷新后查看最新订单。未付订单可以在订单里继续支付。' : 'Refresh pulls the latest orders. If a payment is still open, pay it from the order.' }}</p>
    <p v-if="orderId" class="amt">{{ zh ? '订单' : 'Order' }} {{ orderId }}</p>
    <button type="button" class="btn" @click="refresh">{{ zh ? '刷新状态' : 'Refresh status' }}</button>
    <router-link class="ghost" to="/chat">{{ zh ? '联系客服' : 'Contact support' }}</router-link>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const zh = computed(() => String(navigator.language || '').toLowerCase().startsWith('zh'))
const route = useRoute()
const router = useRouter()
const orderId = computed(() => String(route.query.id || route.query.order || ''))

function refresh() {
  if (orderId.value) router.push('/orders/' + encodeURIComponent(orderId.value))
  else router.push('/orders')
}
</script>

<style scoped>
.page { min-height: 100vh; background: #FDF9F6; color: #1C2430; padding: 16px 24px 40px; text-align: center; }
.back { border: 0; background: transparent; font-size: 20px; cursor: pointer; float: left; }
.brand { clear: both; margin: 36px 0 0; color: #F96141; font-weight: 800; letter-spacing: 0.08em; }
h1 { margin: 28px 0 8px; font-size: 26px; }
.sub { margin: 0 auto 16px; max-width: 36ch; color: #8B919A; }
.amt { font-size: 20px; font-weight: 800; color: #F96141; }
.btn, .ghost {
  display: flex; align-items: center; justify-content: center; height: 52px; margin: 12px auto 0;
  width: min(100%, 420px); border-radius: 16px; font-weight: 700;
}
.btn { border: 0; background: #F96141; color: #fff; cursor: pointer; }
.ghost { border: 1.5px solid #F96141; color: #F96141; background: #fff; }
</style>
