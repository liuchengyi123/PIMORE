<template>
  <div class="page">
    <header class="head">
      <button type="button" class="back" @click="$router.back()" aria-label="back">‹</button>
      <h1 class="title">Payment methods</h1>
    </header>
    <div v-if="loginRequired" class="state">Sign in to manage payment methods.</div>
    <template v-else>
      <div v-if="loading" class="state">Loading…</div>
      <div v-else-if="!rows.length" class="state">No payment methods yet.</div>
      <div v-else class="list">
        <div v-for="(r, i) in rows" :key="i" class="card">
          <div class="row">
            <div class="nm">{{ label(r) }}</div>
            <span v-if="i === 0" class="badge">Preferred</span>
          </div>
          <div v-if="sub(r)" class="sub">{{ sub(r) }}</div>
        </div>
      </div>
    </template>
  </div>
</template>
<script setup lang="ts">
import { ChevronLeft } from 'lucide-vue-next'
import { onMounted, ref } from 'vue'
import { addPaymentMethod, fetchPayments, shopPath, type PayMethodRow } from '@/api/accountApi'
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
  const b = r.brand || r.name || 'Card'
  const l4 = r.last4 || ''
  return l4 ? `Card · ${b} ••${l4}` : String(b)
}
function sub(r: any) { return r.provider || r.meta || '' }
</script>
<style scoped>
.page { min-height: 100vh; background: #F4F7FB; color: #1B2B4A; padding: 12px 16px 40px; padding-top: calc(12px + env(safe-area-inset-top)); }
.head { display: flex; gap: 10px; align-items: center; margin-bottom: 12px; }
.back { border: 0; background: transparent; font-size: 22px; font-weight: 700; cursor: pointer; color: #1B2B4A; }
.title { font-size: 17px; font-weight: 700; margin: 0; }
.list { display: flex; flex-direction: column; gap: 8px; }
.card { background: #fff; border: 1px solid #E2E6EE; border-radius: 16px; padding: 14px; }
.row { display: flex; justify-content: space-between; align-items: center; gap: 10px; }
.nm { font-size: 16px; font-weight: 700; }
.badge { background: #E0F2FE; color: #FF6B4A; font-size: 11px; font-weight: 600; padding: 4px 10px; border-radius: 999px; }
.sub { margin-top: 4px; font-size: 11px; color: #5C6570; }
.state { text-align: center; color: #6B7280; padding: 36px 8px; }
</style>
