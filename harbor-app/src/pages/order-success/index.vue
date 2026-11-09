<template>
  <view class="page">
    <view class="status hb-status"><text>9:41</text><text>●●● 5G</text></view>
    <view class="center">
      <view class="ok"><text>✓</text></view>
      <text class="title">Payment successful</text>
      <text class="meta">{{ orderId || '—' }}{{ total ? ' · ' + total : '' }}</text>
      <view class="cta" @click="viewOrder">View order</view>
    </view>
    <HbLucky />
  </view>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { onLoad, onShow } from '@dcloudio/uni-app'
import { showOrderEgg } from '@/composables/lucky'
const orderId = ref('')
const total = ref('')
onLoad((q) => {
  orderId.value = q?.id ? decodeURIComponent(q.id) : (q?.order ? decodeURIComponent(q.order) : '')
  total.value = q?.total ? decodeURIComponent(q.total) : ''
  showOrderEgg(orderId.value)
})
function viewOrder() {
  if (orderId.value) {
    uni.redirectTo({ url: '/pages/order-detail/index?id=' + encodeURIComponent(orderId.value) })
  } else {
    uni.redirectTo({ url: '/pages/orders/index' })
  }
}
onShow(() => uni.setNavigationBarTitle({ title: 'Success' }))
</script>
<style scoped>
.page { min-height: 100vh; background: #F7F4EF; color: #0F2744; padding-top: env(safe-area-inset-top); }
.status { display: flex; justify-content: space-between; padding: 14px 28px 0; font-size: 12px; font-weight: 700; }
.center { padding: 100px 32px 40px; display: flex; flex-direction: column; align-items: center; }
.ok { width: 72px; height: 72px; border-radius: 36px; background: #D1FAE5; color: #047857; font-size: 28px; display: flex; align-items: center; justify-content: center; }
.title { margin-top: 14px; font-size: 22px; font-weight: 700; text-align: center; }
.meta { margin-top: 8px; font-size: 11px; color: #5C6570; text-align: center; }
.cta { margin-top: 20px; width: 100%; max-width: 320px; height: 41px; border-radius: 12px; background: #0F2744; color: #fff; font-weight: 600; display: flex; align-items: center; justify-content: center; }
</style>
