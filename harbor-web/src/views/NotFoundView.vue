<template>
  <div class="page">
    <div class="mark" aria-hidden="true">404</div>
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
  min-height: 100vh; background: var(--hb-page); color: var(--hb-ink);
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: 32px 24px; text-align: center;
}
.mark { min-width: 72px; height: 64px; padding: 0 12px; border-radius: 20px; background: var(--hb-primary-soft); color: var(--hb-primary); display: grid; place-items: center; font-size: 22px; font-weight: 800; margin-bottom: 12px; }
h1 { margin: 8px 0; font-size: 24px; }
.sub { margin: 0 0 20px; color: var(--hb-muted); }
.btn {
  display: inline-flex; align-items: center; height: 48px; padding: 0 22px;
  border-radius: 999px; background: var(--hb-primary); color: var(--hb-on-primary); font-weight: 700;
}
</style>
