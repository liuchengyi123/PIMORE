<template>
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

type TabId = 'home' | 'browse' | 'cart' | 'me'

defineProps<{ active: TabId }>()

const { t } = useI18n()

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
  height: 88px;
}
.homeind {
  position: absolute;
  left: 50%;
  bottom: 6px;
  width: 108px;
  height: 4px;
  margin-left: -54px;
  border-radius: 2px;
  background: rgba(15, 39, 68, 0.18);
}
.icon-wrap.on {
  background: #0F2744;
  border-radius: 10px;
  width: 36px;
  height: 28px;
}
.icon-wrap.on .ico, .icon-wrap.on .ico.home, .icon-wrap.on .ico.browse, .icon-wrap.on .ico.bag, .icon-wrap.on .ico.me {
  filter: brightness(10);
}
.tab-bar {
  position: fixed;
  left: 14px;
  right: 14px;
  bottom: calc(10px + env(safe-area-inset-bottom));
  height: $hb-tab-height;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.86);
  border: 1px solid rgba(255, 255, 255, 0.65);
  display: flex;
  align-items: center;
  justify-content: space-around;
  z-index: 100;
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
  box-shadow: $hb-shadow-tab;
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
  font-size: 10px;
  font-weight: 500;
  letter-spacing: 0.2px;
  color: $hb-muted;
  &.on {
    font-weight: 700;
    color: $hb-forest;
  }
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
  border-bottom-color: $hb-forest;
}
.home.on .home-body {
  border-color: $hb-forest;
  background: rgba(30, 77, 59, 0.12);
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
  border-color: $hb-forest;
}
.browse.on .a {
  background: $hb-forest;
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
.bag.on .bag-body {
  border-color: $hb-forest;
  background: rgba(30, 77, 59, 0.12);
}
.bag.on .bag-handle {
  border-color: $hb-forest;
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
.me.on .head {
  border-color: $hb-forest;
  background: rgba(30, 77, 59, 0.12);
}
.me.on .shoulders {
  border-color: $hb-forest;
}

/* capsule tab */
.tab-bar {
  background: rgba(247, 244, 239, 0.96) !important;
  border-top: 1px solid #E8E4DC !important;
  padding-bottom: calc(8px + env(safe-area-inset-bottom)) !important;
}
.icon-wrap.on {
  background: #0F2744 !important;
  border-radius: 14px !important;
}
.icon-wrap.on .ico, .icon-wrap.on .ico * { border-color: #fff !important; background: #fff !important; }
.label.on { color: #0F2744 !important; font-weight: 700 !important; }
</style>

