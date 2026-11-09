<template>
  <div class="page" data-figma="M15">
    <header class="head">
      <button type="button" class="back" @click="$router.back()" aria-label="back"><ChevronLeft :size="22" :stroke-width="1.75" /></button>
      <h1>{{ zh ? '订单' : 'Order' }} #{{ id }}</h1>
    </header>
    <div v-if="loading" class="state">{{ t('pdp_loading') }}</div>
    <div v-else-if="!detail.ok" class="state">{{ detail.rawHint || 'Not found' }}</div>
    <template v-else>
      <div class="card track">
        <div class="steps">
          <span :class="{ on: true }">{{ zh ? '已支付' : 'Paid' }}</span>
          <span :class="{ on: /ship|deliver/i.test(detail.status) }">● {{ zh ? '已发货' : 'Shipped' }}</span>
          <span :class="{ on: /deliver/i.test(detail.status) }">{{ zh ? '已送达' : 'Delivered' }}</span>
        </div>
        <div class="bar"><i :style="{ width: /deliver/i.test(detail.status) ? '100%' : (/ship/i.test(detail.status) ? '66%' : '33%') }" /></div>
        <div class="meta" v-if="detail.tracking">{{ zh ? '承运商' : 'Carrier' }} {{ detail.carrier || '—' }} · {{ detail.tracking }}</div>
        <div class="meta" v-else>{{ zh ? '状态' : 'Status' }} · {{ detail.status }}</div>
      </div>
      <div class="card">
        <div class="row"><span>{{ zh ? '状态' : 'Status' }}</span><b>{{ detail.status }}</b></div>
        <div class="row"><span>{{ zh ? '应付' : 'Due' }}</span><b class="due">{{ detail.due || '—' }}</b></div>
        <div v-if="detail.arrives" class="row"><span>{{ zh ? '送达' : 'Arrives' }}</span><b>{{ detail.arrives }}</b></div>
      </div>
      <div v-if="detail.summary.length" class="card">
        <div v-for="(s, i) in detail.summary" :key="i" class="sum">{{ s }}</div>
      </div>
      <router-link v-if="id" class="btn soft" :to="{ path: '/invoice', query: { id } }">{{ zh ? '发票' : 'Invoice' }}</router-link>
      <button type="button" class="btn" @click="askCs">{{ t('chat_entry') }}</button>
    </template>
  </div>
</template>
<script setup lang="ts">
import { ChevronLeft } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { fetchOrderDetail, type OrderDetail } from '@/api/accountApi'
import { buildOrderBody } from '@/api/supportApi'
import { useI18n } from '@/composables/i18n'

const { t, lang } = useI18n()
const zh = computed(() => String(lang.value).startsWith('zh'))
const route = useRoute()
const router = useRouter()
const id = String(route.params.id || '')
const loading = ref(true)
const detail = ref<OrderDetail>({
  ok: false, live: false, id, status: '', due: '', arrives: '', tracking: '', carrier: '', summary: [], canPay: false, canCancel: false,
})

onMounted(async () => {
  detail.value = await fetchOrderDetail(id)
  loading.value = false
})

function askCs() {
  const body = buildOrderBody({
    id: detail.value.id,
    status: detail.value.status,
    tracking: detail.value.tracking,
    items: detail.value.summary.slice(0, 4),
  })
  sessionStorage.setItem('harbor_cs_prefill_order', body)
  router.push({ path: '/chat', query: { order: id } })
}
</script>
<style lang="scss" scoped>
@import '@/styles/theme.scss';
.page { min-height: 100vh; background: $hb-paper; padding: 8px 16px 40px; padding-top: calc(8px + env(safe-area-inset-top)); }
.head { display: flex; align-items: center; gap: 10px; margin-bottom: 14px; }
.back { width: 36px; height: 36px; border: 0; border-radius: 12px; background: #fff; display: inline-flex; align-items: center; justify-content: center; box-shadow: $hb-shadow-soft; color: $hb-ink; }
h1 { margin: 0; font-size: 18px; font-weight: 800; color: $hb-ink; }
.card { background: #fff; border-radius: 14px; padding: 14px; margin-bottom: 10px; border: 1px solid $hb-line; }
.row { display: flex; justify-content: space-between; gap: 12px; padding: 6px 0; font-size: 13px; color: $hb-muted; }
.row b { color: $hb-ink; font-weight: 700; }
.due { color: $hb-price !important; }
.steps { display: flex; justify-content: space-between; font-size: 12px; font-weight: 600; color: $hb-muted; }
.steps .on { color: #F96141; }
.bar { height: 4px; background: #F3E4DE; border-radius: 4px; margin: 10px 0; overflow: hidden; }
.bar i { display: block; height: 100%; background: #F96141; }
.meta { font-size: 12px; color: $hb-muted; margin-top: 4px; }
.sum { font-size: 13px; color: $hb-ink; padding: 6px 0; border-bottom: 1px solid $hb-line; }
.sum:last-child { border: 0; }
.state { text-align: center; color: $hb-muted; padding: 40px 8px; }
.btn {
  display: flex; align-items: center; justify-content: center; width: 100%; height: 48px; margin-top: 10px;
  border: 0; border-radius: 999px; background: #F96141; color: #fff; font-weight: 700; text-decoration: none; cursor: pointer;
}
.btn.soft { background: #fff; color: $hb-ink; border: 1px solid $hb-line; }
</style>
