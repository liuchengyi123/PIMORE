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
  width: 84px; height: 84px; margin: 0 auto 16px; border-radius: 42px;
  background: #F96141; color: #fff; display: flex; align-items: center; justify-content: center;
  font-size: 36px; font-weight: 800; box-shadow: 0 12px 30px rgba(249,97,65,0.35);
}
h1 { margin: 0; font-size: 28px; font-weight: 800; color: #1C2430; }
.sub { margin: 10px auto 0; max-width: 320px; font-size: 14px; color: #8B919A; line-height: 1.45; }
.btn {
  display: flex; align-items: center; justify-content: center; margin: 16px auto 0; width: min(420px, 100%);
  height: 52px; border-radius: 999px; background: #F96141; color: #fff; font-weight: 700; text-decoration: none;
}
.btn.soft { background: #fff; color: #F96141; border: 1.5px solid #F96141; }
</style>
