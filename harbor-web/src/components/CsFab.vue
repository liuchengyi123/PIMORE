<template>
  <router-link
    v-if="show"
    class="cs-fab"
    :to="to"
    aria-label="Customer support"
  >
    <MessageCircle :size="18" :stroke-width="1.75" class="ico" />
    <span class="lab">{{ label }}</span>
  </router-link>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { MessageCircle } from 'lucide-vue-next'
import { useI18n } from '@/composables/i18n'

const route = useRoute()
const { lang } = useI18n()

// Fab only on PDP + account home; hide on chat and all other pages
const ALLOWED = new Set(['pdp', 'product', 'me'])
const show = computed(() => ALLOWED.has(String(route.name || '')))
const label = computed(() => (lang.value === 'en' ? 'Chat' : '客服'))
const to = computed(() => {
  const sku = route.query.sku || route.params.sku
  if (sku) {
    return {
      path: '/chat',
      query: {
        sku: String(sku),
        ...(route.query.name ? { name: String(route.query.name) } : {}),
        ...(route.query.image ? { image: String(route.query.image) } : {}),
        ...(route.query.price ? { price: String(route.query.price) } : {}),
      },
    }
  }
  return { path: '/chat' }
})
</script>

<style scoped lang="scss">
@import '@/styles/theme.scss';
.cs-fab {
  position: fixed;
  right: max(14px, env(safe-area-inset-right));
  bottom: calc(78px + env(safe-area-inset-bottom));
  z-index: 40;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 11px 15px;
  border-radius: 999px;
  background: $hb-coral;
  color: #fff;
  font-weight: 720;
  font-size: $hb-type-13;
  border: 0;
  box-shadow: 0 8px 20px rgba(249, 97, 65, 0.28);
}
.cs-fab:hover { background: $hb-coral-hot; }
.ico { display: block; }
.lab { line-height: 1; }
@media (min-width: 960px) {
  .cs-fab {
    right: 28px;
    bottom: 28px;
    padding: 12px 18px;
    font-size: $hb-type-14;
  }
}
</style>