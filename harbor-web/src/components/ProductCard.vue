<template>
  <article class="card" @click="go">
    <div class="thumb" :style="thumbStyle">
      <img v-if="product.image" class="thumb-img" :src="product.image" alt="" loading="lazy" />
      <span v-if="imageBadge" class="img-badge" :class="imageBadge.tone">{{ imageBadge.label }}</span>
      <span v-if="product.onlyLeft" class="only-left">{{ t('only_left') }} {{ product.onlyLeft }}</span>
    </div>
    <div class="body">
      <div class="name">{{ product.name }}</div>
      <div class="price-row">
        <span class="price">{{ money(product.price) }}</span>
        <span v-if="product.compareAt" class="was">{{ money(product.compareAt) }}</span>
        <span v-if="offPct" class="off-badge">-{{ offPct }}%</span>
      </div>
      <div v-if="product.shipNote || product.onlyLeft" class="ship-line">
        <template v-if="product.onlyLeft">{{ t('only_left') }} {{ product.onlyLeft }}</template>
        <template v-else>{{ product.shipNote }}</template>
      </div>
    </div>
  </article>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import type { Product } from '@/api/products'
import { money } from '@/api/products'
import { useI18n } from '@/composables/i18n'

const props = defineProps<{ product: Product }>()
const router = useRouter()
const { t } = useI18n()

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

const imageBadge = computed(() => {
  const tag = props.product.tag
  if (tag === 'Flash') return { label: t('badge_flash'), tone: 'flash' }
  if (tag === 'New') return { label: t('badge_new'), tone: 'new' }
  if (tag === 'Ship-fast') return { label: t('badge_ship'), tone: 'ship' }
  if (tag === 'Staff') return { label: t('badge_staff'), tone: 'new' }
  if (tag === 'Deal') return { label: t('badge_deal'), tone: 'deal' }
  return null
})

function go() {
  router.push({ path: '/pdp', query: { sku: props.product.sku } })
}
</script>

<style lang="scss" scoped>
@import '@/styles/theme.scss';
.card {
  border-radius: 18px;
  overflow: hidden;
  background: $hb-white;
  box-shadow: $hb-shadow-soft;
  cursor: pointer;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.card:active { transform: scale(0.985); }
.thumb {
  aspect-ratio: 1 / 1;
  position: relative;
  background: $hb-soft;
}
.thumb-img { width: 100%; height: 100%; object-fit: cover; display: block; }
.img-badge {
  position: absolute; left: 8px; top: 8px;
  padding: 4px 8px; border-radius: 999px; font-size: 11px; font-weight: 720; color: #fff;
  &.flash, &.deal { background: $hb-coral; }
  &.new { background: $hb-forest; }
  &.ship { background: #2a6f9e; }
}
.only-left {
  position: absolute; right: 8px; bottom: 8px;
  background: rgba(0,0,0,0.55); color: #fff; font-size: 11px; padding: 3px 7px; border-radius: 8px;
}
.body { padding: 11px 11px 13px; }
.name {
  font-size: 13px; font-weight: 650; color: $hb-ink; line-height: 1.35;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; min-height: 2.7em;
}
.price-row { display: flex; align-items: baseline; gap: 6px; margin-top: 7px; flex-wrap: wrap; }
.ship-line { margin-top: 4px; font-size: 11px; color: \-muted; }
.price { font-size: 16px; font-weight: 780; color: $hb-ink; letter-spacing: -0.02em; }
.was { font-size: 12px; color: $hb-muted; text-decoration: line-through; }
.off-badge { font-size: 11px; color: $hb-forest; font-weight: 720; background: $hb-soft; padding: 2px 7px; border-radius: 999px; }
</style>
