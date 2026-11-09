<template>
  <view class="clock" :class="{ compact, light }">
    <text v-if="label" class="lab">{{ label }}</text>
    <text class="cd">{{ text }}</text>
  </view>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { dealEndsAt, formatCountdown } from '@/api/products'

const props = withDefaults(
  defineProps<{
    endsAt?: string | null
    label?: string
    compact?: boolean
    light?: boolean
  }>(),
  { endsAt: '', label: '', compact: false, light: false },
)

const text = ref('--:--:--')
let timer: ReturnType<typeof setInterval> | null = null

function tick() {
  const end = dealEndsAt(props.endsAt)
  text.value = formatCountdown(end - Date.now())
}

watch(
  () => props.endsAt,
  () => tick(),
)

onMounted(() => {
  tick()
  timer = setInterval(tick, 1000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style lang="scss" scoped>
@import '@/styles/theme.scss';

.clock {
  display: inline-flex;
  align-items: baseline;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 12px;
  background: $hb-ink;
  color: #fff;
  &.compact {
    padding: 0;
    border-radius: 0;
    background: transparent;
    color: $hb-coral;
  }
  &.light {
    background: rgba(255, 255, 255, 0.18);
    border: 1px solid rgba(255, 255, 255, 0.22);
    color: #fff;
  }
}
.lab {
  font-size: 11px;
  font-weight: 650;
  letter-spacing: 0.4px;
  text-transform: uppercase;
  opacity: 0.75;
}
.cd {
  font-size: 15px;
  font-weight: 780;
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.5px;
}
</style>
