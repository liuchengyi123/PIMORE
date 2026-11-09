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
  background: #F4F7FB;
  color: #1B2B4A;
  -webkit-tap-highlight-color: transparent;
  -webkit-font-smoothing: antialiased;
}
* { box-sizing: border-box; }
a { color: inherit; text-decoration: none; }
button, input { font: inherit; }
img { max-width: 100%; }
</style>
