<template>
  <view class="page" data-figma="A21">
    <view class="head">
      <view class="head-left">
        <text class="title">{{ t('cart_title') }}</text>
        <text class="badge" v-if="live">{{ t('cart_live') }}</text>
        <text class="badge local" v-else-if="count">{{ t('cart_local') }}</text>
      </view>
      <text class="count">{{ count }} items</text>
    </view>

    <view v-if="syncing" class="sync">{{ t('cart_syncing') }}</view>
    <view v-if="lastError && !live" class="warn">{{ t('cart_server_unavailable') }}</view>

    <view v-if="!lines.length" class="empty">
      <view class="empty-orb" />
      <text class="empty-title">{{ t('cart_empty_title') }}</text>
      <text class="empty-sub">{{ t('cart_empty_body') }}</text>
      <view class="shop" @click="goHome">{{ t('cart_shop') }}</view>
    </view>

    <template v-else>
      <view v-for="line in lines" :key="line.code + line.size" class="line">
        <image v-if="line.product.image" class="thumb-img" :src="line.product.image" mode="aspectFill" />
        <view v-else class="thumb" />
        <view class="meta">
          <text class="name">{{ line.product.name }}</text>
          <text class="opt">{{ line.size }}</text>
          <view class="row">
            <text class="price">{{ money(line.product.price) }}</text>
            <view class="qty">
              <view class="qbtn" @click="bump(line, -1)">−</view>
              <text class="qnum">{{ line.qty }}</text>
              <view class="qbtn" @click="bump(line, 1)">+</view>
            </view>
          </view>
        </view>
      </view>

      <view class="ship" v-if="freeShipThreshold > 0 || shipLine">
        <view class="ship-row">
          <text class="ship-title">{{ t('cart_min_order') }}</text>
          <text class="ship-left">
            {{ (freeShipThreshold > 0 && remainingToFreeShip <= 0) || shipMet ? t('cart_unlocked') : t('cart_to_go', { amount: money(remainingToFreeShip) }) }}
          </text>
        </view>
        <view class="bar" v-if="freeShipThreshold > 0">
          <view class="fill" :style="{ width: freeShipProgress * 100 + '%' }" />
        </view>
        <text class="ship-note">
          {{ shipLine || (freeShipThreshold > 0 ? (t('cart_min_order') + ' ' + money(freeShipThreshold) + ' · ' + t('cart_free_shipping')) : t('cart_free_shipping')) }}
        </text>
      </view>

      <view class="sum-card">
        <view class="sum">
          <text class="muted">{{ t('cart_subtotal') }}</text>
          <text class="bold">{{ money(subtotal) }}</text>
        </view>
      </view>

      <view class="checkout" @click="goCheckout">{{ t('cart_checkout', { amount: money(subtotal) }) }}</view>
      <text class="hint">Pay on Harbor — PayPal / card / LianLian. No ads on checkout.</text>
    </template>

    <HbTabBar active="cart" />
  </view>
</template>

<script setup lang="ts">
import { onShow } from '@dcloudio/uni-app'
import { money } from '@/api/products'
import { useCart, type CartLine } from '@/composables/cart'
import { useI18n } from '@/composables/i18n'
import HbTabBar from '@/components/HbTabBar.vue'

const { t } = useI18n()
const {
  lines,
  count,
  subtotal,
  remainingToFreeShip,
  freeShipProgress,
  freeShipThreshold,
  shipLine,
  shipMet,
  live,
  syncing,
  lastError,
  setQty,
  refresh,
} = useCart()

onShow(() => {
  refresh()
})

function bump(line: CartLine, delta: number) {
  setQty(line.code, line.size, line.qty + delta)
}

function goHome() {
  uni.reLaunch({ url: '/pages/home/index' })
}
function goCheckout() {
  uni.navigateTo({ url: '/pages/checkout/index' })
}
</script>

<style lang="scss" scoped>
@import '@/styles/theme.scss';

.page {
  min-height: 100vh;
  background: $hb-paper;
  padding: 16px;
  padding-top: calc(16px + env(safe-area-inset-top));
}
.head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 16px;
}
.head-left {
  display: flex;
  align-items: center;
  gap: 8px;
}
.title {
  font-size: 28px;
  font-weight: 720;
  letter-spacing: -0.7px;
}
.badge {
  font-size: 10px;
  font-weight: 700;
  color: $hb-forest;
  background: $hb-soft;
  padding: 4px 9px;
  border-radius: 999px;
  &.local {
    color: $hb-muted;
    background: rgba(20, 26, 23, 0.06);
  }
}
.count {
  font-size: 13px;
  color: $hb-muted;
}
.sync,
.warn {
  font-size: 12px;
  color: $hb-muted;
  margin-bottom: 12px;
}
.warn {
  color: $hb-coral;
  background: $hb-coral-soft;
  padding: 10px 12px;
  border-radius: 14px;
}
.empty {
  padding: 56px 12px;
  text-align: center;
}
.empty-orb {
  width: 72px;
  height: 72px;
  margin: 0 auto 16px;
  border-radius: 24px;
  background: linear-gradient(160deg, $hb-soft, #d8e4dc);
}
.empty-title {
  display: block;
  font-size: 18px;
  font-weight: 700;
  letter-spacing: -0.3px;
}
.empty-sub {
  display: block;
  margin-top: 6px;
  font-size: 13px;
  color: $hb-muted;
}
.shop {
  margin: 20px auto 0;
  width: 160px;
  height: 48px;
  border-radius: $hb-radius-pill;
  background: $hb-forest;
  color: $hb-white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
}
.line {
  display: flex;
  gap: 14px;
  padding: 14px;
  border-radius: 20px;
  background: $hb-white;
  margin-bottom: 10px;
  box-shadow: $hb-shadow-soft;
}
.thumb,
.thumb-img {
  width: 84px;
  height: 84px;
  border-radius: 16px;
  background: linear-gradient(160deg, #eceee9, #e0e4de);
  flex: none;
}
.thumb-img {
  display: block;
}
.meta {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.name {
  display: block;
  font-size: 14px;
  font-weight: 650;
  line-height: 1.3;
  letter-spacing: -0.2px;
}
.opt {
  display: block;
  font-size: 12px;
  color: $hb-muted;
  margin-top: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.row {
  margin-top: auto;
  padding-top: 10px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.price {
  color: $hb-ink;
  font-weight: 720;
  font-size: 16px;
  letter-spacing: -0.3px;
}
.qty {
  display: flex;
  align-items: center;
  gap: 10px;
  background: $hb-paper;
  border-radius: 999px;
  padding: 4px;
}
.qbtn {
  width: 28px;
  height: 28px;
  border-radius: 99px;
  background: $hb-white;
  text-align: center;
  line-height: 28px;
  font-weight: 700;
  color: $hb-ink;
  box-shadow: $hb-shadow-soft;
}
.qnum {
  min-width: 16px;
  text-align: center;
  font-size: 13px;
  font-weight: 700;
}
.ship {
  border-radius: 20px;
  background: $hb-soft;
  padding: 16px;
  margin: 6px 0 14px;
}
.ship-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 10px;
}
.ship-title {
  font-size: 13px;
  font-weight: 700;
  color: $hb-forest;
}
.ship-left {
  font-size: 13px;
  color: $hb-forest;
  font-weight: 600;
}
.bar {
  height: 6px;
  border-radius: 99px;
  background: rgba(255, 255, 255, 0.85);
  overflow: hidden;
}
.fill {
  height: 100%;
  background: $hb-forest;
  border-radius: 99px;
}
.ship-note {
  display: block;
  font-size: 11px;
  color: $hb-muted;
  margin-top: 8px;
}
.sum-card {
  background: $hb-white;
  border-radius: 18px;
  padding: 14px 16px;
  margin-bottom: 12px;
  box-shadow: $hb-shadow-soft;
}
.sum {
  display: flex;
  justify-content: space-between;
  font-size: 14px;
}
.muted {
  color: $hb-muted;
}
.bold {
  font-weight: 720;
  letter-spacing: -0.2px;
}
.checkout {
  height: 54px;
  border-radius: $hb-radius-pill;
  background: $hb-forest;
  color: $hb-white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 720;
  font-size: 16px;
  letter-spacing: -0.2px;
  box-shadow: 0 10px 24px rgba(30, 77, 59, 0.25);
}
.hint {
  display: block;
  margin-top: 14px;
  font-size: 12px;
  color: $hb-muted;
  text-align: center;
  line-height: 1.45;
  padding-bottom: 12px;
}
.page { background: #F7F4EF; padding-top: env(safe-area-inset-top); }
.price { color: #B45309 !important; }
</style>
