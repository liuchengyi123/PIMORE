<template>
  <view class="page">
    <view class="status hb-status"><text>9:41</text><text>●●● 5G</text></view>
    <view class="nav">
      <text class="back" @click="goBack">‹</text>
      <text class="title">Order detail</text>
    </view>
    <view v-if="loading" class="state">Loading…</view>
    <view v-else>
      <view class="card status-card">
        <view class="row">
          <text class="st">{{ detail.status || '—' }}</text>
          <text class="oid">{{ detail.id || '—' }}</text>
        </view>
        <text v-if="detail.carrier || detail.tracking" class="track">
          {{ [detail.carrier, detail.tracking].filter(Boolean).join(' ') }}
        </text>
        <text v-if="detail.arrives" class="track">Arrives {{ detail.arrives }}</text>
        <view class="pill"><text class="pill-t">物流 · order fields only</text></view>
      </view>

      <view v-for="(line, i) in detail.summary" :key="i" class="card item">
        <view class="thumb" />
        <view class="meta">
          <text class="nm">{{ line }}</text>
        </view>
      </view>

      <view v-if="detail.canPay" class="cta" @click="pay">Pay now</view>
      <view class="cta soft" @click="invoice">Invoice</view>
      <view class="cta soft" @click="openSite">Open on Harbor</view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { useI18n } from '@/composables/i18n'
import { reactive, ref } from 'vue'
import { onLoad, onShow } from '@dcloudio/uni-app'
import { fetchOrderDetail, openHarborWeb, type OrderDetail } from '@/api/accountApi'
const { t } = useI18n()

const loading = ref(false)
const detail = reactive<OrderDetail>({
  ok: false, live: false, id: '', status: '', due: '', arrives: '', tracking: '', carrier: '',
  summary: [], canPay: false, canCancel: false,
})

async function load(id: string) {
  loading.value = true
  try {
    Object.assign(detail, await fetchOrderDetail(id))
  } finally {
    loading.value = false
  }
}

function pay() {
  openHarborWeb('/orders/' + encodeURIComponent(detail.id) + '/pay', 'Pay')
}
function invoice() {
  uni.navigateTo({ url: '/pages/invoice/index?id=' + encodeURIComponent(detail.id) })
}
function openSite() {
  openHarborWeb('/orders/' + encodeURIComponent(detail.id), 'Order')
}
function goBack() {
  uni.navigateBack({ fail: () => uni.redirectTo({ url: '/pages/orders/index' }) })
}

onLoad((q) => {
  const id = q?.id ? decodeURIComponent(q.id) : ''
  if (id) load(id)
})

onShow(() => {
  uni.setNavigationBarTitle({ title: t('order_title') })
})
</script>

<style scoped>
.page { min-height: 100vh; background: #F7F4EF; color: #0F2744; padding: 0 16px 40px; padding-top: env(safe-area-inset-top); }
.status { display: flex; justify-content: space-between; padding: 14px 12px 0; font-size: 12px; font-weight: 700; color: #0F2744; }
.nav { display: flex; align-items: center; gap: 10px; padding: 8px 0 12px; }
.back { font-size: 18px; font-weight: 700; padding: 0 4px; }
.title { font-size: 17px; font-weight: 700; }
.card { background: #fff; border: 1px solid #E2E6EE; border-radius: 16px; padding: 14px; margin-bottom: 10px; }
.row { display: flex; justify-content: space-between; align-items: center; }
.st { font-size: 16px; font-weight: 700; color: #0E7490; }
.oid { font-size: 11px; color: #5C6570; }
.track { display: block; margin-top: 8px; font-size: 11px; color: #5C6570; }
.pill { margin-top: 10px; display: inline-flex; background: #DBEAFE; border-radius: 6px; padding: 3px 6px; }
.pill-t { font-size: 9px; font-weight: 700; color: #1E40AF; }
.item { display: flex; gap: 12px; align-items: flex-start; }
.thumb { width: 64px; height: 64px; border-radius: 10px; background: linear-gradient(145deg, #fcd34d 6%, #b45309 94%); flex-shrink: 0; }
.nm { font-size: 13px; font-weight: 600; line-height: 1.35; }
.cta { margin-top: 8px; height: 41px; border-radius: 12px; background: #0F2744; color: #fff; font-size: 14px; font-weight: 600; display: flex; align-items: center; justify-content: center; }
.cta.soft { background: #fff; color: #0F2744; border: 1px solid #E8E4DC; }
.state { text-align: center; color: #6B7280; padding: 36px 8px; }
</style>
