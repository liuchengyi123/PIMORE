<template>
  <div class="page" data-figma="M12">
    <header class="head">
      <button type="button" class="back" @click="$router.back()" aria-label="back"><ChevronLeft :size="22" :stroke-width="1.75" /></button>
      <h1>{{ zh ? '结算' : 'Checkout' }}</h1>
    </header>

    <div class="card ship">
      <div class="row between">
        <div class="sec">{{ zh ? '收货地址' : 'Ship to' }}</div>
        <button type="button" class="link" @click="focusShip">{{ zh ? '修改' : 'Change' }}</button>
      </div>
      <div class="addr" v-if="form.name">
        {{ form.name }}<br />
        {{ form.address }}{{ form.city ? ', ' + form.city : '' }}{{ form.region ? ', ' + form.region : '' }} {{ form.postal }}<br />
        {{ form.ship_country }}
      </div>
      <div class="addr muted" v-else>{{ zh ? '还没有地址' : 'No address yet' }}</div>
      <button type="button" class="link" @click="addrSheet = true">{{ zh ? '填写地址' : 'Address form' }}</button>
    </div>
    <div v-if="addrSheet" class="addr-mask" @click.self="addrSheet = false">
      <div class="addr-sheet" role="dialog">
        <h2>{{ zh ? '收货地址' : 'Shipping address' }}</h2>
        <label class="field"><span>{{ zh ? '邮箱' : 'Email' }}</span><input v-model="form.email" type="email" /></label>
        <label class="field"><span>{{ zh ? '姓名' : 'Name' }}</span><input v-model="form.name" /></label>
        <label class="field"><span>{{ zh ? '地址' : 'Address' }}</span><input v-model="form.address" /></label>
        <label class="field"><span>{{ zh ? '城市' : 'City' }}</span><input v-model="form.city" /></label>
        <label class="field"><span>{{ zh ? '地区' : 'Region' }}</span><input v-model="form.region" /></label>
        <label class="field"><span>{{ zh ? '邮编' : 'Postal' }}</span><input v-model="form.postal" /></label>
        <label class="field"><span>{{ zh ? '电话' : 'Phone' }}</span><input v-model="form.phone" /></label>
        <label class="field"><span>{{ zh ? '国家' : 'Country' }}</span>
          <select v-model="form.ship_country">
            <option value="US">US</option><option value="CN">CN</option><option value="TW">TW</option>
            <option value="HK">HK</option><option value="GB">GB</option><option value="CA">CA</option>
            <option value="JP">JP</option>
          </select>
        </label>
        <button type="button" class="place" @click="addrSheet = false">{{ zh ? '完成' : 'Done' }}</button>
      </div>
    </div>

    <form class="form" @submit.prevent="place">
      <div class="ship-fields">
      <label class="field"><span>{{ zh ? '邮箱' : 'Contact email' }}</span><input v-model="form.email" type="email" required /></label>
      <label class="field"><span>{{ zh ? '姓名' : 'Name' }}</span><input ref="nameEl" v-model="form.name" required /></label>
      <label class="field"><span>{{ zh ? '地址' : 'Address' }}</span><input v-model="form.address" required /></label>
      <div class="split">
        <label class="field"><span>{{ zh ? '城市' : 'City' }}</span><input v-model="form.city" required /></label>
        <label class="field"><span>{{ zh ? '地区' : 'Region' }}</span><input v-model="form.region" /></label>
      </div>
      <div class="split">
        <label class="field"><span>{{ zh ? '邮编' : 'Postal' }}</span><input v-model="form.postal" required /></label>
        <label class="field"><span>{{ zh ? '国家' : 'Country' }}</span>
          <select v-model="form.ship_country">
            <option value="US">US</option><option value="CN">CN</option><option value="TW">TW</option>
            <option value="HK">HK</option><option value="GB">GB</option><option value="CA">CA</option>
            <option value="DE">DE</option><option value="FR">FR</option><option value="ES">ES</option>
            <option value="PT">PT</option><option value="BR">BR</option><option value="MX">MX</option>
            <option value="JP">JP</option>
          </select>
        </label>
      </div>
      <label class="field"><span>{{ zh ? '电话' : 'Phone' }}</span><input v-model="form.phone" /></label>
      </div>

      <div class="card">
        <div class="row between">
          <div class="sec">{{ zh ? '优惠券' : 'Coupon' }}</div>
          <span class="link">{{ zh ? '选择' : 'Select' }} ›</span>
        </div>
        <div class="tiny" v-if="form.coupon_code">{{ form.coupon_code }}</div>
        <input class="coupon-in" v-model="form.coupon_code" :placeholder="zh ? '优惠码' : 'Code'" />
      </div>

      <div class="card">
        <div class="row between">
          <div class="sec">{{ zh ? '使用余额' : 'Use balance' }}</div>
          <button type="button" class="toggle" :class="{ on: form.use_balance }" @click="form.use_balance = !form.use_balance" aria-label="toggle balance">
            <span class="knob" />
          </button>
        </div>
        <div class="tiny">{{ zh ? '有余额时在付款时抵扣' : 'Applied at payment when available' }}</div>
      </div>

      <div class="card">
        <div class="sec" style="margin-bottom:10px">{{ zh ? '支付方式' : 'Pay with' }}</div>
        <label class="pay" :class="{ on: form.pay_method === 'paypal' }">
          <input v-model="form.pay_method" type="radio" value="paypal" /> PayPal
        </label>
        <label class="pay" :class="{ on: form.pay_method === 'card' }">
          <input v-model="form.pay_method" type="radio" value="card" /> {{ zh ? '银行卡 · Visa / Mastercard / Amex' : 'Card · Visa / Mastercard / Amex (Stripe)' }}
        </label>
        <label class="pay" :class="{ on: form.pay_method === 'lianlian' }">
          <input v-model="form.pay_method" type="radio" value="lianlian" /> LianLian
        </label>
      </div>

      <div class="card totals">
        <div class="row between tiny-row"><span class="tiny">{{ zh ? '商品' : 'Items' }}</span><span>{{ money(subtotal) }}</span></div>
        <div class="row between tiny-row"><span class="tiny">{{ zh ? '运费' : 'Shipping' }}</span><span>{{ zh ? '可追踪' : 'Tracked' }}</span></div>
        <div class="row between total-row"><span class="sec">{{ zh ? '合计' : 'Total' }}</span><span class="price">{{ money(subtotal) }}</span></div>
        <div class="tiny" style="margin-top:8px">{{ zh ? '可追踪物流 · 预计 7–12 天' : 'Tracked shipping · Est. 7–12 days' }}</div>
      </div>

      <p v-if="error" class="err">{{ error }}</p>
      <p v-if="!lines.length" class="err">{{ t('checkout_empty') }}</p>
    </form>

    <div class="dock">
      <div class="price">{{ money(subtotal) }}</div>
      <button type="button" class="place" :disabled="!lines.length || busy" @click="place">{{ busy ? '…' : (zh ? '提交订单' : 'Place order') }}</button>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ChevronLeft } from 'lucide-vue-next'
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { money } from '@/api/products'
import { useCart } from '@/composables/cart'
import { useI18n } from '@/composables/i18n'
import { checkoutUrl, submitCheckoutForm } from '@/api/accountApi'

const { t, lang } = useI18n()
const zh = computed(() => String(lang.value).startsWith('zh'))
const addrSheet = ref(false)
const cart = useCart()
const router = useRouter()
const lines = computed(() => cart.lines.value)
const subtotal = computed(() => cart.subtotal.value)
const busy = ref(false)
const error = ref('')
const nameEl = ref<HTMLInputElement | null>(null)
function focusShip() { nameEl.value?.focus() }
const form = reactive({
  email: '',
  name: '',
  address: '',
  city: '',
  region: '',
  postal: '',
  ship_country: 'US',
  phone: '',
  street_number: '',
  district: '',
  pay_method: 'paypal',
  use_balance: true,
  coupon_code: '',
  gift: '',
  buy: '',
  submit_id: '',
})

onMounted(async () => {
  form.submit_id = 'h5-' + Date.now().toString(36) + Math.random().toString(36).slice(2, 8)
  try {
    await cart.syncLocalToServer()
  } catch {
    try { await cart.refreshFromServer() } catch { /* */ }
  }
})

function openHtml() {
  window.location.href = checkoutUrl(false)
}

async function place() {
  if (!lines.value.length || busy.value) return
  busy.value = true
  error.value = ''
  try {
    try { await cart.syncLocalToServer() } catch { /* continue */ }
    const res = await submitCheckoutForm({ ...form })
    if (res.ok && res.orderId) {
      if (res.payUrl && /^https?:\/\//i.test(res.payUrl) && !/\/orders\//i.test(res.payUrl)) {
        window.location.href = res.payUrl
        return
      }
      router.replace({ path: '/order-success', query: { id: res.orderId } })
      return
    }
    if (res.ok && res.payUrl) {
      window.location.href = res.payUrl
      return
    }
    error.value = '下单未通过校验，请检查地址/邮箱或改用店铺结算页'
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    busy.value = false
  }
}
</script>
<style lang="scss" scoped>
@import '@/styles/theme.scss';
.page { min-height: 100vh; background: $hb-paper; padding: 8px 16px 120px; padding-top: calc(8px + env(safe-area-inset-top)); }
.ship-fields { display: none; }
.head { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
.back { width: 36px; height: 36px; border: 0; border-radius: 12px; background: var(--hb-surface); display: inline-flex; align-items: center; justify-content: center; color: $hb-ink; box-shadow: $hb-shadow-soft; }
h1 { margin: 0; font-size: 22px; font-weight: 800; color: $hb-ink; letter-spacing: -0.03em; }
.card { background: var(--hb-surface); border-radius: 16px; padding: 14px; margin-bottom: 12px; border: 0; box-shadow: 0 8px 20px rgba(28,36,48,0.05); }
.sec { font-weight: 700; font-size: 14px; color: $hb-ink; }
.row { display: flex; align-items: center; gap: 8px; }
.between { justify-content: space-between; }
.link { border: 0; background: transparent; color: var(--hb-primary); font-size: 13px; font-weight: 700; cursor: pointer; }
.addr { margin-top: 8px; font-size: 13px; color: $hb-ink; line-height: 1.45; }
.muted { color: $hb-muted; }
.field { display: flex; flex-direction: column; gap: 6px; margin-bottom: 10px; font-size: 11px; font-weight: 600; color: $hb-muted; }
.field input, .field select, .coupon-in {
  height: 42px; border-radius: 12px; border: 1px solid $hb-line; padding: 0 12px;
  font-size: 14px; color: $hb-ink; background: var(--hb-surface);
}
.split { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.tiny { font-size: 12px; color: $hb-muted; margin-top: 6px; }
.toggle {
  width: 40px; height: 24px; border-radius: 12px; border: 0; background: #E2E6EE; position: relative; cursor: pointer;
}
.toggle.on { background: $hb-coral; }
.knob {
  position: absolute; top: 3px; left: 3px; width: 18px; height: 18px; border-radius: 9px; background: var(--hb-surface); transition: left .15s;
}
.toggle.on .knob { left: 19px; }
.pay {
  display: flex; align-items: center; min-height: 48px; padding: 0 14px; border: 1px solid var(--hb-line); border-radius: 14px; margin-bottom: 8px;
  font-size: 14px; font-weight: 650; color: $hb-ink; cursor: pointer;
}
.pay.on { border-width: 2px; border-color: $hb-coral; background: var(--hb-primary-soft); }
.pay input { margin-right: 8px; }
.tiny-row { margin-bottom: 6px; font-size: 13px; color: $hb-ink; }
.total-row { margin-top: 8px; padding-top: 8px; border-top: 1px solid $hb-line; }
.price { font-size: 18px; font-weight: 800; color: $hb-price; }
.err { color: #B91C1C; font-size: 13px; margin: 8px 0; }
.dock {
  position: fixed; left: 50%; transform: translateX(-50%); width: min(100vw, 768px); bottom: 0; z-index: 20;
  background: var(--hb-surface); border-top: 1px solid var(--hb-line); padding: 12px 16px;
  display: flex; gap: 12px; align-items: center;
  padding-bottom: calc(12px + env(safe-area-inset-bottom));
  box-shadow: 0 -8px 24px rgba(28,36,48,0.06);
}
.dock .price { font-size: 20px; }
.place {
  flex: 1; height: 52px; border: 0; border-radius: 999px; background: var(--hb-primary); color: var(--hb-on-primary);
  font-weight: 700; font-size: 16px; cursor: pointer;
}
.place:disabled { opacity: .5; }
.addr-mask {
  position: fixed; inset: 0; z-index: 70; background: rgba(28,36,48,0.45);
  display: flex; align-items: flex-end; justify-content: center;
}
.addr-sheet {
  width: min(100%, 768px); background: var(--hb-surface); border-radius: 20px 20px 0 0;
  padding: 16px 16px calc(16px + env(safe-area-inset-bottom));
}
.addr-sheet h2 { margin: 0 0 10px; font-size: 18px; }
.addr-sheet .place { width: 100%; margin-top: 8px; }
</style>
