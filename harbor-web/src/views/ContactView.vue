<template>
  <div class="page">
    <header class="head">
      <button type="button" class="back" @click="$router.back()" aria-label="back">‹</button>
      <h1 class="title">{{ zh ? '联系我们' : 'Contact us' }}</h1>
    </header>

    <section class="chat-card">
      <div class="h">{{ zh ? '在线客服' : 'Online chat' }}</div>
      <p class="sub">{{ zh ? '订单和商品问题最快。' : 'Fastest for order & product questions' }}</p>
      <router-link class="open" to="/chat">{{ zh ? '打开客服' : 'Open chat' }}</router-link>
    </section>

    <label class="field">
      <span>{{ zh ? '邮箱' : 'Your email' }}</span>
      <input v-model="email" type="email" :placeholder="zh ? 'you@email.com' : 'you@email.com'" />
    </label>
    <label class="field">
      <span>{{ zh ? '主题' : 'Subject' }}</span>
      <input v-model="topic" :placeholder="zh ? '订单问题' : 'Order question'" />
    </label>
    <label class="field tall">
      <span>{{ zh ? '留言' : 'Message' }}</span>
      <textarea v-model="body" rows="4" :placeholder="zh ? '写下你的问题…' : 'Write your message…'" />
    </label>
    <p v-if="msg" class="msg">{{ msg }}</p>
    <button type="button" class="send" :disabled="busy" @click="send">{{ busy ? '…' : (zh ? '发送' : 'Send message') }}</button>
  </div>
</template>
<script setup lang="ts">
import { computed, ref } from 'vue'
import { postContact } from '@/api/accountApi'
import { useI18n } from '@/composables/i18n'
const { lang } = useI18n()
const zh = computed(() => String(lang.value).startsWith('zh'))
const email = ref('')
const topic = ref('')
const body = ref('')
const busy = ref(false)
const msg = ref('')
async function send() {
  if (!email.value.includes('@') || !body.value.trim()) {
    msg.value = zh.value ? '请填写邮箱和留言' : 'Email and message required'
    return
  }
  busy.value = true
  msg.value = ''
  try {
    const res = await postContact(email.value, body.value, topic.value)
    msg.value = res.statusCode < 400 ? (zh.value ? '已发送' : 'Sent') : (zh.value ? '发送失败，请改用店铺联系页' : 'Failed — try shop contact page')
    if (res.statusCode < 400) { body.value = ''; topic.value = '' }
  } catch {
    msg.value = zh.value ? '网络错误' : 'Network error'
  } finally { busy.value = false }
}
</script>
<style scoped>
.page { min-height: 100vh; background: var(--hb-page); color: var(--hb-ink); padding: 10px 16px 32px; padding-top: calc(10px + env(safe-area-inset-top)); }
.head { display: flex; gap: 8px; align-items: center; margin-bottom: 8px; }
.back { border: 0; background: transparent; font-size: 22px; font-weight: 700; cursor: pointer; color: var(--hb-ink); padding: 0; }
.title { font-size: 20px; font-weight: 800; letter-spacing: -0.03em; margin: 0; }
.chat-card {
  background: var(--hb-surface); border: 1px solid var(--hb-line); border-radius: 14px; padding: 12px; margin-bottom: 8px;
}
.chat-card .h { font-size: 15px; font-weight: 800; }
.chat-card .sub { margin: 4px 0 0; font-size: 12px; color: var(--hb-muted); line-height: 1.3; }
.open {
  display: flex; align-items: center; justify-content: center; margin-top: 10px; height: 34px;
  border-radius: 10px; background: var(--hb-primary); color: var(--hb-on-primary); font-size: 14px; font-weight: 700; text-decoration: none;
}
.field {
  display: block; background: var(--hb-surface); border: 1px solid var(--hb-line); border-radius: 12px;
  padding: 8px 12px; margin-bottom: 8px;
}
.field.tall { min-height: 88px; }
.field span { display: block; font-size: 11px; font-weight: 700; color: var(--hb-muted); margin-bottom: 2px; }
.field input, .field textarea {
  width: 100%; border: 0; outline: 0; font-size: 14px; color: var(--hb-ink); background: transparent; resize: vertical;
  font-family: inherit; height: 34px; padding: 0;
}
.field textarea { height: 72px; }
.send {
  width: 100%; height: 40px; border-radius: 999px; border: 0; background: var(--hb-primary);
  color: var(--hb-on-primary); font-size: 14px; font-weight: 700; cursor: pointer;
}
.msg { font-size: 12px; color: #0E7490; margin: 0 0 10px; }
</style>
