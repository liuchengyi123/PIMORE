<template>
  <div class="fn-page page" data-figma="M37">
    <header class="head">
      <button type="button" class="back" @click="$router.back()" aria-label="back"><ChevronLeft :size="22" :stroke-width="1.75" /></button>
      <div><div class="title">邀请码</div><div class="sub">{{ code || 'Invite link' }}</div></div>
    </header>
    <div class="card">
      <div class="kicker">Referral code</div>
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
.page { min-height: 100vh; background: $hb-paper; padding: 12px 16px 40px; padding-top: calc(12px + env(safe-area-inset-top)); }
.head { display: flex; gap: 12px; align-items: center; margin-bottom: 16px; }
.back { width: 40px; height: 40px; border: 0; border-radius: 14px; background: #fff; color: #121816; display: inline-flex; align-items: center; justify-content: center; box-shadow: 0 4px 16px rgba(18,24,22,0.06); cursor: pointer; }
.title { font-size: 24px; font-weight: 720; }
.sub { font-size: 12px; color: $hb-muted; margin-top: 2px; }
.state { text-align: center; color: $hb-muted; padding: 36px 8px; }
.card { background: $hb-white; border-radius: 20px; padding: 16px; box-shadow: $hb-shadow-soft; }
.btn { display: inline-flex; align-items: center; justify-content: center; border: 0; border-radius: 16px; padding: 14px 16px; background: $hb-forest; color: #fff; font-weight: 720; cursor: pointer; width: 100%; margin-top: 12px; text-decoration: none; box-sizing: border-box; }
.btn.soft { background: $hb-soft; color: $hb-forest; }
.btn.coral { background: $hb-coral; color: #fff; }
.shop { display: block; margin-top: 12px; text-align: center; color: $hb-forest; font-weight: 680; font-size: 13px; }

.kicker { font-size: 11px; color: $hb-muted; letter-spacing: 1px; text-transform: uppercase; font-weight: 650; }
.code { margin-top: 10px; font-size: 28px; font-weight: 780; color: $hb-forest; letter-spacing: 1px; }
.note { margin-top: 10px; font-size: 13px; color: $hb-muted; line-height: 1.4; }

.fn-page { --ink:#1C2430; --teal:#0E7490; --amber:#F96141; --sand:#FCFAF8; }
</style>
