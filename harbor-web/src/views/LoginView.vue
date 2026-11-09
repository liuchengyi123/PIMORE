<template>
  <div class="fn-page page" data-figma="M17">
    <button type="button" class="back" @click="$router.back()" aria-label="back"><ChevronLeft :size="22" :stroke-width="1.75" /></button>
    <h1>{{ t('me_sign_in') }}</h1>
    <p class="sub">Sign in to sync orders, cart, and rewards across devices.</p>
    <form class="form" @submit.prevent="submit">
      <label>Email<input v-model="email" type="email" required autocomplete="email" /></label>
      <label>Password<input v-model="password" type="password" required autocomplete="current-password" /></label>
      <p v-if="error" class="err">{{ error }}</p>
      <button type="submit" class="btn" :disabled="busy">{{ busy ? '…' : t('me_sign_in') }}</button>
    </form>
    <router-link class="link" :to="{ path: '/register', query: $route.query }">Create an account</router-link>
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
.page { min-height: 100vh; background: $hb-paper; padding: 16px; padding-top: calc(16px + env(safe-area-inset-top)); max-width: 480px; margin: 0 auto; }
.back { width: 40px; height: 40px; border: 0; border-radius: 14px; background: #fff; color: #121816; display: inline-flex; align-items: center; justify-content: center; box-shadow: 0 4px 16px rgba(18,24,22,0.06); cursor: pointer; }
h1 { margin: 18px 0 6px; font-size: 26px; }
.sub { color: $hb-muted; font-size: 13px; margin-bottom: 18px; }
.form { display: flex; flex-direction: column; gap: 12px; background: $hb-white; padding: 16px; border-radius: 18px; box-shadow: $hb-shadow-soft; }
label { display: flex; flex-direction: column; gap: 6px; font-size: 12px; font-weight: 700; color: $hb-muted; }
input { border: 1px solid $hb-line; border-radius: 12px; padding: 12px; font-size: 15px; color: $hb-ink; }
.btn { border: 0; height: 48px; border-radius: $hb-radius-sm; background: $hb-coral; color: #fff; font-weight: 740; cursor: pointer; }
.err { color: $hb-coral-deep; font-size: 13px; margin: 0; }
.link { display: inline-block; margin-top: 16px; color: $hb-coral; font-weight: 680; }

.fn-page { --ink:#1B2B4A; --teal:#FF6B4A; --amber:#FF6B4A; --sand:#F4F7FB; }
</style>
