<template>
  <div class="page">
    <button type="button" class="back" @click="$router.push('/login')">←</button>
    <h1>{{ token ? 'Set a new password' : 'Reset password' }}</h1>
    <p class="sub">{{ token ? 'Choose a password of at least 8 characters.' : 'We’ll email a link if this address has a Harbor account.' }}</p>
    <form @submit.prevent="submit">
      <label v-if="!token">Email<input v-model="email" type="email" required autocomplete="email" /></label>
      <template v-else>
        <label>New password<input v-model="password" type="password" required minlength="8" autocomplete="new-password" /></label>
        <label>Confirm<input v-model="confirm" type="password" required minlength="8" autocomplete="new-password" /></label>
      </template>
      <p v-if="error" class="err">{{ error }}</p>
      <p v-if="sent" class="ok">Check that inbox for the reset link.</p>
      <button class="btn" type="submit" :disabled="busy">{{ busy ? '…' : (token ? 'Update password' : 'Send link') }}</button>
    </form>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { apiRoot } from '@/api/config'

const route = useRoute()
const router = useRouter()
const token = computed(() => String(route.query.token || ''))
const email = ref('')
const password = ref('')
const confirm = ref('')
const busy = ref(false)
const error = ref('')
const sent = ref(false)

async function submit() {
  error.value = ''
  sent.value = false
  if (token.value && password.value !== confirm.value) {
    error.value = 'Passwords do not match.'
    return
  }
  busy.value = true
  try {
    const body = new URLSearchParams(token.value
      ? { token: token.value, password: password.value }
      : { email: email.value.trim().toLowerCase() })
    const res = await fetch(apiRoot().replace(/\/$/, '') + '/reset-password', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded', Accept: 'text/html,*/*' },
      body,
    })
    if (!res.ok && res.status !== 303) {
      error.value = 'Could not reset that password.'
      return
    }
    if (token.value) router.replace('/login')
    else sent.value = true
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    busy.value = false
  }
}
</script>

<style scoped>
.page { min-height: 100vh; background: var(--hb-page); color: var(--hb-ink); padding: 16px 20px 32px; }
.back { border: 0; background: transparent; font-size: 20px; cursor: pointer; }
h1 { margin: 18px 0 6px; font-size: 28px; }
.sub { margin: 0 0 18px; color: var(--hb-muted); }
form { display: flex; flex-direction: column; gap: 12px; }
label { display: flex; flex-direction: column; gap: 6px; font-size: 12px; font-weight: 700; color: var(--hb-muted); }
input { border: 1.5px solid #E7DFD8; border-radius: 16px; padding: 14px 16px; font-size: 15px; background: var(--hb-surface); color: var(--hb-ink); }
.btn { height: 52px; border: 0; border-radius: 999px; background: var(--hb-primary); color: var(--hb-on-primary); font-weight: 700; cursor: pointer; }
.err { color: #E11D2E; margin: 0; font-size: 13px; }
.ok { color: #128A5E; margin: 0; font-size: 13px; }
</style>
