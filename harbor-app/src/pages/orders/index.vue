<template>
  <view class="page" data-figma="A08">
    <view class="status"><text>9:41</text><text>●●●</text></view>
    <view class="head">
      <text class="back" @click="goBack">‹</text>
      <text class="title">My orders</text>
    </view>
    <view class="tabs">
      <view class="tab" :class="{ on: filter === '' }" @click="filter=''">All</view>
      <view class="tab" :class="{ on: filter === 'pending' }" @click="filter='pending'">To pay</view>
      <view class="tab" :class="{ on: filter === 'paid' }" @click="filter='paid'">Paid</view>
      <view class="tab" :class="{ on: filter === 'shipped' }" @click="filter='shipped'">Shipped</view>
    </view>

    <view v-if="loginRequired" class="gate">
      <text class="gate-t">{{ t('orders_signin') }}</text>
      <view class="gate-btn" @click="login">{{ t('nav_sign_in') }}</view>
    </view>
    <view v-else-if="loading" class="state">{{ t('orders_loading') }}</view>
    <view v-else-if="!visible.length" class="state">
      <text>{{ t('orders_empty') }}</text>
      <view class="ghost" @click="shop">{{ t('orders_keep_shopping') }}</view>
    </view>
    <view v-else class="list">
      <view v-for="o in visible" :key="o.id" class="card">
        <view class="row">
          <text class="oid">HB-{{ o.id }}</text>
          <text class="pill" :class="o.status">{{ o.statusLabel || o.status }}</text>
        </view>
        <view class="thumbs">
          <image v-if="o.image" class="img" :src="o.image" mode="aspectFill" />
          <view v-else class="img ph" />
        </view>
        <view class="row">
          <text class="meta">{{ o.due }}</text>
          <text class="price">{{ o.due }}</text>
        </view>
        <view class="actions">
          <view class="btn soft" @click="openOrder(o.id)">Details</view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { useI18n } from '@/composables/i18n'
import { computed, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { fetchOrders, openHarborWeb, accountLinks, type OrderRow } from '@/api/accountApi'
const { t } = useI18n()

const orders = ref<OrderRow[]>([])
const filter = ref('')
const loading = ref(false)
const loginRequired = ref(false)
const visible = computed(() => {
  if (!filter.value) return orders.value
  return orders.value.filter(o => String(o.status || '').toLowerCase().includes(filter.value))
})

async function refresh() {
  loading.value = true
  try {
    const res = await fetchOrders()
    orders.value = res.orders
    loginRequired.value = res.loginRequired && !res.orders.length
  } finally {
    loading.value = false
  }
}
function openOrder(id: string) {
  uni.navigateTo({ url: '/pages/order-detail/index?id=' + encodeURIComponent(id) })
}
function login() { uni.navigateTo({ url: '/pages/login/index' }) }
function shop() { uni.reLaunch({ url: '/pages/home/index' }) }
function goBack() { uni.navigateBack({ fail: () => uni.reLaunch({ url: '/pages/me/index' }) }) }
onShow(() => {
  uni.setNavigationBarTitle({ title: t('orders_title') })
  refresh()
})
</script>

<style lang="scss" scoped>
@import '@/styles/theme.scss';
.page { min-height: 100vh; background: $hb-paper; padding: 0 16px 40px; padding-top: env(safe-area-inset-top); }
.status { display: flex; justify-content: space-between; padding: 10px 4px 0; font-size: 12px; font-weight: 700; color: $hb-ink; }
.head { display: flex; align-items: center; gap: 10px; padding: 8px 0 10px; }
.back { font-size: 22px; font-weight: 700; width: 28px; color: $hb-ink; }
.title { font-size: 17px; font-weight: 800; color: $hb-ink; }
.tabs { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 12px; }
.tab { height: 31px; padding: 0 12px; line-height: 31px; border-radius: 999px; border: 1px solid #E8E4DC; background: #fff; font-size: 12px; color: $hb-ink; }
.tab.on { background: $hb-ink; color: #fff; border-color: $hb-ink; }
.list { display: flex; flex-direction: column; gap: 10px; }
.card { background: #fff; border: 1px solid #E8E4DC; border-radius: 16px; padding: 14px; }
.row { display: flex; justify-content: space-between; align-items: center; }
.oid { font-size: 11px; color: #6B7280; }
.pill { font-size: 11px; font-weight: 600; padding: 4px 10px; border-radius: 999px; background: #ECFDF5; color: #047857; }
.thumbs { margin-top: 10px; }
.img { width: 64px; height: 64px; border-radius: 10px; background: $hb-soft; }
.ph { background: linear-gradient(145deg,#bae6fd,#0369a1); }
.meta { font-size: 11px; color: #6B7280; margin-top: 8px; }
.price { font-size: 16px; font-weight: 800; color: $hb-price; }
.actions { display: flex; justify-content: flex-end; margin-top: 12px; }
.btn { height: 33px; padding: 0 12px; line-height: 33px; border-radius: 12px; background: $hb-ink; color: #fff; font-size: 12px; font-weight: 600; }
.btn.soft { background: #fff; color: $hb-ink; border: 1px solid #E8E4DC; }
.state, .gate { text-align: center; color: $hb-muted; padding: 36px 8px; }
.gate-btn, .ghost { display: inline-flex; margin-top: 12px; padding: 12px 18px; border-radius: 999px; background: $hb-ink; color: #fff; font-weight: 700; }
</style>
