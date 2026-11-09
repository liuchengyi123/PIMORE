<template>
  <view v-if="visible" class="sku-sheet" :class="{ open: panelUp }" data-figma="1:3">
    <view class="sku-backdrop" @click="close" @touchmove.stop.prevent="noop" />
    <view class="sku-panel" :class="{ up: panelUp }" @touchmove.stop @click.stop>
      <view class="grab" />

      <view class="sheet-close" @click="close">
        <text class="sheet-close-x">×</text>
      </view>

      <view class="sku-head">
        <image
          v-if="headImage"
          class="sku-head-img"
          :src="headImage"
          mode="aspectFill"
        />
        <view v-else class="sku-head-img placeholder" />
        <view class="sku-head-meta">
          <text class="sku-brand">{{ brand }}</text>
          <text class="sku-title">{{ title }}</text>
          <text class="sku-price">{{ money(headPrice) }}</text>
          <text class="sku-tag">{{ tagline }}</text>
        </view>
      </view>

      <scroll-view class="sku-scroll" scroll-y :show-scrollbar="false">
        <!-- Color -->
        <view class="section">
          <text class="sec-lab">Color</text>
          <view class="swatches">
            <view
              v-for="c in colorOptions"
              :key="c.id"
              class="swatch-wrap"
              @click="selectColor(c)"
            >
              <view
                class="swatch"
                :class="{ on: colorId === c.id }"
                :style="{ background: c.hex }"
              />
              <text class="swatch-lab" :class="{ on: colorId === c.id }">{{ c.label }}</text>
            </view>
          </view>
        </view>

        <!-- Size -->
        <view class="section">
          <text class="sec-lab">Size</text>
          <view class="size-row">
            <view
              v-for="s in sizeOptions"
              :key="s"
              class="size-pill"
              :class="{ on: selected === s }"
              @click="selectOption(s)"
            >
              <text>{{ s }}</text>
            </view>
          </view>
        </view>

        <!-- Live offer fallback chips when product options are not size-like -->
        <view v-if="offerMode" class="section">
          <text class="sec-lab">{{ t('common_option') }}</text>
          <view class="offer-chips">
            <view
              v-for="opt in offerOptions"
              :key="opt.key"
              class="offer-chip"
              :class="{ on: selected === opt.label }"
              @click="selectOption(opt.label)"
            >
              <text>{{ opt.label }}</text>
            </view>
          </view>
        </view>

        <!-- Quantity -->
        <view class="section qty-sec">
          <text class="sec-lab">Quantity</text>
          <view class="qty-pill">
            <view class="qty-btn" @click="bumpQty(-1)"><text>−</text></view>
            <text class="qty-val">{{ qty }}</text>
            <view class="qty-btn" @click="bumpQty(1)"><text>+</text></view>
          </view>
        </view>
      </scroll-view>

      <view class="sku-foot">
        <view class="sku-go" :class="{ busy }" @click="confirm">
          <text>{{ ctaLabel }}</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { money, type Product, type ProductOffer } from '@/api/products'
import { useI18n } from '@/composables/i18n'

const FIGMA_THUMB = '/static/figma/sku-sheet/thumb.png'

const FIGMA_COLORS = [
  { id: 'coral', label: 'Coral', hex: '#FF6B4A' },
  { id: 'black', label: 'Black', hex: '#1A1A1A' },
  { id: 'heather', label: 'Heather Gray', hex: '#C8CCD1' },
  { id: 'navy', label: 'Navy', hex: '#1B2B4A' },
  { id: 'olive', label: 'Olive', hex: '#6B7A3A' },
]

const DEFAULT_SIZES = ['XS', 'S', 'M', 'L', 'XL', 'XXL']

const props = withDefaults(
  defineProps<{
    open: boolean
    mode?: 'add' | 'buy'
    product: Product | null
    modelValue?: string
  }>(),
  {
    mode: 'add',
    modelValue: '',
  },
)

const emit = defineEmits<{
  (e: 'update:open', v: boolean): void
  (e: 'update:modelValue', v: string): void
  (e: 'confirm', payload: { size: string; qty: number; mode: 'add' | 'buy' }): void
}>()

const { t } = useI18n()

const qty = ref(1)
const busy = ref(false)
const visible = ref(false)
const panelUp = ref(false)
const selected = ref('')
const colorId = ref('coral')

type OptionItem = { key: string; label: string; image?: string; price?: number; compareAt?: number }

const offerOptions = computed<OptionItem[]>(() => {
  const p = props.product
  if (!p) return []
  const offers = p.offers || []
  if (offers.length) {
    return offers.map((o: ProductOffer, i: number) => ({
      key: o.id || `offer-${i}`,
      label: o.label,
      image: o.image,
      price: o.price,
      compareAt: o.compareAt,
    }))
  }
  return []
})

function looksLikeSize(label: string) {
  return /^(XXS|XS|S|M|L|XL|XXL|XXXL|\d{1,2})$/i.test(String(label).trim())
}

const productSizes = computed(() => {
  const p = props.product
  if (!p) return [] as string[]
  if (p.sizes?.length && p.sizes.every(looksLikeSize)) return [...p.sizes]
  const fromOffers = (p.offers || []).map((o) => o.label).filter(looksLikeSize)
  if (fromOffers.length) return fromOffers
  return [] as string[]
})

const offerMode = computed(() => {
  // Show offer chips only when we have non-size offers and no size list
  if (productSizes.value.length) return false
  return offerOptions.value.length > 0 && !offerOptions.value.every((o) => looksLikeSize(o.label))
})

const sizeOptions = computed(() => {
  if (offerMode.value) return [] as string[]
  if (productSizes.value.length) return productSizes.value
  return DEFAULT_SIZES
})

const colorOptions = computed(() => FIGMA_COLORS)

const selectedOffer = computed(() => offerOptions.value.find((o) => o.label === selected.value))

const brand = computed(() => {
  const p = props.product
  if (!p) return 'Everlane'
  if (/everlane/i.test(p.name || '')) return 'Everlane'
  if (p.hub) return p.hub
  if (p.category && p.category !== 'Bags') return p.category
  return 'Everlane'
})

const title = computed(() => props.product?.name || 'Everyday Hoodie')

const tagline = computed(
  () => props.product?.blurb || 'Soft. Durable. Made for real life.',
)

const headImage = computed(() => {
  return (
    selectedOffer.value?.image ||
    props.product?.image ||
    props.product?.images?.[0] ||
    FIGMA_THUMB
  )
})

const headPrice = computed(() => {
  return selectedOffer.value?.price ?? props.product?.price ?? 68
})

const ctaLabel = computed(() =>
  props.mode === 'buy' ? 'Confirm Buy Now' : 'Confirm Add to Cart',
)

watch(
  () => props.open,
  async (v) => {
    if (v) {
      visible.value = true
      qty.value = 1
      busy.value = false
      panelUp.value = false
      colorId.value = 'coral'
      let next = props.modelValue || ''
      if (offerMode.value) {
        next = next || offerOptions.value[0]?.label || ''
      } else {
        const sizes = sizeOptions.value
        if (!next || !sizes.includes(next)) {
          next = sizes.includes('M') ? 'M' : sizes[0] || 'M'
        }
      }
      selected.value = next
      if (next && next !== props.modelValue) emit('update:modelValue', next)
      await nextTick()
      requestAnimationFrame(() => {
        panelUp.value = true
      })
    } else {
      panelUp.value = false
      setTimeout(() => {
        if (!props.open) visible.value = false
      }, 280)
    }
  },
  { immediate: true },
)

watch(
  () => props.modelValue,
  (v) => {
    if (v && v !== selected.value) selected.value = v
  },
)

function noop() {}

function close() {
  if (busy.value) return
  emit('update:open', false)
}

function selectColor(c: { id: string }) {
  colorId.value = c.id
}

function selectOption(label: string) {
  selected.value = label
  emit('update:modelValue', label)
}

function bumpQty(delta: number) {
  qty.value = Math.max(1, Math.min(99, (qty.value || 1) + delta))
}

function confirm() {
  if (busy.value || !props.product) return
  const size = selected.value || sizeOptions.value[0] || offerOptions.value[0]?.label || 'default'
  if ((sizeOptions.value.length || offerOptions.value.length) && !selected.value) {
    uni.showToast({ title: t('common_choose_option'), icon: 'none' })
    return
  }
  busy.value = true
  emit('confirm', {
    size,
    qty: Math.max(1, qty.value || 1),
    mode: props.mode === 'buy' ? 'buy' : 'add',
  })
  setTimeout(() => {
    busy.value = false
  }, 600)
}
</script>

<style lang="scss" scoped>
@import '@/styles/theme.scss';

.sku-sheet {
  position: fixed;
  inset: 0;
  z-index: 200;
  pointer-events: none;
  &.open {
    pointer-events: auto;
  }
}

.sku-backdrop {
  position: absolute;
  inset: 0;
  background: rgba(20, 24, 30, 0.48);
  opacity: 0;
  transition: opacity 0.24s ease;
}
.sku-sheet.open .sku-backdrop {
  opacity: 1;
}

.sku-panel {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  max-height: min(82vh, 760px);
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 24px 24px 0 0;
  padding-bottom: calc(12px + env(safe-area-inset-bottom));
  box-shadow: 0 -12px 40px rgba(20, 26, 23, 0.14);
  transform: translateY(110%);
  transition: transform 0.28s cubic-bezier(0.22, 1, 0.36, 1);
  &.up {
    transform: translateY(0);
  }
}

.grab {
  width: 40px;
  height: 4px;
  margin: 10px auto 0;
  border-radius: 99px;
  background: #d5d8de;
  flex-shrink: 0;
}

.sheet-close {
  position: absolute;
  top: 14px;
  right: 14px;
  z-index: 3;
  width: 32px;
  height: 32px;
  border-radius: 99px;
  background: #eef0f3;
  display: flex;
  align-items: center;
  justify-content: center;
}
.sheet-close-x {
  font-size: 20px;
  line-height: 1;
  color: #5b6573;
  font-weight: 500;
  margin-top: -1px;
}

.sku-head {
  flex: 0 0 auto;
  display: flex;
  gap: 12px;
  align-items: flex-start;
  padding: 14px 52px 16px 20px;
}
.sku-head-img {
  width: 72px;
  height: 72px;
  border-radius: 12px;
  background: #f0f1f3;
  flex-shrink: 0;
  &.placeholder {
    display: block;
  }
}
.sku-head-meta {
  min-width: 0;
  flex: 1;
  padding-top: 2px;
}
.sku-brand {
  display: block;
  font-size: 12px;
  color: #8b93a1;
  font-weight: 500;
}
.sku-title {
  display: block;
  margin-top: 2px;
  font-size: 16px;
  font-weight: 800;
  color: #1f2430;
  letter-spacing: -0.2px;
  line-height: 1.25;
}
.sku-price {
  display: block;
  margin-top: 4px;
  font-size: 16px;
  font-weight: 800;
  color: #1f2430;
}
.sku-tag {
  display: block;
  margin-top: 4px;
  font-size: 12px;
  color: #8b93a1;
  line-height: 1.35;
}

.sku-scroll {
  flex: 1 1 auto;
  min-height: 0;
  max-height: 48vh;
  padding: 4px 20px 8px;
  box-sizing: border-box;
}

.section {
  margin-bottom: 18px;
}
.sec-lab {
  display: block;
  margin-bottom: 12px;
  font-size: 15px;
  font-weight: 800;
  color: #1f2430;
}

.swatches {
  display: flex;
  justify-content: space-between;
  gap: 6px;
}
.swatch-wrap {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}
.swatch {
  width: 36px;
  height: 36px;
  border-radius: 99px;
  box-sizing: border-box;
  border: 3px solid transparent;
  box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.04);
}
.swatch.on {
  border-color: $hb-coral;
  box-shadow: 0 0 0 2px #fff, 0 0 0 4px $hb-coral;
}
.swatch-lab {
  font-size: 10px;
  color: #8b93a1;
  text-align: center;
  line-height: 1.2;
  font-weight: 500;
}
.swatch-lab.on {
  color: #1f2430;
  font-weight: 700;
}

.size-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.size-pill {
  min-width: 48px;
  height: 36px;
  padding: 0 14px;
  border-radius: 99px;
  border: 1.2px solid #e2e5ea;
  background: #fff;
  color: #1f2430;
  font-size: 13px;
  font-weight: 650;
  display: flex;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
}
.size-pill.on {
  background: $hb-coral;
  border-color: $hb-coral;
  color: #fff;
}

.offer-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.offer-chip {
  padding: 8px 14px;
  border-radius: 99px;
  border: 1.2px solid #e2e5ea;
  font-size: 13px;
  font-weight: 600;
  color: #1f2430;
}
.offer-chip.on {
  background: $hb-coral;
  border-color: $hb-coral;
  color: #fff;
}

.qty-sec {
  margin-bottom: 8px;
}
.qty-pill {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 48px;
  padding: 0 8px;
  border-radius: 14px;
  background: #f3f4f6;
}
.qty-btn {
  width: 44px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: 500;
  color: #1f2430;
}
.qty-val {
  flex: 1;
  text-align: center;
  font-size: 16px;
  font-weight: 750;
  color: #1f2430;
}

.sku-foot {
  flex: 0 0 auto;
  padding: 8px 20px 4px;
}
.sku-go {
  height: 52px;
  border-radius: 16px;
  background: $hb-coral;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  font-size: 16px;
  letter-spacing: -0.2px;
  &.busy {
    opacity: 0.7;
  }
}
</style>
