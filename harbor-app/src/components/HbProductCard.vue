<template>
  <view class="card" @click="go">
    <view class="thumb" :style="thumbStyle">
      <image v-if="product.image" class="thumb-img" :src="product.image" mode="aspectFill" />
      <view v-if="variant === 'browse'" class="heart" :class="{ on: saved }" @click.stop="saved = !saved" />
      <view v-if="showBand && variant !== 'browse'" class="band"><text>$1–$10</text></view>
      <view v-else-if="imageBadge" class="img-badge" :class="imageBadge.tone">
        <text>{{ imageBadge.label }}</text>
      </view>
      <view v-if="product.onlyLeft" class="only-left">
        <text>{{ t('badge_only_left', { n: product.onlyLeft }) }}</text>
      </view>
    </view>
    <view class="body">
      <text class="name">{{ product.name }}</text>
      <text v-if="variant === 'browse'" class="cat">{{ product.category }}</text>
      <view class="price-row">
        <text class="price" :class="{ ink: variant === 'browse' }">{{ money(product.price) }}</text>
        <text v-if="!plain && variant !== 'browse' && product.compareAt" class="was">{{ money(product.compareAt) }}</text>
        <text v-if="!plain && variant !== 'browse' && offPct" class="off-badge">{{ t('badge_off_pct', { pct: offPct }) }}</text>
        <view v-if="variant === 'browse'" class="add-text" @click.stop="go">Add +</view>
        <view v-else class="add" @click.stop="go"><view class="add-ico" /></view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Product } from '@/api/products'
import { money } from '@/api/products'
import { useI18n } from '@/composables/i18n'

const { t } = useI18n()
const props = withDefaults(defineProps<{ product: Product; plain?: boolean; variant?: 'shelf' | 'browse' }>(), {
  variant: 'shelf',
})
const saved = ref(false)
const showBand = computed(() => props.product.price > 0 && props.product.price <= 10)

const palette = [
  'linear-gradient(160deg, #E8F1EC 0%, #D5E4DB 100%)',
  'linear-gradient(160deg, #F0EBE3 0%, #E4D9CC 100%)',
  'linear-gradient(160deg, #E9EEF2 0%, #D5DEE6 100%)',
  'linear-gradient(160deg, #F3E8E4 0%, #E6D5CF 100%)',
]

const thumbStyle = computed(() => {
  if (props.product.image) return {}
  const i = Math.abs((props.product.sku || props.product.id || '').length) % palette.length
  return { background: palette[i] }
})

const offPct = computed(() => {
  if (props.product.offPct && props.product.offPct > 0) return props.product.offPct
  const p = props.product.price
  const c = props.product.compareAt
  if (c && c > p && p > 0) return Math.round((1 - p / c) * 100)
  return 0
})

/** Image badge: Flash / New / Ship only — not generic Deal (web puts % by the price). */
const imageBadge = computed(() => {
  const tag = props.product.tag
  if (tag === 'Flash') return { label: t('tag_flash'), tone: 'flash' }
  if (tag === 'New') return { label: t('tag_new'), tone: 'new' }
  if (tag === 'Ship-fast') return { label: t('tag_ship_fast'), tone: 'ship' }
  if (tag === 'Staff') return { label: t('tag_staff'), tone: 'new' }
  // Sale-feed Deal: compact coral ribbon, not pale peach pill
  if (tag === 'Deal') return { label: t('tag_deal'), tone: 'deal' }
  return null
})

function go() {
  uni.navigateTo({ url: '/pages/pdp/index?sku=' + encodeURIComponent(props.product.sku) })
}
</script>

<style lang="scss" scoped>
@import '@/styles/theme.scss';

.card {
  border-radius: $hb-radius-card;
  overflow: hidden;
  background: $hb-white;
  box-shadow: $hb-shadow-soft;
}
.thumb {
  aspect-ratio: 1 / 1;
  background: linear-gradient(160deg, #eceee9 0%, #e2e5df 100%);
  position: relative;
  overflow: hidden;
}
.thumb-img {
  width: 100%;
  height: 100%;
  display: block;
}
.img-badge {
  position: absolute;
  left: 0;
  top: 10px;
  z-index: 1;
  padding: 4px 8px 4px 10px;
  border-radius: 0 8px 8px 0;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.2px;
  color: #fff;
  line-height: 1.2;
  &.flash {
    background: $hb-coral;
  }
  &.deal {
    background: $hb-coral;
  }
  &.new {
    background: $hb-forest;
  }
  &.ship {
    background: #0e7a36;
  }
}
.only-left {
  position: absolute;
  left: 8px;
  bottom: 8px;
  z-index: 1;
  padding: 3px 7px;
  border-radius: 999px;
  background: rgba(14, 122, 54, 0.92);
  color: #fff;
  font-size: 11px;
  font-weight: 700;
}
.body {
  padding: 10px 10px 12px;
}
.name {
  font-size: 13px;
  line-height: 1.35;
  min-height: 35px;
  max-height: 35px;
  overflow: hidden;
  font-weight: 560;
  letter-spacing: -0.15px;
  color: $hb-ink;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}
.price-row {
  margin-top: 8px;
  display: flex;
  align-items: center;
  flex-wrap: nowrap;
  gap: 6px 8px;
}
.price {
  font-size: 15px;
  font-weight: 800;
  letter-spacing: -0.3px;
  color: $hb-coral;
}
.band {
  position: absolute;
  left: 8px;
  top: 8px;
  z-index: 1;
  padding: 2px 6px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.94);
  color: $hb-coral;
  font-size: 10px;
  font-weight: 800;
}
.add {
  margin-left: auto;
  width: 28px;
  height: 28px;
  border-radius: 99px;
  background: $hb-coral;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: none;
}
.add-ico {
  width: 12px;
  height: 10px;
  border: 1.6px solid #fff;
  border-radius: 2px 2px 3px 3px;
  position: relative;
}
.price.ink { color: $hb-ink; font-size: 16px; }
.cat { display: block; margin-top: 2px; font-size: 12px; color: #98A2B3; }
.heart {
  position: absolute; right: 8px; top: 8px; z-index: 2;
  width: 22px; height: 22px; border-radius: 99px; background: rgba(255,255,255,.92);
}
.heart::before {
  content: '';
  position: absolute; left: 6px; top: 6px;
  width: 8px; height: 8px;
  border: 1.6px solid #98A2B3;
  border-radius: 8px 8px 2px 8px;
  transform: rotate(-45deg);
}
.heart.on::before { background: $hb-coral; border-color: $hb-coral; }
.add-text {
  margin-left: auto; color: $hb-coral; font-size: 13px; font-weight: 700; flex: none;
}
.add-ico::before {
  content: '';
  position: absolute;
  left: 2px;
  top: -4px;
  width: 6px;
  height: 4px;
  border: 1.6px solid #fff;
  border-bottom: none;
  border-radius: 4px 4px 0 0;
}
.was {
  font-size: 12px;
  color: $hb-strike;
  text-decoration: line-through;
  font-weight: 500;
}
.off-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 7px;
  border-radius: 4px;
  background: #ffe8df;
  color: $hb-coral;
  font-size: 12px;
  font-weight: 800;
  line-height: 1.2;
}
</style>
