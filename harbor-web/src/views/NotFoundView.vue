<template>
  <div class="page">
    <p class="code">404</p>
    <h1>{{ zh ? '页面不存在' : 'Page not found' }}</h1>
    <p class="sub">{{ zh ? '这个链接没有对应的页面。' : 'That link doesn’t lead to a Harbor page.' }}</p>
    <router-link class="btn" to="/home">{{ zh ? '回首页' : 'Back home' }}</router-link>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
const zh = computed(() => String(navigator.language || '').toLowerCase().startsWith('zh'))
</script>
<style scoped>
.page {
  min-height: 100vh; background: #FCFAF8; color: #1C2430;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: 32px 24px; text-align: center;
}
.code { margin: 0; font-size: 64px; font-weight: 800; color: #F96141; letter-spacing: -0.04em; }
h1 { margin: 8px 0; font-size: 24px; }
.sub { margin: 0 0 20px; color: #8B919A; }
.btn {
  display: inline-flex; align-items: center; height: 48px; padding: 0 22px;
  border-radius: 999px; background: #F96141; color: #fff; font-weight: 700;
}
</style>
