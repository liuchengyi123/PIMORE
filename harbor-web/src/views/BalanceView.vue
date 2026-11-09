<template>
  <AgShell tabs="me">
    <header class="brand ag-top ag-pad">
      <AgBrand wave />
      <div class="tag">{{ tx('每天发现\n点亮家的光', 'Everyday Finds\nfor a Brighter Home') }}</div>
      <button type="button" class="ag-gear" @click="router.push('/locale')" :aria-label="tx('设置', 'Settings')">
        <Settings :size="20" />
      </button>
    </header>

    <section class="wallet ag-pad">
      <div class="card">
        <div class="label"><Wallet :size="16" /> {{ tx('钱包余额', 'Wallet Balance') }}</div>
        <div class="avail">{{ tx('可用', 'Available') }}</div>
        <div class="amt">{{ info.balanceText || '—' }}</div>
        <div class="slogan">{{ tx('小额消费，大有意义。', 'Small purchases. Big moments.') }}</div>
        <Home class="house" :size="42" color="rgba(255,255,255,0.9)" :stroke-width="1.4" />
      </div>
      <div class="actions">
        <button type="button" @click="topup = !topup"><span class="ag-icon"><Plus :size="18" /></span>{{ tx('充值', 'Top up') }}</button>
        <button type="button" @click="router.push('/withdraw')"><span class="ag-icon"><ArrowLeftRight :size="18" /></span>{{ tx('提现', 'Withdraw') }}</button>
        <button type="button" @click="scrollTx"><span class="ag-icon"><ScrollText :size="18" /></span>{{ tx('交易记录', 'Transaction history') }}</button>
      </div>
      <p v-if="topup" class="ag-toast">{{ tx('余额来自退款、签到和邀请奖励，暂不支持银行卡充值。', 'Balance comes from refunds, check-ins, and invites. Card top-up is not available.') }}</p>
      <div v-if="info.message === 'login-required'" class="ag-empty">
        <router-link class="ag-cta" :to="{ path: '/login', query: { next: '/balance' } }">{{ tx('登录后查看余额', 'Sign in to see balance') }}</router-link>
      </div>
    </section>

    <section id="tx" class="ag-pad">
      <div class="ag-sec">
        <h2>{{ tx('最近交易', 'Recent transactions') }}</h2>
        <button type="button" class="ag-link" @click="showAll = !showAll">{{ tx('查看全部', 'View all') }} ›</button>
      </div>
      <div v-if="!shown.length" class="ag-card ag-empty">
        <h3>{{ tx('还没有交易', 'No transactions yet') }}</h3>
        <p>{{ info.note || tx('邀请和奖励会记在这里。', 'Invite and reward credits appear here.') }}</p>
      </div>
      <article v-for="(r, i) in shown" :key="i" class="tx">
        <span class="bubble" :class="r.kind"><component :is="r.icon" :size="16" /></span>
        <div class="mid">
          <div class="nm">{{ r.title }}</div>
          <div class="when">{{ r.when }}</div>
          <div class="sub">{{ r.sub }}</div>
        </div>
        <div class="right">
          <b :class="r.pos ? 'pos' : 'neg'">{{ r.amount }}</b>
          <span class="st">{{ tx('已完成', 'Completed') }}</span>
        </div>
      </article>
    </section>
  </AgShell>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeftRight, Gift, Home, Plus, RotateCcw, ScrollText, Settings, ShoppingBag, Wallet } from 'lucide-vue-next'
import AgBrand from '@/components/account/AgBrand.vue'
import AgShell from '@/components/account/AgShell.vue'
import { fetchHtmlPath, parseBalanceHtml, type BalanceInfo } from '@/api/accountApi'
import { useZh } from '@/composables/zh'

const { tx } = useZh()
const router = useRouter()
const info = reactive<BalanceInfo>({ ok: false, live: false, signedIn: false, balanceText: '—', note: '' })
const rows = ref<{ title: string; when: string; sub: string; amount: string; pos: boolean; kind: string; icon: typeof Gift }[]>([])
const showAll = ref(false)
const topup = ref(false)
const shown = computed(() => showAll.value ? rows.value : rows.value.slice(0, 5))

function kindOf(title: string, amount: string) {
  const pos = /^\s*\+/.test(amount) || /退|奖|reward|refund/i.test(title)
  if (/退|refund/i.test(title)) return { kind: 'mint', icon: RotateCcw, pos: true }
  if (/奖|reward|邀请|referral/i.test(title)) return { kind: 'coral', icon: Gift, pos: true }
  return { kind: pos ? 'mint' : 'sand', icon: ShoppingBag, pos }
}

onMounted(async () => {
  try {
    const html = await fetchHtmlPath('/account/balance')
    Object.assign(info, parseBalanceHtml(html))
    const found: typeof rows.value = []
    for (const m of html.matchAll(/<(?:li|tr|article)[^>]*>([\s\S]*?)<\/(?:li|tr|article)>/gi)) {
      const text = m[1].replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim()
      const amt = text.match(/[+-]\s*[$¥]?\s*\d+(?:\.\d{1,2})?/)
      if (!amt || text.length > 180) continue
      const title = text.replace(amt[0], '').trim().slice(0, 42) || tx('余额变动', 'Balance')
      const k = kindOf(title, amt[0])
      found.push({ title, when: '', sub: '', amount: amt[0].replace(/\s/g, ''), ...k })
    }
    rows.value = found
  } catch { /* guest / offline */ }
})

function scrollTx() {
  document.getElementById('tx')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}
</script>

<style scoped>
.brand { display: flex; align-items: center; gap: 10px; margin-bottom: 14px; }
.tag { flex: 1; font-size: 11px; color: #8B919A; white-space: pre-line; line-height: 1.3; border-left: 1px solid #E7E1DA; padding-left: 10px; }
.wallet { margin-bottom: 6px; }
.card {
  position: relative; overflow: hidden; border-radius: 22px; padding: 18px 18px 20px; color: #fff;
  background:
    radial-gradient(120px 80px at 92% 78%, rgba(255,255,255,0.18), transparent 70%),
    linear-gradient(145deg, #FF8A6A 0%, #F96141 55%, #F04A2A 100%);
}
.card::after {
  content: ""; position: absolute; right: -20px; bottom: -30px; width: 180px; height: 90px;
  background: rgba(255,255,255,0.12); border-radius: 80px 80px 0 0; transform: rotate(-8deg);
}
.label { display: flex; align-items: center; gap: 6px; font-weight: 700; font-size: 14px; }
.avail { margin-top: 14px; font-size: 13px; opacity: 0.9; }
.amt { font-size: 40px; font-weight: 800; letter-spacing: -0.04em; line-height: 1.05; }
.slogan { margin-top: 6px; font-size: 13px; opacity: 0.92; }
.house { position: absolute; right: 18px; bottom: 16px; z-index: 1; }
.actions { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-top: 16px; }
.actions button {
  border: 0; background: transparent; cursor: pointer; color: #1C2430;
  display: flex; flex-direction: column; align-items: center; gap: 8px; font-size: 12.5px; font-weight: 650;
}
.tx { display: flex; align-items: center; gap: 10px; padding: 12px 0; border-bottom: 1px solid #F1ECE6; }
.bubble { width: 38px; height: 38px; border-radius: 50%; display: grid; place-items: center; flex: 0 0 auto; }
.bubble.mint { background: #E7F6EF; color: #128A5E; }
.bubble.coral { background: #FFF1EC; color: #F96141; }
.bubble.sand { background: #FFF4E8; color: #E07A2F; }
.mid { flex: 1; min-width: 0; }
.nm { font-weight: 750; font-size: 14.5px; }
.when, .sub { font-size: 12px; color: #8B919A; }
.right { text-align: right; }
.right b { display: block; font-size: 15px; }
.pos { color: #128A5E; }
.neg { color: #1C2430; }
.st { display: inline-flex; margin-top: 4px; font-size: 11px; color: #128A5E; background: #E7F6EF; border-radius: 999px; padding: 2px 8px; font-weight: 700; }
.neg + .st, .right .neg ~ .st { color: #8B919A; background: #F3F1EE; }
</style>
