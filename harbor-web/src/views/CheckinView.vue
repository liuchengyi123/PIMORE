<template>
  <AgShell tabs="home">
    <header class="top ag-top ag-pad">
      <div>
        <AgBrand />
        <div class="ag-tagline">{{ tx('家居好物 · 每天更好', 'HOME GOODS · BETTER EVERYDAY') }}</div>
      </div>
      <div class="burst">{{ tx('好物\n$1–$10', 'Great finds\n$1 – $10') }}</div>
    </header>

    <section class="stage">
      <div class="kicker">{{ tx('每日', 'DAILY') }}</div>
      <h1>{{ tx('签到', 'Check-in') }}</h1>
      <p>{{ tx('一小步，更多奖励。\n每天回来，奖励不断！', 'Small steps. Bigger rewards.\nCome back daily and get rewarded!') }}</p>
    </section>

    <div class="ag-pad">
      <section class="week ag-card">
        <div v-for="d in days" :key="d.n" class="day" :class="d.state">
          <small>{{ tx(`第${d.n}天`, `Day ${d.n}`) }}</small>
          <b>{{ d.n }}</b>
          <span>{{ d.state === 'done' ? '✓' : d.state === 'today' ? tx('今天', 'Today') : '○' }}</span>
        </div>
      </section>

      <section class="preview ag-card">
        <Coins :size="42" color="#F6C445" />
        <div>
          <div class="lab">{{ tx('签到奖励预览', 'Check-in reward preview') }}</div>
          <div class="plus">{{ tx('+ 10 积分', '+ 10 points') }}</div>
          <p>{{ tx('连续 7 天再送 50 积分！', 'Collect 7 days in a row to get a bonus 50 points!') }}</p>
        </div>
      </section>

      <button type="button" class="ag-cta" :disabled="checked || busy" @click="claim">
        <CalendarCheck :size="18" />
        {{ busy ? '…' : checked ? tx('今日已签到', 'Checked in today') : tx('今日签到', 'Check in today') }}
      </button>
      <router-link v-if="needLogin" class="login" :to="{ path: '/login', query: { next: '/checkin' } }">{{ tx('登录后把积分记到账户', 'Sign in to keep points on your account') }}</router-link>

      <section class="streak ag-card">
        <Flame :size="28" color="#F96141" />
        <div>
          <div class="lab">{{ tx('当前连续', 'CURRENT STREAK') }}</div>
          <b>{{ tx(`${streak} 天`, `${streak} days`) }}</b>
          <p>{{ tx('继续保持！', 'Keep it going!') }}</p>
        </div>
        <div class="badge">{{ tx('7 日\n连续', '7-DAY\nSTREAK') }}</div>
      </section>

      <section class="rules ag-card">
        <div class="lab"><Info :size="16" color="#F96141" /> {{ tx('签到规则', 'Check-in Rules') }}</div>
        <ul>
          <li>{{ tx('每天点一次按钮领取积分。', 'Tap the button once per day to earn points.') }}</li>
          <li>{{ tx('每天只能签到一次。', 'You can only check in once per day.') }}</li>
          <li>{{ tx('连续 7 天有额外奖励。', 'Keep your 7-day streak for a bonus reward!') }}</li>
          <li>{{ tx('积分可在之后的订单里抵扣。', 'Points can be used for discounts on future purchases.') }}</li>
        </ul>
      </section>
      <p class="slogan">♡ {{ tx('家更好 · 你更开心', 'Better Home · Happier You') }} ♡</p>
    </div>
  </AgShell>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { CalendarCheck, Coins, Flame, Info } from 'lucide-vue-next'
import AgBrand from '@/components/account/AgBrand.vue'
import AgShell from '@/components/account/AgShell.vue'
import { fetchAccountSummary, fetchCheckInHtml, postCheckIn } from '@/api/accountApi'
import { useZh } from '@/composables/zh'

const { tx } = useZh()
const checked = ref(false)
const busy = ref(false)
const needLogin = ref(false)
const streak = ref(1)
const today = computed(() => Math.min(7, Math.max(1, streak.value)))
const days = computed(() => Array.from({ length: 7 }, (_, i) => {
  const n = i + 1
  const state = n < today.value ? 'done' : n === today.value ? (checked.value ? 'done' : 'today') : 'wait'
  return { n, state }
}))

async function refresh() {
  const sum = await fetchAccountSummary()
  checked.value = !!sum.checkedToday
  needLogin.value = !sum.signedIn
  try {
    const html = await fetchCheckInHtml()
    const m = html.match(/day\s*(\d)/i) || html.match(/streak[^0-9]*(\d)/i) || html.match(/连续\s*(\d)/)
    if (m) streak.value = Math.min(7, Math.max(1, Number(m[1])))
  } catch { /* keep default */ }
}
async function claim() {
  if (checked.value || busy.value) return
  busy.value = true
  try { await postCheckIn(); await refresh() } finally { busy.value = false }
}
onMounted(refresh)
</script>

<style scoped>
.top { display: flex; align-items: flex-start; justify-content: space-between; }
.burst {
  background: #F96141; color: #fff; border-radius: 16px 4px 16px 16px; padding: 8px 10px;
  font-size: 12px; font-weight: 800; white-space: pre-line; line-height: 1.15; transform: rotate(6deg);
}
.stage { text-align: center; padding: 18px 24px 8px; }
.kicker { color: #F96141; font-weight: 800; letter-spacing: 0.16em; font-size: 13px; }
h1 { margin: 2px 0 0; font-size: 36px; font-weight: 800; letter-spacing: -0.045em; }
.stage p { margin: 6px 0 0; color: #5C6570; white-space: pre-line; font-size: 14px; }
.week { margin-top: 12px; display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; padding: 12px 8px; text-align: center; }
.day small { display: block; color: #8B919A; font-size: 10px; }
.day b { display: grid; place-items: center; width: 32px; height: 32px; margin: 4px auto; border-radius: 50%; background: #F3EFEA; font-size: 13px; }
.day span { font-size: 10px; color: #8B919A; }
.day.done b { background: #E7F6EF; color: #128A5E; }
.day.done span { color: #128A5E; }
.day.today b { background: #F96141; color: #fff; }
.day.today span { color: #F96141; font-weight: 800; }
.preview { margin-top: 12px; display: flex; gap: 12px; align-items: center; padding: 14px; background: #FFF6F3; }
.lab { font-size: 13px; color: #5C6570; display: flex; align-items: center; gap: 6px; }
.plus { color: #F96141; font-size: 22px; font-weight: 800; }
.preview p, .streak p { margin: 2px 0 0; color: #8B919A; font-size: 12.5px; }
.ag-cta { margin-top: 12px; }
.login { display: block; text-align: center; margin-top: 8px; color: #F96141; font-weight: 700; font-size: 13px; }
.streak { margin-top: 12px; display: flex; align-items: center; gap: 10px; padding: 14px; }
.streak b { font-size: 22px; }
.badge {
  margin-left: auto; width: 72px; height: 72px; border-radius: 50%; background: #F96141; color: #fff;
  display: grid; place-items: center; text-align: center; font-size: 11px; font-weight: 800; white-space: pre-line; line-height: 1.15;
}
.rules { margin-top: 12px; padding: 14px 16px; }
.rules ul { margin: 8px 0 0; padding-left: 18px; color: #5C6570; font-size: 13px; line-height: 1.55; }
.slogan { text-align: center; color: #F96141; font-weight: 700; margin: 16px 0 4px; }
</style>
