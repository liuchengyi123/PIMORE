<template>
  <div class="page">
    <header class="head">
      <button type="button" class="back" @click="$router.back()" aria-label="back">‹</button>
      <h1 class="title">奖励</h1>
    </header>
    <button type="button" class="spin" @click="spin">{{ result || (zh ? '转动幸运转盘' : 'Spin the wheel') }}</button>
    <div class="tiles">
      <router-link class="tile wheel" to="/checkin"><span class="tt">幸运转盘</span><span class="td">每日签到领取</span></router-link>
      <router-link class="tile" to="/balance"><span class="tt">余额</span><span class="td">奖励钱包</span></router-link>
      <router-link class="tile" to="/withdraw"><span class="tt">提现</span><span class="td">转出</span></router-link>
      <router-link class="tile" to="/invite"><span class="tt">邀请</span><span class="td">分享得奖励</span></router-link>
    </div>
    <AppTabBar active="me" />
  </div>
</template>
<script setup lang="ts">
import { computed, ref } from 'vue'
import AppTabBar from '@/components/AppTabBar.vue'
import { apiRoot } from '@/api/config'
const zh = computed(() => String(navigator.language || '').toLowerCase().startsWith('zh'))
const result = ref('')
async function spin() {
  const res = await fetch(apiRoot().replace(/\/$/, '') + '/api/lucky/spin', { method: 'POST', credentials: 'include' })
  const data = await res.json().catch(() => ({}))
  const percent = data?.spin?.percent ?? data?.percent
  result.value = percent ? (zh.value ? `抽到 ${percent}%` : `You got ${percent}%`) : (zh.value ? '今天已经转过' : 'Already spun')
}
</script>
<style scoped>
.page { min-height: 100vh; background: #FCFAF8; color: #1C2430; padding: 12px 16px 40px; padding-top: calc(12px + env(safe-area-inset-top)); }
.head { display: flex; gap: 10px; align-items: center; margin-bottom: 12px; }
.back { border: 0; background: transparent; font-size: 22px; font-weight: 700; cursor: pointer; color: #1C2430; }
.title { font-size: 22px; font-weight: 800; letter-spacing: -0.03em; margin: 0; }
.spin { width: 100%; height: 48px; border: 0; border-radius: 999px; background: #F96141; color: #fff; font-weight: 700; margin-bottom: 12px; cursor: pointer; }
.tiles { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.tile {
  background: #fff; border: 1px solid #E8E4DC; border-radius: 16px; padding: 16px; text-decoration: none; color: inherit;
  display: flex; flex-direction: column; gap: 6px; min-height: 96px;
}
.tile.wheel { background: #FFF1EC; border-color: #F8D5CC; }
.tt { font-size: 15px; font-weight: 700; }
.td { font-size: 12px; color: #6B7280; }
</style>
