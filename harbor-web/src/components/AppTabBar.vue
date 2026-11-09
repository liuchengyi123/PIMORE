<template>
  <div class="tab-spacer" />
  <nav class="tab-bar" aria-label="main">
    <button
      v-for="t in tabs"
      :key="t.id"
      type="button"
      class="tab"
      :class="{ on: t.id === active }"
      @click="go(t.path)"
    >
      <component :is="t.icon" class="ico" :size="22" :stroke-width="active === t.id ? 2 : 1.65" />
      <span class="label">{{ t.label }}</span>
      <span v-if="t.id === 'cart' && cartCount > 0" class="badge">{{ cartCount > 99 ? '99+' : cartCount }}</span>
    </button>
  </nav>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { Home, Search, ShoppingBag, UserRound } from 'lucide-vue-next'
import { useI18n } from '@/composables/i18n'
import { useCart } from '@/composables/cart'

defineProps<{ active: 'home' | 'browse' | 'cart' | 'me' }>()

const router = useRouter()
const { t } = useI18n()
const cart = useCart()
const cartCount = computed(() => cart.count.value)

const tabs = computed(() => [
  { id: 'home' as const, label: t('tab_home'), path: '/home', icon: Home },
  { id: 'browse' as const, label: t('tab_browse'), path: '/browse', icon: Search },
  { id: 'cart' as const, label: t('tab_cart'), path: '/cart', icon: ShoppingBag },
  { id: 'me' as const, label: t('tab_me'), path: '/me', icon: UserRound },
])

function go(path: string) {
  router.push(path)
}
</script>

<style lang="scss" scoped>
@import '@/styles/theme.scss';
.tab-spacer { height: 72px; }
.tab-bar {
  position: fixed;
  left: 50%;
  transform: translateX(-50%);
  width: min(100vw, 768px);
  bottom: 0;
  height: calc(58px + env(safe-area-inset-bottom));
  padding-bottom: env(safe-area-inset-bottom);
  border-radius: 0;
  background: #fff;
  border-top: 1px solid #F1EEEA;
  display: flex; align-items: center; justify-content: space-around;
  z-index: 100;
}
.tab {
  position: relative;
  flex: 1; border: 0; background: transparent; padding: 6px 0 4px; cursor: pointer;
  color: #9AA0A8;
  display: flex; flex-direction: column; align-items: center; gap: 2px;
  &.on { color: $hb-coral; }
}
.ico { display: block; }
.label { display: block; font-size: 11px; font-weight: 650; letter-spacing: 0; }
.badge {
  position: absolute; top: 2px; right: 22%;
  min-width: 16px; height: 16px; border-radius: 999px; padding: 0 4px;
  background: $hb-coral; color: #fff; font-size: 10px; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
}
</style>
