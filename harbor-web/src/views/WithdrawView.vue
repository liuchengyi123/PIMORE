<template>
  <div class="page">
    <header class="head">
      <button type="button" class="back" @click="$router.back()" aria-label="back">‹</button>
      <h1 class="title">Withdraw</h1>
    </header>
    <p class="avail">Available {{ balance }}</p>
    <label class="field">
      <span>Amount (USD)</span>
      <input v-model="amount" inputmode="decimal" placeholder="0.00" />
    </label>
    <label class="field">
      <span>Payout method</span>
      <input v-model="payout" placeholder="PayPal · you@email.com" />
    </label>
    <p class="hint">{{ note || 'Withdrawals follow account rewards rules. Processing time varies by method.' }}</p>
    <p v-if="msg" class="msg">{{ msg }}</p>
    <button type="button" class="cta" :disabled="busy" @click="submit">{{ busy ? '…' : 'Request withdraw' }}</button>
  </div>
</template>
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { fetchWithdrawHtml, parseBalanceHtml, postWithdraw } from '@/api/accountApi'
import { useI18n } from '@/composables/i18n'
const { t } = useI18n()
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
    msg.value = res.statusCode < 400 ? 'Submitted' : 'Failed — try shop form'
  } catch {
    msg.value = 'Network error'
  } finally { busy.value = false }
}
</script>
<style scoped>
.page { min-height: 100vh; background: #F7F4EF; color: #0F2744; padding: 12px 16px 40px; padding-top: calc(12px + env(safe-area-inset-top)); }
.head { display: flex; gap: 10px; align-items: center; margin-bottom: 8px; }
.back { border: 0; background: transparent; font-size: 22px; font-weight: 700; cursor: pointer; color: #0F2744; }
.title { font-size: 17px; font-weight: 700; margin: 0; }
.avail { font-size: 11px; color: #6B7280; margin: 0 0 10px; }
.field {
  display: block; background: #fff; border: 1px solid #E8E4DC; border-radius: 12px;
  padding: 12px 14px; margin-bottom: 10px;
}
.field span { display: block; font-size: 11px; font-weight: 600; color: #6B7280; margin-bottom: 4px; }
.field input { width: 100%; border: 0; outline: 0; font-size: 14px; color: #0F2744; background: transparent; }
.hint { font-size: 11px; color: #6B7280; line-height: 1.45; margin: 0 0 14px; }
.msg { font-size: 12px; color: #0E7490; margin: 0 0 10px; }
.cta {
  width: 100%; height: 41px; border: 0; border-radius: 12px; background: #0F2744; color: #fff;
  font-size: 14px; font-weight: 600; cursor: pointer;
}
.cta:disabled { opacity: 0.7; }
</style>
