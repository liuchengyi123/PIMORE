<template>
  <div class="fn-page page" data-figma="M37">
    <header class="head">
      <button type="button" class="back" @click="$router.back()" aria-label="back"><ChevronLeft :size="22" :stroke-width="1.75" /></button>
      <div><div class="title">邀请码</div><div class="sub">{{ code || '还没有邀请码' }}</div></div>
    </header>
    <div class="card">
      <div class="kicker">邀请码</div>
      <div class="code">{{ code || '—' }}</div>
      <p class="note">打开店铺领取页，把邀请绑定到账号。</p>
      <a v-if="code" class="btn coral" :href="shopPath('/r/' + encodeURIComponent(code))" target="_blank" rel="noopener">领取邀请</a>
      <router-link class="btn soft" to="/invite">我的邀请链接</router-link>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ChevronLeft } from 'lucide-vue-next'
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { shopPath } from '@/api/accountApi'
const route = useRoute()
const code = computed(() => String(route.query.code || route.params.code || ''))
</script>
<style lang="scss" scoped>

@import '@/styles/theme.scss';
.page { min-height: 100vh; background: $hb-paper; padding: 10px 16px 32px; padding-top: calc(10px + env(safe-area-inset-top)); }
.head { display: flex; gap: 8px; align-items: center; margin-bottom: 10px; }
.back { width: 34px; height: 34px; border: 0; border-radius: 12px; background: #fff; color: #1C2430; display: inline-flex; align-items: center; justify-content: center; cursor: pointer; padding: 0; }
.title { font-size: 20px; font-weight: 800; letter-spacing: -0.03em; line-height: 1.15; color: #1C2430; }
.sub { font-size: 12px; color: #8B919A; margin-top: 2px; }
.state { text-align: center; color: $hb-muted; padding: 36px 8px; }
.card { background: $hb-white; border: 1px solid #F1EEEA; border-radius: 14px; padding: 12px; }
.btn { display: inline-flex; align-items: center; justify-content: center; border: 0; border-radius: 999px; height: 36px; padding: 0 16px; background: #F96141; color: #fff; font-size: 14px; font-weight: 700; cursor: pointer; width: 100%; margin-top: 8px; text-decoration: none; box-sizing: border-box; }
.btn.soft { background: #FFF1EC; color: #F96141; }
.btn.coral { background: #F96141; color: #fff; }
.shop { display: block; margin-top: 12px; text-align: center; color: $hb-forest; font-weight: 680; font-size: 13px; }

.kicker { font-size: 11px; color: #8B919A; letter-spacing: 0; text-transform: none; font-weight: 700; }
.code { margin-top: 4px; font-size: 24px; font-weight: 800; color: #F96141; letter-spacing: 0.04em; line-height: 1.15; }
.note { margin: 6px 0 0; font-size: 12px; color: #5C6570; line-height: 1.4; }

.fn-page { --ink:#1C2430; --teal:#0E7490; --amber:#F96141; --sand:#FCFAF8; }
</style>
