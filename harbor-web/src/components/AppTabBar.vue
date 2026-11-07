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
import { Home, LayoutGrid, ShoppingBag, UserRound } from 'lucide-vue-next'
import { useI18n } from '@/composables/i18n'
import { useCart } from '@/composables/cart'

defineProps<{ active: 'home' | 'browse' | 'cart' | 'me' }>()

const router = useRouter()
const { t } = useI18n()
const cart = useCart()
const cartCount = computed(() => cart.count.value)

const tabs = computed(() => [
  { id: 'home' as const, label: t('tab_home'), path: '/home', icon: Home },
  { id: 'browse' as const, label: t('tab_browse'), path: '/browse', icon: LayoutGrid },
  { id: 'cart' as const, label: t('tab_cart'), path: '/cart', icon: ShoppingBag },
  { id: 'me' as const, label: t('tab_me'), path: '/me', icon: UserRound },
])

function go(path: string) {
  router.push(path)
}
</script>

<style lang="scss" scoped>
@import '@/styles/theme.scss';
.tab-spacer { height: 92px; }
.tab-bar {
  position: fixed;
  left: 14px; right: 14px;
  bottom: calc(10px + env(safe-area-inset-bottom));
  height: 64px;
  border-radius: 24px;
  background: rgba(255,255,255,0.92);
  border: 1px solid rgba(255,255,255,0.7);
  display: flex; align-items: center; justify-content: space-around;
  z-index: 100;
  backdrop-filter: blur(18px);
  box-shadow: $hb-shadow-float;
}
.tab {
  position: relative;
  width: 68px; border: 0; background: transparent; padding: 6px 0; cursor: pointer;
  color: $hb-muted;
  display: flex; flex-direction: column; align-items: center; gap: 2px;
  &.on { color: $hb-forest; }
}
.ico { display: block; }
.label { display: block; font-size: 10px; font-weight: 680; letter-spacing: 0.01em; }
.badge {
  position: absolute; top: 2px; right: 12px;
  min-width: 16px; height: 16px; border-radius: 999px; padding: 0 4px;
  background: $hb-price; color: #fff; font-size: 10px; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
}
</style>
