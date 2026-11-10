<template>
  <div class="page">
    <header class="head">
      <button type="button" class="back" @click="$router.back()" aria-label="back">‹</button>
      <h1 class="title">{{ t('checkin_title') || 'Daily check-in' }}</h1>
    </header>

    <section class="hero">
      <div class="kicker">{{ checked ? (t('checkin_done_kicker') || 'Checked in') : (streakLabel) }}</div>
      <div class="headline">{{ checked ? (t('checkin_done') || 'Come back tomorrow') : (t('checkin_tap') || 'Check in for a coupon') }}</div>
      <button type="button" class="cta" :disabled="checked || busy" @click="claim">
        {{ busy ? (t('checkin_busy') || '…') : checked ? (t('checkin_tomorrow') || 'Done for today') : (t('checkin_go') || 'Check in today') }}
      </button>
      <router-link v-if="needLogin" class="login" :to="{ path: '/login', query: { next: '/checkin' } }">{{ t('checkin_login') || 'Sign in' }}</router-link>
    </section>

    <div class="days">
      <div v-for="d in 5" :key="d" class="day" :class="{ done: d < streakDay, today: d === streakDay, future: d > streakDay }">
        <div class="mark">{{ d < streakDay ? '✓' : (d === streakDay ? '●' : '') }}</div>
        <div class="lab">{{ zh ? ('第' + d + '天') : ('Day ' + d) }}</div>
      </div>
    </div>

    <section class="balance-card">
      <div class="row">
        <span class="b-title">{{ zh ? '余额' : 'Balance' }}</span>
        <span class="b-amt">{{ balanceText }}</span>
      </div>
      <p class="b-note">{{ detail || (zh ? '来自邀请和奖励 · 可提现' : 'From invites & rewards · Withdraw available') }}</p>
      <div class="b-actions">
        <router-link class="btn outline" to="/rewards">{{ zh ? '奖励' : 'Rewards' }}</router-link>
        <router-link class="btn solid" to="/withdraw">{{ zh ? '提现' : 'Withdraw' }}</router-link>
      </div>
    </section>
  </div>
</template>
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { fetchAccountSummary, fetchCheckInHtml, fetchBalancePanel, postCheckIn } from '@/api/accountApi'
import { useI18n } from '@/composables/i18n'
const { t, lang } = useI18n()
const zh = computed(() => String(lang.value).startsWith('zh'))
const checked = ref(false)
const busy = ref(false)
const detail = ref('')
const needLogin = ref(false)
const streakDay = ref(3)
const balanceText = ref('$0.00')
const streakLabel = computed(() => zh.value ? `连续 ${streakDay.value} 天` : `Day ${streakDay.value} streak`)
async function refresh() {
  const sum = await fetchAccountSummary()
  checked.value = !!sum.checkedToday
  needLogin.value = !sum.signedIn
  detail.value = !sum.signedIn
    ? (t('checkin_guest') || 'Sign in to keep your streak')
    : sum.checkedToday
      ? (t('checkin_done_note') || 'Streak saved for today')
      : (t('checkin_hint') || 'Check in for a coupon')
  try {
    const bal = await fetchBalancePanel()
    if (bal.balanceText) balanceText.value = bal.balanceText
  } catch { /* */ }
  try {
    const html = await fetchCheckInHtml()
    const m = html.match(/day\s*(\d)/i) || html.match(/streak[^0-9]*(\d)/i)
    if (m) streakDay.value = Math.min(5, Math.max(1, Number(m[1])))
  } catch { /* */ }
}
async function claim() {
  if (checked.value || busy.value) return
  busy.value = true
  try {
    await postCheckIn()
    await refresh()
  } finally { busy.value = false }
}
onMounted(refresh)
</script>
<style scoped>
.page { min-height: 100vh; background: var(--hb-page); color: var(--hb-ink); padding: 12px 16px 40px; padding-top: calc(12px + env(safe-area-inset-top)); }
.head { display: flex; gap: 10px; align-items: center; margin-bottom: 12px; }
.back { border: 0; background: transparent; font-size: 22px; font-weight: 700; cursor: pointer; color: var(--hb-ink); }
.title { font-size: 22px; font-weight: 800; letter-spacing: -0.03em; margin: 0; }
.hero {
  border-radius: 16px; padding: 16px;
  background: linear-gradient(162deg, var(--hb-primary) 4%, var(--hb-primary-pressed) 96%);
  color: var(--hb-on-primary);
}
.kicker { font-size: 13px; opacity: 0.85; }
.headline { margin-top: 6px; font-size: 22px; font-weight: 800; }
.cta {
  margin-top: 14px; height: 41px; padding: 0 16px; border: 0; border-radius: 12px;
  background: var(--hb-surface); color: var(--hb-ink); font-size: 14px; font-weight: 600; cursor: pointer;
}
.cta:disabled { opacity: 0.7; }
.login { display: inline-block; margin-top: 10px; color: var(--hb-on-primary); font-size: 13px; }
.days { display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px; margin-top: 14px; }
.day {
  background: var(--hb-surface); border: 1px solid var(--hb-line); border-radius: 12px; padding: 10px 4px;
  text-align: center; min-height: 65px;
}
.day.today { background: var(--hb-primary); border-color: var(--hb-ink); color: var(--hb-on-primary); }
.day.done .mark { color: #047857; font-weight: 700; }
.mark { font-size: 12px; font-weight: 700; min-height: 16px; }
.lab { margin-top: 4px; font-size: 11px; color: var(--hb-muted); }
.day.today .lab { color: var(--hb-on-primary); }
.balance-card {
  margin-top: 14px; background: var(--hb-surface); border: 1px solid var(--hb-line); border-radius: 16px; padding: 14px;
}
.row { display: flex; justify-content: space-between; align-items: center; }
.b-title { font-size: 16px; font-weight: 700; }
.b-amt { font-size: 16px; font-weight: 700; color: var(--hb-sale); }
.b-note { margin: 6px 0 0; font-size: 11px; color: var(--hb-muted); }
.b-actions { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 12px; }
.btn {
  display: flex; align-items: center; justify-content: center; height: 41px; border-radius: 12px;
  font-size: 14px; font-weight: 600; text-decoration: none;
}
.btn.outline { background: var(--hb-surface); border: 1px solid var(--hb-line); color: var(--hb-ink); }
.btn.solid { background: var(--hb-primary); color: var(--hb-on-primary); border: 0; }
</style>
