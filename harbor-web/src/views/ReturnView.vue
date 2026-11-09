<template>
  <div class="page">
    <button type="button" class="back" @click="$router.back()">←</button>
    <h1>{{ zh ? '申请退货' : 'Request a return' }}</h1>
    <p class="sub">{{ zh ? '告诉我们要退的商品，然后在客服里继续。' : 'Tell us what to send back. This opens buyer chat with the same order.' }}</p>
    <form @submit.prevent="submit">
      <label>{{ zh ? '订单号' : 'Order' }}<input v-model="orderId" required :placeholder="zh ? '订单号' : 'Order number'" /></label>
      <label>{{ zh ? '原因' : 'Reason' }}
        <select v-model="why">
          <option value="Damaged">{{ zh ? '破损' : 'Damaged' }}</option>
          <option value="Not as described">{{ zh ? '与描述不符' : 'Not as described' }}</option>
          <option value="Wrong item">{{ zh ? '错发' : 'Wrong item' }}</option>
          <option value="Changed mind">{{ zh ? '不想要了' : 'Changed mind' }}</option>
        </select>
      </label>
      <label>{{ zh ? '说明' : 'Details' }}
        <textarea v-model="reason" required minlength="3" rows="4" :placeholder="zh ? '出了什么问题？' : 'What went wrong?'" />
      </label>
      <label><input v-model="refund" type="radio" value="original" /> {{ zh ? '原路退回' : 'Original payment' }}</label>
      <label><input v-model="refund" type="radio" value="balance" /> {{ zh ? '退到余额' : 'Balance' }}</label>
      <p v-if="error" class="err">{{ error }}</p>
      <button class="btn" type="submit">{{ zh ? '去客服' : 'Continue to chat' }}</button>
    </form>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { apiRoot } from '@/api/config'

const zh = computed(() => String(navigator.language || '').toLowerCase().startsWith('zh'))
const route = useRoute()
const router = useRouter()
const orderId = ref(String(route.query.order || route.query.id || ''))
const why = ref('Damaged')
const reason = ref('')
const refund = ref('original')
const error = ref('')

async function submit() {
  if (reason.value.trim().length < 3) {
    error.value = zh.value ? '请写一句原因' : 'Please add a short reason.'
    return
  }
  const body = new URLSearchParams()
  body.set('reason', why.value)
  body.set('details', reason.value.trim())
  body.set('refund', refund.value)
  const res = await fetch(apiRoot().replace(/\/$/, '') + '/orders/' + encodeURIComponent(orderId.value) + '/return', {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  })
  if (res.status === 403 || res.status === 401) {
    error.value = zh.value ? '请先登录且订单可退' : 'Sign in. Only paid or shipped orders can be returned.'
    return
  }
  router.push('/orders/' + encodeURIComponent(orderId.value))
}
</script>

<style scoped>
.page { min-height: 100vh; background: #FCFAF8; color: #1C2430; padding: 16px 20px 32px; }
.back { border: 0; background: transparent; font-size: 20px; cursor: pointer; color: #1C2430; }
h1 { margin: 12px 0 6px; font-size: 24px; letter-spacing: -0.03em; }
.sub { margin: 0 0 16px; color: #8B919A; font-size: 14px; }
form { display: flex; flex-direction: column; gap: 12px; }
label { display: flex; flex-direction: column; gap: 6px; font-size: 12px; font-weight: 700; color: #8B919A; }
input, textarea {
  border: 1.5px solid #E7DFD8; border-radius: 16px; padding: 12px 14px;
  font-size: 15px; color: #1C2430; background: #fff;
}
.btn { height: 52px; border: 0; border-radius: 999px; background: #F96141; color: #fff; font-weight: 700; cursor: pointer; }
.err { color: #E11D2E; margin: 0; font-size: 13px; }
</style>
