<template>
  <router-view />
  <CsFab />
</template>

<script setup lang="ts">
import CsFab from '@/components/CsFab.vue'
</script>

<style>
html, body, #app {
  margin: 0;
  padding: 0;
  min-height: 100%;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
  background: #EFEAE4;
  color: #1C2430;
  -webkit-tap-highlight-color: transparent;
  -webkit-font-smoothing: antialiased;
}
#app {
  max-width: 768px;
  margin: 0 auto;
  min-height: 100vh;
  background: #FCFAF8;
  position: relative;
}
* { box-sizing: border-box; }
a { color: inherit; text-decoration: none; }
button, input, textarea, select { font: inherit; }
img { max-width: 100%; }
</style>
