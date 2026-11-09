<template>
  <AgShell tabs="me">
    <header class="head ag-top">
      <button type="button" class="ag-back" @click="router.back()" :aria-label="tx('返回', 'Back')"><ChevronLeft :size="26" :stroke-width="2.2" /></button>
      <h1>{{ tx('支付方式', 'Payment methods') }}</h1>
    </header>

    <div class="ag-pad">
      <p v-if="msg" class="ag-toast">{{ msg }}</p>
      <div v-if="loginRequired && !rows.length" class="ag-empty">
        <h3>{{ tx('登录后管理支付方式', 'Sign in to manage payment methods') }}</h3>
        <router-link class="ag-cta" style="margin-top:12px" :to="{ path: '/login', query: { next: '/payments' } }">{{ tx('登录', 'Sign in') }}</router-link>
      </div>
      <template v-else>
        <div class="label">{{ tx('已保存的卡', 'SAVED CARDS') }}</div>
        <div v-if="loading" class="ag-note">{{ tx('加载中…', 'Loading…') }}</div>
        <button v-for="(r, i) in rows" :key="i" type="button" class="row ag-card" @click="adding = 'card'">
          <span class="mark card">{{ (r.brand || 'Card').slice(0, 1) }}</span>
          <span class="mid">
            <b>{{ r.brand || tx('银行卡', 'Card') }} ···· {{ r.last4 || '••••' }}</b>
            <small>{{ tx('已保存', 'Saved') }}</small>
          </span>
          <span v-if="i === 0" class="def">{{ tx('默认', 'Default') }}</span>
          <ChevronRight :size="16" color="#C5C0BA" />
        </button>
        <p v-if="!loading && !rows.length" class="ag-note">{{ tx('还没有保存的卡。', 'No saved cards yet.') }}</p>

        <div class="label">{{ tx('已关联账户', 'LINKED ACCOUNTS') }}</div>
        <button type="button" class="row ag-card" @click="router.push('/checkout')">
          <span class="mark pp">P</span>
          <span class="mid"><b>PayPal</b><small>{{ tx('快速结账', 'Fast checkout') }}</small></span>
          <ChevronRight :size="16" color="#C5C0BA" />
        </button>
        <button type="button" class="row ag-card" @click="router.push('/checkout')">
          <span class="mark ll">连</span>
          <span class="mid"><b>LianLian</b><small>{{ tx('已支持的账户', 'Linked account') }}</small></span>
          <ChevronRight :size="16" color="#C5C0BA" />
        </button>
        <button type="button" class="row ag-card" @click="router.push('/balance')">
          <span class="mark wal"><Wallet :size="18" /></span>
          <span class="mid"><b>{{ tx('钱包余额', 'Wallet balance') }}</b><small>{{ balance }}</small></span>
          <ChevronRight :size="16" color="#C5C0BA" />
        </button>

        <div class="label">{{ tx('添加新的支付方式', 'ADD A NEW PAYMENT METHOD') }}</div>
        <button type="button" class="add" @click="adding = adding === 'card' ? '' : 'card'">
          <CreditCard :size="18" /> {{ tx('添加银行卡', 'Add card') }} <ChevronRight :size="16" />
        </button>
        <button type="button" class="add" @click="adding = adding === 'pp' ? '' : 'pp'">
          <span class="ppdot">P</span> {{ tx('添加 PayPal', 'Add PayPal') }} <ChevronRight :size="16" />
        </button>

        <form v-if="adding === 'card'" class="form ag-card" @submit.prevent="saveCard">
          <label class="ag-field"><span>{{ tx('卡组织', 'Brand') }}</span><input v-model="brand" placeholder="Visa" /></label>
          <label class="ag-field"><span>{{ tx('卡号后四位', 'Last 4') }}</span><input v-model="last4" maxlength="4" inputmode="numeric" /></label>
          <button class="ag-cta" type="submit" :disabled="busy">{{ tx('保存', 'Save') }}</button>
        </form>
        <form v-else-if="adding === 'pp'" class="form ag-card" @submit.prevent="savePaypal">
          <label class="ag-field"><span>PayPal</span><input v-model="paypal" placeholder="you@email.com" /></label>
          <button class="ag-cta" type="submit">{{ tx('保存到本机', 'Save on this device') }}</button>
        </form>
      </template>

      <div class="secure">
        <Shield :size="16" color="#F96141" />
        <p>{{ tx('你的支付信息已加密，受到保护。', 'Your payment information is secure and protected.') }}</p>
      </div>
    </div>
  </AgShell>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ChevronLeft, ChevronRight, CreditCard, Shield, Wallet } from 'lucide-vue-next'
import AgShell from '@/components/account/AgShell.vue'
import { addPaymentMethod, fetchBalancePanel, fetchPayments, type PayMethodRow } from '@/api/accountApi'
import { useZh } from '@/composables/zh'

const { tx } = useZh()
const router = useRouter()
const rows = ref<PayMethodRow[]>([])
const loading = ref(true)
const loginRequired = ref(false)
const adding = ref<'' | 'card' | 'pp'>('')
const brand = ref('Visa')
const last4 = ref('')
const paypal = ref('')
const busy = ref(false)
const msg = ref('')
const balance = ref(tx('查看余额', 'See balance'))

async function refresh() {
  loading.value = true
  try {
    const res = await fetchPayments()
    rows.value = res.rows
    loginRequired.value = res.loginRequired && !res.rows.length
  } finally { loading.value = false }
  try {
    const b = await fetchBalancePanel()
    if (b.balanceText && b.balanceText !== '—') balance.value = tx(`${b.balanceText} 可用`, `${b.balanceText} available`)
  } catch { /* ignore */ }
}
onMounted(refresh)

async function saveCard() {
  if (last4.value.replace(/\D/g, '').length < 4) { msg.value = tx('请填写后四位', 'Enter the last 4 digits'); return }
  busy.value = true
  msg.value = ''
  try {
    const res = await addPaymentMethod(brand.value || 'Card', last4.value.replace(/\D/g, '').slice(-4))
    msg.value = res.status === 401 ? tx('请先登录', 'Please sign in') : res.ok ? tx('已保存', 'Saved') : tx('保存失败', 'Could not save')
    if (res.ok) { adding.value = ''; last4.value = ''; await refresh() }
  } finally { busy.value = false }
}
function savePaypal() {
  if (!paypal.value.includes('@')) { msg.value = tx('请填写 PayPal 邮箱', 'Enter a PayPal email'); return }
  try { localStorage.setItem('harbor_paypal', paypal.value.trim()) } catch { /* ignore */ }
  msg.value = tx('PayPal 已记在本机', 'PayPal saved on this device')
  adding.value = ''
}
</script>

<style scoped>
.head { display: grid; grid-template-columns: 44px 1fr 44px; align-items: center; padding: 0 8px 8px; }
.head h1 { margin: 0; text-align: center; font-size: 18px; font-weight: 800; }
.label { margin: 16px 0 8px; font-size: 12px; letter-spacing: 0.08em; color: #8B919A; font-weight: 800; }
.row {
  width: 100%; display: flex; align-items: center; gap: 10px; padding: 12px; margin-bottom: 8px;
  text-align: left; cursor: pointer; color: inherit; border: 1px solid #F1ECE6;
}
.mark { width: 42px; height: 42px; border-radius: 12px; display: grid; place-items: center; font-weight: 800; color: #fff; flex: 0 0 auto; }
.mark.card { background: linear-gradient(135deg, #EB001B, #F79E1B); }
.mark.pp { background: #003087; }
.mark.ll { background: #2F6BFF; font-size: 14px; }
.mark.wal { background: #FFF1EC; color: #F96141; }
.mid { flex: 1; min-width: 0; }
.mid b { display: block; font-size: 15px; }
.mid small { color: #8B919A; font-size: 12px; }
.def { background: #F96141; color: #fff; border-radius: 999px; font-size: 12px; font-weight: 800; padding: 4px 8px; }
.add {
  width: 100%; height: 52px; border: 0; border-radius: 16px; background: #F96141; color: #fff;
  display: flex; align-items: center; gap: 10px; padding: 0 16px; font-weight: 750; font-size: 15px; cursor: pointer; margin-bottom: 10px;
}
.add :last-child { margin-left: auto; }
.ppdot { width: 22px; text-align: center; font-weight: 800; }
.form { padding: 12px; margin-bottom: 10px; }
.secure { display: flex; gap: 8px; align-items: flex-start; justify-content: center; margin-top: 22px; color: #8B919A; }
.secure p { margin: 0; font-size: 12.5px; text-align: center; max-width: 220px; }
</style>
