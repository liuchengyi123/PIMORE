<template>
  <view class="page" data-figma="A07">
    <view class="status"><text>9:41</text><text>●●●</text></view>
    <view class="head"><text class="back" @click="goBack">‹</text><text class="h">Checkout</text></view>

    <view class="card">
      <view class="row"><text class="sec">Ship to</text><text class="link">Change</text></view>
      <text class="tiny">Guest checkout · email becomes your tracking account</text>
    </view>

    <view class="card">
      <text class="sec">Order</text>
      <view v-for="line in lines" :key="line.code" class="row line">
        <text class="name">{{ line.product.name }} × {{ line.qty }}</text>
        <text class="amt">{{ money(line.product.price * line.qty) }}</text>
      </view>
      <view v-if="!lines.length" class="empty">{{ t('checkout_empty') }}</view>
    </view>

    <view class="card">
      <text class="sec">Pay with</text>
      <view class="pay on">● PayPal / Card / LianLian</view>
      <text class="tiny">{{ live ? 'Cart synced with store' : 'Local cart syncs before payment' }}</text>
    </view>

    <view class="card">
      <view class="row"><text class="tiny">Items</text><text>{{ money(subtotal) }}</text></view>
      <view v-if="off" class="row"><text class="tiny">{{ lucky.percent }}% off</text><text>-{{ money(off) }}</text></view>
      <view class="row total"><text class="sec">Total</text><text class="price">{{ money(due) }}</text></view>
    </view>

    <view class="dock">
      <text class="price">{{ money(due) }}</text>
      <view class="place" :class="{ disabled: !lines.length }" @click="place">{{ t('checkout_place') }}</view>
    </view>
    <text class="alt" @click="openBrowser">{{ t('checkout_browser') }}</text>
    <HbLucky />
  </view>
</template>
<script setup lang="ts">
import { computed } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { useI18n } from '@/composables/i18n'
import { money } from '@/api/products'
import { checkoutHandoffUrl } from '@/api/http'
import { useCart } from '@/composables/cart'
import { lucky, luckyToken, openPayRetain, closeLucky } from '@/composables/lucky'
const { t } = useI18n()

const { lines, subtotal, live } = useCart()
const off = computed(() => (lucky.spin?.live ? Math.round(subtotal.value * lucky.percent) / 100 : 0))
const due = computed(() => Math.max(0, Math.round((subtotal.value - off.value) * 100) / 100))

function place() {
  if (!lines.value.length) {
    uni.showToast({ title: t('checkout_empty'), icon: 'none' })
    return
  }
  const url = encodeURIComponent(checkoutHandoffUrl(false, luckyToken()))
  uni.navigateTo({ url: '/pages/webview/index?url=' + url })
}

function openBrowser() {
  const url = checkoutHandoffUrl(false, luckyToken())
  // #ifdef H5
  place()
  // #endif
  // #ifndef H5
  try {
    // @ts-expect-error plus
    plus.runtime.openURL(url)
  } catch {
    uni.setClipboardData({ data: url })
    uni.showToast({ title: t('checkout_copied'), icon: 'none' })
  }
  // #endif
}

function goBack() {
  if (lucky.pane) {
    closeLucky()
    return
  }
  if (openPayRetain()) return
  uni.navigateBack({ fail: () => uni.reLaunch({ url: '/pages/cart/index' }) })
}
onShow(() => {
  uni.setNavigationBarTitle({ title: t('checkout_title') })
})
</script>
<style lang="scss" scoped>
@import '@/styles/theme.scss';
.page { min-height: 100vh; background: $hb-paper; padding: 0 16px 120px; padding-top: env(safe-area-inset-top); }
.status { display: flex; justify-content: space-between; padding: 10px 4px 0; font-size: 12px; font-weight: 700; color: $hb-ink; }
.head { display: flex; align-items: center; gap: 10px; padding: 8px 0 12px; }
.back { font-size: 22px; font-weight: 700; color: $hb-ink; width: 28px; }
.h { font-size: 18px; font-weight: 800; color: $hb-ink; }
.card { background: #fff; border: 1px solid $hb-line; border-radius: 14px; padding: 14px; margin-bottom: 10px; }
.sec { font-size: 14px; font-weight: 700; color: $hb-ink; }
.row { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.line { margin-top: 8px; }
.name { flex: 1; font-size: 13px; color: $hb-ink; }
.amt { font-size: 13px; color: $hb-ink; font-weight: 600; }
.link { font-size: 12px; color: $hb-deep; font-weight: 600; }
.tiny { display: block; margin-top: 6px; font-size: 12px; color: $hb-muted; }
.pay { margin-top: 8px; padding: 12px; border: 2px solid $hb-ink; border-radius: 12px; font-size: 13px; font-weight: 600; color: $hb-ink; }
.total { margin-top: 8px; padding-top: 8px; border-top: 1px solid $hb-line; }
.price { font-size: 18px; font-weight: 800; color: $hb-price; }
.empty { color: $hb-muted; font-size: 13px; margin-top: 8px; }
.dock {
  position: fixed; left: 0; right: 0; bottom: 0; background: #fff; border-top: 1px solid $hb-line;
  padding: 12px 16px; padding-bottom: calc(12px + env(safe-area-inset-bottom));
  display: flex; gap: 12px; align-items: center;
}
.place {
  flex: 1; height: 48px; border-radius: 14px; background: $hb-ink; color: #fff;
  display: flex; align-items: center; justify-content: center; font-weight: 700;
}
.place.disabled { opacity: .45; }
.alt { display: block; text-align: center; margin-top: 12px; color: $hb-muted; font-size: 12px; }
</style>
