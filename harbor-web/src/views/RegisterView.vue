<template>
  <div class="fn-page page" data-figma="M19">
    <button type="button" class="back" @click="$router.back()" aria-label="back"><ChevronLeft :size="22" :stroke-width="1.75" /></button>
    <h1>注册</h1>
    <p class="sub">创建账号后可同步订单与余额。</p>
    <div class="social">
      <button type="button" @click="socialHint">Apple</button>
      <button type="button" @click="socialHint">Google</button>
      <button type="button" @click="socialHint">Facebook</button>
    </div>
    <p class="or">或使用邮箱</p>
    <form class="form" @submit.prevent="submit">
      <label>邮箱<input v-model="email" type="email" required autocomplete="email" /></label>
      <label>密码（至少 8 位）<input v-model="password" type="password" required minlength="8" autocomplete="new-password" /></label>
      <p v-if="note" class="note">{{ note }}</p>
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
const note = ref('')
function socialHint() { note.value = '请使用邮箱注册' }
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
.page { min-height: 100vh; background: #FDF9F6; padding: 10px 16px 28px; padding-top: calc(10px + env(safe-area-inset-top)); max-width: 480px; margin: 0 auto; color: #1C2430; }
.back { width: 34px; height: 34px; border: 0; border-radius: 12px; background: transparent; color: #1C2430; display: inline-flex; align-items: center; justify-content: center; cursor: pointer; padding: 0; }
h1 { margin: 12px 0 4px; font-size: 22px; letter-spacing: -0.03em; }
.sub { margin: 0 0 12px; font-size: 13px; color: #8B919A; line-height: 1.4; }
.social { display: flex; gap: 8px; }
.social button {
  flex: 1; height: 40px; border-radius: 999px; border: 1px solid #F1EEEA; background: #fff;
  color: #1C2430; font-size: 13px; font-weight: 700; cursor: pointer;
}
.or { margin: 10px 0; text-align: center; font-size: 12px; color: #8B919A; }
.form { display: flex; flex-direction: column; gap: 8px; background: transparent; padding: 0; }
label { display: flex; flex-direction: column; gap: 4px; font-size: 12px; font-weight: 700; color: #8B919A; }
input { height: 44px; border: 1px solid #E8E4DC; border-radius: 12px; padding: 0 14px; font-size: 14px; color: #1C2430; background: #fff; box-sizing: border-box; }
.btn { border: 0; height: 40px; border-radius: 999px; background: #F96141; color: #fff; font-size: 14px; font-weight: 700; cursor: pointer; margin-top: 4px; }
.err { color: #E11D2E; font-size: 12px; margin: 0; }
.note { color: #8B919A; font-size: 12px; margin: 0; text-align: center; }
.link { display: inline-block; margin-top: 12px; color: #F96141; font-weight: 700; font-size: 13px; text-decoration: none; }

.fn-page { --ink:#1C2430; --teal:#0E7490; --amber:#F96141; --sand:#FCFAF8; }
</style>
