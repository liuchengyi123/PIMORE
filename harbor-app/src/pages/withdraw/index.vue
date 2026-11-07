<template>
  <view class="page">
    <view class="status hb-status"><text>9:41</text><text>●●● 5G</text></view>
    <view class="nav">
      <text class="back" @click="goBack">‹</text>
      <text class="title">Withdraw</text>
    </view>
    <text class="avail">Available {{ balance }}</text>
    <view class="field">
      <text class="lab">Amount (USD)</text>
      <input class="inp" v-model="amount" type="digit" placeholder="0.00" />
    </view>
    <view class="field">
      <text class="lab">Payout method</text>
      <input class="inp" v-model="payout" placeholder="PayPal · you@email.com" />
    </view>
    <text class="hint">{{ note || 'Withdrawals follow account rewards rules. Processing time varies by method.' }}</text>
    <view class="cta" @click="submit">Request withdraw</view>
    <view class="cta soft" @click="openSite">Open Harbor form</view>
  </view>
</template>
<script setup lang="ts">
import { useI18n } from '@/composables/i18n'
import { ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { fetchWithdrawHtml, postWithdraw, openHarborWeb, parseBalanceHtml } from '@/api/accountApi'
const { t } = useI18n()
const balance = ref('—')
const note = ref('Rebate wallet')
const payout = ref('')
const amount = ref('')
async function refresh() {
  try {
    const b = parseBalanceHtml(await fetchWithdrawHtml())
    balance.value = b.balanceText
    note.value = b.note || note.value
  } catch { /* */ }
}
async function submit() {
  if (!payout.value || !amount.value) {
    uni.showToast({ title: t('withdraw_fill'), icon: 'none' })
    return
  }
  try {
    const res = await postWithdraw(payout.value, amount.value)
    uni.showToast({ title: res.statusCode < 400 ? 'Submitted' : 'Open Harbor form', icon: 'none' })
    if (res.statusCode >= 400) openHarborWeb('/account/withdraw', 'Withdraw')
  } catch {
    openHarborWeb('/account/withdraw', 'Withdraw')
  }
}
function openSite() { openHarborWeb('/account/withdraw', 'Withdraw') }
function goBack() { uni.navigateBack({ fail: () => uni.navigateTo({ url: '/pages/balance/index' }) }) }
onShow(() => refresh())
</script>
<style scoped>
.page { min-height: 100vh; background: #F7F4EF; color: #0F2744; padding: 0 16px 40px; padding-top: env(safe-area-inset-top); }
.status { display: flex; justify-content: space-between; padding: 14px 12px 0; font-size: 12px; font-weight: 700; }
.nav { display: flex; align-items: center; gap: 10px; padding: 8px 0 12px; }
.back { font-size: 18px; font-weight: 700; }
.title { font-size: 17px; font-weight: 700; }
.avail { display: block; font-size: 11px; color: #6B7280; margin-bottom: 10px; }
.field { background: #fff; border: 1px solid #E8E4DC; border-radius: 12px; padding: 12px 14px; margin-bottom: 10px; }
.lab { display: block; font-size: 11px; font-weight: 600; color: #6B7280; margin-bottom: 4px; }
.inp { font-size: 14px; color: #0F2744; width: 100%; }
.hint { display: block; font-size: 11px; color: #6B7280; line-height: 1.45; margin: 0 0 14px; }
.cta { height: 41px; border-radius: 12px; background: #0F2744; color: #fff; font-size: 14px; font-weight: 600; display: flex; align-items: center; justify-content: center; margin-bottom: 10px; }
.cta.soft { background: #fff; color: #0F2744; border: 1px solid #E8E4DC; height: 43px; }
</style>
