<template>
  <div class="page">
    <h1>You’re offline</h1>
    <p class="sub">Check the connection, then try Harbor again.</p>
    <button type="button" class="btn" @click="retry">Retry</button>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
const router = useRouter()
function retry() {
  if (navigator.onLine) router.push('/home')
  else window.location.reload()
}
</script>

<style scoped>
.page {
  min-height: 100vh; background: #FCFAF8; color: #1C2430;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: 32px 24px; text-align: center;
}
h1 { margin: 0 0 8px; font-size: 28px; }
.sub { margin: 0 0 20px; color: #8B919A; }
.btn {
  height: 48px; padding: 0 22px; border: 0; border-radius: 999px;
  background: #F96141; color: #fff; font-weight: 700; cursor: pointer;
}
</style>
