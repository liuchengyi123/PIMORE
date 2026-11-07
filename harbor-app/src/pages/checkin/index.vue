<template>
  <view class="page">
    <view class="head">
      <view class="back" @click="goBack">←</view>
      <view>
        <text class="title">{{ t('checkin_title') }}</text>
        <text class="sub">{{ t('checkin_sub') }}</text>
      </view>
    </view>
    <view class="card">
      <text class="kicker">{{ checked ? 'Done for today' : 'Claim today’s perk' }}</text>
      <text class="title2">{{ checked ? 'Checked in' : 'Tap to check in' }}</text>
      <text class="note">{{ detail }}</text>
      <view class="btn" :class="{ dim: checked || busy }" @click="claim">{{ busy ? 'Working…' : checked ? 'Come back tomorrow' : 'Check in' }}</view>
    </view>
    <view v-if="offers.length" class="list">
      <view v-for="(o, i) in offers" :key="i" class="art">
        <text class="nm">{{ o }}</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { useI18n } from '@/composables/i18n'
import { ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { fetchCheckInHtml, postCheckIn, openHarborWeb, accountLinks, fetchAccountSummary } from '@/api/accountApi'
const { t } = useI18n()

const checked = ref(false)
const busy = ref(false)
const detail = ref('Sign in on Harbor to keep your streak.')
const offers = ref<string[]>([])

async function refresh() {
  const sum = await fetchAccountSummary()
  checked.value = sum.checkedToday
  if (!sum.signedIn) {
    detail.value = 'Guest · sign in so the coupon lands in your account.'
  } else {
    detail.value = sum.checkedToday ? 'Streak saved · coupons in Me' : 'One tap · coupon unlocks after claim'
  }
  try {
    const html = await fetchCheckInHtml()
    const found: string[] = []
    const re = /class="nm"[^>]*>([\s\S]*?)<\/div>/gi
    let m: RegExpExecArray | null
    while ((m = re.exec(html))) {
      const t = m[1].replace(/<[^>]+>/g, '').trim()
      if (t) found.push(t)
    }
    offers.value = found.slice(0, 6)
  } catch { /* ignore */ }
}

async function claim() {
  if (checked.value || busy.value) return
  const sum = await fetchAccountSummary()
  if (!sum.signedIn) {
    openHarborWeb(accountLinks().login, 'Sign in')
    return
  }
  busy.value = true
  try {
    const res = await postCheckIn()
    if (res.ok) {
      checked.value = true
      uni.showToast({ title: t('me_checked_in'), icon: 'success' })
      await refresh()
    } else {
      openHarborWeb('/check-in', 'Check-in')
    }
  } finally {
    busy.value = false
  }
}

function goBack() { uni.navigateBack({ fail: () => uni.reLaunch({ url: '/pages/me/index' }) }) }
onShow(() => refresh())
</script>

<style lang="scss" scoped>
@import '@/styles/theme.scss';
.page { min-height: 100vh; background: $hb-paper; padding: 12px 16px 40px; padding-top: calc(12px + env(safe-area-inset-top)); }
.head { display: flex; gap: 12px; align-items: center; margin-bottom: 16px; }
.back { width: 36px; height: 36px; border-radius: 12px; background: $hb-white; text-align: center; line-height: 36px; box-shadow: $hb-shadow-soft; }
.title { display: block; font-size: 24px; font-weight: 720; }
.sub { display: block; font-size: 12px; color: $hb-muted; margin-top: 2px; }
.card {
  border-radius: 26px; padding: 22px 20px; margin-bottom: 14px;
  background: linear-gradient(160deg, $hb-deep, $hb-forest); color: #fff; box-shadow: $hb-shadow-lift;
}
.kicker { display: block; font-size: 11px; letter-spacing: 1px; text-transform: uppercase; opacity: 0.75; font-weight: 650; }
.title2 { display: block; font-size: 26px; font-weight: 760; margin-top: 8px; letter-spacing: -0.5px; }
.note { display: block; margin-top: 10px; font-size: 13px; opacity: 0.85; line-height: 1.4; }
.btn { margin-top: 18px; display: inline-flex; background: $hb-coral; color: #fff; padding: 12px 16px; border-radius: 999px; font-weight: 720; }
.btn.dim { opacity: 0.55; }
.list { display: flex; flex-direction: column; gap: 8px; }
.art { background: $hb-white; border-radius: 16px; padding: 14px 16px; box-shadow: $hb-shadow-soft; }
.nm { font-size: 14px; font-weight: 680; color: $hb-coral; }
</style>
