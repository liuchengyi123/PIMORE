<template>
  <div class="page">
    <header class="head">
      <button type="button" class="back" @click="$router.back()" aria-label="back">‹</button>
      <h1 class="title">Addresses</h1>
      <a class="add" :href="shopPath('/account/addresses')" target="_blank" rel="noopener">Add</a>
    </header>
    <div v-if="loginRequired" class="state">Sign in to manage addresses.</div>
    <div v-else-if="loading" class="state">Loading…</div>
    <div v-else-if="!rows.length" class="state">No addresses yet.</div>
    <div v-else class="list">
      <article v-for="(r, i) in rows" :key="i" class="card">
        <span v-if="i === 0" class="badge">Default</span>
        <div class="nm">{{ r.name }}</div>
        <div class="line">{{ r.line }}</div>
      </article>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ChevronLeft } from 'lucide-vue-next'
import { onMounted, reactive, ref } from 'vue'
import { addAddress, fetchAddresses, shopPath, type AddressRow } from '@/api/accountApi'
const rows = ref<AddressRow[]>([])
const loading = ref(true)
const loginRequired = ref(false)
const busy = ref(false)
const msg = ref('')
const countries = ['US','CN','TW','HK','GB','CA','DE','FR','ES','PT','BR','MX','JP']
const form = reactive({
  name: '', address: '', city: '', region: '', postal: '', ship_country: 'US', phone: '', street_number: '', district: '',
})
async function refresh() {
  loading.value = true
  try {
    const res = await fetchAddresses()
    rows.value = res.rows
    loginRequired.value = res.loginRequired && !res.rows.length
  } finally { loading.value = false }
}
async function add() {
  busy.value = true
  msg.value = ''
  try {
    const res = await addAddress({ ...form })
    if (!res.ok || res.status === 401) {
      msg.value = res.status === 401 ? '请先登录' : '保存失败'
      if (res.status === 401) loginRequired.value = true
      return
    }
    msg.value = '已新增'
    form.name = form.address = form.city = form.region = form.postal = form.phone = ''
    await refresh()
  } catch {
    msg.value = '网络错误'
  } finally { busy.value = false }
}
onMounted(refresh)
</script>
<style scoped>
.page { min-height: 100vh; background: #F7F4EF; color: #0F2744; padding: 12px 16px 40px; padding-top: calc(12px + env(safe-area-inset-top)); }
.head { display: flex; gap: 10px; align-items: center; margin-bottom: 12px; }
.back { border: 0; background: transparent; font-size: 22px; font-weight: 700; cursor: pointer; color: #0F2744; }
.title { flex: 1; font-size: 17px; font-weight: 700; margin: 0; }
.add { font-size: 13px; font-weight: 600; color: #0E7490; text-decoration: none; }
.list { display: flex; flex-direction: column; gap: 10px; }
.card { background: #fff; border: 2px solid #0F2744; border-radius: 16px; padding: 14px; }
.badge { display: inline-flex; background: #E0F2FE; color: #0E7490; font-size: 11px; font-weight: 600; padding: 4px 10px; border-radius: 999px; margin-bottom: 8px; }
.nm { font-size: 13px; font-weight: 600; }
.line { margin-top: 4px; font-size: 13px; line-height: 1.45; }
.state { text-align: center; color: #6B7280; padding: 36px 8px; }
</style>
