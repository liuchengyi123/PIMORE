<template>
  <div class="fn-page page" data-figma="M19">
    <button type="button" class="back" @click="$router.back()" aria-label="back"><ChevronLeft :size="22" :stroke-width="1.75" /></button>
    <h1>注册</h1>
    <form class="form" @submit.prevent="submit">
      <label>Email<input v-model="email" type="email" required /></label>
      <label>Password（至少 8 位）<input v-model="password" type="password" required minlength="8" /></label>
      <p v-if="error" class="err">{{ error }}</p>
      <button type="submit" class="btn" :disabled="busy">{{ busy ? '…' : '创建账号' }}</button>
    </form>
    <router-link class="link" :to="{ path: '/login', query: $route.query }">已有账号？登录</router-link>
  </div>
</template>
<script setup lang="ts">
import { ChevronLeft } from 'lucide-vue-next'
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { registerAccount } from '@/api/accountApi'
const route = useRoute()
const router = useRouter()
const email = ref('')
const password = ref('')
const busy = ref(false)
const error = ref('')
async function submit() {
  busy.value = true
  error.value = ''
  const next = String(route.query.next || '/me')
  try {
    const res = await registerAccount(email.value, password.value, next.startsWith('/') ? next : '/me')
    if (!res.ok) { error.value = '注册失败（邮箱无效或已占用）'; return }
    router.replace(next.startsWith('/') ? next : '/me')
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally { busy.value = false }
}
</script>
<style lang="scss" scoped>
@import '@/styles/theme.scss';
.page { min-height: 100vh; background: $hb-paper; padding: 16px; padding-top: calc(16px + env(safe-area-inset-top)); max-width: 480px; margin: 0 auto; }
.back { width: 40px; height: 40px; border: 0; border-radius: 14px; background: #fff; color: #121816; display: inline-flex; align-items: center; justify-content: center; box-shadow: 0 4px 16px rgba(18,24,22,0.06); cursor: pointer; }
h1 { margin: 18px 0 16px; }
.form { display: flex; flex-direction: column; gap: 12px; background: $hb-white; padding: 16px; border-radius: 18px; box-shadow: $hb-shadow-soft; }
label { display: flex; flex-direction: column; gap: 6px; font-size: 12px; font-weight: 700; color: $hb-muted; }
input { border: 1px solid $hb-line; border-radius: 12px; padding: 12px; font-size: 15px; }
.btn { border: 0; height: 52px; border-radius: 999px; background: #F96141; color: #fff; font-weight: 740; cursor: pointer; }
.err { color: $hb-coral; font-size: 13px; margin: 0; }
.link { display: inline-block; margin-top: 16px; color: $hb-forest; font-weight: 680; }

.fn-page { --ink:#0F2744; --teal:#0E7490; --amber:#B45309; --sand:#F7F4EF; }
</style>
