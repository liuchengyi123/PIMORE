<template>
  <div class="page" data-figma="1:58">
    <header class="top">
      <router-link to="/home" class="brand">
        <span class="mark" aria-hidden="true"><Home :size="16" :stroke-width="2.2" /></span>
        <span>
          <span class="logo">Harbor</span>
          <span class="tag">{{ zh ? '家居好物 · $1–$10' : 'Home goods · $1–$10' }}</span>
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

    <div class="stage">
      <svg class="wifi" viewBox="0 0 200 170" aria-hidden="true">
        <g fill="none" stroke="#C5CAD1" stroke-width="10" stroke-linecap="round">
          <path d="M38 78c34-34 90-34 124 0" />
          <path d="M58 98c22-22 62-22 84 0" />
          <path d="M78 116c12-12 32-12 44 0" />
        </g>
        <circle cx="100" cy="138" r="18" fill="#C5CAD1" />
        <circle cx="93" cy="134" r="2.2" fill="#fff" />
        <circle cx="107" cy="134" r="2.2" fill="#fff" />
        <path d="M92 150c6-6 12-6 18 0" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" />
        <path d="M46 58l108 96" stroke="#F96141" stroke-width="8" stroke-linecap="round" />
        <path d="M28 92h14M158 92h14M34 70l10 8M156 78l10-8" stroke="#F96141" stroke-width="4" stroke-linecap="round" />
      </svg>
      <h1>{{ zh ? '你当前离线' : "You're offline" }}</h1>
      <p>{{ zh ? '网络好像断开了。检查一下连接后再试。' : "It looks like you've lost your internet connection. Check your network and try again." }}</p>
      <button type="button" class="btn" @click="retry">{{ zh ? '再试一次' : 'Try again' }}</button>
    </div>
    <AppTabBar active="home" variant="wish" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { Home, Search, ShoppingCart } from 'lucide-vue-next'
import { useCart } from '@/composables/cart'
import { useI18n } from '@/composables/i18n'
import AppTabBar from '@/components/AppTabBar.vue'

const { lang } = useI18n()
const zh = computed(() => String(lang.value).startsWith('zh'))
const cart = useCart()
const count = computed(() => cart.count.value)
const router = useRouter()

function retry() {
  if (navigator.onLine) router.push('/home')
  else window.location.reload()
}
</script>

<style lang="scss" scoped>
.page {
  min-height: 100vh; background: #FCFAF8; color: #1C2430;
  padding: calc(14px + env(safe-area-inset-top)) 16px 0;
  font-family: "Plus Jakarta Sans", "PingFang SC", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
.top { display: flex; align-items: center; justify-content: space-between; }
.brand { display: flex; align-items: center; gap: 8px; color: inherit; }
.mark {
  width: 32px; height: 32px; border-radius: 10px; background: #F96141; color: #fff;
  display: inline-flex; align-items: center; justify-content: center;
}
.logo { display: block; font-size: 20px; font-weight: 800; letter-spacing: -0.04em; line-height: 1; color: #F96141; }
.tag { display: block; margin-top: 2px; font-size: 10px; letter-spacing: 0.06em; color: #8B919A; text-transform: uppercase; }
.tools { display: flex; gap: 14px; color: #1C2430; }
.cart { position: relative; color: inherit; }
.cart i {
  position: absolute; top: -6px; right: -8px; min-width: 16px; height: 16px; padding: 0 4px;
  border-radius: 99px; background: #F96141; color: #fff; font-size: 10px; font-style: normal; font-weight: 800;
  display: grid; place-items: center;
}
.stage {
  min-height: calc(100vh - 180px); display: flex; flex-direction: column; align-items: center; justify-content: center;
  text-align: center; padding: 24px 12px 12px;
}
.wifi { width: 168px; height: 142px; }
h1 { margin: 8px 0 0; font-size: 28px; letter-spacing: -0.03em; font-weight: 800; }
p { margin: 10px 0 0; max-width: 280px; color: #8B919A; font-size: 14px; line-height: 1.5; }
.btn {
  margin-top: 22px; min-width: 220px; height: 48px; border: 0; border-radius: 999px;
  background: #F96141; color: #fff; font-weight: 750; font-size: 16px; cursor: pointer;
}
</style>
