<template>
  <div class="ag" :class="{ 'ag-tabbed': !!tabs }">
    <slot />
    <AppTabBar v-if="tabs" :active="tabs" />
  </div>
</template>

<script setup lang="ts">
import AppTabBar from '@/components/AppTabBar.vue'

defineProps<{ tabs?: 'home' | 'browse' | 'cart' | 'me' }>()
</script>

<style lang="scss">
.ag {
  min-height: 100vh;
  background: #FCFAF8;
  color: #1C2430;
  padding-bottom: 28px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
}
.ag-tabbed { padding-bottom: 0; }
.ag-pad { padding-left: 16px; padding-right: 16px; }
.ag-top { padding-top: calc(10px + env(safe-area-inset-top)); }
.ag-back {
  width: 36px; height: 36px; border: 0; background: transparent; color: #F96141;
  display: inline-flex; align-items: center; justify-content: center; cursor: pointer; padding: 0; flex: 0 0 auto;
}
.ag-back.ink { color: #1C2430; }
.ag-back.light { color: #fff; }
.ag-h1 { margin: 0; font-size: 28px; font-weight: 800; letter-spacing: -0.045em; line-height: 1.12; color: #1A1D26; }
.ag-sub { margin: 6px 0 0; font-size: 13.5px; line-height: 1.45; color: #8B919A; }
.ag-kicker { font-size: 11px; font-weight: 800; letter-spacing: 0.12em; color: #F96141; }
.ag-sec { display: flex; align-items: flex-end; justify-content: space-between; gap: 12px; margin: 22px 0 10px; }
.ag-sec h2 { margin: 0; font-size: 18px; font-weight: 800; letter-spacing: -0.03em; }
.ag-sec p { margin: 4px 0 0; font-size: 12.5px; color: #8B919A; }
.ag-link { border: 0; background: transparent; color: #F96141; font-weight: 700; font-size: 13px; cursor: pointer; padding: 0; }
.ag-card { background: #fff; border: 1px solid #F1ECE6; border-radius: 18px; box-shadow: 0 8px 24px rgba(28, 36, 48, 0.04); }
.ag-cta, a.ag-cta {
  display: flex; align-items: center; justify-content: center; gap: 8px;
  width: 100%; height: 52px; border: 0; border-radius: 16px;
  background: #F96141; color: #fff; font-size: 16px; font-weight: 750; cursor: pointer;
  text-decoration: none; box-sizing: border-box;
}
.ag-cta.pill { border-radius: 999px; }
.ag-cta.ghost { background: #fff; color: #F96141; border: 1.5px solid #F7B2A4; }
.ag-cta.soft { background: #FFF1EC; color: #F96141; }
.ag-cta:disabled { opacity: 0.55; cursor: default; }
.ag-logo { display: inline-flex; align-items: center; gap: 6px; color: #F96141; }
.ag-logo.light { color: #fff; }
.ag-logo.center { justify-content: center; }
.ag-house { width: 26px; height: 26px; display: block; flex: 0 0 auto; }
.ag-word { position: relative; font-size: 26px; font-weight: 800; letter-spacing: -0.045em; line-height: 1; }
.ag-wave { display: block; width: 68px; height: 8px; margin-top: 1px; }
.ag-tagline { font-size: 11px; color: #8B919A; letter-spacing: 0.04em; }
.ag-logo.light + .ag-tagline, .ag-tagline.light { color: rgba(255,255,255,0.86); }
.ag-icon {
  width: 46px; height: 46px; border-radius: 50%; background: #FFF1EC; color: #F96141;
  display: grid; place-items: center; flex: 0 0 auto;
}
.ag-icon.solid { background: #F96141; color: #fff; }
.ag-field { display: block; margin: 0 0 12px; }
.ag-field > span { display: block; font-size: 14px; font-weight: 750; margin-bottom: 8px; }
.ag-field input, .ag-field textarea, .ag-field select {
  width: 100%; border: 1px solid #E7E1DA; background: #fff; border-radius: 14px;
  padding: 14px 14px; font-size: 15px; color: #1C2430; outline: none; font-family: inherit;
  box-sizing: border-box;
}
.ag-field textarea { min-height: 120px; resize: vertical; }
.ag-field input:focus, .ag-field textarea:focus, .ag-field select:focus { border-color: #F96141; }
.ag-note { font-size: 12.5px; color: #8B919A; line-height: 1.5; }
.ag-toast {
  margin: 10px 16px 0; background: #FFF1EC; color: #C2412D; border-radius: 12px;
  padding: 10px 12px; font-size: 13px; font-weight: 650;
}
.ag-empty { text-align: center; padding: 28px 18px 22px; color: #1C2430; }
.ag-empty h3 { margin: 12px 0 6px; font-size: 18px; font-weight: 800; }
.ag-empty p { margin: 0; color: #8B919A; font-size: 13.5px; line-height: 1.5; }
.ag-chip {
  display: inline-flex; align-items: center; gap: 4px; height: 26px; padding: 0 10px;
  border-radius: 999px; background: #FFF1EC; color: #F96141; font-size: 12px; font-weight: 750;
}
.ag-gear {
  width: 36px; height: 36px; border: 0; border-radius: 12px; background: transparent; color: #1C2430;
  display: inline-flex; align-items: center; justify-content: center; cursor: pointer;
}
.ag-search {
  display: flex; align-items: center; gap: 8px; background: #F3EFEA; border-radius: 999px;
  padding: 0 14px; height: 46px; color: #8B919A;
}
.ag-search input {
  flex: 1; border: 0; background: transparent; outline: none; font-size: 14px; color: #1C2430; font-family: inherit;
}
.ag-tabs {
  display: flex; background: #F6F1EC; border-radius: 999px; padding: 4px; gap: 4px;
}
.ag-tabs button {
  flex: 1; height: 36px; border: 0; border-radius: 999px; background: transparent; color: #8B919A;
  font-weight: 700; font-size: 14px; cursor: pointer;
}
.ag-tabs button.on { background: #F96141; color: #fff; }
</style>
