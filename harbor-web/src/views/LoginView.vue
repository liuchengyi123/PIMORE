<template>
  <div class="fn-page page" data-figma="M17">
    <button type="button" class="back" @click="$router.back()" aria-label="back"><ChevronLeft :size="22" :stroke-width="1.75" /></button>
    <div class="brand">Harbor</div>
    <h1>{{ zh ? '欢迎回来' : 'Welcome back!' }}</h1>
    <p class="sub">{{ t('me_sign_in') }}</p>
    <div class="social">
      <button type="button" @click="socialHint">Apple</button>
      <button type="button" @click="socialHint">Google</button>
      <button type="button" @click="socialHint">Facebook</button>
    </div>
    <p class="or">{{ zh ? '或使用邮箱' : 'or use email' }}</p>
    <form class="form" @submit.prevent="submit">
      <label>{{ zh ? '邮箱' : 'Email' }}<input v-model="email" type="email" required autocomplete="email" /></label>
      <label>{{ zh ? '密码' : 'Password' }}<input v-model="password" type="password" required autocomplete="current-password" /></label>
      <p v-if="note" class="note">{{ note }}</p>
      <p v-if="error" class="err">{{ error }}</p>
      <button type="submit" class="btn" :disabled="busy">{{ busy ? '…' : t('me_sign_in') }}</button>
    </form>
    <div class="auth-links">
      <router-link to="/reset">{{ zh ? '忘记密码' : 'Forgot password?' }}</router-link>
      <router-link :to="{ path: '/register', query: $route.query }">{{ zh ? '注册' : 'Register' }}</router-link>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ChevronLeft } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { loginAccount } from '@/api/accountApi'
import { useI18n } from '@/composables/i18n'
const { t, lang } = useI18n()
const zh = computed(() => String(lang.value).startsWith('zh'))
const route = useRoute()
const router = useRouter()
const email = ref('')
const password = ref('')
const busy = ref(false)
const error = ref('')
const note = ref('')
function socialHint() {
  note.value = zh.value ? '请使用邮箱登录' : 'Use email to sign in'
}
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
.page { min-height: 100vh; background: var(--hb-page); padding: 10px 16px 28px; padding-top: calc(10px + env(safe-area-inset-top)); }
.back { width: 34px; height: 34px; border: 0; border-radius: 12px; background: transparent; color: var(--hb-ink); display: inline-flex; align-items: center; justify-content: center; cursor: pointer; padding: 0; }
.brand { margin-top: 20px; text-align: center; font-size: 28px; font-weight: 800; color: var(--hb-primary); letter-spacing: -0.04em; }
h1 { margin: 16px 0 4px; font-size: 22px; text-align: center; letter-spacing: -0.03em; }
.sub { color: var(--hb-muted); font-size: 13px; margin: 0 0 12px; text-align: center; line-height: 1.4; }
.social { display: flex; gap: 8px; }
.social button {
  flex: 1; height: 40px; border-radius: 999px; border: 1px solid var(--hb-line); background: var(--hb-surface);
  color: var(--hb-ink); font-size: 13px; font-weight: 700; cursor: pointer;
}
.or { margin: 10px 0; text-align: center; font-size: 12px; color: var(--hb-muted); }
.form { display: flex; flex-direction: column; gap: 8px; background: transparent; padding: 0; }
label { display: flex; flex-direction: column; gap: 4px; font-size: 12px; font-weight: 700; color: var(--hb-muted); }
input { height: 44px; border: 1px solid var(--hb-line); border-radius: 12px; padding: 0 14px; font-size: 14px; color: var(--hb-ink); background: var(--hb-surface); box-sizing: border-box; }
.btn { border: 0; height: 40px; border-radius: 999px; background: var(--hb-primary); color: var(--hb-on-primary); font-size: 14px; font-weight: 700; cursor: pointer; margin-top: 4px; }
.err { color: #E11D2E; font-size: 12px; margin: 0; }
.note { color: var(--hb-muted); font-size: 12px; margin: 0; text-align: center; }
.auth-links { display: flex; justify-content: space-between; margin-top: 12px; color: var(--hb-primary); font-weight: 700; font-size: 13px; }

.fn-page { --ink:var(--hb-ink); --teal:var(--hb-primary); --amber:var(--hb-sale); --sand:var(--hb-page); }
</style>
