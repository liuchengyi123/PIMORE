<template>
  <HbLucky />
  <view class="tab-spacer" />
  <view class="tab-bar">
    <view class="homeind" aria-hidden="true" />
    <view v-for="t in tabs" :key="t.id" class="tab" @click="go(t)">
      <view class="icon-wrap" :class="{ on: t.id === active }">
        <!-- Home -->
        <view v-if="t.id === 'home'" class="ico home" :class="{ on: t.id === active }">
          <view class="home-roof" />
          <view class="home-body" />
        </view>
        <!-- Browse -->
        <view v-else-if="t.id === 'browse'" class="ico browse" :class="{ on: t.id === active }">
          <view class="sq a" /><view class="sq b" /><view class="sq c" /><view class="sq d" />
        </view>
        <!-- Cart -->
        <view v-else-if="t.id === 'cart'" class="ico bag" :class="{ on: t.id === active }">
          <view class="bag-body" />
          <view class="bag-handle" />
          <view v-if="cartCount > 0" class="cart-badge">
            <text>{{ cartCount > 9 ? '9+' : cartCount }}</text>
          </view>
        </view>
        <!-- Me -->
        <view v-else class="ico me" :class="{ on: t.id === active }">
          <view class="head" />
          <view class="shoulders" />
        </view>
      </view>
      <text class="label" :class="{ on: t.id === active }">{{ t.label }}</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from '@/composables/i18n'
import { useCart } from '@/composables/cart'

type TabId = 'home' | 'browse' | 'cart' | 'me'

defineProps<{ active: TabId }>()

const { t } = useI18n()
const { count } = useCart()
const cartCount = computed(() => count.value)

const tabs = computed(() => [
  { id: 'home' as const, label: t('tab_home'), url: '/pages/home/index' },
  { id: 'browse' as const, label: t('tab_browse'), url: '/pages/browse/index' },
  { id: 'cart' as const, label: t('tab_cart'), url: '/pages/cart/index' },
  { id: 'me' as const, label: t('tab_me'), url: '/pages/me/index' },
])

function go(tab: { id: TabId; label: string; url: string }) {
  uni.reLaunch({ url: tab.url })
}
</script>

<style lang="scss" scoped>
@import '@/styles/theme.scss';

.tab-spacer {
  height: calc(64px + env(safe-area-inset-bottom));
}
.homeind {
  position: absolute;
  left: 50%;
  bottom: 6px;
  width: 128px;
  height: 5px;
  margin-left: -64px;
  border-radius: 99px;
  background: #1B2B4A;
}
.icon-wrap.on {
  background: transparent;
  width: 28px;
  height: 28px;
}
.tab-bar {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  height: auto;
  padding: 8px 8px calc(12px + env(safe-area-inset-bottom));
  border-radius: 0;
  background: #fff;
  border-top: 1px solid #EEF1F6;
  display: flex;
  align-items: flex-end;
  justify-content: space-around;
  z-index: 100;
  box-shadow: none;
}
.tab {
  width: 64px;
  text-align: center;
  padding: 4px 0;
}
.icon-wrap {
  width: 28px;
  height: 28px;
  margin: 0 auto 2px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.ico {
  position: relative;
  width: 22px;
  height: 22px;
}
.label {
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 0;
  color: #9AA3B2;
  &.on {
    font-weight: 700;
    color: $hb-coral;
  }
}
.cart-badge {
  position: absolute;
  top: -6px;
  right: -8px;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  border-radius: 99px;
  background: $hb-coral;
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 16px;
}

/* Home icon */
.home-roof {
  position: absolute;
  left: 2px;
  top: 2px;
  width: 0;
  height: 0;
  border-left: 9px solid transparent;
  border-right: 9px solid transparent;
  border-bottom: 8px solid $hb-muted;
}
.home-body {
  position: absolute;
  left: 5px;
  top: 9px;
  width: 12px;
  height: 10px;
  border: 2px solid $hb-muted;
  border-top: none;
  border-radius: 0 0 2px 2px;
  box-sizing: border-box;
}
.home.on .home-roof {
  border-bottom-color: $hb-coral;
}
.home.on .home-body {
  border-color: $hb-coral;
  background: transparent;
}

/* Browse 2x2 */
.browse .sq {
  position: absolute;
  width: 8px;
  height: 8px;
  border-radius: 2px;
  border: 1.5px solid $hb-muted;
  box-sizing: border-box;
}
.browse .a { left: 1px; top: 1px; }
.browse .b { right: 1px; top: 1px; }
.browse .c { left: 1px; bottom: 1px; }
.browse .d { right: 1px; bottom: 1px; }
.browse.on .sq {
  border-color: $hb-coral;
}
.browse.on .a {
  background: $hb-coral;
}

/* Bag */
.bag-body {
  position: absolute;
  left: 3px;
  top: 7px;
  width: 16px;
  height: 13px;
  border: 2px solid $hb-muted;
  border-radius: 3px 3px 5px 5px;
  box-sizing: border-box;
}
.bag-handle {
  position: absolute;
  left: 7px;
  top: 2px;
  width: 8px;
  height: 7px;
  border: 2px solid $hb-muted;
  border-bottom: none;
  border-radius: 8px 8px 0 0;
  box-sizing: border-box;
}
.bag.on .bag-body,
.bag.on .bag-handle {
  border-color: $hb-coral;
}
.bag.on .bag-body {
  background: transparent;
}

/* Me */
.me .head {
  position: absolute;
  left: 7px;
  top: 1px;
  width: 8px;
  height: 8px;
  border-radius: 99px;
  border: 2px solid $hb-muted;
  box-sizing: border-box;
}
.me .shoulders {
  position: absolute;
  left: 3px;
  bottom: 1px;
  width: 16px;
  height: 8px;
  border: 2px solid $hb-muted;
  border-bottom: none;
  border-radius: 10px 10px 0 0;
  box-sizing: border-box;
}
.me.on .head,
.me.on .shoulders {
  border-color: $hb-coral;
}
.me.on .head {
  background: transparent;
}
</style>

