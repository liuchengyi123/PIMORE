<template>
  <div class="page">
    <header class="head">
      <button type="button" class="back" @click="$router.back()" aria-label="back">‹</button>
      <h1 class="title">奖励</h1>
    </header>
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
import AppTabBar from '@/components/AppTabBar.vue'
</script>
<style scoped>
.page { min-height: 100vh; background: #FCFAF8; color: #1C2430; padding: 12px 16px 40px; padding-top: calc(12px + env(safe-area-inset-top)); }
.head { display: flex; gap: 10px; align-items: center; margin-bottom: 12px; }
.back { border: 0; background: transparent; font-size: 22px; font-weight: 700; cursor: pointer; color: #1C2430; }
.title { font-size: 17px; font-weight: 700; margin: 0; }
.tiles { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.tile {
  background: #fff; border: 1px solid #E8E4DC; border-radius: 16px; padding: 16px; text-decoration: none; color: inherit;
  display: flex; flex-direction: column; gap: 6px; min-height: 88px;
}
.tt { font-size: 15px; font-weight: 700; }
.td { font-size: 12px; color: #6B7280; }
</style>
