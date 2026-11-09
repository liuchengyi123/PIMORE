<template>
  <AgShell tabs="me">
    <header class="head ag-top ag-pad">
      <button type="button" class="ag-back" @click="router.back()" :aria-label="tx('返回', 'Back')">
        <ChevronLeft :size="26" :stroke-width="2.2" />
      </button>
      <div>
        <h1 class="ag-h1">{{ tx('收货地址', 'Shipping addresses') }}</h1>
        <p class="ag-sub">{{ tx('管理收货地址，让购物更顺畅。', 'Manage your delivery addresses for a smoother shopping experience.') }}</p>
      </div>
    </header>

    <div class="ag-pad list">
      <p v-if="msg" class="ag-toast">{{ msg }}</p>
      <div v-if="loading" class="ag-empty"><p>{{ tx('加载中…', 'Loading…') }}</p></div>
      <div v-else-if="loginRequired && !rows.length" class="ag-empty">
        <h3>{{ tx('登录后管理地址', 'Sign in to manage addresses') }}</h3>
        <router-link class="ag-cta" style="margin-top:14px" :to="{ path: '/login', query: { next: '/addresses' } }">{{ tx('登录', 'Sign in') }}</router-link>
      </div>
      <div v-else-if="!shown.length && !adding" class="ag-empty">
        <h3>{{ tx('还没有收货地址', 'No addresses yet') }}</h3>
        <p>{{ tx('添加一个地址，下单会更快。', 'Add one so checkout is faster.') }}</p>
      </div>

      <article v-for="(r, i) in shown" :key="r.key" class="card ag-card">
        <div class="top">
          <div>
            <span v-if="i === 0" class="ag-chip">{{ tx('默认', 'Default') }}</span>
            <div class="nm">{{ r.name }}</div>
            <div v-if="r.phone" class="line">{{ r.phone }}</div>
            <div class="line">{{ r.addr }}</div>
          </div>
          <button type="button" class="more" @click="makeDefault(r.key)" :aria-label="tx('设为默认', 'Make default')">
            <MoreHorizontal :size="18" />
          </button>
        </div>
        <div class="acts">
          <button type="button" @click="startEdit(r)"><Pencil :size="15" /> {{ tx('编辑', 'Edit') }}</button>
          <button type="button" @click="remove(r.key)"><Trash2 :size="15" /> {{ tx('删除', 'Delete') }}</button>
        </div>
      </article>

      <form v-if="adding" class="form ag-card" @submit.prevent="save">
        <label class="ag-field"><span>{{ tx('收件人', 'Name') }}</span><input v-model="form.name" required /></label>
        <label class="ag-field"><span>{{ tx('电话', 'Phone') }}</span><input v-model="form.phone" /></label>
        <label class="ag-field"><span>{{ tx('街道地址', 'Street') }}</span><input v-model="form.address" required /></label>
        <div class="split">
          <label class="ag-field"><span>{{ tx('城市', 'City') }}</span><input v-model="form.city" /></label>
          <label class="ag-field"><span>{{ tx('省 / 州', 'Region') }}</span><input v-model="form.region" /></label>
        </div>
        <div class="split">
          <label class="ag-field"><span>{{ tx('邮编', 'Postal') }}</span><input v-model="form.postal" /></label>
          <label class="ag-field">
            <span>{{ tx('国家', 'Country') }}</span>
            <select v-model="form.ship_country">
              <option v-for="c in countries" :key="c" :value="c">{{ c }}</option>
            </select>
          </label>
        </div>
        <button class="ag-cta" type="submit" :disabled="busy">{{ busy ? '…' : tx('保存地址', 'Save address') }}</button>
        <button class="ag-cta ghost" type="button" style="margin-top:8px" @click="adding = false">{{ tx('取消', 'Cancel') }}</button>
      </form>

      <button v-else type="button" class="ag-cta add" @click="startAdd">
        <Plus :size="18" /> {{ tx('新增地址', 'Add new address') }}
      </button>
    </div>
  </AgShell>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ChevronLeft, MoreHorizontal, Pencil, Plus, Trash2 } from 'lucide-vue-next'
import AgShell from '@/components/account/AgShell.vue'
import { addAddress, fetchAddresses, type AddressRow } from '@/api/accountApi'
import { STORE_COUNTRIES } from '@/api/countryLocale'
import { useZh } from '@/composables/zh'

interface Card extends AddressRow {
  key: string
  phone: string
  addr: string
}

const { tx } = useZh()
const router = useRouter()
const rows = ref<Card[]>([])
const hidden = ref(new Set<string>())
const order = ref<string[]>([])
const loading = ref(true)
const loginRequired = ref(false)
const adding = ref(false)
const busy = ref(false)
const msg = ref('')
const countries = STORE_COUNTRIES
const form = reactive({ name: '', address: '', city: '', region: '', postal: '', ship_country: 'CN', phone: '', street_number: '', district: '' })

const shown = computed(() => {
  const list = rows.value.filter((r) => !hidden.value.has(r.key))
  const rank = new Map(order.value.map((k, i) => [k, i]))
  return [...list].sort((a, b) => (rank.get(a.key) ?? 99) - (rank.get(b.key) ?? 99))
})

function split(row: AddressRow, i: number): Card {
  const raw = row.line || ''
  const phoneM = raw.match(/(\+?\d[\d\s().-]{6,}\d)/)
  const phone = phoneM ? phoneM[1].trim() : ''
  const addr = raw.replace(phone, '').replace(/^[,·\s]+|[,·\s]+$/g, '').trim() || raw
  return { ...row, key: `${row.name}-${i}`, phone, addr }
}

async function refresh() {
  loading.value = true
  try {
    const res = await fetchAddresses()
    rows.value = res.rows.map(split)
    loginRequired.value = res.loginRequired && !res.rows.length
  } finally { loading.value = false }
}
onMounted(refresh)

function startAdd() {
  form.name = form.address = form.city = form.region = form.postal = form.phone = ''
  form.ship_country = 'CN'
  adding.value = true
}
function startEdit(r: Card) {
  form.name = r.name
  form.phone = r.phone
  form.address = r.addr
  adding.value = true
}
function remove(key: string) {
  hidden.value = new Set([...hidden.value, key])
}
function makeDefault(key: string) {
  order.value = [key, ...order.value.filter((k) => k !== key)]
  msg.value = tx('已设为默认（本机）', 'Default updated on this device')
}
async function save() {
  busy.value = true
  msg.value = ''
  try {
    const res = await addAddress({ ...form })
    if (!res.ok || res.status === 401) {
      msg.value = res.status === 401 ? tx('请先登录', 'Please sign in') : tx('保存失败', 'Could not save')
      if (res.status === 401) loginRequired.value = true
      return
    }
    msg.value = tx('地址已保存', 'Address saved')
    adding.value = false
    await refresh()
  } catch {
    msg.value = tx('网络错误', 'Network error')
  } finally { busy.value = false }
}
</script>

<style scoped>
.head { display: grid; grid-template-columns: 36px 1fr; gap: 4px; align-items: start; margin-bottom: 14px; }
.list { display: flex; flex-direction: column; gap: 12px; padding-bottom: 12px; }
.card { padding: 14px 14px 0; overflow: hidden; }
.top { display: flex; justify-content: space-between; gap: 8px; padding-bottom: 12px; }
.nm { margin-top: 8px; font-size: 16px; font-weight: 800; }
.line { margin-top: 3px; font-size: 13.5px; color: #5C6570; line-height: 1.4; }
.more { border: 0; background: transparent; color: #8B919A; cursor: pointer; height: 28px; }
.acts { display: grid; grid-template-columns: 1fr 1fr; border-top: 1px solid #F1ECE6; margin: 0 -14px; }
.acts button {
  height: 44px; border: 0; background: transparent; color: #F96141; font-weight: 700; cursor: pointer;
  display: inline-flex; align-items: center; justify-content: center; gap: 6px;
}
.acts button + button { border-left: 1px solid #F1ECE6; }
.add { margin-top: 4px; }
.form { padding: 14px; }
.split { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
</style>
