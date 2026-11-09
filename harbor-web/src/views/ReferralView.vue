<template>
  <AgShell>
    <header class="top ag-top ag-pad">
      <div>
        <AgBrand />
        <div class="ag-tagline">{{ tx('家居好物 · $1–$10', 'HOME GOODS · $1 – $10') }}</div>
      </div>
      <button type="button" class="bag" @click="router.push('/cart')" :aria-label="tx('购物车', 'Cart')"><ShoppingBag :size="20" /></button>
    </header>

    <div class="ag-pad">
      <div class="kicker">{{ tx('领取邀请', 'REFERRAL CLAIM') }}</div>
      <h1>{{ tx('欢迎来到 Harbor！', 'Welcome to Harbor!') }}</h1>
      <p class="lead">{{ tx('还差一步就能拿到见面礼。输入好友的邀请码，领取你的礼物。', "You're one step away from your welcome reward. Enter the invite code from a friend and claim your gift!") }}</p>

      <div class="gift" aria-hidden="true">
        <div class="box"><span>$5</span></div>
        <em>{{ tx('小物不小，\n快乐很大。', 'Small things.\nBig joy.') }} ♥</em>
      </div>

      <label class="ag-field">
        <span>{{ tx('输入邀请码', 'Enter invite code') }}</span>
        <span class="inbox">
          <Ticket :size="16" color="#8B919A" />
          <input v-model="code" :placeholder="tx('例如 HARBOR123', 'e.g. HARBOR123')" />
        </span>
      </label>

      <section class="welcome ag-card">
        <div>
          <div class="pill"><Gift :size="14" /> {{ tx('你的见面礼', 'Your welcome gift') }}</div>
          <div class="off">{{ tx('$5 立减', '$5 OFF') }}</div>
          <div class="on">{{ tx('首单可用', 'on your first order') }}</div>
          <p>{{ tx('满 $10 可用 · 仅限新客', 'Valid on orders $10+ · New customers only') }}</p>
        </div>
        <div class="stub">$5<br />OFF</div>
      </section>

      <p v-if="msg" class="ag-toast">{{ msg }}</p>
      <button type="button" class="ag-cta" :disabled="busy" @click="claim">{{ tx('领取奖励', 'Claim reward') }} →</button>
      <button type="button" class="ag-cta ghost" style="margin-top:10px" @click="router.push('/home')">{{ tx('进入店铺', 'Enter shop') }} →</button>
      <p class="foot">{{ tx('探索 $1–$10 的家居好物', 'Explore great home goods for $1–$10') }}</p>

      <div class="perks">
        <div><Home :size="18" /><span>{{ tx('每日家居', 'Everyday home essentials') }}</span></div>
        <div><Tag :size="18" /><span>{{ tx('好价 $1–$10', 'Great prices $1–$10') }}</span></div>
        <div><Heart :size="18" /><span>{{ tx('你会喜欢的品质', "Quality you'll love") }}</span></div>
        <div><Leaf :size="18" /><span>{{ tx('更开心的家', 'A happier home') }}</span></div>
      </div>
    </div>
  </AgShell>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Gift, Heart, Home, Leaf, ShoppingBag, Tag, Ticket } from 'lucide-vue-next'
import AgBrand from '@/components/account/AgBrand.vue'
import AgShell from '@/components/account/AgShell.vue'
import { shopPath } from '@/api/accountApi'
import { useZh } from '@/composables/zh'

const { tx } = useZh()
const route = useRoute()
const router = useRouter()
const code = ref(String(route.query.code || ''))
const busy = ref(false)
const msg = ref('')

onMounted(() => {
  if (!code.value) {
    try { code.value = localStorage.getItem('harbor_invite_code') || '' } catch { /* ignore */ }
  }
})

function claim() {
  const c = code.value.trim()
  if (!c) { msg.value = tx('请输入邀请码', 'Enter an invite code'); return }
  busy.value = true
  try { localStorage.setItem('harbor_invite_code', c) } catch { /* ignore */ }
  msg.value = tx('正在打开领取页…', 'Opening the claim page…')
  window.location.href = shopPath('/r/' + encodeURIComponent(c))
}
</script>

<style scoped>
.top { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 18px; }
.bag { border: 0; background: transparent; color: #1C2430; cursor: pointer; }
.kicker { text-align: center; color: #F96141; font-weight: 800; letter-spacing: 0.14em; font-size: 12px; }
h1 { margin: 8px 0 0; text-align: center; font-size: 30px; font-weight: 800; letter-spacing: -0.04em; }
.lead { text-align: center; color: #5C6570; font-size: 14px; line-height: 1.45; }
.gift { position: relative; height: 150px; margin: 8px 0 12px; }
.box {
  width: 120px; height: 100px; margin: 24px auto 0; background: #F96141; border-radius: 8px;
  box-shadow: 0 12px 0 #F3E4DC inset; display: grid; place-items: center; color: #fff; position: relative;
}
.box span { position: absolute; right: -6px; top: 22px; z-index: 2; background: #fff; color: #F96141; font-weight: 800; border-radius: 8px; padding: 6px 8px; transform: rotate(-8deg); }
.box::before, .box::after { content: ""; position: absolute; background: #fff; }
.box::before { left: 0; right: 0; top: 42px; height: 14px; }
.box::after { top: 0; bottom: 0; left: 52px; width: 14px; }
.gift em { position: absolute; right: 18px; top: 18px; color: #F96141; font-family: 'Segoe Script', cursive; font-size: 14px; white-space: pre-line; }
.inbox { display: flex; align-items: center; gap: 8px; border: 1px solid #E7E1DA; border-radius: 14px; padding: 0 12px; background: #fff; }
.inbox input { border: 0; height: 48px; padding: 0; }
.welcome { margin: 8px 0 14px; padding: 14px; display: flex; align-items: center; gap: 10px; background: #FFF6F3; }
.pill { display: inline-flex; align-items: center; gap: 4px; color: #F96141; font-weight: 750; font-size: 13px; }
.off { font-size: 28px; font-weight: 800; letter-spacing: -0.04em; margin-top: 4px; }
.on { font-weight: 800; }
.welcome p { margin: 6px 0 0; color: #8B919A; font-size: 12px; }
.stub {
  margin-left: auto; width: 84px; height: 64px; background: #F96141; color: #fff; border-radius: 10px;
  display: grid; place-items: center; font-weight: 800; text-align: center; line-height: 1.05; transform: rotate(-8deg);
}
.foot { text-align: center; color: #8B919A; font-size: 12.5px; }
.perks { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; margin-top: 18px; text-align: center; color: #F96141; }
.perks span { display: block; margin-top: 6px; color: #5C6570; font-size: 11px; line-height: 1.3; }
</style>
