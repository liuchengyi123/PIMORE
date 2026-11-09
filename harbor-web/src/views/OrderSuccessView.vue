<template>
  <div class="page" data-figma="M13">
    <div class="ok-ico">✓</div>
    <h1>Payment success</h1>
    <p class="sub" v-if="orderId">Order #{{ orderId }}</p>
    <p class="sub">Tracked shipping will appear on the order page once the carrier scans your parcel.</p>
    <router-link v-if="orderId" class="btn" :to="'/orders/' + encodeURIComponent(orderId)">View order</router-link>
    <router-link class="btn soft" to="/orders">My orders</router-link>
    <router-link class="btn soft" to="/home">Keep shopping</router-link>
  </div>
</template>
<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
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
  width: 72px; height: 72px; margin: 0 auto 16px; border-radius: 36px;
  background: rgba(22, 163, 74, 0.12); color: $hb-success; display: flex; align-items: center; justify-content: center;
  font-size: 28px; font-weight: 800;
}
h1 { margin: 0; font-size: 26px; font-weight: 800; color: $hb-ink; }
.sub { margin: 10px auto 0; max-width: 320px; font-size: 13px; color: $hb-muted; line-height: 1.45; }
.btn {
  display: flex; align-items: center; justify-content: center; margin: 12px auto 0; width: min(320px, 100%);
  height: 48px; border-radius: $hb-radius-sm; background: $hb-coral; color: #fff; font-weight: 700; text-decoration: none;
}
.btn.soft { background: #fff; color: $hb-ink; border: 1px solid $hb-line; }
</style>
