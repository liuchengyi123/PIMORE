<template>
  <div class="page">
    <header class="head">
      <button type="button" class="back" @click="$router.back()" aria-label="back">‹</button>
      <h1 class="title">{{ zh ? '支付方式' : 'Payment methods' }}</h1>
    </header>
    <div v-if="loginRequired" class="state">{{ zh ? '登录后管理支付方式。' : 'Sign in to manage payment methods.' }}</div>
    <template v-else>
      <div v-if="loading" class="state">{{ zh ? '加载中…' : 'Loading…' }}</div>
      <div v-else-if="!rows.length" class="state">{{ zh ? '还没有支付方式' : 'No payment methods yet.' }}</div>
      <div v-else class="list">
        <div v-for="(r, i) in rows" :key="i" class="card">
          <div class="row">
            <div class="nm">{{ label(r) }}</div>
            <span v-if="i === 0" class="badge">{{ zh ? '常用' : 'Preferred' }}</span>
          </div>
          <div v-if="sub(r)" class="sub">{{ sub(r) }}</div>
        </div>
      </div>
    </template>
  </div>
</template>
<script setup lang="ts">
import { ChevronLeft } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import { addPaymentMethod, fetchPayments, shopPath, type PayMethodRow } from '@/api/accountApi'
import { useI18n } from '@/composables/i18n'
const { lang } = useI18n()
const zh = computed(() => String(lang.value).startsWith('zh'))
const rows = ref<PayMethodRow[]>([])
const loading = ref(true)
const loginRequired = ref(false)
const brand = ref('Card')
const last4 = ref('')
const busy = ref(false)
const msg = ref('')
async function refresh() {
  loading.value = true
  try {
    const res = await fetchPayments()
    rows.value = res.rows
    loginRequired.value = res.loginRequired && !res.rows.length
  } finally { loading.value = false }
}
async function add() {
  busy.value = true
  msg.value = ''
  try {
    const res = await addPaymentMethod(brand.value, last4.value)
    if (!res.ok || res.status === 401) {
      msg.value = res.status === 401 ? '请先登录' : '保存失败'
      return
    }
    msg.value = '已新增'
    last4.value = ''
    await refresh()
  } catch {
    msg.value = '网络错误'
  } finally { busy.value = false }
}
onMounted(refresh)

function label(r: any) {
  const b = r.brand || r.name || (zh.value ? '银行卡' : 'Card')
  const l4 = r.last4 || ''
  return l4 ? `${zh.value ? '卡' : 'Card'} · ${b} ••${l4}` : String(b)
}
function sub(r: any) { return r.provider || r.meta || '' }
</script>
<style scoped>
.page { min-height: 100vh; background: var(--hb-page); color: var(--hb-ink); padding: 10px 16px 32px; padding-top: calc(10px + env(safe-area-inset-top)); }
.head { display: flex; gap: 8px; align-items: center; margin-bottom: 8px; }
.back { border: 0; background: transparent; font-size: 22px; font-weight: 700; cursor: pointer; color: var(--hb-ink); padding: 0; }
.title { font-size: 20px; font-weight: 800; letter-spacing: -0.03em; margin: 0; }
.list { display: flex; flex-direction: column; gap: 6px; }
.card { background: var(--hb-surface); border: 1px solid var(--hb-line); border-radius: 14px; padding: 10px 12px; }
.row { display: flex; justify-content: space-between; align-items: center; gap: 8px; min-height: 24px; }
.nm { font-size: 14px; font-weight: 700; line-height: 1.25; }
.badge { background: var(--hb-primary-soft); color: var(--hb-primary); font-size: 11px; font-weight: 700; padding: 3px 8px; border-radius: 999px; }
.sub { margin-top: 2px; font-size: 12px; color: var(--hb-muted); }
.state { text-align: center; color: var(--hb-muted); padding: 20px 8px; font-size: 13px; }
</style>
