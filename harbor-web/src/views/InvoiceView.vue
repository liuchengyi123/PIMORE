<template>
  <div class="page" data-figma="1:28">
    <header class="hero">
      <button type="button" class="back" aria-label="back" @click="$router.back()"><ChevronLeft :size="22" :stroke-width="2.2" /></button>
      <h1>{{ zh ? '发票' : 'Invoice' }}</h1>
      <button type="button" class="bag" aria-label="cart" @click="$router.push('/cart')"><ShoppingBag :size="20" :stroke-width="1.8" /></button>
    </header>

    <div v-if="loading" class="state">{{ zh ? '加载中…' : 'Loading…' }}</div>
    <section v-else class="sheet">
      <div class="mast">
        <div class="brand">
          <span class="mark" aria-hidden="true"><Home :size="18" :stroke-width="2.4" /></span>
          <div>
            <div class="logo">Harbor</div>
            <div class="tag">{{ zh ? '每日家居，超值之选' : 'EVERYDAY HOME. GREAT VALUE.' }}</div>
          </div>
        </div>
        <div class="inv">
          <div class="kicker">{{ zh ? '发票' : 'INVOICE' }}</div>
          <b>{{ displayId }}</b>
          <div class="date">{{ dateLabel }}</div>
        </div>
      </div>

      <div class="bill">
        <div class="kicker soft">{{ zh ? '账单寄至' : 'Bill To' }}</div>
        <b>{{ invoice.shipName || (zh ? '顾客' : 'Customer') }}</b>
        <p v-if="invoice.address">{{ invoice.address }}</p>
        <p v-if="invoice.email">{{ invoice.email }}</p>
      </div>

      <div class="table">
        <div class="tr head">
          <span>SKU</span><span>{{ zh ? '商品' : 'ITEM' }}</span><span>{{ zh ? '数量' : 'QTY' }}</span><span>{{ zh ? '金额' : 'AMOUNT' }}</span>
        </div>
        <div v-if="!rows.length" class="empty">{{ zh ? '暂无明细' : 'No line items' }}</div>
        <div v-for="(row, i) in rows" :key="row.sku + i" class="tr">
          <span class="sku">{{ row.sku }}</span>
          <span class="item">
            <img v-if="row.image" :src="row.image" alt="" />
            <span>
              <b>{{ row.name || row.sku }}</b>
              <small v-if="row.option">{{ row.option }}</small>
            </span>
          </span>
          <span>{{ row.qty || 1 }}</span>
          <span>{{ row.amount || '—' }}</span>
        </div>
      </div>

      <div class="totals">
        <div v-for="(row, i) in totals" :key="row.label + i" class="money" :class="{ total: row.emphasis }">
          <span>{{ row.label }}</span>
          <b>{{ row.value }}</b>
        </div>
      </div>

      <div class="thanks">
        <span class="house"><Home :size="16" /></span>
        <div>
          <b>{{ zh ? '感谢在 Harbor 购物' : 'Thanks for shopping Harbor!' }}</b>
          <p>{{ zh ? '每天的家居好物。' : 'Quality home goods. Everyday value.' }}</p>
        </div>
      </div>
      <div class="foot">♥ {{ zh ? '小物，更大的家' : 'SMALL ITEMS. A BIGGER HOME.' }}</div>
    </section>

    <div class="actions">
      <button type="button" class="btn solid" @click="download"><Download :size="16" /> {{ zh ? '下载 PDF' : 'Download PDF' }}</button>
      <button type="button" class="btn ghost" @click="share"><Share2 :size="16" /> {{ zh ? '分享' : 'Share' }}</button>
    </div>
    <p v-if="notice" class="notice">{{ notice }}</p>
  </div>
</template>

<script setup lang="ts">
import { ChevronLeft, Download, Home, Share2, ShoppingBag } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import {
  fetchInvoiceHtml,
  fetchOrderDetail,
  parseInvoiceHtml,
  type InvoiceModel,
  type OrderLine,
  type OrderTotal,
} from '@/api/accountApi'
import { getProduct } from '@/api/products'
import { useI18n } from '@/composables/i18n'

const { lang } = useI18n()
const zh = computed(() => String(lang.value).startsWith('zh'))
const route = useRoute()
const orderId = ref(String(route.query.id || route.params.id || ''))
const loading = ref(false)
const notice = ref('')
const invoice = ref<InvoiceModel>({
  ok: false, id: '', email: '', shipName: '', address: '', lines: [], due: '', payMethod: '', note: '',
})
const totals = ref<OrderTotal[]>([])
const rows = ref<OrderLine[]>([])

const displayId = computed(() => {
  const raw = String(invoice.value.id || orderId.value || '').trim()
  if (!raw) return '—'
  if (/^#/.test(raw)) return raw
  if (/^h/i.test(raw)) return '#' + raw.toUpperCase()
  return '#H' + raw
})
const dateLabel = computed(() => new Date().toLocaleDateString(zh.value ? 'zh-CN' : 'en-US', {
  month: 'short', day: 'numeric', year: 'numeric',
}))

onMounted(async () => {
  if (!orderId.value) return
  loading.value = true
  try {
    const [html, order] = await Promise.all([
      fetchInvoiceHtml(orderId.value).catch(() => ''),
      fetchOrderDetail(orderId.value).catch(() => null),
    ])
    const parsed = parseInvoiceHtml(html)
    invoice.value = parsed.ok ? parsed : { ...invoice.value, id: orderId.value }
    rows.value = parsed.lines
    const fromOrder = (order?.totals || []).filter((r) => r.label && r.value)
    if (fromOrder.length) totals.value = fromOrder
    else if (parsed.due || order?.due) {
      totals.value = [{ label: zh.value ? '合计' : 'Total', value: parsed.due || order?.due || '', emphasis: true }]
    }
    if (!invoice.value.due && order?.due) invoice.value = { ...invoice.value, due: order.due }
  } finally {
    loading.value = false
  }
  void enrich()
})

async function enrich() {
  const next: OrderLine[] = []
  for (const line of rows.value.slice(0, 8)) {
    try {
      const product = await getProduct(line.sku.split('~')[0])
      next.push({
        ...line,
        name: product?.name || line.name,
        image: product?.image || line.image,
        option: product?.sizes?.[0] || line.option,
      })
    } catch {
      next.push(line)
    }
  }
  if (next.length) rows.value = next
}

function download() {
  window.print()
}

async function share() {
  const title = (zh.value ? '发票 ' : 'Invoice ') + displayId.value
  const url = location.href
  try {
    if (navigator.share) {
      await navigator.share({ title, url })
      return
    }
  } catch { /* cancelled or unsupported */ }
  try {
    await navigator.clipboard.writeText(url)
    notice.value = zh.value ? '链接已复制' : 'Link copied'
  } catch {
    notice.value = url
  }
}
</script>

<style lang="scss" scoped>
@import '@/styles/theme.scss';
.page { min-height: 100vh; background: #FCFAF8; color: #1C2430; padding-bottom: 28px; }
.hero {
  position: relative; display: flex; align-items: center; justify-content: center;
  background: #F96141; color: #fff; min-height: 64px;
  padding: 16px 48px; padding-top: calc(16px + env(safe-area-inset-top));
}
.back, .bag {
  position: absolute; top: calc(12px + env(safe-area-inset-top));
  width: 36px; height: 36px; border: 0; background: transparent; color: #fff;
  display: inline-flex; align-items: center; justify-content: center; cursor: pointer;
}
.back { left: 8px; }
.bag { right: 8px; }
h1 { margin: 0; font-size: 18px; font-weight: 800; }
.sheet {
  margin: 16px; background: #fff; border-radius: 18px; padding: 18px 16px 14px;
  box-shadow: 0 10px 28px rgba(28, 36, 48, 0.05);
}
.mast, .bill { display: flex; justify-content: space-between; gap: 12px; }
.brand { display: flex; gap: 8px; align-items: center; }
.mark {
  width: 36px; height: 36px; border-radius: 10px; background: #FFF1EC; color: #F96141;
  display: inline-flex; align-items: center; justify-content: center;
}
.logo { font-size: 22px; font-weight: 800; color: #F96141; letter-spacing: -0.04em; line-height: 1; }
.tag { margin-top: 3px; font-size: 9px; letter-spacing: 0.08em; color: #8B919A; font-weight: 700; }
.inv { text-align: right; }
.kicker { font-size: 11px; letter-spacing: 0.14em; font-weight: 800; color: #1C2430; }
.kicker.soft { letter-spacing: 0.04em; color: #8B919A; font-weight: 700; }
.inv b { display: block; margin-top: 4px; font-size: 14px; }
.date, .bill p { margin-top: 2px; font-size: 12px; color: #8B919A; }
.bill { display: block; margin-top: 18px; }
.bill b { display: block; margin-top: 4px; font-size: 15px; }
.bill p { margin: 2px 0 0; }
.table { margin-top: 16px; border-top: 1px solid #F0EBE6; }
.tr { display: grid; grid-template-columns: 72px 1fr 36px 64px; gap: 8px; align-items: center; padding: 10px 0; border-bottom: 1px solid #F6F1EC; font-size: 12px; }
.tr.head { font-size: 10px; letter-spacing: 0.06em; color: #8B919A; font-weight: 800; }
.sku { color: #6B7280; word-break: break-all; }
.item { display: flex; gap: 8px; align-items: center; min-width: 0; }
.item img { width: 36px; height: 36px; border-radius: 8px; object-fit: cover; background: #F6F1EC; }
.item b { display: block; font-size: 13px; line-height: 1.25; }
.item small { color: #8B919A; }
.empty { padding: 16px 0; text-align: center; color: #8B919A; font-size: 13px; }
.totals { margin-top: 8px; }
.money { display: flex; justify-content: flex-end; gap: 28px; padding: 4px 0; font-size: 13px; color: #6B7280; }
.money b { min-width: 72px; text-align: right; color: #1C2430; }
.money.total { margin-top: 6px; color: #F96141; font-weight: 800; font-size: 16px; }
.money.total b { color: #F96141; }
.thanks {
  margin-top: 14px; display: flex; gap: 10px; align-items: center;
  background: #FFF7F4; border-radius: 12px; padding: 12px;
}
.house {
  width: 32px; height: 32px; border-radius: 10px; background: #fff; color: #F96141;
  display: inline-flex; align-items: center; justify-content: center; flex: 0 0 auto;
}
.thanks b { font-size: 13px; }
.thanks p { margin: 2px 0 0; font-size: 12px; color: #8B919A; }
.foot { margin-top: 14px; text-align: center; font-size: 11px; letter-spacing: 0.08em; color: #F96141; font-weight: 700; }
.actions { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin: 14px 16px 0; }
.btn {
  height: 48px; border-radius: 14px; font-size: 14px; font-weight: 800; cursor: pointer;
  display: inline-flex; align-items: center; justify-content: center; gap: 6px;
}
.solid { border: 0; background: #F96141; color: #fff; }
.ghost { border: 1.5px solid #F96141; background: #fff; color: #F96141; }
.notice, .state { text-align: center; color: #8B919A; font-size: 12px; padding: 10px 16px; }
@media print {
  .hero, .actions, .notice { display: none; }
  .page { background: #fff; }
  .sheet { box-shadow: none; margin: 0; }
}
</style>
