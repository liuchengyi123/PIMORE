<template>
  <view class="page">
    <view class="status hb-status"><text>9:41</text><text>●●● 5G</text></view>
    <view class="nav">
      <text class="back" @click="goBack">‹</text>
      <text class="title">Addresses</text>
      <text class="add" @click="manage">Add</text>
    </view>
    <view v-if="loginRequired" class="state">Sign in to manage addresses.</view>
    <view v-else-if="loading" class="state">Loading…</view>
    <view v-else-if="!rows.length" class="state">No addresses yet.</view>
    <view v-else class="list">
      <view v-for="(r, i) in rows" :key="i" class="card">
        <view v-if="i === 0" class="badge"><text>Default</text></view>
        <text class="nm">{{ r.name }}</text>
        <text class="line">{{ r.line }}</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { useI18n } from '@/composables/i18n'
import { ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { fetchAddresses, openHarborWeb, accountLinks, type AddressRow } from '@/api/accountApi'
const { t } = useI18n()
const rows = ref<AddressRow[]>([])
const loading = ref(false)
const loginRequired = ref(false)
async function refresh() {
  loading.value = true
  try {
    const res = await fetchAddresses()
    rows.value = res.rows
    loginRequired.value = res.loginRequired && !res.rows.length
  } finally { loading.value = false }
}
function login() { openHarborWeb(accountLinks().login, 'Sign in') }
function manage() { openHarborWeb('/account/addresses', 'Addresses') }
function goBack() { uni.navigateBack({ fail: () => uni.reLaunch({ url: '/pages/me/index' }) }) }
onShow(() => {
  uni.setNavigationBarTitle({ title: t('addresses_title') })
  refresh()
})
</script>

<style scoped>
.page { min-height: 100vh; background: #F7F4EF; color: #0F2744; padding: 0 16px 40px; padding-top: env(safe-area-inset-top); }
.status { display: flex; justify-content: space-between; padding: 14px 12px 0; font-size: 12px; font-weight: 700; }
.nav { display: flex; align-items: center; gap: 10px; padding: 8px 0 12px; }
.back { font-size: 18px; font-weight: 700; }
.title { flex: 1; font-size: 17px; font-weight: 700; }
.add { font-size: 13px; font-weight: 600; color: #0E7490; }
.list { display: flex; flex-direction: column; gap: 10px; }
.card { background: #fff; border: 2px solid #0F2744; border-radius: 16px; padding: 14px; }
.badge { display: inline-flex; background: #E0F2FE; color: #0E7490; font-size: 11px; font-weight: 600; padding: 4px 10px; border-radius: 999px; margin-bottom: 8px; }
.nm { display: block; font-size: 13px; font-weight: 600; }
.line { display: block; margin-top: 4px; font-size: 13px; color: #0F2744; line-height: 1.45; }
.state { text-align: center; color: #6B7280; padding: 36px 8px; }
</style>
