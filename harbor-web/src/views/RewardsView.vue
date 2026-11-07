<template>
  <div class="page">
    <header class="head">
      <button type="button" class="back" @click="$router.back()" aria-label="back">‹</button>
      <h1 class="title">Rewards</h1>
    </header>
    <div class="tiles">
      <router-link class="tile" to="/balance"><span class="tt">Balance</span><span class="td">Rewards wallet</span></router-link>
      <router-link class="tile" to="/withdraw"><span class="tt">Withdraw</span><span class="td">Cash out</span></router-link>
      <router-link class="tile" to="/checkin"><span class="tt">Check-in</span><span class="td">Daily perk</span></router-link>
      <router-link class="tile" to="/invite"><span class="tt">Invite</span><span class="td">Earn rewards</span></router-link>
    </div>
  </div>
</template>
<script setup lang="ts"></script>
<style scoped>
.page { min-height: 100vh; background: #F7F4EF; color: #0F2744; padding: 12px 16px 40px; padding-top: calc(12px + env(safe-area-inset-top)); }
.head { display: flex; gap: 10px; align-items: center; margin-bottom: 12px; }
.back { border: 0; background: transparent; font-size: 22px; font-weight: 700; cursor: pointer; color: #0F2744; }
.title { font-size: 17px; font-weight: 700; margin: 0; }
.tiles { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.tile {
  background: #fff; border: 1px solid #E8E4DC; border-radius: 16px; padding: 16px; text-decoration: none; color: inherit;
  display: flex; flex-direction: column; gap: 6px; min-height: 88px;
}
.tt { font-size: 15px; font-weight: 700; }
.td { font-size: 12px; color: #6B7280; }
</style>
