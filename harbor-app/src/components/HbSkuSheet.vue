<template>
  <view v-if="visible" class="sku-sheet" :class="{ open: panelUp }">
    <view class="sku-backdrop" @click="close" @touchmove.stop.prevent="noop" />
    <view
      class="sku-panel"
      :class="{ up: panelUp }"
      @touchmove.stop
      @click.stop
    >
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
          <text class="sku-head-price">{{ money(headPrice) }}</text>
          <text v-if="headCompare" class="sku-head-was">{{ money(headCompare) }}</text>
          <text class="sku-picked">{{ selectedLabel || t('common_select_option') }}</text>
        </view>
      </view>

      <scroll-view
        v-if="options.length"
        class="sku-scroll"
        scroll-y
        :show-scrollbar="false"
      >
        <text class="sku-label">{{ t('common_option') }}</text>
        <view class="sku-chips">
          <view
            v-for="opt in options"
            :key="opt.key"
            class="sku-chip"
            :class="{ on: selected === opt.label }"
            @click="selectOption(opt.label)"
          >
            <image
              v-if="opt.image"
              class="sku-chip-shot"
              :src="opt.image"
              mode="aspectFill"
            />
            <text class="sku-chip-name">{{ opt.label }}</text>
          </view>
        </view>
      </scroll-view>

      <view class="sku-qty">
        <text class="sku-qty-label">{{ t('common_qty') }}</text>
        <view class="stepper">
          <view class="stepper-btn" @click="bumpQty(-1)">
            <text>−</text>
          </view>
          <input
            class="stepper-input"
            type="number"
            :value="String(qty)"
            @input="onQtyInput"
          />
          <view class="stepper-btn" @click="bumpQty(1)">
            <text>+</text>
          </view>
        </view>
      </view>

      <view class="sku-foot">
        <view class="cart-dock" @click="goCart">
          <view class="cart-ico">
            <view class="bag-body" />
            <view class="bag-handle" />
          </view>
          <view v-if="cartCount > 0" class="cart-badge">
            <text>{{ cartCountLabel }}</text>
          </view>
        </view>
        <view
          class="sku-go"
          :class="{ busy }"
          @click="confirm"
        >
          <text>{{ mode === 'buy' ? t('sheet_buy_now') : t('sheet_add') }}</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { money, type Product, type ProductOffer } from '@/api/products'
import { useCart } from '@/composables/cart'
import { useI18n } from '@/composables/i18n'

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
const cart = useCart()
const cartCount = computed(() => cart.count.value)
const cartCountLabel = computed(() => (cartCount.value > 99 ? '99+' : String(cartCount.value)))

const qty = ref(1)
const busy = ref(false)
const visible = ref(false)
const panelUp = ref(false)
const selected = ref('')

type OptionItem = { key: string; label: string; image?: string; price?: number; compareAt?: number }

const options = computed<OptionItem[]>(() => {
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
  return (p.sizes || []).map((s, i) => ({
    key: `size-${i}-${s}`,
    label: s,
  }))
})

const selectedOffer = computed(() => {
  const label = selected.value
  return options.value.find((o) => o.label === label)
})

const selectedLabel = computed(() => selected.value)

const headImage = computed(() => {
  return (
    selectedOffer.value?.image ||
    props.product?.image ||
    props.product?.images?.[0] ||
    ''
  )
})

const headPrice = computed(() => {
  return selectedOffer.value?.price ?? props.product?.price ?? 0
})

const headCompare = computed(() => {
  const c = selectedOffer.value?.compareAt ?? props.product?.compareAt
  const price = headPrice.value
  if (!c || c <= price) return 0
  return c
})

watch(
  () => props.open,
  async (v) => {
    if (v) {
      visible.value = true
      qty.value = 1
      busy.value = false
      panelUp.value = false
      const next =
        props.modelValue ||
        options.value[0]?.label ||
        (options.value.length ? '' : 'default')
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

function selectOption(label: string) {
  selected.value = label
  emit('update:modelValue', label)
}

function bumpQty(delta: number) {
  qty.value = Math.max(1, (qty.value || 1) + delta)
}

function onQtyInput(e: { detail?: { value?: string } }) {
  const raw = e?.detail?.value ?? ''
  const n = parseInt(String(raw), 10)
  qty.value = Number.isFinite(n) && n > 0 ? n : 1
}

function confirm() {
  if (busy.value || !props.product) return
  const size = selected.value || options.value[0]?.label || 'default'
  if (options.value.length && !selected.value) {
    uni.showToast({ title: t('common_choose_option'), icon: 'none' })
    return
  }
  busy.value = true
  emit('confirm', {
    size,
    qty: Math.max(1, qty.value || 1),
    mode: props.mode === 'buy' ? 'buy' : 'add',
  })
  // parent closes sheet; release busy shortly if still open
  setTimeout(() => {
    busy.value = false
  }, 600)
}

function goCart() {
  emit('update:open', false)
  uni.navigateTo({ url: '/pages/cart/index' })
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
  background: rgba(20, 26, 23, 0.45);
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
  max-height: min(78vh, 720px);
  display: flex;
  flex-direction: column;
  background: $hb-white;
  border-radius: 22px 22px 0 0;
  padding-bottom: calc(12px + env(safe-area-inset-bottom));
  box-shadow: 0 -12px 40px rgba(20, 26, 23, 0.12);
  transform: translateY(110%);
  transition: transform 0.28s cubic-bezier(0.22, 1, 0.36, 1);
  &.up {
    transform: translateY(0);
  }
}

.sheet-close {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 3;
  width: 40px;
  height: 40px;
  border-radius: $hb-radius-pill;
  background: $hb-paper;
  display: flex;
  align-items: center;
  justify-content: center;
}
.sheet-close-x {
  font-size: 22px;
  line-height: 1;
  color: $hb-ink;
  font-weight: 500;
}

.sku-head {
  flex: 0 0 auto;
  display: flex;
  gap: 12px;
  align-items: flex-start;
  padding: 18px 52px 14px 16px;
  border-bottom: 1px solid $hb-line;
}
.sku-head-img {
  width: 88px;
  height: 88px;
  border-radius: 12px;
  background: $hb-paper;
  flex-shrink: 0;
  &.placeholder {
    display: block;
  }
}
.sku-head-meta {
  min-width: 0;
  flex: 1;
  padding-top: 4px;
}
.sku-head-price {
  display: block;
  font-size: 26px;
  font-weight: 740;
  color: $hb-coral;
  letter-spacing: -0.6px;
  line-height: 1.1;
}
.sku-head-was {
  display: block;
  margin-top: 4px;
  font-size: 13px;
  color: $hb-strike;
  text-decoration: line-through;
}
.sku-picked {
  margin-top: 8px;
  font-size: 14px;
  line-height: 1.4;
  color: $hb-muted;
  white-space: normal;
  word-break: break-word;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
}

.sku-scroll {
  flex: 1 1 auto;
  min-height: 0;
  max-height: 42vh;
  padding: 14px 16px 4px;
  box-sizing: border-box;
}
.sku-label {
  display: block;
  margin-bottom: 10px;
  font-size: 12px;
  font-weight: 680;
  letter-spacing: 0.6px;
  text-transform: uppercase;
  color: $hb-muted;
}
.sku-chips {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}
.sku-chip {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  width: 100%;
  box-sizing: border-box;
  padding: 12px 14px;
  border-radius: 16px;
  background: $hb-paper;
  &.on {
    background: $hb-forest;
    .sku-chip-name {
      color: $hb-white;
      font-weight: 680;
    }
  }
}
.sku-chip-shot {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: $hb-white;
  flex-shrink: 0;
  margin-top: 1px;
}
.sku-chip-name {
  flex: 1 1 auto;
  min-width: 0;
  font-size: 13px;
  font-weight: 560;
  line-height: 1.4;
  color: $hb-ink;
  white-space: normal;
  word-break: break-word;
  overflow: visible;
}

.sku-qty {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 16px 8px;
}
.sku-qty-label {
  font-size: 14px;
  font-weight: 680;
  color: $hb-ink;
}
.stepper {
  display: flex;
  align-items: center;
  gap: 6px;
}
.stepper-btn {
  width: 36px;
  height: 36px;
  border-radius: 12px;
  background: $hb-paper;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: 600;
  color: $hb-ink;
}
.stepper-input {
  width: 52px;
  height: 36px;
  text-align: center;
  font-size: 15px;
  font-weight: 650;
  color: $hb-ink;
  background: $hb-white;
  border: 1px solid $hb-line;
  border-radius: 10px;
}

.sku-foot {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 4px 16px 0;
}
.cart-dock {
  position: relative;
  flex: 0 0 44px;
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: $hb-ink;
}
.cart-ico {
  position: relative;
  width: 22px;
  height: 22px;
}
.bag-body {
  position: absolute;
  left: 2px;
  right: 2px;
  top: 7px;
  bottom: 1px;
  border: 1.8px solid currentColor;
  border-radius: 4px 4px 6px 6px;
}
.bag-handle {
  position: absolute;
  left: 6px;
  right: 6px;
  top: 2px;
  height: 8px;
  border: 1.8px solid currentColor;
  border-bottom: 0;
  border-radius: 8px 8px 0 0;
}
.cart-badge {
  position: absolute;
  top: 0;
  right: 0;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  border-radius: $hb-radius-pill;
  background: $hb-coral;
  color: $hb-white;
  font-size: 10px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
  box-sizing: border-box;
}
.sku-go {
  flex: 1 1 auto;
  height: 52px;
  border-radius: $hb-radius-btn-lg;
  background: $hb-forest;
  color: $hb-white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 15px;
  &.busy {
    opacity: 0.7;
  }
}
</style>
