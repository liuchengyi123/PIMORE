<template>
  <div class="fn-page page" data-figma="M17">
    <button type="button" class="back" @click="$router.back()" aria-label="back"><ChevronLeft :size="22" :stroke-width="1.75" /></button>
    <div class="brand">Harbor</div>
    <h1>Welcome back!</h1>
    <p class="sub">{{ t('me_sign_in') }} · Harbor</p>
    <form class="form" @submit.prevent="submit">
      <label>Email<input v-model="email" type="email" required autocomplete="email" /></label>
      <label>Password<input v-model="password" type="password" required autocomplete="current-password" /></label>
      <p v-if="error" class="err">{{ error }}</p>
      <button type="submit" class="btn" :disabled="busy">{{ busy ? '…' : t('me_sign_in') }}</button>
    </form>
    <div class="auth-links">
      <router-link to="/reset">Forgot password?</router-link>
      <router-link :to="{ path: '/register', query: $route.query }">Register</router-link>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ChevronLeft } from 'lucide-vue-next'
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { loginAccount } from '@/api/accountApi'
import { useI18n } from '@/composables/i18n'
const { t } = useI18n()
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
    const res = await loginAccount(email.value, password.value, next.startsWith('/') ? next : '/me')
    if (!res.ok) {
      error.value = res.error === 'bad-credentials' ? '邮箱或密码不对' : '登录失败'
      return
    }
    const dest = res.next && res.next.startsWith('/') ? res.next : next
    if (/^https?:\/\//i.test(String(res.next || ''))) window.location.href = String(res.next)
    else router.replace(dest.startsWith('/') ? dest : '/me')
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    busy.value = false
  }
}
</script>
<style lang="scss" scoped>
@import '@/styles/theme.scss';
.page { min-height: 100vh; background: #FDF9F6; padding: 16px 20px 32px; padding-top: calc(16px + env(safe-area-inset-top)); }
.back { width: 40px; height: 40px; border: 0; border-radius: 14px; background: transparent; color: #1C2430; display: inline-flex; align-items: center; justify-content: center; cursor: pointer; }
.brand { margin-top: 28px; text-align: center; font-size: 32px; font-weight: 800; color: #F96141; letter-spacing: -0.03em; }
h1 { margin: 28px 0 6px; font-size: 28px; text-align: center; letter-spacing: -0.03em; }
.sub { color: $hb-muted; font-size: 14px; margin: 0 0 22px; text-align: center; line-height: 1.45; }
.form { display: flex; flex-direction: column; gap: 12px; background: transparent; padding: 0; }
label { display: flex; flex-direction: column; gap: 6px; font-size: 12px; font-weight: 700; color: $hb-muted; }
input { border: 1.5px solid #E7DFD8; border-radius: 16px; padding: 14px 16px; font-size: 15px; color: $hb-ink; background: #fff; }
.btn { border: 0; height: 52px; border-radius: 999px; background: #F96141; color: #fff; font-weight: 740; cursor: pointer; margin-top: 4px; }
.err { color: #E11D2E; font-size: 13px; margin: 0; }
.auth-links { display: flex; justify-content: space-between; margin-top: 16px; color: #F96141; font-weight: 700; font-size: 14px; }

.fn-page { --ink:#0F2744; --teal:#0E7490; --amber:#B45309; --sand:#F7F4EF; }
</style>
