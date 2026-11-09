<template>
  <div class="page" data-figma="1:6">
    <header class="head">
      <button type="button" class="back" @click="$router.back()" :aria-label="zh ? '返回' : 'back'">
        <ChevronLeft :size="22" :stroke-width="1.75" />
      </button>
      <h1>{{ zh ? '结算' : 'Checkout' }}</h1>
      <div class="secure"><Lock :size="14" :stroke-width="1.75" /> {{ zh ? '安全结算' : 'Secure Checkout' }}</div>
    </header>

    <section class="card">
      <div class="card-h">
        <MapPin :size="16" :stroke-width="1.75" class="ico" />
        <b>{{ zh ? '收货地址' : 'Shipping Address' }}</b>
        <button type="button" class="link" @click="addrSheet = true">{{ zh ? '修改' : 'Edit' }}</button>
      </div>
      <button type="button" class="addr" @click="addrSheet = true">
        <span v-if="form.name">
          <b>{{ form.name }}</b><br />
          {{ form.address }}<template v-if="form.city">，{{ form.city }}</template>
          <template v-if="form.region"> {{ form.region }}</template>
          {{ form.postal }}<br />
          {{ countryName }}<template v-if="form.phone"> · {{ form.phone }}</template>
        </span>
        <span v-else class="muted">{{ zh ? '还没有收货地址' : 'No address yet' }}</span>
        <ChevronRight :size="18" class="chev" />
      </button>
    </section>

    <section class="card">
      <div class="card-h">
        <Truck :size="16" :stroke-width="1.75" class="ico" />
        <b>{{ zh ? '配送方式' : 'Shipping Method' }}</b>
      </div>
      <button
        v-for="opt in ships"
        :key="opt.id"
        type="button"
        class="opt"
        :class="{ on: shipId === opt.id }"
        @click="shipId = opt.id"
      >
        <span class="radio" :class="{ on: shipId === opt.id }" />
        <span class="opt-copy">
          <b>{{ zh ? opt.zh : opt.en }}</b>
          <small>{{ zh ? opt.daysZh : opt.daysEn }}</small>
        </span>
        <span class="opt-price">{{ zh ? opt.priceZh : opt.priceEn }}</span>
      </button>
    </section>

    <section class="card">
      <div class="card-h">
        <Ticket :size="16" :stroke-width="1.75" class="ico" />
        <b>{{ zh ? '使用优惠券' : 'Apply Coupon' }}</b>
      </div>
      <div class="coupon">
        <input v-model="form.coupon_code" :placeholder="zh ? '输入优惠码' : 'Enter coupon code'" />
        <button type="button" class="apply" @click="couponOn = true">{{ zh ? '使用' : 'Apply' }}</button>
      </div>
      <p v-if="couponOn && form.coupon_code" class="hint">{{ zh ? '已记下优惠码，提交时一并带上' : 'Code will be sent with the order' }}</p>
    </section>

    <section class="card">
      <div class="card-h">
        <Gift :size="16" :stroke-width="1.75" class="ico" />
        <b>{{ zh ? '礼物选项' : 'Gift Option' }}</b>
        <button type="button" class="toggle" :class="{ on: giftOn }" @click="giftOn = !giftOn" :aria-label="zh ? '礼物' : 'gift'">
          <span class="knob" />
        </button>
      </div>
      <button type="button" class="gift-row" @click="giftOn = !giftOn">
        <Gift :size="16" />
        <span>{{ zh ? '添加赠言（可选）' : 'Add gift message (optional)' }}</span>
        <ChevronRight :size="16" />
      </button>
      <textarea v-if="giftOn" v-model="form.gift" rows="3" :placeholder="zh ? '写给收件人的话' : 'A note for the recipient'" />
    </section>

    <section class="card">
      <div class="card-h">
        <CreditCard :size="16" :stroke-width="1.75" class="ico" />
        <b>{{ zh ? '支付方式' : 'Payment Method' }}</b>
      </div>
      <button type="button" class="opt" :class="{ on: form.pay_method === 'card' }" @click="form.pay_method = 'card'">
        <span class="radio" :class="{ on: form.pay_method === 'card' }" />
        <CreditCard :size="18" class="pay-ico" />
        <span class="opt-copy">
          <b>{{ zh ? '信用卡 / 借记卡' : 'Credit / Debit Card' }}</b>
          <small>Visa、Mastercard、Amex</small>
        </span>
        <span class="brands"><i>VISA</i><i>MC</i><i>AE</i></span>
      </button>
      <button type="button" class="opt" :class="{ on: form.pay_method === 'paypal' }" @click="form.pay_method = 'paypal'">
        <span class="radio" :class="{ on: form.pay_method === 'paypal' }" />
        <span class="pp" aria-hidden="true"><b>Pay</b><b>Pal</b></span>
        <span class="opt-copy">
          <b>PayPal</b>
          <small>{{ zh ? '使用 PayPal 账户支付' : 'Pay with your PayPal account' }}</small>
        </span>
      </button>
      <button type="button" class="opt" :class="{ on: form.pay_method === 'lianlian' }" @click="form.pay_method = 'lianlian'">
        <span class="radio" :class="{ on: form.pay_method === 'lianlian' }" />
        <Wallet :size="18" class="pay-ico" />
        <span class="opt-copy">
          <b>{{ zh ? '连连钱包' : 'LianLian Wallet' }}</b>
          <small>{{ zh ? '连连支付' : 'LianLian' }}</small>
        </span>
        <span class="ll">连连</span>
      </button>
      <div class="bal-row">
        <span>{{ zh ? '使用余额抵扣' : 'Use balance' }}</span>
        <button type="button" class="toggle" :class="{ on: form.use_balance }" @click="form.use_balance = !form.use_balance" :aria-label="zh ? '余额' : 'balance'">
          <span class="knob" />
        </button>
      </div>
    </section>

    <section class="card">
      <div class="card-h">
        <Receipt :size="16" :stroke-width="1.75" class="ico" />
        <b>{{ zh ? '订单摘要' : 'Order Summary' }}</b>
      </div>
      <div class="sum"><span>{{ zh ? `商品小计（${lines.length} 件）` : `Subtotal (${lines.length} items)` }}</span><span>{{ money(subtotal) }}</span></div>
      <div class="sum"><span>{{ zh ? '运费' : 'Shipping' }}</span><span>{{ zh ? '免费' : 'Free' }}</span></div>
      <div class="sum">
        <span>{{ zh ? '优惠' : 'Coupon' }}</span>
        <span :class="{ off: couponOn && form.coupon_code }">{{ couponOn && form.coupon_code ? form.coupon_code : (zh ? '未使用' : 'None') }}</span>
      </div>
      <div class="sum total"><span>{{ zh ? '合计' : 'Total' }}</span><span class="due">{{ money(subtotal) }}</span></div>
      <p class="hint">{{ zh ? '可追踪物流 · 预计 7–12 天 · 包邮' : 'Tracked shipping · est. 7–12 days · free' }}</p>
    </section>

    <p v-if="error" class="err">{{ error }}</p>
    <p v-if="!lines.length" class="err">{{ t('checkout_empty') }}</p>

    <button type="button" class="place" :disabled="!lines.length || busy" @click="place">
      <Lock :size="16" :stroke-width="1.75" />
      {{ busy ? (zh ? '提交中…' : '…') : (zh ? '提交订单' : 'Place Order') }}
    </button>
    <p class="legal">
      {{ zh ? '提交订单即表示同意' : 'By placing your order, you agree to our' }}
      <router-link to="/policy/terms">{{ zh ? '服务条款' : 'Terms of Service' }}</router-link>
      {{ zh ? '和' : 'and' }}
      <router-link to="/policy/privacy">{{ zh ? '隐私政策' : 'Privacy Policy' }}</router-link>
    </p>

    <div v-if="addrSheet" class="addr-mask" @click.self="addrSheet = false">
      <div class="addr-sheet" role="dialog" :aria-label="zh ? '收货地址' : 'Shipping address'">
        <h2>{{ zh ? '收货地址' : 'Shipping address' }}</h2>
        <label class="field"><span>{{ zh ? '邮箱' : 'Email' }}</span><input v-model="form.email" type="email" autocomplete="email" /></label>
        <label class="field"><span>{{ zh ? '姓名' : 'Name' }}</span><input v-model="form.name" autocomplete="name" /></label>
        <label class="field"><span>{{ zh ? '地址' : 'Address' }}</span><input v-model="form.address" autocomplete="street-address" /></label>
        <label class="field"><span>{{ zh ? '城市' : 'City' }}</span><input v-model="form.city" autocomplete="address-level2" /></label>
        <label class="field"><span>{{ zh ? '地区' : 'Region' }}</span><input v-model="form.region" autocomplete="address-level1" /></label>
        <label class="field"><span>{{ zh ? '邮编' : 'Postal' }}</span><input v-model="form.postal" autocomplete="postal-code" /></label>
        <label class="field"><span>{{ zh ? '电话' : 'Phone' }}</span><input v-model="form.phone" autocomplete="tel" /></label>
        <label class="field"><span>{{ zh ? '国家' : 'Country' }}</span>
          <select v-model="form.ship_country">
            <option value="US">United States</option>
            <option value="CN">中国</option>
            <option value="TW">台湾</option>
            <option value="HK">香港</option>
            <option value="GB">United Kingdom</option>
            <option value="CA">Canada</option>
            <option value="JP">日本</option>
          </select>
        </label>
        <button type="button" class="place" @click="addrSheet = false">{{ zh ? '完成' : 'Done' }}</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ChevronLeft, ChevronRight, CreditCard, Gift, Lock, MapPin, Receipt, Ticket, Truck, Wallet } from 'lucide-vue-next'
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { money } from '@/api/products'
import { useCart } from '@/composables/cart'
import { useI18n } from '@/composables/i18n'
import { submitCheckoutForm } from '@/api/accountApi'

const { t, lang } = useI18n()
const zh = computed(() => String(lang.value).startsWith('zh'))
const addrSheet = ref(false)
const giftOn = ref(false)
const couponOn = ref(false)
const shipId = ref('economy')
const ships = [
  { id: 'express', zh: '加急配送', en: 'Express Shipping', daysZh: '3–5 个工作日', daysEn: '3–5 business days', priceZh: '优先', priceEn: 'Priority' },
  { id: 'standard', zh: '标准配送', en: 'Standard Shipping', daysZh: '7–12 个工作日', daysEn: '7–12 business days', priceZh: '可追踪', priceEn: 'Tracked' },
  { id: 'economy', zh: '经济配送', en: 'Economy Shipping', daysZh: '12–18 个工作日', daysEn: '12–18 business days', priceZh: '免费', priceEn: 'Free' },
]
const cart = useCart()
const router = useRouter()
const lines = computed(() => cart.lines.value)
const subtotal = computed(() => cart.subtotal.value)
const busy = ref(false)
const error = ref('')
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
  pay_method: 'card',
  use_balance: true,
  coupon_code: '',
  gift: '',
  buy: '',
  submit_id: '',
})
const countryName = computed(() => {
  const map: Record<string, string> = {
    US: zh.value ? '美国' : 'United States',
    CN: '中国',
    TW: '台湾',
    HK: '香港',
    GB: zh.value ? '英国' : 'United Kingdom',
    CA: zh.value ? '加拿大' : 'Canada',
    JP: '日本',
  }
  return map[form.ship_country] || form.ship_country
})

onMounted(async () => {
  form.submit_id = 'h5-' + Date.now().toString(36) + Math.random().toString(36).slice(2, 8)
  try {
    await cart.syncLocalToServer()
  } catch {
    try { await cart.refreshFromServer() } catch { /* */ }
  }
})

async function place() {
  if (!lines.value.length || busy.value) return
  if (!form.email.includes('@') || !form.name.trim() || !form.address.trim() || !form.city.trim() || !form.postal.trim()) {
    error.value = zh.value ? '请先填写邮箱和收货地址' : 'Add an email and shipping address'
    addrSheet.value = true
    return
  }
  busy.value = true
  error.value = ''
  try {
    try { await cart.syncLocalToServer() } catch { /* continue */ }
    const res = await submitCheckoutForm({
      email: form.email,
      name: form.name,
      address: form.address,
      city: form.city,
      region: form.region,
      postal: form.postal,
      ship_country: form.ship_country,
      phone: form.phone,
      street_number: form.street_number,
      district: form.district,
      pay_method: form.pay_method,
      use_balance: form.use_balance ? '1' : '',
      coupon_code: couponOn.value ? form.coupon_code : '',
      gift: giftOn.value ? form.gift : '',
      buy: form.buy,
      submit_id: form.submit_id,
    })
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
    error.value = zh.value ? '下单未通过校验，请检查地址和邮箱' : 'Checkout was not accepted. Check the address and email.'
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    busy.value = false
  }
}
</script>

<style lang="scss" scoped>
@import '@/styles/theme.scss';
.page {
  min-height: 100vh; background: $hb-paper; color: $hb-ink;
  padding: calc(8px + env(safe-area-inset-top)) 16px 32px;
}
.head { display: grid; grid-template-columns: 40px 1fr auto; align-items: center; gap: 8px; margin-bottom: 14px; }
.back {
  width: 36px; height: 36px; border: 0; border-radius: 12px; background: #fff; color: $hb-ink;
  display: inline-flex; align-items: center; justify-content: center; box-shadow: $hb-shadow-soft; cursor: pointer;
}
h1 { margin: 0; text-align: center; font-size: 18px; font-weight: 800; }
.secure { display: inline-flex; align-items: center; gap: 4px; color: $hb-muted; font-size: 12px; font-weight: 650; }
.card {
  background: #fff; border-radius: 18px; padding: 14px; margin-bottom: 12px; box-shadow: $hb-shadow-soft;
}
.card-h { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.card-h b { flex: 1; font-size: 15px; }
.ico { color: $hb-coral; }
.link { border: 0; background: transparent; color: $hb-coral; font-weight: 750; cursor: pointer; font-size: 13px; }
.addr {
  width: 100%; border: 0; background: transparent; display: flex; align-items: center; gap: 8px;
  text-align: left; color: $hb-ink; font-size: 13px; line-height: 1.45; cursor: pointer; padding: 0;
}
.addr b { font-size: 14px; }
.muted { color: $hb-muted; }
.chev { margin-left: auto; color: $hb-muted; flex: 0 0 auto; }
.opt {
  width: 100%; border: 0; background: transparent; border-radius: 14px; padding: 12px 10px;
  display: flex; align-items: center; gap: 10px; text-align: left; cursor: pointer; color: $hb-ink;
}
.opt.on { background: $hb-coral-soft; }
.opt + .opt { margin-top: 4px; }
.radio {
  width: 18px; height: 18px; border-radius: 50%; border: 2px solid #D9D3CB; flex: 0 0 auto; box-sizing: border-box;
}
.radio.on { border-color: $hb-coral; background: $hb-coral; box-shadow: inset 0 0 0 3px #fff; }
.opt-copy { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.opt-copy b { font-size: 14px; }
.opt-copy small { color: $hb-muted; font-size: 12px; margin-top: 2px; }
.opt-price { font-weight: 750; font-size: 14px; color: $hb-ink; }
.coupon { display: flex; gap: 8px; }
.coupon input, .field input, .field select, textarea {
  width: 100%; border: 1px solid $hb-line; border-radius: 12px; background: #fff; color: $hb-ink;
  font-size: 14px; padding: 0 12px;
}
.coupon input { height: 44px; flex: 1; }
.apply {
  height: 44px; padding: 0 16px; border: 0; border-radius: 12px; background: $hb-coral; color: #fff;
  font-weight: 750; cursor: pointer;
}
.hint { margin: 8px 0 0; font-size: 12px; color: $hb-muted; line-height: 1.45; }
.toggle {
  width: 44px; height: 26px; border-radius: 13px; border: 0; background: #E4DFD8; position: relative; cursor: pointer;
}
.toggle.on { background: $hb-coral; }
.knob {
  position: absolute; top: 3px; left: 3px; width: 20px; height: 20px; border-radius: 50%; background: #fff; transition: left .15s;
}
.toggle.on .knob { left: 21px; }
.gift-row {
  width: 100%; border: 0; background: transparent; display: flex; align-items: center; gap: 8px;
  color: $hb-muted; font-size: 13px; cursor: pointer; padding: 4px 0 0;
}
.gift-row span { flex: 1; text-align: left; }
textarea { margin-top: 10px; padding: 10px 12px; resize: vertical; min-height: 72px; }
.pay-ico { color: $hb-ink; }
.brands { display: flex; gap: 4px; }
.brands i {
  font-style: normal; font-size: 9px; font-weight: 800; letter-spacing: 0.02em;
  border: 1px solid $hb-line; border-radius: 4px; padding: 2px 4px; color: #5C6570;
}
.pp { font-weight: 800; font-size: 13px; letter-spacing: -0.03em; }
.pp b:first-child { color: #003087; }
.pp b:last-child { color: #009cde; }
.ll {
  background: #1F4BFF; color: #fff; font-size: 11px; font-weight: 800; border-radius: 6px; padding: 3px 6px;
}
.bal-row {
  display: flex; align-items: center; justify-content: space-between; margin-top: 8px;
  padding-top: 10px; border-top: 1px solid $hb-line; font-size: 13px; font-weight: 650;
}
.sum { display: flex; justify-content: space-between; gap: 12px; font-size: 13px; padding: 5px 0; color: $hb-ink; }
.sum.total { margin-top: 6px; padding-top: 10px; border-top: 1px solid $hb-line; font-weight: 750; }
.due { color: $hb-coral; font-size: 20px; font-weight: 800; }
.off { color: $hb-coral; font-weight: 700; }
.err { color: #B91C1C; font-size: 13px; margin: 8px 0; }
.place {
  width: 100%; height: 52px; border: 0; border-radius: 16px; background: $hb-coral; color: #fff;
  font-weight: 750; font-size: 16px; cursor: pointer; display: inline-flex; align-items: center; justify-content: center; gap: 8px;
  margin-top: 4px;
}
.place:disabled { opacity: 0.5; }
.legal { margin: 12px 0 0; text-align: center; color: $hb-muted; font-size: 12px; line-height: 1.5; }
.legal a { color: $hb-coral; font-weight: 700; }
.addr-mask {
  position: fixed; inset: 0; z-index: 70; background: rgba(28, 36, 48, 0.45);
  display: flex; align-items: flex-end; justify-content: center;
}
.addr-sheet {
  width: min(100%, 768px); background: #fff; border-radius: 20px 20px 0 0;
  padding: 16px 16px calc(16px + env(safe-area-inset-bottom)); max-height: 88vh; overflow: auto;
}
.addr-sheet h2 { margin: 0 0 12px; font-size: 18px; }
.field { display: flex; flex-direction: column; gap: 6px; margin-bottom: 10px; font-size: 11px; font-weight: 650; color: $hb-muted; }
.field input, .field select { height: 42px; }
.addr-sheet .place { margin-top: 4px; }
</style>
