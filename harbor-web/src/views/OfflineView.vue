<template>
  <div class="page">
    <div class="mark" aria-hidden="true">!</div>
    <h1>{{ zh ? '当前离线' : 'You’re offline' }}</h1>
    <p class="sub">{{ zh ? '检查网络后再试一次。' : 'Check the connection, then try Harbor again.' }}</p>
    <button type="button" class="btn" @click="retry">{{ zh ? '重试' : 'Retry' }}</button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
const zh = computed(() => String(navigator.language || '').toLowerCase().startsWith('zh'))
const router = useRouter()
function retry() {
  if (navigator.onLine) router.push('/home')
  else window.location.reload()
}
</script>

<style scoped>
.page {
  min-height: 100vh; background: var(--hb-page); color: var(--hb-ink);
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: 32px 24px; text-align: center;
}
.mark { width: 64px; height: 64px; border-radius: 20px; background: var(--hb-primary-soft); color: var(--hb-primary); display: grid; place-items: center; font-size: 28px; font-weight: 800; margin-bottom: 12px; }
h1 { margin: 0 0 8px; font-size: 28px; }
.sub { margin: 0 0 20px; color: var(--hb-muted); }
.btn {
  height: 48px; padding: 0 22px; border: 0; border-radius: 999px;
  background: var(--hb-primary); color: var(--hb-on-primary); font-weight: 700; cursor: pointer;
}
</style>
