<template>
  <header class="page-head" :class="{ sticky, light }">
    <button v-if="back" type="button" class="back" aria-label="back" @click="onBack">
      <ChevronLeft :size="22" :stroke-width="1.75" />
    </button>
    <div class="main">
      <div v-if="title" class="title">{{ title }}</div>
      <div v-if="sub" class="sub">{{ sub }}</div>
      <slot />
    </div>
    <div v-if="$slots.right" class="right"><slot name="right" /></div>
  </header>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { ChevronLeft } from 'lucide-vue-next'

const props = withDefaults(defineProps<{
  title?: string
  sub?: string
  back?: boolean
  sticky?: boolean
  light?: boolean
  fallback?: string
}>(), {
  back: true,
  sticky: false,
  light: false,
  fallback: '/home',
})

const router = useRouter()
function onBack() {
  if (window.history.length > 1) router.back()
  else router.replace(props.fallback || '/home')
}
</script>

<style lang="scss" scoped>
@import '@/styles/theme.scss';
.page-head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0 12px;
}
.page-head.sticky {
  position: sticky;
  top: 0;
  z-index: 30;
  background: rgba(247, 248, 250, 0.92);
  backdrop-filter: blur(14px);
  margin: 0 -16px;
  padding: calc(8px + env(safe-area-inset-top)) 16px 12px;
}
.back {
  width: 40px;
  height: 40px;
  border: 1px solid $hb-line;
  border-radius: 14px;
  background: $hb-white;
  color: $hb-ink;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  box-shadow: none;
  cursor: pointer;
  flex: 0 0 auto;
}
.page-head.light .back {
  background: rgba(255,255,255,0.18);
  color: #fff;
  border-color: transparent;
  box-shadow: none;
}
.main { flex: 1; min-width: 0; }
.title { font-size: 20px; font-weight: 740; line-height: 1.2; color: inherit; }
.sub { margin-top: 2px; font-size: 12px; color: $hb-muted; }
.page-head.light .sub { color: rgba(255,255,255,0.8); }
.right { flex: 0 0 auto; display: flex; align-items: center; gap: 8px; }
</style>
