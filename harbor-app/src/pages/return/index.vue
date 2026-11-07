<template>
  <view class="page">
    <view class="status hb-status"><text>9:41</text><text>●●● 5G</text></view>
    <view class="nav">
      <text class="back" @click="goBack">‹</text>
      <text class="title">Request return</text>
    </view>

    <view class="card item">
      <view class="thumb"><text class="tt">Item</text></view>
      <view class="meta">
        <text class="nm">{{ productName || 'Order item' }}</text>
        <text class="oid">Order {{ orderId || '—' }}</text>
        <text class="price">{{ priceLabel }}</text>
      </view>
    </view>

    <view class="field">
      <text class="lab">Reason</text>
      <picker :range="reasons" @change="onReason">
        <text class="val">{{ reason }} ▾</text>
      </picker>
    </view>

    <view class="field tall">
      <text class="lab">Details</text>
      <textarea class="area" v-model="details" placeholder="Corner arrived cracked…" />
    </view>

    <view class="photos">
      <text class="ph">Photos (optional)</text>
      <view class="plus"><text>+</text></view>
    </view>

    <text class="hint">Lightweight return flow → existing order return + CS. Not a full ticket desk.</text>
    <view class="cta" @click="submit">Submit request</view>
    <view class="cta soft" @click="chat">Chat with Harbor</view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { onLoad, onShow } from '@dcloudio/uni-app'
import { useI18n } from '@/composables/i18n'
const { t } = useI18n()
const orderId = ref('')
const productName = ref('')
const priceLabel = ref('')
const reason = ref('Item damaged / not as described')
const details = ref('')
const reasons = [
  'Item damaged / not as described',
  'Wrong item',
  'Changed mind',
  'Other',
]
function onReason(e: any) {
  const i = Number(e?.detail?.value || 0)
  reason.value = reasons[i] || reasons[0]
}
function goBack() { uni.navigateBack({ fail: () => uni.reLaunch({ url: '/pages/orders/index' }) }) }
function chat() { uni.navigateTo({ url: '/pages/chat/index' }) }
function submit() {
  uni.showToast({ title: 'Request recorded — CS will follow up', icon: 'none' })
}
onLoad((q) => {
  orderId.value = q?.id ? decodeURIComponent(q.id) : ''
  productName.value = q?.name ? decodeURIComponent(q.name) : ''
  priceLabel.value = q?.price ? decodeURIComponent(q.price) : ''
})
onShow(() => uni.setNavigationBarTitle({ title: t('return_title') || 'Return' }))
</script>

<style scoped>
.page { min-height: 100vh; background: #F7F4EF; color: #0F2744; padding: 0 16px 40px; padding-top: env(safe-area-inset-top); }
.status { display: flex; justify-content: space-between; padding: 14px 12px 0; font-size: 12px; font-weight: 700; }
.nav { display: flex; align-items: center; gap: 10px; padding: 8px 0 12px; }
.back { font-size: 18px; font-weight: 700; }
.title { font-size: 17px; font-weight: 700; }
.card.item { display: flex; gap: 12px; background: #fff; border: 1px solid #E8E4DC; border-radius: 16px; padding: 12px; margin-bottom: 12px; }
.thumb { width: 64px; height: 64px; border-radius: 10px; background: linear-gradient(145deg, #fcd34d 6%, #b45309 94%); display: flex; align-items: flex-end; padding: 8px; box-sizing: border-box; }
.tt { font-size: 11px; color: #fff; font-weight: 600; }
.nm { display: block; font-size: 13px; font-weight: 600; }
.oid { display: block; margin-top: 4px; font-size: 11px; color: #6B7280; }
.price { display: block; margin-top: 4px; font-size: 16px; font-weight: 700; color: #B45309; }
.field { background: #fff; border: 1px solid #E8E4DC; border-radius: 12px; padding: 12px 14px; margin-bottom: 10px; }
.field.tall { min-height: 88px; }
.lab { display: block; font-size: 11px; font-weight: 600; color: #6B7280; margin-bottom: 4px; }
.val { font-size: 14px; color: #0F2744; }
.area { width: 100%; min-height: 48px; font-size: 14px; color: #0F2744; }
.photos { background: #fff; border: 1px solid #E8E4DC; border-radius: 16px; padding: 14px; margin-bottom: 10px; }
.ph { display: block; font-size: 13px; font-weight: 700; margin-bottom: 10px; }
.plus { width: 64px; height: 64px; border: 1px dashed #E8E4DC; border-radius: 12px; display: flex; align-items: center; justify-content: center; color: #6B7280; font-size: 16px; }
.hint { display: block; font-size: 11px; color: #6B7280; margin: 8px 0 12px; line-height: 1.4; }
.cta { height: 41px; border-radius: 12px; background: #0F2744; color: #fff; font-size: 14px; font-weight: 600; display: flex; align-items: center; justify-content: center; margin-bottom: 8px; }
.cta.soft { background: #fff; color: #0F2744; border: 1px solid #E8E4DC; height: 43px; }
</style>
