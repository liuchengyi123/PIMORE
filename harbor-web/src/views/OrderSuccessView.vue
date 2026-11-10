<template>
  <div class="page" data-figma="M13">
    <div class="ok-ico">✓</div>
    <h1>{{ zh ? '支付成功' : 'Payment success' }}</h1>
    <p class="sub" v-if="orderId">{{ zh ? '订单' : 'Order' }} #{{ orderId }}</p>
    <p class="sub">{{ zh ? '承运商扫描后，物流会显示在订单页。' : 'Tracked shipping will appear on the order page once the carrier scans your parcel.' }}</p>
    <router-link v-if="orderId" class="btn" :to="'/orders/' + encodeURIComponent(orderId)">{{ zh ? '查看订单' : 'View order' }}</router-link>
    <router-link class="btn soft" to="/orders">{{ zh ? '我的订单' : 'My orders' }}</router-link>
    <router-link class="btn soft" to="/home">{{ zh ? '继续逛' : 'Keep shopping' }}</router-link>
  </div>
</template>
<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from '@/composables/i18n'
const { lang } = useI18n()
const zh = computed(() => String(lang.value).startsWith('zh'))
const route = useRoute()
const orderId = computed(() => String(route.query.id || ''))
</script>
<style lang="scss" scoped>
@import '@/styles/theme.scss';
.page {
  min-height: 100vh; background: $hb-paper; text-align: center;
  padding: 80px 24px 40px; padding-top: calc(80px + env(safe-area-inset-top));
}
.ok-ico {
  width: 72px; height: 72px; margin: 0 auto 16px; border-radius: 22px;
  background: var(--hb-primary); color: var(--hb-on-primary); display: flex; align-items: center; justify-content: center;
  font-size: 36px; font-weight: 800; box-shadow: 0 12px 30px rgba(249,97,65,0.35);
}
h1 { margin: 0; font-size: 28px; font-weight: 800; color: var(--hb-ink); }
.sub { margin: 10px auto 0; max-width: 320px; font-size: 14px; color: var(--hb-muted); line-height: 1.45; }
.btn {
  display: flex; align-items: center; justify-content: center; margin: 16px auto 0; width: min(420px, 100%);
  height: 52px; border-radius: 999px; background: var(--hb-primary); color: var(--hb-on-primary); font-weight: 700; text-decoration: none;
}
.btn.soft { background: var(--hb-surface); color: var(--hb-primary); border: 1.5px solid var(--hb-primary); }
</style>
