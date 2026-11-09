<template>
  <div class="page">
    <header class="head">
      <button type="button" class="back" @click="$router.back()" aria-label="back">‹</button>
      <h1 class="title">{{ zh ? '提现' : 'Withdraw' }}</h1>
    </header>
    <p class="avail">{{ zh ? '可提现' : 'Available' }} {{ balance }}</p>
    <label class="field">
      <span>{{ zh ? '金额（美元）' : 'Amount (USD)' }}</span>
      <input v-model="amount" inputmode="decimal" placeholder="0.00" />
    </label>
    <label class="field">
      <span>{{ zh ? '收款方式' : 'Payout method' }}</span>
      <input v-model="payout" :placeholder="zh ? 'PayPal · you@email.com' : 'PayPal · you@email.com'" />
    </label>
    <p class="hint">{{ note || (zh ? '提现按账户奖励规则处理，到账时间看收款方式。' : 'Withdrawals follow account rewards rules. Processing time varies by method.') }}</p>
    <p v-if="msg" class="msg">{{ msg }}</p>
    <button type="button" class="cta" :disabled="busy" @click="submit">{{ busy ? '…' : (zh ? '申请提现' : 'Request withdraw') }}</button>
  </div>
</template>
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { fetchWithdrawHtml, parseBalanceHtml, postWithdraw } from '@/api/accountApi'
import { useI18n } from '@/composables/i18n'
const { t, lang } = useI18n()
const zh = computed(() => String(lang.value).startsWith('zh'))
const balance = ref('—')
const note = ref(t('withdraw_note_default'))
const payout = ref('')
const amount = ref('')
const busy = ref(false)
const msg = ref('')
onMounted(async () => {
  try {
    const b = parseBalanceHtml(await fetchWithdrawHtml())
    balance.value = b.balanceText
    note.value = b.note || note.value
  } catch { /* */ }
})
async function submit() {
  busy.value = true
  msg.value = ''
  try {
    const res = await postWithdraw(payout.value, amount.value)
    msg.value = res.statusCode < 400 ? (zh.value ? '已提交' : 'Submitted') : (zh.value ? '提交失败，请改用店铺表单' : 'Failed — try shop form')
  } catch {
    msg.value = zh.value ? '网络错误' : 'Network error'
  } finally { busy.value = false }
}
</script>
<style scoped>
.page { min-height: 100vh; background: #F7F8FA; color: #1C2430; padding: 12px 16px 40px; padding-top: calc(12px + env(safe-area-inset-top)); }
.head { display: flex; gap: 10px; align-items: center; margin-bottom: 8px; }
.back { border: 0; background: transparent; font-size: 22px; font-weight: 700; cursor: pointer; color: #1C2430; }
.title { font-size: 22px; font-weight: 800; letter-spacing: -0.03em; margin: 0; }
.avail { font-size: 11px; color: #6B7280; margin: 0 0 10px; }
.field {
  display: block; background: #fff; border: 1px solid #E8EAF0; border-radius: 12px;
  padding: 12px 14px; margin-bottom: 10px;
}
.field span { display: block; font-size: 11px; font-weight: 600; color: #6B7280; margin-bottom: 4px; }
.field input { width: 100%; border: 0; outline: 0; font-size: 14px; color: #1C2430; background: transparent; }
.hint { font-size: 11px; color: #6B7280; line-height: 1.45; margin: 0 0 14px; }
.msg { font-size: 12px; color: #0E7490; margin: 0 0 10px; }
.cta {
  width: 100%; height: 46px; border: 0; border-radius: 999px; background: #F96141; color: #fff;
  font-size: 14px; font-weight: 600; cursor: pointer;
}
.cta:disabled { opacity: 0.7; }
</style>
