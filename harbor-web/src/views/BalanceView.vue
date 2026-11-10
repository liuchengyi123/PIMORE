<template>
  <div class="page">
    <header class="head">
      <button type="button" class="back" @click="$router.back()" aria-label="back">‹</button>
      <h1 class="title">{{ zh ? '余额' : 'Balance' }}</h1>
    </header>

    <section class="hero">
      <div class="label">{{ zh ? '可用余额' : 'Available balance' }}</div>
      <div class="amt">{{ info.balanceText || '—' }}</div>
      <div class="actions">
        <router-link class="btn white" to="/withdraw">{{ zh ? '提现' : 'Withdraw' }}</router-link>
        <router-link class="btn ghost" to="/rewards">{{ zh ? '奖励' : 'Rewards' }}</router-link>
      </div>
    </section>

    <div v-if="info.message === 'login-required'" class="gate">
      <router-link class="gate-btn" :to="{ path: '/login', query: { next: '/balance' } }">{{ zh ? '登录' : 'Sign in' }}</router-link>
    </div>

    <section class="activity">
      <h2>{{ zh ? '最近变动' : 'Recent activity' }}</h2>
      <div v-if="!rows.length" class="empty">{{ info.note || (zh ? '邀请和奖励会记在这里。' : 'Invite and reward credits appear here.') }}</div>
      <div v-for="(r, i) in rows" :key="i" class="row-card">
        <div>
          <div class="nm">{{ r.title }}</div>
          <div class="when">{{ r.when }}</div>
        </div>
        <div class="delta" :class="{ pos: r.pos, neg: !r.pos }">{{ r.amount }}</div>
      </div>
    </section>
  </div>
</template>
<script setup lang="ts">
import { computed, onMounted, reactive } from 'vue'
import { fetchBalancePanel, type BalanceInfo } from '@/api/accountApi'
import { useI18n } from '@/composables/i18n'
const { lang } = useI18n()
const zh = computed(() => String(lang.value).startsWith('zh'))
const info = reactive<BalanceInfo>({ ok: false, live: false, signedIn: false, balanceText: '—', note: '' })
onMounted(async () => { Object.assign(info, await fetchBalancePanel()) })
const rows = computed(() => {
  const list = (info as any).activity || (info as any).rows || []
  if (Array.isArray(list) && list.length) {
    return list.map((x: any) => ({
      title: String(x.title || x.name || 'Activity'),
      when: String(x.when || x.date || ''),
      amount: String(x.amount || x.delta || ''),
      pos: String(x.amount || x.delta || '').includes('+') || Number(x.cents || 0) > 0,
    }))
  }
  return []
})
</script>
<style scoped>
.page { min-height: 100vh; background: var(--hb-page); color: var(--hb-ink); padding: 12px 16px 40px; padding-top: calc(12px + env(safe-area-inset-top)); }
.head { display: flex; gap: 10px; align-items: center; margin-bottom: 12px; }
.back { border: 0; background: transparent; font-size: 22px; font-weight: 700; cursor: pointer; color: var(--hb-ink); }
.title { font-size: 22px; font-weight: 800; letter-spacing: -0.03em; margin: 0; }
.hero {
  border-radius: 18px; padding: 20px;
  background: linear-gradient(163deg, var(--hb-primary) 6%, #1A3A5C 94%);
  color: var(--hb-on-primary);
}
.label { font-size: 12px; opacity: 0.8; }
.amt { margin-top: 6px; font-size: 36px; font-weight: 800; line-height: 1.1; }
.actions { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 16px; }
.btn {
  display: flex; align-items: center; justify-content: center; height: 41px; border-radius: 12px;
  font-size: 14px; font-weight: 600; text-decoration: none;
}
.btn.white { background: var(--hb-surface); color: var(--hb-ink); }
.btn.ghost { background: rgba(255,255,255,0.15); border: 1px solid rgba(255,255,255,0.25); color: var(--hb-on-primary); }
.gate { margin-top: 14px; text-align: center; }
.gate-btn { display: inline-flex; background: var(--hb-primary); color: var(--hb-on-primary); padding: 12px 18px; border-radius: 999px; text-decoration: none; font-weight: 600; }
.activity { margin-top: 16px; }
.activity h2 { font-size: 16px; font-weight: 700; margin: 0 0 10px; }
.empty { color: var(--hb-muted); font-size: 13px; padding: 8px 0; }
.row-card {
  display: flex; justify-content: space-between; align-items: center;
  background: var(--hb-surface); border: 1px solid var(--hb-line); border-radius: 16px; padding: 14px; margin-bottom: 8px;
}
.nm { font-size: 13px; font-weight: 600; }
.when { margin-top: 2px; font-size: 11px; color: var(--hb-muted); }
.delta { font-size: 16px; font-weight: 700; }
.delta.pos { color: #047857; }
.delta.neg { color: #B91C1C; }
</style>
