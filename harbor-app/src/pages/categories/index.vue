<template>
  <view class="page">
    <view class="head">
      <view class="back" @click="goBack">←</view>
      <view>
        <text class="title">{{ t('categories_title') }}</text>
        <text class="sub">{{ t('categories_sub') }}</text>
      </view>
    </view>
    <view class="list">
      <view v-for="c in cats" :key="c.id" class="row" @click="openCat(c.id)">
        <view class="mark">{{ (c.tip || c.name).slice(0, 1) }}</view>
        <view class="meta">
          <text class="name">{{ catLabel(c.id) }}</text>
          <text class="chips">{{ chipPreview(c.id) }}</text>
        </view>
        <text class="chev">›</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { onShow } from '@dcloudio/uni-app'
import { useI18n } from '@/composables/i18n'
import { ALL_CATEGORIES, SUBCATEGORIES } from '@/api/products'

const { t, catLabel } = useI18n()
const cats = ALL_CATEGORIES

function chipPreview(id: string) {
  const kids = SUBCATEGORIES[id] || []
  return kids.slice(0, 3).map((k) => k.name).join(' · ') || t('home_see_all')
}

function openCat(id: string) {
  uni.navigateTo({ url: '/pages/category/index?cat=' + encodeURIComponent(id) })
}

function goBack() {
  uni.navigateBack({ fail: () => uni.reLaunch({ url: '/pages/home/index' }) })
}

onShow(() => {
  uni.setNavigationBarTitle({ title: t('categories_title') })
})
</script>

<style lang="scss" scoped>
@import '@/styles/theme.scss';
.page { min-height: 100vh; background: $hb-paper; padding: 12px 16px 40px; padding-top: calc(12px + env(safe-area-inset-top)); }
.head { display: flex; gap: 12px; align-items: center; margin-bottom: 18px; }
.back { width: 36px; height: 36px; border-radius: 12px; background: $hb-white; text-align: center; line-height: 36px; box-shadow: $hb-shadow-soft; }
.title { display: block; font-size: 26px; font-weight: 720; letter-spacing: -0.6px; }
.sub { display: block; font-size: 13px; color: $hb-muted; margin-top: 2px; }
.list { background: $hb-white; border-radius: 22px; overflow: hidden; box-shadow: $hb-shadow-soft; }
.row { display: flex; align-items: center; gap: 12px; padding: 14px 16px; border-bottom: 1px solid $hb-line; }
.row:last-child { border-bottom: none; }
.mark { width: 44px; height: 44px; border-radius: 14px; background: $hb-soft; color: $hb-forest; font-weight: 750; display: flex; align-items: center; justify-content: center; }
.meta { flex: 1; }
.name { display: block; font-size: 15px; font-weight: 700; }
.chips { display: block; font-size: 12px; color: $hb-muted; margin-top: 3px; }
.chev { color: $hb-muted; font-size: 22px; }
</style>
