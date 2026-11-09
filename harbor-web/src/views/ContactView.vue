<template>
  <AgShell>
    <header class="bar">
      <button type="button" class="ag-back light" @click="router.back()" :aria-label="tx('返回', 'Back')"><ChevronLeft :size="26" /></button>
      <h1>{{ tx('联系我们', 'Contact us') }}</h1>
    </header>

    <div class="ag-pad">
      <div class="intro">
        <div>
          <AgBrand />
          <div class="mini">{{ tx('每天的家居好物', 'EVERYDAY GOOD FINDS') }}</div>
        </div>
        <p>{{ tx('有问题？我们在。用你最方便的方式联系。', "Questions? We're here to help. Get in touch in the way that's easiest for you.") }}</p>
      </div>

      <h2>{{ tx('联系方式', 'Contact channels') }}</h2>
      <div class="channels">
        <button type="button" @click="router.push('/chat')">
          <span class="ag-icon"><MessageCircle :size="18" /></span>
          <b>{{ tx('在线客服', 'Live chat') }}</b>
          <small>{{ tx('和客服实时聊。', 'Chat with our team in real time.') }}</small>
        </button>
        <button type="button" @click="focusEmail">
          <span class="ag-icon"><Mail :size="18" /></span>
          <b>{{ tx('邮件', 'Email') }}</b>
          <small>{{ tx('随时给我们留言。', 'Send us a message anytime.') }}</small>
        </button>
        <a href="https://wa.me/?text=Harbor" target="_blank" rel="noopener">
          <span class="ag-icon"><Phone :size="18" /></span>
          <b>WhatsApp</b>
          <small>{{ tx('用 WhatsApp 快速联系。', 'Quick support on WhatsApp.') }}</small>
        </a>
      </div>

      <h2>{{ tx('给我们留言', 'Send us a message') }}</h2>
      <label class="ag-field" ref="emailEl">
        <span>{{ tx('邮箱', 'Email') }}</span>
        <input v-model="email" type="email" placeholder="you@email.com" />
      </label>
      <label class="ag-field">
        <span>{{ tx('主题', 'Subject') }}</span>
        <select v-model="topic">
          <option value="">{{ tx('选择主题', 'Select a subject') }}</option>
          <option value="order">{{ tx('订单问题', 'Order question') }}</option>
          <option value="shipping">{{ tx('物流', 'Shipping') }}</option>
          <option value="return">{{ tx('退货', 'Return') }}</option>
          <option value="payment">{{ tx('支付', 'Payment') }}</option>
          <option value="other">{{ tx('其他', 'Something else') }}</option>
        </select>
      </label>
      <label class="ag-field">
        <span>{{ tx('留言', 'Message') }}</span>
        <textarea v-model="body" maxlength="500" :placeholder="tx('在这里写下你的问题…', 'Type your message here...')" />
        <em>{{ body.length }}/500</em>
      </label>
      <p v-if="msg" class="ag-toast">{{ msg }}</p>
      <button type="button" class="ag-cta" :disabled="busy" @click="send"><Send :size="16" /> {{ tx('发送留言', 'Send message') }}</button>

      <section class="hours ag-card">
        <span class="ag-icon"><Clock :size="18" /></span>
        <div>
          <b>{{ tx('客服时间', 'Our support hours') }}</b>
          <p>{{ tx('周一至周日 6:00–22:00（美西）', 'Mon – Sun, 6:00 AM – 10:00 PM (PT)') }}</p>
          <p>{{ tx('我们会尽快回复你。', "We'll get back to you as soon as possible.") }}</p>
        </div>
      </section>
      <p class="slogan">{{ tx('家更好，每天更开心。', 'Better home. Happier everyday.') }}</p>
    </div>
  </AgShell>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ChevronLeft, Clock, Mail, MessageCircle, Phone, Send } from 'lucide-vue-next'
import AgBrand from '@/components/account/AgBrand.vue'
import AgShell from '@/components/account/AgShell.vue'
import { postContact } from '@/api/accountApi'
import { useZh } from '@/composables/zh'

const { tx } = useZh()
const router = useRouter()
const email = ref('')
const topic = ref('')
const body = ref('')
const busy = ref(false)
const msg = ref('')
const emailEl = ref<HTMLElement | null>(null)

function focusEmail() { emailEl.value?.querySelector('input')?.focus() }

async function send() {
  if (!email.value.includes('@') || !body.value.trim()) {
    msg.value = tx('请填写邮箱和留言', 'Email and message are required')
    return
  }
  busy.value = true
  msg.value = ''
  try {
    const res = await postContact(email.value, body.value, topic.value)
    msg.value = res.statusCode < 400 ? tx('已发送', 'Sent') : tx('发送失败，请改用在线客服', 'Could not send — try live chat')
    if (res.statusCode < 400) { body.value = ''; topic.value = '' }
  } catch {
    msg.value = tx('网络错误', 'Network error')
  } finally { busy.value = false }
}
</script>

<style scoped>
.bar {
  display: grid; grid-template-columns: 44px 1fr 44px; align-items: center;
  background: #F96141; color: #fff; padding: 8px 8px 14px; padding-top: calc(8px + env(safe-area-inset-top));
}
.bar h1 { margin: 0; text-align: center; font-size: 20px; font-weight: 800; }
.intro { display: grid; grid-template-columns: auto 1fr; gap: 12px; align-items: center; margin: 16px 0; }
.mini { font-size: 10px; letter-spacing: 0.08em; color: #F96141; font-weight: 800; }
.intro p { margin: 0; font-size: 14px; line-height: 1.4; color: #1C2430; }
h2 { margin: 8px 0 12px; font-size: 18px; font-weight: 800; }
.channels { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; text-align: center; margin-bottom: 8px; }
.channels button, .channels a { border: 0; background: transparent; color: inherit; cursor: pointer; text-decoration: none; padding: 0; }
.channels .ag-icon { margin: 0 auto 6px; }
.channels b { display: block; font-size: 13px; }
.channels small { display: block; margin-top: 4px; color: #8B919A; font-size: 11px; line-height: 1.3; }
.ag-field { position: relative; }
.ag-field em { position: absolute; right: 8px; bottom: 18px; font-style: normal; color: #8B919A; font-size: 12px; }
.hours { margin-top: 16px; padding: 14px; display: flex; gap: 10px; align-items: flex-start; }
.hours b { display: block; }
.hours p { margin: 2px 0 0; color: #8B919A; font-size: 12.5px; }
.slogan { text-align: center; color: #F96141; font-weight: 700; margin-top: 18px; }
</style>
