<template>
  <div class="page">
    <header class="head">
      <button type="button" class="back" @click="$router.back()" aria-label="back">‹</button>
      <h1 class="title">Contact us</h1>
    </header>

    <section class="chat-card">
      <div class="h">Online chat</div>
      <p class="sub">Fastest for order &amp; product questions</p>
      <router-link class="open" to="/chat">Open chat</router-link>
    </section>

    <label class="field">
      <span>Your email</span>
      <input v-model="email" type="email" placeholder="you@email.com" />
    </label>
    <label class="field">
      <span>Subject</span>
      <input v-model="topic" placeholder="Order question" />
    </label>
    <label class="field tall">
      <span>Message</span>
      <textarea v-model="body" rows="4" placeholder="Write your message…" />
    </label>
    <p v-if="msg" class="msg">{{ msg }}</p>
    <button type="button" class="send" :disabled="busy" @click="send">{{ busy ? '…' : 'Send message' }}</button>
  </div>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { postContact } from '@/api/accountApi'
const email = ref('')
const topic = ref('')
const body = ref('')
const busy = ref(false)
const msg = ref('')
async function send() {
  if (!email.value.includes('@') || !body.value.trim()) {
    msg.value = 'Email and message required'
    return
  }
  busy.value = true
  msg.value = ''
  try {
    const res = await postContact(email.value, body.value, topic.value)
    msg.value = res.statusCode < 400 ? 'Sent' : 'Failed — try shop contact page'
    if (res.statusCode < 400) { body.value = ''; topic.value = '' }
  } catch {
    msg.value = 'Network error'
  } finally { busy.value = false }
}
</script>
<style scoped>
.page { min-height: 100vh; background: #F4F7FB; color: #1B2B4A; padding: 12px 16px 40px; padding-top: calc(12px + env(safe-area-inset-top)); }
.head { display: flex; gap: 10px; align-items: center; margin-bottom: 12px; }
.back { border: 0; background: transparent; font-size: 22px; font-weight: 700; cursor: pointer; color: #1B2B4A; }
.title { font-size: 17px; font-weight: 700; margin: 0; }
.chat-card {
  background: #fff; border: 1px solid #E7ECF3; border-radius: 16px; padding: 14px; margin-bottom: 10px;
}
.chat-card .h { font-size: 16px; font-weight: 700; }
.chat-card .sub { margin: 6px 0 0; font-size: 11px; color: #6B7280; }
.open {
  display: flex; align-items: center; justify-content: center; margin-top: 12px; height: 37px;
  border-radius: 12px; background: #1B2B4A; color: #fff; font-size: 14px; font-weight: 600; text-decoration: none;
}
.field {
  display: block; background: #fff; border: 1px solid #E7ECF3; border-radius: 12px;
  padding: 12px 14px; margin-bottom: 10px;
}
.field.tall { min-height: 100px; }
.field span { display: block; font-size: 11px; font-weight: 600; color: #6B7280; margin-bottom: 4px; }
.field input, .field textarea {
  width: 100%; border: 0; outline: 0; font-size: 14px; color: #1B2B4A; background: transparent; resize: vertical;
  font-family: inherit;
}
.send {
  width: 100%; height: 43px; border-radius: 12px; border: 1px solid #E7ECF3; background: #fff;
  color: #1B2B4A; font-size: 14px; font-weight: 600; cursor: pointer;
}
.msg { font-size: 12px; color: #FF6B4A; margin: 0 0 10px; }
</style>
