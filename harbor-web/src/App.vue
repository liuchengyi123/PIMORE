<template>
  <FigmaFrame v-if="frame" :frame="frame" />
  <router-view v-show="!frame" />
  <CsFab v-if="!frame" />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import CsFab from '@/components/CsFab.vue'
import FigmaFrame from '@/components/FigmaFrame.vue'
import { ROUTE_FRAME } from '@/figma/frames'

const route = useRoute()

const frame = computed(() => {
  if (route.name === 'pdp' && route.query.sheet) return '1-3'
  if (route.name === 'cart' && route.query.gap) return '1-22'
  if (route.name === 'cart' && route.query.bundle) return '1-23'
  const name = String(route.name || '')
  return ROUTE_FRAME[name] || ''
})
</script>

<style>
html, body, #app {
  margin: 0;
  padding: 0;
  min-height: 100%;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
  background: #FCFAF8;
  color: #1C2430;
  -webkit-tap-highlight-color: transparent;
  -webkit-font-smoothing: antialiased;
}
* { box-sizing: border-box; }
a { color: inherit; text-decoration: none; }
button, input { font: inherit; }
img { max-width: 100%; }
</style>
