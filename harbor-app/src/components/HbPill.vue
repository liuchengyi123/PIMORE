<template>
  <view class="hb-pill" :class="tone">
    <text>{{ label }}</text>
  </view>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{ label: string; tone?: 'green' | 'coral' | 'ink' }>(),
  { tone: 'green' },
)
</script>

<style lang="scss" scoped>
@import '@/styles/theme.scss';

.hb-pill {
  display: inline-flex;
  align-items: center;
  font-size: 11px;
  font-weight: 650;
  letter-spacing: 0.1px;
  padding: 5px 10px;
  border-radius: $hb-radius-pill;
  &.green {
    color: $hb-forest;
    background: rgba(30, 77, 59, 0.08);
  }
  &.coral {
    color: $hb-coral;
    background: $hb-coral-soft;
  }
  &.ink {
    color: $hb-muted;
    background: rgba(20, 26, 23, 0.05);
  }
}
</style>
