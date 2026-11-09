<template>
  <div class="page" data-figma="1:27">
    <header class="hero">
      <button type="button" class="back" aria-label="back" @click="$router.back()"><ChevronLeft :size="22" :stroke-width="2.2" /></button>
      <h1>{{ zh ? '订单' : 'Order' }} {{ displayId }}</h1>
    </header>

    <div v-if="loading" class="state">{{ t('pdp_loading') }}</div>
    <div v-else-if="!detail.ok" class="state">{{ detail.rawHint || (zh ? '没有找到订单' : 'Not found') }}</div>
    <template v-else>
      <section class="card steps">
        <div class="rail" aria-hidden="true"><i :style="{ width: rail }" /></div>
        <div v-for="(step, i) in steps" :key="step.key" class="step" :class="{ on: i <= activeStep, now: i === activeStep }">
          <span class="dot"><component :is="step.icon" :size="18" :stroke-width="2.25" /></span>
          <b>{{ step.label }}</b>
          <small>{{ step.when }}</small>
        </div>
      </section>

      <p v-if="trackLine" class="track">{{ trackLine }}</p>

      <section class="card block">
        <div class="sec">
          <MapPin :size="16" :stroke-width="2.2" />
          <span>{{ zh ? '收货地址' : 'Shipping Address' }}</span>
        </div>
        <div v-if="detail.shipName || detail.address" class="addr">
          <b>{{ detail.shipName }}</b>
          <p>{{ detail.address }}</p>
        </div>
        <p v-else class="muted">{{ zh ? '地址在发票里确认后会显示在这里' : 'Address shows here once the invoice is available.' }}</p>
      </section>

      <section class="card block">
        <div class="sec">
          <ShoppingBag :size="16" :stroke-width="2.2" />
          <span>{{ zh ? '商品' : 'Items' }}<template v-if="lines.length"> ({{ lines.length }})</template></span>
        </div>
        <div v-if="!lines.length" class="muted">{{ zh ? '明细在发票里' : 'Line items appear on the invoice.' }}</div>
        <div v-for="(line, i) in lines" :key="line.sku + i" class="item">
          <img v-if="line.image" :src="line.image" alt="" />
          <div v-else class="ph">{{ (line.name || line.sku || '?').slice(0, 1) }}</div>
          <div class="item-body">
            <div class="nm">{{ line.name || line.sku }}</div>
            <div v-if="line.option" class="opt">{{ line.option }}</div>
            <div class="opt">{{ zh ? '数量' : 'Qty' }}: {{ line.qty || 1 }}</div>
          </div>
          <div v-if="line.amount || line.price" class="item-price">{{ line.amount || line.price }}</div>
        </div>
      </section>

      <section class="card block">
        <div class="sec">
          <CreditCard :size="16" :stroke-width="2.2" />
          <span>{{ zh ? '支付方式' : 'Payment Method' }}</span>
        </div>
        <div class="pay">
          <b>{{ payLabel }}</b>
          <p>{{ payMeta }}</p>
        </div>
      </section>

      <section class="card block">
        <div class="sec">
          <Receipt :size="16" :stroke-width="2.2" />
          <span>{{ zh ? '订单合计' : 'Order Totals' }}</span>
        </div>
        <div v-for="(row, i) in moneyRows" :key="row.label + i" class="money" :class="{ total: row.emphasis || i === moneyRows.length - 1 }">
          <span>{{ row.label }}</span>
          <b>{{ row.value }}</b>
        </div>
      </section>

      <form v-if="detail.canPay" class="pay-form" :action="payAction" method="post">
        <input type="hidden" name="pay_method" :value="detail.payMethod || 'paypal'" />
        <button class="cta" type="submit"><Wallet :size="18" /> {{ zh ? '去支付' : 'Pay now' }}</button>
      </form>
      <button v-else type="button" class="cta" @click="primary">
        <Truck :size="18" /> {{ primaryLabel }}
      </button>
      <div class="links">
        <router-link :to="{ path: '/invoice', query: { id } }">{{ zh ? '发票' : 'Invoice' }}</router-link>
        <router-link :to="{ path: '/return', query: { order: id } }">{{ zh ? '申请退货' : 'Request a return' }}</router-link>
        <button type="button" @click="askCs">{{ zh ? '联系客服' : 'Chat' }}</button>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ChevronLeft, Check, CreditCard, MapPin, Package, Receipt, ShoppingBag, Truck, Wallet } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  fetchInvoiceHtml,
  fetchOrderDetail,
  parseInvoiceHtml,
  postBuyAgain,
  type OrderDetail,
  type OrderLine,
} from '@/api/accountApi'
import { apiRoot } from '@/api/config'
import { getProduct } from '@/api/products'
import { buildOrderBody } from '@/api/supportApi'
import { useCart } from '@/composables/cart'
import { useI18n } from '@/composables/i18n'

const { t, lang } = useI18n()
const zh = computed(() => String(lang.value).startsWith('zh'))
const route = useRoute()
const router = useRouter()
const cart = useCart()
const id = String(route.params.id || '')
const loading = ref(true)
const detail = ref<OrderDetail>({
  ok: false, live: false, id, status: '', due: '', arrives: '', tracking: '', carrier: '',
  summary: [], canPay: false, canCancel: false, email: '', shipName: '', address: '',
  payMethod: '', lines: [], totals: [],
})

const displayId = computed(() => {
  const raw = String(detail.value.id || id || '').trim()
  if (!raw) return ''
  if (/^#/.test(raw)) return raw
  if (/^h/i.test(raw)) return '#' + raw
  return '#H' + raw
})

const activeStep = computed(() => {
  const s = String(detail.value.status || '').toLowerCase()
  if (/deliver|送达/.test(s)) return 3
  if (/ship|发货|运输/.test(s)) return 2
  if (/paid|pack|已付|打包|complete|完成/.test(s)) return 1
  return 0
})
const rail = computed(() => ['8%', '36%', '64%', '100%'][activeStep.value])

const steps = computed(() => {
  const labels = zh.value
    ? ['已支付', '已打包', '已发货', '已送达']
    : ['Paid', 'Packed', 'Shipped', 'Delivered']
  if (activeStep.value === 0) labels[0] = zh.value ? '待支付' : 'Unpaid'
  const icons = [Check, Package, Truck, Check]
  return labels.map((label, i) => ({
    key: label,
    label,
    icon: icons[i],
    when: i === 3 && detail.value.arrives
      ? (zh.value ? `预计 ${detail.value.arrives} 天` : `Est. ${detail.value.arrives} days`)
      : '',
  }))
})

const lines = computed(() => detail.value.lines || [])
const trackLine = computed(() => {
  const d = detail.value
  if (d.tracking) return `${d.carrier ? d.carrier + ' · ' : ''}${d.tracking}`
  return ''
})
const payLabel = computed(() => {
  const raw = String(detail.value.payMethod || '').toLowerCase()
  if (!raw) return zh.value ? '在线支付' : 'Online payment'
  if (raw.includes('paypal')) return 'PayPal'
  if (raw.includes('card') || raw.includes('stripe') || raw.includes('visa')) return zh.value ? '银行卡' : 'Card'
  if (raw.includes('lian') || raw.includes('连连')) return zh.value ? '连连' : 'LianLian'
  return detail.value.payMethod
})
const payMeta = computed(() => {
  const d = detail.value
  const state = d.canPay ? (zh.value ? '待支付' : 'Unpaid') : (zh.value ? '已支付' : 'Paid')
  return [state, d.due].filter(Boolean).join(' · ')
})
const moneyRows = computed(() => {
  const rows = (detail.value.totals || []).filter((r) => r.label && r.value)
  if (rows.length) return rows
  if (detail.value.due) return [{ label: zh.value ? '合计' : 'Total', value: detail.value.due, emphasis: true }]
  return []
})
const primaryLabel = computed(() => {
  if (activeStep.value >= 2) return zh.value ? '查看物流' : 'Track shipment'
  if (activeStep.value === 1) return zh.value ? '再买一次' : 'Buy again'
  return zh.value ? '联系客服' : 'Chat'
})
const payAction = computed(() => apiRoot().replace(/\/$/, '') + '/orders/' + encodeURIComponent(id) + '/pay')

onMounted(async () => {
  const order = await fetchOrderDetail(id)
  detail.value = order
  loading.value = false
  if (!order.ok) return
  try {
    const html = await fetchInvoiceHtml(id)
    const inv = parseInvoiceHtml(html)
    if (inv.ok) {
      detail.value = {
        ...detail.value,
        email: inv.email || detail.value.email,
        shipName: inv.shipName || detail.value.shipName,
        address: inv.address || detail.value.address,
        payMethod: detail.value.payMethod || inv.payMethod,
        due: detail.value.due || inv.due,
        lines: inv.lines.length ? inv.lines : detail.value.lines,
      }
    }
  } catch { /* invoice is optional */ }
  void enrichLines()
})

async function enrichLines() {
  const current = detail.value.lines.slice(0, 6)
  if (!current.length) return
  const next: OrderLine[] = []
  for (const line of current) {
    const sku = line.sku.split('~')[0]
    try {
      const product = await getProduct(sku)
      next.push({
        ...line,
        name: product?.name || line.name,
        image: product?.image || line.image,
        option: line.option || product?.sizes?.[0] || '',
        price: line.price,
      })
    } catch {
      next.push(line)
    }
  }
  if (detail.value.lines.length > next.length) next.push(...detail.value.lines.slice(next.length))
  detail.value = { ...detail.value, lines: next }
}

async function primary() {
  if (activeStep.value === 1) {
    try { await postBuyAgain(id) } catch { /* cart may still refresh */ }
    try { await cart.refreshFromServer() } catch { /* keep going */ }
    router.push('/cart')
    return
  }
  if (activeStep.value >= 2 && detail.value.tracking) {
    try { await navigator.clipboard.writeText(detail.value.tracking) } catch { /* ignore */ }
    return
  }
  askCs()
}

function askCs() {
  const body = buildOrderBody({
    id: detail.value.id,
    status: detail.value.status,
    tracking: detail.value.tracking,
    items: detail.value.lines.slice(0, 4).map((l) => l.name || l.sku),
  })
  sessionStorage.setItem('harbor_cs_prefill_order', body)
  router.push({ path: '/chat', query: { order: id } })
}
</script>

<style lang="scss" scoped>
@import '@/styles/theme.scss';
.page { min-height: 100vh; background: #FCFAF8; color: #1C2430; padding-bottom: 32px; }
.hero {
  position: relative; display: flex; align-items: center; justify-content: center;
  background: #F96141; color: #fff; min-height: 64px;
  padding: 16px 48px; padding-top: calc(16px + env(safe-area-inset-top));
}
.back {
  position: absolute; left: 8px; top: calc(12px + env(safe-area-inset-top));
  width: 36px; height: 36px; border: 0; background: transparent; color: #fff;
  display: inline-flex; align-items: center; justify-content: center; cursor: pointer;
}
h1 { margin: 0; font-size: 18px; font-weight: 800; }
.card {
  margin: 16px 16px 0; background: #fff; border-radius: 20px; padding: 16px;
  box-shadow: 0 10px 28px rgba(28, 36, 48, 0.05);
}
.steps {
  position: relative; display: grid; grid-template-columns: repeat(4, 1fr); gap: 0;
  text-align: center; padding: 6px 2px 2px;
}
.rail {
  position: absolute; left: 12.5%; right: 12.5%; top: 24px; height: 3px; background: #F6D5CB; border-radius: 3px;
}
.rail i { display: block; height: 100%; background: #F96141; border-radius: 3px; }
.step { position: relative; z-index: 1; display: flex; flex-direction: column; align-items: center; gap: 8px; color: #C5CAD1; }
.step b { font-size: 13px; font-weight: 800; letter-spacing: -0.02em; line-height: 1.15; }
.step small {
  min-height: 28px; margin-top: -2px; font-size: 11px; font-weight: 600; line-height: 1.25;
  color: #9AA1A9; letter-spacing: -0.01em;
}
.dot {
  width: 40px; height: 40px; border-radius: 50%; background: #fff; border: 2px solid #E7DFD8;
  display: inline-flex; align-items: center; justify-content: center; color: #C5CAD1;
}
.step.on { color: #1C2430; }
.step.on .dot, .step.now .dot { background: #F96141; border-color: #F96141; color: #fff; box-shadow: 0 6px 14px rgba(249, 97, 65, 0.28); }
.track { margin: 10px 20px 0; font-size: 12px; color: #8B919A; }
.block { padding-bottom: 8px; }
.sec { display: flex; align-items: center; gap: 8px; font-size: 14px; font-weight: 800; color: #1C2430; }
.sec svg { color: #F96141; }
.addr, .pay, .muted { margin: 10px 0 8px 24px; font-size: 13px; line-height: 1.45; }
.addr b, .pay b { display: block; font-size: 14px; }
.addr p, .pay p, .muted { margin: 4px 0 0; color: #6B7280; }
.item { display: flex; gap: 10px; align-items: center; padding: 12px 0; border-top: 1px solid #F3EFEA; }
.item img, .ph { width: 58px; height: 58px; border-radius: 12px; object-fit: cover; background: #F6F1EC; flex: 0 0 auto; }
.ph { display: flex; align-items: center; justify-content: center; font-weight: 800; color: #F96141; }
.item-body { flex: 1; min-width: 0; }
.nm { font-size: 14px; font-weight: 750; line-height: 1.3; }
.opt { margin-top: 2px; font-size: 12px; color: #8B919A; }
.item-price { font-size: 14px; font-weight: 800; }
.money { display: flex; justify-content: space-between; gap: 12px; padding: 6px 0; font-size: 13px; color: #6B7280; }
.money b { color: #1C2430; font-weight: 650; }
.money.total { margin-top: 4px; padding-top: 8px; border-top: 1px solid #F3EFEA; color: #1C2430; font-weight: 800; }
.money.total b { color: #1C2430; font-size: 16px; }
.cta, .pay-form { margin: 16px 16px 0; }
.cta {
  width: 100%; height: 52px; border: 0; border-radius: 16px; background: #F96141; color: #fff;
  font-size: 16px; font-weight: 800; display: flex; align-items: center; justify-content: center; gap: 8px; cursor: pointer;
}
.links { display: flex; justify-content: center; gap: 18px; margin: 14px 16px 0; font-size: 13px; font-weight: 700; color: #F96141; }
.links button { border: 0; background: transparent; color: inherit; font: inherit; font-weight: 700; cursor: pointer; }
.state { text-align: center; color: #8B919A; padding: 48px 16px; }
</style>
