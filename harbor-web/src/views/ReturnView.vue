<template>
  <div class="page" data-figma="1:29">
    <header class="hero">
      <button type="button" class="back" aria-label="back" @click="$router.back()"><ChevronLeft :size="22" :stroke-width="2.2" /></button>
      <div class="brand">
        <div class="logo"><Home :size="14" :stroke-width="2.4" /> Harbor</div>
        <div class="tag">{{ zh ? '每日家居好物' : 'EVERYDAY HOME GOODS' }}</div>
        <div class="range">$1 – $10</div>
      </div>
    </header>

    <div class="body">
      <h1>{{ zh ? '申请退货' : 'Request a return' }}</h1>
      <p class="lead">{{ zh ? '选择要退的商品并告诉我们原因，其余的交给我们。' : "Select the item(s) you'd like to return and tell us the reason. We'll take care of the rest." }}</p>

      <section class="prog" :aria-label="zh ? '售后进度' : 'Return progress'">
        <div class="rail" aria-hidden="true"><i :style="{ width: progRail }" /></div>
        <div v-for="(label, i) in progSteps" :key="label" class="pstep" :class="{ on: i <= progAt, now: i === progAt }">
          <span class="pdot">
            <Check v-if="i < progAt" :size="13" :stroke-width="2.8" />
            <template v-else>{{ i + 1 }}</template>
          </span>
          <b>{{ label }}</b>
        </div>
      </section>

      <label v-if="!orderLocked" class="order-field">
        <span>{{ zh ? '订单号' : 'Order' }}</span>
        <input v-model="orderId" :placeholder="zh ? '订单号' : 'Order number'" @change="loadItems" />
      </label>

      <div v-if="done" class="done">
        <b>{{ zh ? '退货已提交' : 'Return submitted' }}</b>
        <p>{{ zh ? '我们会按你选择的方式处理。' : 'We will follow the refund method you picked.' }}</p>
        <button type="button" class="submit" @click="goOrder">{{ zh ? '返回订单' : 'Back to order' }}</button>
      </div>

      <form v-else @submit.prevent="submit">
        <div class="sec-row">
          <b>{{ zh ? '退货商品' : 'Items to return' }}</b>
          <span>{{ zh ? `已选 ${selectedCount}` : `${selectedCount} selected` }}</span>
        </div>
        <div v-if="loading" class="muted">{{ zh ? '加载中…' : 'Loading…' }}</div>
        <div v-else-if="!items.length" class="muted">{{ zh ? '没有可退的商品，仍可以提交原因。' : 'No items loaded. You can still submit a reason.' }}</div>
        <label v-for="item in items" :key="item.key" class="item" :class="{ on: item.on }">
          <input v-model="item.on" type="checkbox" />
          <span class="box" aria-hidden="true"><Check v-if="item.on" :size="14" :stroke-width="3" /></span>
          <img v-if="item.image" :src="item.image" alt="" />
          <span v-else class="ph">{{ item.name.slice(0, 1) }}</span>
          <span class="meta">
            <b>{{ item.name }}</b>
            <small v-if="item.option">{{ item.option }}</small>
            <strong v-if="item.price">{{ item.price }}</strong>
          </span>
          <span class="qty">{{ zh ? '数量' : 'Qty' }} {{ item.qty }}</span>
        </label>

        <div class="sec">{{ zh ? '退货原因' : 'Reason for return' }}</div>
        <button type="button" class="select" @click="reasonOpen = !reasonOpen">
          <span>{{ reasonLabel }}</span>
          <ChevronDown :size="18" />
        </button>
        <div v-if="reasonOpen" class="menu">
          <button v-for="opt in reasons" :key="opt.id" type="button" :class="{ on: reason === opt.id }" @click="pickReason(opt.id)">
            {{ opt.label }}
            <Check v-if="reason === opt.id" :size="16" />
          </button>
        </div>

        <div class="sec flat">{{ zh ? '添加照片' : 'Add photos' }} <span>{{ zh ? '（选填）' : '(optional)' }}</span></div>
        <p class="hint">{{ zh ? '拍下问题，最多 3 张。' : 'Show the issue. Up to 3 photos.' }}</p>
        <div class="photos">
          <button v-for="slot in 3" :key="slot" type="button" class="photo" @click="pickPhoto(slot - 1)">
            <img v-if="photos[slot - 1]" :src="photos[slot - 1]" alt="" />
            <template v-else>
              <Camera :size="18" />
              <span>{{ zh ? '点击添加' : 'Tap to add photo' }}</span>
            </template>
          </button>
        </div>
        <input ref="fileEl" class="file" type="file" accept="image/*" @change="onPhoto" />

        <div class="sec">{{ zh ? '退款方式' : 'Refund method' }}</div>
        <p class="hint">{{ zh ? '选择退款到哪里。' : "Choose how you'd like to receive your refund." }}</p>
        <label class="method" :class="{ on: refund === 'original' }">
          <input v-model="refund" type="radio" value="original" />
          <span class="radio" />
          <CreditCard :size="18" />
          <span>
            <b>{{ zh ? '原支付方式' : 'Original payment method' }}</b>
            <small>{{ payHint }}</small>
          </span>
        </label>
        <label class="method" :class="{ on: refund === 'wallet' }">
          <input v-model="refund" type="radio" value="wallet" />
          <span class="radio" />
          <Wallet :size="18" />
          <span>
            <b>{{ zh ? '钱包余额' : 'Wallet balance' }}</b>
            <small>{{ zh ? '立即退回 Harbor 钱包' : 'Instant credit to your Harbor Wallet' }}</small>
          </span>
        </label>

        <p v-if="error" class="err">{{ error }}</p>
        <button class="submit" type="submit" :disabled="busy">{{ busy ? '…' : (zh ? '提交退货' : 'Submit return') }}</button>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Camera, Check, ChevronDown, ChevronLeft, CreditCard, Home, Wallet } from 'lucide-vue-next'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { fetchInvoiceHtml, fetchOrderDetail, parseInvoiceHtml, postOrderReturn } from '@/api/accountApi'
import { getProduct } from '@/api/products'
import { useI18n } from '@/composables/i18n'

interface ReturnItem {
  key: string
  name: string
  option: string
  qty: number
  price: string
  image?: string
  on: boolean
}

const { lang } = useI18n()
const zh = computed(() => String(lang.value).startsWith('zh'))
const route = useRoute()
const router = useRouter()
const orderId = ref(String(route.query.order || route.query.id || ''))
const orderLocked = computed(() => Boolean(route.query.order || route.query.id))
const items = ref<ReturnItem[]>([])
const loading = ref(false)
const reason = ref('')
const reasonOpen = ref(false)
const refund = ref<'original' | 'wallet'>('original')
const payHint = ref('')
const photos = ref<string[]>([])
const photoSlot = ref(0)
const fileEl = ref<HTMLInputElement | null>(null)
const error = ref('')
const busy = ref(false)
const done = ref(false)

const reasons = computed(() => zh.value
  ? [
      { id: 'damaged', label: '商品损坏' },
      { id: 'wrong', label: '发错商品' },
      { id: 'mind', label: '改变主意' },
    ]
  : [
      { id: 'damaged', label: 'Damaged' },
      { id: 'wrong', label: 'Wrong item' },
      { id: 'mind', label: 'Changed mind' },
    ])
const reasonLabel = computed(() => reasons.value.find((r) => r.id === reason.value)?.label || (zh.value ? '请选择原因' : 'Select a reason'))
const selectedCount = computed(() => items.value.filter((i) => i.on).length)
const progSteps = computed(() => (zh.value ? ['申请', '审核', '退款'] : ['Request', 'Review', 'Refund']))
const progAt = computed(() => (done.value ? 1 : 0))
const progRail = computed(() => ['0%', '50%', '100%'][progAt.value])

onMounted(loadItems)
onBeforeUnmount(() => {
  for (const url of photos.value) if (url) URL.revokeObjectURL(url)
})

async function loadItems() {
  const id = orderId.value.trim()
  if (!id) return
  loading.value = true
  error.value = ''
  try {
    const [order, html] = await Promise.all([
      fetchOrderDetail(id).catch(() => null),
      fetchInvoiceHtml(id).catch(() => ''),
    ])
    const inv = parseInvoiceHtml(html)
    const rawPay = String(order?.payMethod || inv.payMethod || '')
    payHint.value = /paypal/i.test(rawPay) ? 'PayPal' : (rawPay || (zh.value ? '原路退回' : 'Back to the original method'))
    const seed = (inv.lines.length ? inv.lines : []).map((line, i) => ({
      key: line.sku + i,
      name: line.name || line.sku,
      option: line.option,
      qty: line.qty || 1,
      price: line.amount || line.price,
      image: line.image,
      on: i < 2,
    }))
    items.value = seed
    for (const item of seed.slice(0, 6)) {
      try {
        const product = await getProduct(item.name.split('~')[0])
        if (!product) continue
        const hit = items.value.find((row) => row.key === item.key)
        if (!hit) continue
        hit.name = product.name || hit.name
        hit.image = product.image || hit.image
        hit.option = hit.option || product.sizes?.[0] || ''
        if (!hit.price && product.price) hit.price = '$' + Number(product.price).toFixed(2)
      } catch { /* keep the sku */ }
    }
  } finally {
    loading.value = false
  }
}

function pickReason(id: string) {
  reason.value = id
  reasonOpen.value = false
}

function pickPhoto(index: number) {
  photoSlot.value = index
  fileEl.value?.click()
}

function onPhoto(ev: Event) {
  const input = ev.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  const url = URL.createObjectURL(file)
  const next = photos.value.slice()
  if (next[photoSlot.value]) URL.revokeObjectURL(next[photoSlot.value])
  next[photoSlot.value] = url
  photos.value = next
}

async function submit() {
  error.value = ''
  const id = orderId.value.trim()
  if (!id) {
    error.value = zh.value ? '请填写订单号' : 'Add the order number.'
    return
  }
  if (!reason.value) {
    error.value = zh.value ? '请选择原因' : 'Select a reason.'
    reasonOpen.value = true
    return
  }
  if (items.value.length && !selectedCount.value) {
    error.value = zh.value ? '请至少选择一件商品' : 'Select at least one item.'
    return
  }
  const picked = items.value.filter((i) => i.on).map((i) => i.name).join('、')
  const why = reasons.value.find((r) => r.id === reason.value)?.label || reason.value
  const method = refund.value === 'wallet'
    ? (zh.value ? '钱包余额' : 'Wallet balance')
    : (zh.value ? '原支付方式' : 'Original payment method')
  const text = [why, picked, method].filter(Boolean).join(' · ').slice(0, 300)
  busy.value = true
  try {
    const res = await postOrderReturn(id, text)
    if (!res.ok) {
      error.value = zh.value ? '没能提交，请确认这是你的订单。' : 'Could not submit. Confirm this order is yours.'
      return
    }
    done.value = true
  } catch {
    error.value = zh.value ? '网络异常，请稍后再试。' : 'Network error. Try again.'
  } finally {
    busy.value = false
  }
}

function goOrder() {
  const id = orderId.value.trim()
  if (id) router.push('/orders/' + encodeURIComponent(id))
  else router.push('/orders')
}
</script>

<style lang="scss" scoped>
@import '@/styles/theme.scss';
.page { min-height: 100vh; background: #FCFAF8; color: #1C2430; }
.hero {
  position: relative; background: #fff; text-align: center;
  padding: 10px 44px 2px; padding-top: calc(8px + env(safe-area-inset-top));
}
.back {
  position: absolute; left: 8px; top: calc(10px + env(safe-area-inset-top));
  width: 36px; height: 36px; border: 0; background: transparent; color: #1C2430;
  display: inline-flex; align-items: center; justify-content: center; cursor: pointer;
}
.logo { display: inline-flex; align-items: center; gap: 4px; color: #F96141; font-size: 18px; font-weight: 800; letter-spacing: -0.03em; }
.tag { margin-top: 1px; font-size: 9px; letter-spacing: 0.1em; color: #8B919A; font-weight: 700; }
.range { margin-top: 1px; font-size: 11px; font-weight: 800; }
.body { padding: 6px 16px 24px; }
h1 { margin: 8px 0 0; font-size: 26px; font-weight: 800; letter-spacing: -0.04em; line-height: 1.15; }
.lead { margin: 4px 0 8px; color: #8B919A; font-size: 13px; line-height: 1.4; }
.prog {
  position: relative; display: grid; grid-template-columns: repeat(3, 1fr);
  margin: 0 0 4px; padding: 8px 4px 2px; background: #fff; border-radius: 14px;
  box-shadow: 0 6px 16px rgba(28, 36, 48, 0.04);
}
.rail { position: absolute; left: 16.6%; right: 16.6%; top: 20px; height: 2px; background: #F6D5CB; }
.rail i { display: block; height: 100%; background: #F96141; }
.pstep { position: relative; z-index: 1; display: flex; flex-direction: column; align-items: center; gap: 4px; color: #C5CAD1; }
.pstep b { font-size: 12px; font-weight: 800; letter-spacing: -0.02em; line-height: 1.1; }
.pdot {
  width: 26px; height: 26px; border-radius: 50%; background: #fff; border: 2px solid #E7DFD8; color: #C5CAD1;
  display: inline-flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 800;
}
.pstep.on { color: #1C2430; }
.pstep.on .pdot, .pstep.now .pdot { background: #F96141; border-color: #F96141; color: #fff; }
.pstep.now b { color: #F96141; }
.order-field { display: flex; flex-direction: column; gap: 6px; margin-bottom: 12px; font-size: 12px; font-weight: 700; color: #8B919A; }
.order-field input, .select {
  width: 100%; height: 44px; border-radius: 12px; border: 1.5px solid #E7DFD8; background: #fff;
  padding: 0 12px; font-size: 14px; font-weight: 650; color: #1C2430;
}
.sec-row, .sec { display: flex; justify-content: space-between; align-items: baseline; margin: 12px 0 6px; font-size: 15px; font-weight: 800; letter-spacing: -0.02em; }
.sec.flat { justify-content: flex-start; gap: 4px; }
.sec-row span, .sec span, .hint { font-size: 12px; font-weight: 650; letter-spacing: 0; color: #9AA1A9; }
.hint { margin: 0 0 6px; line-height: 1.35; }
.item, .method {
  display: flex; align-items: center; gap: 8px; background: #fff; border-radius: 14px;
  padding: 8px 10px; margin-bottom: 6px; border: 1.5px solid transparent;
  box-shadow: 0 4px 12px rgba(28, 36, 48, 0.04);
}
.item.on, .method.on { border-color: #F96141; }
.item input, .method input, .file { position: absolute; opacity: 0; pointer-events: none; }
.box {
  width: 22px; height: 22px; border-radius: 6px; border: 1.5px solid #E7DFD8; color: #fff;
  display: inline-flex; align-items: center; justify-content: center; flex: 0 0 auto;
}
.item.on .box { background: #F96141; border-color: #F96141; }
.item img, .ph { width: 48px; height: 48px; border-radius: 10px; object-fit: cover; background: #F6F1EC; flex: 0 0 auto; }
.ph { display: inline-flex; align-items: center; justify-content: center; color: #F96141; font-weight: 800; font-size: 14px; }
.meta { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 1px; }
.meta b { font-size: 14px; font-weight: 800; letter-spacing: -0.02em; line-height: 1.2; }
.meta small, .qty { color: #9AA1A9; font-size: 12px; line-height: 1.25; }
.meta strong { color: #1C2430; font-size: 13px; font-weight: 800; }
.qty { flex: 0 0 auto; }
.select { display: flex; align-items: center; justify-content: space-between; cursor: pointer; text-align: left; }
.menu { margin-top: 4px; background: #fff; border: 1.5px solid #F6C7BA; border-radius: 12px; overflow: hidden; box-shadow: 0 8px 18px rgba(249, 97, 65, 0.08); }
.menu button {
  width: 100%; display: flex; justify-content: space-between; align-items: center;
  border: 0; background: #fff; padding: 10px 12px; font-size: 14px; cursor: pointer; color: #1C2430;
}
.menu button.on { background: #FFF1EC; color: #F96141; font-weight: 700; }
.photos { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
.photo {
  aspect-ratio: 1; border: 1.5px dashed #E7C8BE; border-radius: 12px; background: #fff; color: #C4B8B2;
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 4px;
  font-size: 11px; font-weight: 650; line-height: 1.2; cursor: pointer; overflow: hidden; padding: 6px;
}
.photo img { width: 100%; height: 100%; object-fit: cover; }
.method svg { color: #F96141; flex: 0 0 auto; }
.method span { display: flex; flex-direction: column; }
.method b { font-size: 14px; font-weight: 800; letter-spacing: -0.02em; line-height: 1.2; }
.method small { color: #9AA1A9; font-size: 12px; margin-top: 1px; }
.radio {
  width: 18px; height: 18px; border-radius: 50%; border: 2px solid #E7DFD8; flex: 0 0 auto; position: relative;
}
.method.on .radio { border-color: #F96141; }
.method.on .radio::after {
  content: ""; position: absolute; inset: 3px; border-radius: 50%; background: #F96141;
}
.err { color: #E11D2E; font-size: 13px; }
.submit {
  width: 100%; height: 48px; margin-top: 12px; border: 0; border-radius: 14px; background: #F96141; color: #fff;
  font-size: 16px; font-weight: 800; letter-spacing: -0.02em; cursor: pointer;
}
.submit:disabled { opacity: 0.6; }
.done { background: #fff; border-radius: 16px; padding: 18px; }
.done b { font-size: 18px; }
.done p { color: #6B7280; }
.muted { color: #8B919A; font-size: 13px; padding: 8px 0; }
</style>
