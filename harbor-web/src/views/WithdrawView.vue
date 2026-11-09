<template>
  <div class="page" data-figma="1:39">
    <header class="head">
      <button type="button" class="back" @click="$router.back()" :aria-label="zh ? '返回' : 'back'">
        <ChevronLeft :size="22" :stroke-width="1.75" />
      </button>
      <h1>{{ zh ? '提现' : 'Withdraw balance' }}</h1>
    </header>

    <div class="brand">
      <span class="mark" aria-hidden="true"><Home :size="18" :stroke-width="2.25" /></span>
      <b>Harbor</b>
      <p>{{ zh ? '跨境家居，更好价格。' : 'Everyday home goods. Better value.' }}</p>
    </div>

    <section class="bal">
      <span class="wallet"><Wallet :size="20" :stroke-width="1.75" /></span>
      <div>
        <div class="k">{{ zh ? '可提现余额' : 'Available balance' }}</div>
        <div class="v">{{ balance }}</div>
        <p v-if="signedOut" class="need">{{ zh ? '登录后查看返利余额' : 'Sign in to see your rebate balance' }}</p>
      </div>
    </section>

    <label class="block">
      <span class="lab">{{ zh ? '金额' : 'Amount' }}</span>
      <span class="amt">
        <span class="cur">$</span>
        <input v-model="amount" inputmode="decimal" :placeholder="zh ? '输入金额' : 'Enter amount'" />
        <span class="range">{{ rangeHint }}</span>
      </span>
    </label>

    <div class="block">
      <div class="lab">{{ zh ? '收款方式' : 'Payout method' }}</div>
      <p class="sub">{{ zh ? '选择收款方式。' : "Choose how you'd like to receive your funds." }}</p>
      <button type="button" class="opt" :class="{ on: method === 'paypal' }" @click="method = 'paypal'">
        <span class="pp">P</span>
        <span class="copy"><b>PayPal</b><small>{{ zh ? '快速安全' : 'Fast and secure' }}</small></span>
        <span class="radio" :class="{ on: method === 'paypal' }" />
      </button>
      <button type="button" class="opt" :class="{ on: method === 'bank' }" @click="method = 'bank'">
        <span class="bank"><Landmark :size="18" :stroke-width="1.75" /></span>
        <span class="copy"><b>{{ zh ? '银行转账' : 'Bank transfer' }}</b><small>{{ zh ? '通常 1–3 个工作日' : 'Typically takes 1–3 business days' }}</small></span>
        <span class="radio" :class="{ on: method === 'bank' }" />
      </button>
      <label class="acct">
        <span>{{ method === 'paypal' ? (zh ? 'PayPal 邮箱' : 'PayPal email') : (zh ? '收款账号' : 'Account') }}</span>
        <input v-model="payout" :placeholder="method === 'paypal' ? 'you@email.com' : (zh ? '银行卡号' : 'Account number')" />
      </label>
    </div>

    <section class="note">
      <Info :size="16" :stroke-width="1.75" />
      <div>
        <b>{{ zh ? '提现说明' : 'Withdrawal note' }}</b>
        <p>{{ noteText }}</p>
      </div>
    </section>

    <p v-if="msg" class="msg" :class="{ bad: msgBad }">{{ msg }}</p>
    <button type="button" class="cta" :disabled="busy || !canSubmit" @click="submit">
      {{ busy ? (zh ? '提交中…' : '…') : (zh ? '确认提现' : 'Confirm withdraw') }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { ChevronLeft, Home, Info, Landmark, Wallet } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import { fetchWithdrawHtml, parseBalanceHtml, postWithdraw } from '@/api/accountApi'
import { useI18n } from '@/composables/i18n'

const { lang } = useI18n()
const zh = computed(() => String(lang.value).startsWith('zh'))
const balance = ref('—')
const balanceNum = ref(NaN)
const serverNote = ref('')
const payout = ref('')
const amount = ref('')
const method = ref<'paypal' | 'bank'>('paypal')
const busy = ref(false)
const msg = ref('')
const msgBad = ref(false)

function dollars(raw: string): number {
  const m = String(raw || '').replace(/,/g, '').match(/-?\d+(?:\.\d+)?/)
  return m ? Number(m[0]) : NaN
}

const amountNum = computed(() => dollars(amount.value))
const rangeHint = computed(() => {
  const max = Number.isFinite(balanceNum.value) ? `$${balanceNum.value.toFixed(2)}` : (zh.value ? '余额' : 'balance')
  return `$10.00 – ${max}`
})
const canSubmit = computed(() => amountNum.value >= 10 && payout.value.trim().length > 3)
const signedOut = computed(() => /登录|sign in|login/i.test(serverNote.value))
const noteText = computed(() => (
  zh.value
    ? '满 $10.00 可申请。提交后从可提现余额划出，到账时间视收款方式而定。'
    : 'Minimum $10.00. The amount leaves your available balance when you submit. Timing depends on the payout method.'
))

onMounted(async () => {
  try {
    const b = parseBalanceHtml(await fetchWithdrawHtml())
    balance.value = b.balanceText || '—'
    balanceNum.value = dollars(b.balanceText)
    serverNote.value = b.note || ''
  } catch { /* keep placeholder */ }
})

async function submit() {
  if (!canSubmit.value || busy.value) return
  if (Number.isFinite(balanceNum.value) && amountNum.value > balanceNum.value + 0.001) {
    msgBad.value = true
    msg.value = zh.value ? '超过可提现余额' : 'Amount is above the available balance'
    return
  }
  busy.value = true
  msg.value = ''
  try {
    const cents = String(Math.round(amountNum.value * 100))
    const account = `${method.value === 'paypal' ? 'PayPal' : 'Bank'} · ${payout.value.trim()}`
    const res = await postWithdraw(account, cents)
    msgBad.value = res.statusCode >= 400
    msg.value = res.statusCode < 400
      ? (zh.value ? '已提交' : 'Submitted')
      : (zh.value ? '提交失败，请检查金额和收款账号' : 'Could not submit. Check the amount and account.')
  } catch {
    msgBad.value = true
    msg.value = zh.value ? '网络错误' : 'Network error'
  } finally {
    busy.value = false
  }
}
</script>

<style lang="scss" scoped>
@import '@/styles/theme.scss';
.page {
  min-height: 100vh; background: $hb-paper; color: $hb-ink;
  padding: calc(8px + env(safe-area-inset-top)) 16px 28px;
}
.head { display: grid; grid-template-columns: 36px 1fr 36px; align-items: center; margin-bottom: 8px; }
.back { width: 36px; height: 36px; border: 0; background: transparent; color: $hb-ink; cursor: pointer; display: grid; place-items: center; }
h1 { margin: 0; text-align: center; font-size: 18px; font-weight: 800; }
.brand { text-align: center; margin: 8px 0 16px; }
.mark {
  width: 36px; height: 36px; margin: 0 auto 4px; border-radius: 10px; background: $hb-coral; color: #fff;
  display: grid; place-items: center;
}
.brand b { color: $hb-coral; font-size: 28px; letter-spacing: -0.04em; }
.brand p { margin: 4px 0 0; color: $hb-muted; font-size: 13px; }
.bal {
  display: flex; align-items: center; gap: 12px; background: $hb-coral-soft; border-radius: 18px; padding: 16px;
}
.wallet {
  width: 48px; height: 48px; border-radius: 16px; background: #fff; color: $hb-coral;
  display: grid; place-items: center; flex: 0 0 auto;
}
.k { font-size: 13px; color: #5C6570; }
.v { font-size: 28px; font-weight: 800; letter-spacing: -0.03em; line-height: 1.15; }
.need { margin: 2px 0 0; font-size: 12px; color: $hb-muted; }
.block { display: block; margin-top: 16px; }
.lab { display: block; font-size: 15px; font-weight: 800; margin-bottom: 8px; }
.sub { margin: -4px 0 8px; color: $hb-muted; font-size: 12px; }
.amt {
  display: flex; align-items: center; gap: 8px; height: 48px; padding: 0 12px;
  background: #fff; border: 1px solid $hb-line; border-radius: 14px;
}
.cur { color: $hb-muted; font-weight: 700; }
.amt input { flex: 1; min-width: 0; border: 0; outline: 0; background: transparent; font-size: 15px; color: $hb-ink; }
.range { color: $hb-muted; font-size: 12px; white-space: nowrap; }
.opt {
  width: 100%; margin-top: 8px; border: 1.5px solid $hb-line; background: #fff; border-radius: 14px;
  padding: 12px; display: flex; align-items: center; gap: 10px; text-align: left; cursor: pointer; color: $hb-ink;
}
.opt.on { border-color: $hb-coral; background: #FFF8F5; }
.copy { flex: 1; display: flex; flex-direction: column; }
.copy b { font-size: 14px; }
.copy small { color: $hb-muted; font-size: 12px; margin-top: 2px; }
.pp, .bank {
  width: 32px; height: 32px; border-radius: 10px; display: grid; place-items: center; flex: 0 0 auto;
  background: #F4F7FB; color: #003087; font-weight: 800;
}
.bank { color: $hb-ink; }
.radio {
  width: 18px; height: 18px; border-radius: 50%; border: 2px solid #D9D3CB; box-sizing: border-box;
}
.radio.on { border-color: $hb-coral; background: $hb-coral; box-shadow: inset 0 0 0 3px #fff; }
.acct { display: block; margin-top: 10px; }
.acct span { display: block; font-size: 12px; color: $hb-muted; font-weight: 650; margin-bottom: 6px; }
.acct input {
  width: 100%; height: 44px; border-radius: 12px; border: 1px solid $hb-line; padding: 0 12px;
  background: #fff; color: $hb-ink; font-size: 14px;
}
.note {
  margin-top: 14px; background: $hb-coral-soft; border-radius: 16px; padding: 12px; display: flex; gap: 8px; color: $hb-coral;
}
.note b { display: block; font-size: 13px; }
.note p { margin: 4px 0 0; color: #5C6570; font-size: 12px; line-height: 1.45; }
.msg { margin: 12px 0 0; font-size: 13px; color: $hb-success; }
.msg.bad { color: #B91C1C; }
.cta {
  width: 100%; height: 52px; margin-top: 16px; border: 0; border-radius: 14px; background: $hb-coral; color: #fff;
  font-size: 16px; font-weight: 750; cursor: pointer;
}
.cta:disabled { opacity: 0.55; }
</style>
