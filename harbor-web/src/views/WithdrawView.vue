<template>
  <AgShell>
    <header class="head ag-top">
      <button type="button" class="ag-back ink" @click="router.back()" :aria-label="tx('返回', 'Back')"><ChevronLeft :size="24" /></button>
      <h1>{{ tx('提现余额', 'Withdraw balance') }}</h1>
    </header>
    <div class="ag-pad">
      <div class="logo">
        <AgBrand />
        <p>{{ tx('每天的家居好物，更值。', 'Everyday home goods. Better value.') }}</p>
      </div>

      <section class="avail ag-card">
        <span class="ag-icon"><Wallet :size="18" /></span>
        <div>
          <small>{{ tx('可提现余额', 'Available balance') }}</small>
          <b>{{ balance }}</b>
        </div>
      </section>

      <label class="ag-field">
        <span>{{ tx('金额', 'Amount') }}</span>
        <span class="amt">
          <i>$</i>
          <input v-model="amount" inputmode="decimal" :placeholder="tx('输入金额', 'Enter amount')" />
          <em>{{ balance && balance !== '—' ? `${tx('最低 $1.00', '$1.00')} – ${balance}` : tx('最低 $1.00', 'Min $1.00') }}</em>
        </span>
      </label>

      <div class="ag-field">
        <span>{{ tx('收款方式', 'Payout method') }}</span>
        <p class="ag-note">{{ tx('选择你希望如何收到款项。', "Choose how you'd like to receive your funds.") }}</p>
      </div>
      <button type="button" class="method" :class="{ on: method === 'paypal' }" @click="method = 'paypal'">
        <span class="mark pp">P</span>
        <span><b>PayPal</b><small>{{ tx('快速且安全', 'Fast and secure') }}</small></span>
        <i />
      </button>
      <button type="button" class="method" :class="{ on: method === 'bank' }" @click="method = 'bank'">
        <span class="mark bank"><Landmark :size="16" /></span>
        <span><b>{{ tx('银行转账', 'Bank transfer') }}</b><small>{{ tx('通常需要 1–3 个工作日', 'Typically takes 1–3 business days') }}</small></span>
        <i />
      </button>
      <label class="ag-field">
        <span>{{ method === 'paypal' ? tx('PayPal 邮箱', 'PayPal email') : tx('收款账户', 'Account') }}</span>
        <input v-model="dest" :placeholder="method === 'paypal' ? 'you@email.com' : tx('户名 / 账号', 'Name / account')" />
      </label>

      <section class="fee">
        <Info :size="16" color="#F96141" />
        <div>
          <b>{{ tx('会收取小额手续费', 'Small fee applies') }}</b>
          <p>{{ note || tx('将从提现金额中扣除 $0.50 手续费。', 'A $0.50 processing fee will be deducted from your withdrawal amount.') }}</p>
        </div>
      </section>
      <p v-if="msg" class="ag-toast">{{ msg }}</p>
      <button type="button" class="ag-cta" :disabled="busy" @click="submit">{{ busy ? '…' : tx('确认提现', 'Confirm withdraw') }}</button>
    </div>
  </AgShell>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ChevronLeft, Info, Landmark, Wallet } from 'lucide-vue-next'
import AgBrand from '@/components/account/AgBrand.vue'
import AgShell from '@/components/account/AgShell.vue'
import { fetchWithdrawHtml, parseBalanceHtml, postWithdraw } from '@/api/accountApi'
import { useZh } from '@/composables/zh'

const { tx } = useZh()
const router = useRouter()
const balance = ref('—')
const note = ref('')
const amount = ref('')
const method = ref<'paypal' | 'bank'>('paypal')
const dest = ref('')
const busy = ref(false)
const msg = ref('')

onMounted(async () => {
  try {
    const b = parseBalanceHtml(await fetchWithdrawHtml())
    balance.value = b.balanceText || '—'
    note.value = b.note || ''
  } catch { /* offline */ }
})

async function submit() {
  const n = Number(amount.value)
  if (!n || n <= 0) { msg.value = tx('请输入金额', 'Enter an amount'); return }
  if (!dest.value.trim()) { msg.value = tx('请填写收款账户', 'Enter a payout account'); return }
  busy.value = true
  msg.value = ''
  try {
    const payout = `${method.value === 'paypal' ? 'PayPal' : 'Bank'} · ${dest.value.trim()}`
    const cents = String(Math.round(n * 100))
    const res = await postWithdraw(payout, cents)
    msg.value = res.statusCode < 400 ? tx('已提交', 'Submitted') : tx('提交失败，请稍后再试', 'Could not submit')
  } catch {
    msg.value = tx('网络错误', 'Network error')
  } finally { busy.value = false }
}
</script>

<style scoped>
.head { display: grid; grid-template-columns: 44px 1fr 44px; align-items: center; }
.head h1 { margin: 0; text-align: center; font-size: 18px; font-weight: 800; }
.logo { text-align: center; margin: 12px 0 16px; }
.logo p { margin: 4px 0 0; color: #8B919A; font-size: 13px; }
.avail { display: flex; align-items: center; gap: 12px; padding: 14px; background: #FFF6F3; margin-bottom: 16px; }
.avail small { color: #8B919A; }
.avail b { display: block; font-size: 28px; letter-spacing: -0.03em; }
.amt { display: flex; align-items: center; gap: 8px; border: 1px solid #E7E1DA; border-radius: 14px; padding: 0 12px; background: #fff; }
.amt i { font-style: normal; color: #8B919A; }
.amt input { border: 0; height: 48px; padding: 0; }
.amt em { font-style: normal; color: #8B919A; font-size: 12px; white-space: nowrap; }
.method { width: 100%; display: flex; align-items: center; gap: 10px; text-align: left; background: #fff; border: 1px solid #E7E1DA; border-radius: 16px; padding: 12px; margin-bottom: 8px; cursor: pointer; color: inherit; }
.method.on { border: 1.5px solid #F96141; }
.method b, .method small { display: block; }
.method small { color: #8B919A; font-size: 12px; }
.method i { margin-left: auto; width: 18px; height: 18px; border-radius: 50%; border: 1.5px solid #D5D0CA; }
.method.on i { border: 5px solid #F96141; }
.mark { width: 36px; height: 36px; border-radius: 10px; display: grid; place-items: center; color: #fff; font-weight: 800; }
.mark.pp { background: #003087; }
.mark.bank { background: #F3EFEA; color: #1C2430; }
.fee { display: flex; gap: 8px; background: #FFF6F3; border-radius: 14px; padding: 12px; margin: 8px 0 14px; }
.fee b { color: #F96141; display: block; }
.fee p { margin: 4px 0 0; color: #5C6570; font-size: 13px; }
</style>
