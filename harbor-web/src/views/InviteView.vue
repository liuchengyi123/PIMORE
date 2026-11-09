<template>
  <AgShell tabs="me">
    <header class="brand ag-top ag-pad">
      <AgBrand wave />
      <button type="button" class="ag-gear" @click="router.push('/locale')" :aria-label="tx('设置', 'Settings')"><Settings :size="20" /></button>
    </header>

    <div class="ag-pad">
      <section class="hero ag-card">
        <div class="copy">
          <h1>{{ tx('邀请好友，\n赚取奖励', 'Invite friends,\nearn rewards') }}</h1>
          <p>{{ tx('分享邀请码，好友购物，双方都有奖励！', 'Share your code, get your friends shopping, and earn rewards for both of you!') }}</p>
        </div>
        <div class="bag" aria-hidden="true">
          <span class="heart">♥</span>
          <div class="sack">Harbor</div>
          <em>{{ tx('在一起\n更好', 'Good things\nare better\ntogether') }}</em>
        </div>
      </section>

      <section class="code ag-card">
        <div class="kicker">{{ tx('你的邀请码', 'YOUR REFERRAL CODE') }}</div>
        <div class="box">
          <b>{{ code }}</b>
          <button type="button" @click="copy" :aria-label="tx('复制', 'Copy')"><Copy :size="16" /></button>
        </div>
        <p>{{ tx('好友首单立减 10%，你获得 $5 余额。', 'Give 10% off to your friends. Get $5 credit when they make their first purchase.') }}</p>
        <div class="pair">
          <button type="button" class="ag-cta pill" @click="copy"><Copy :size="16" /> {{ tx('复制', 'Copy') }}</button>
          <button type="button" class="ag-cta pill" @click="share"><Share2 :size="16" /> {{ tx('分享', 'Share') }}</button>
        </div>
      </section>
      <p v-if="msg" class="ag-toast">{{ msg }}</p>

      <h2>{{ tx('如何运作', 'How it works') }}</h2>
      <div class="steps">
        <div v-for="(s, i) in steps" :key="s.t">
          <span class="bubble"><component :is="s.icon" :size="18" /><i>{{ i + 1 }}</i></span>
          <b>{{ s.t }}</b>
          <small>{{ s.d }}</small>
        </div>
      </div>

      <div class="ag-sec">
        <h2>{{ tx('已加入的好友', 'Friends joined') }}</h2>
        <span class="ag-note">{{ friends.length ? tx(`${friends.length} 位好友`, `${friends.length} friends`) : '' }}</span>
      </div>
      <div v-if="!friends.length" class="ag-card ag-empty">
        <h3>{{ tx('还没有好友加入', 'No friends yet') }}</h3>
        <p>{{ tx('分享邀请码后，好友会出现在这里。', 'Friends show up here after they join with your code.') }}</p>
      </div>
      <article v-for="(f, i) in friends" :key="i" class="friend">
        <span class="av">{{ f.name.slice(0, 1) }}</span>
        <div>
          <b>{{ f.name }}</b>
          <small>{{ f.when }}</small>
        </div>
        <span class="earn">{{ f.earn }}</span>
      </article>
    </div>
  </AgShell>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Copy, Gift, Settings, Share2, ShoppingBag, Share } from 'lucide-vue-next'
import AgBrand from '@/components/account/AgBrand.vue'
import AgShell from '@/components/account/AgShell.vue'
import { fetchShareHtml } from '@/api/accountApi'
import { useZh } from '@/composables/zh'

const { tx } = useZh()
const router = useRouter()
const code = ref('HARBOR')
const link = ref('')
const msg = ref('')
const friends = ref<{ name: string; when: string; earn: string }[]>([])
const steps = computed(() => [
  { icon: Share, t: tx('分享邀请码', 'Share your code'), d: tx('把邀请码发给好友。', 'Send your referral code to friends.') },
  { icon: ShoppingBag, t: tx('好友下单', 'They shop'), d: tx('好友首单立减 10%。', 'Your friends get 10% off their first order.') },
  { icon: Gift, t: tx('双方得奖励', 'You both earn'), d: tx('好友下单后你获得 $5。', 'You get $5 credit when they purchase.') },
])

onMounted(async () => {
  try {
    const saved = localStorage.getItem('harbor_invite_code')
    if (saved) code.value = saved
  } catch { /* ignore */ }
  try {
    const html = await fetchShareHtml()
    const strong = html.match(/class=["']offer["'][\s\S]*?<strong>([\s\S]*?)<\/strong>/i)
    const href = html.match(/https?:\/\/[^"'<\s]+\/r\/[A-Za-z0-9_-]+/i)
    const raw = (strong?.[1] || '').replace(/<[^>]+>/g, '').trim()
    const fromHref = href?.[0]?.match(/\/r\/([A-Za-z0-9_-]+)/)
    if (raw) code.value = raw
    else if (fromHref) code.value = fromHref[1]
    link.value = href?.[0] || ''
  } catch { /* offline */ }
  link.value = link.value || `${location.origin}/referral?code=${encodeURIComponent(code.value)}`
})

async function copy() {
  try {
    await navigator.clipboard.writeText(link.value || code.value)
    msg.value = tx('邀请链接已复制', 'Invite link copied')
  } catch { msg.value = link.value || code.value }
}
async function share() {
  const data = { title: 'Harbor', text: tx(`用我的邀请码 ${code.value} 来 Harbor`, `Join Harbor with my code ${code.value}`), url: link.value }
  if (navigator.share) {
    try { await navigator.share(data); return } catch { /* fall through */ }
  }
  await copy()
}
</script>

<style scoped>
.brand { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.hero { display: grid; grid-template-columns: 1.2fr 0.8fr; gap: 8px; padding: 16px; background: #FFF6F3; overflow: hidden; }
.copy h1 { margin: 0; font-size: 26px; font-weight: 800; letter-spacing: -0.04em; white-space: pre-line; line-height: 1.1; }
.copy p { margin: 8px 0 0; font-size: 13px; color: #5C6570; line-height: 1.4; }
.bag { position: relative; min-height: 120px; }
.sack {
  position: absolute; right: 8px; bottom: 0; width: 92px; height: 100px; border-radius: 8px 8px 16px 16px;
  background: #F96141; color: #fff; display: grid; place-items: end center; padding-bottom: 12px; font-weight: 800;
}
.sack::before { content: ""; position: absolute; left: 18px; right: 18px; top: -10px; height: 18px; border: 3px solid #F96141; border-bottom: 0; border-radius: 12px 12px 0 0; }
.heart { position: absolute; right: 36px; top: 0; color: #F96141; font-size: 18px; }
.bag em { position: absolute; left: 0; top: 0; right: 96px; font-style: normal; color: #F96141; font-family: 'Segoe Script', cursive; font-size: 12px; white-space: pre-line; text-align: right; line-height: 1.15; }
.code { margin-top: 12px; padding: 14px; }
.kicker { font-size: 11px; letter-spacing: 0.08em; color: #8B919A; font-weight: 800; }
.box { margin-top: 8px; display: flex; align-items: center; justify-content: space-between; border: 1px solid #E7E1DA; border-radius: 12px; padding: 12px 14px; }
.box b { letter-spacing: 0.08em; font-size: 18px; }
.box button { border: 0; background: transparent; color: #1C2430; cursor: pointer; }
.code p { font-size: 13px; color: #5C6570; line-height: 1.45; }
.pair { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
h2 { margin: 22px 0 12px; font-size: 20px; font-weight: 800; }
.steps { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; text-align: center; }
.bubble { width: 54px; height: 54px; margin: 0 auto 8px; border-radius: 50%; background: #FFF1EC; color: #F96141; display: grid; place-items: center; position: relative; }
.bubble i { position: absolute; right: -2px; bottom: -2px; width: 18px; height: 18px; border-radius: 50%; background: #F96141; color: #fff; font-style: normal; font-size: 11px; display: grid; place-items: center; }
.steps b { display: block; font-size: 13px; }
.steps small { display: block; margin-top: 4px; color: #8B919A; font-size: 11px; line-height: 1.35; }
.friend { display: flex; align-items: center; gap: 10px; padding: 10px 0; border-bottom: 1px solid #F1ECE6; }
.av { width: 36px; height: 36px; border-radius: 50%; background: #FFF1EC; color: #F96141; display: grid; place-items: center; font-weight: 800; }
.friend div { flex: 1; }
.friend b { display: block; font-size: 14px; }
.friend small { color: #8B919A; font-size: 12px; }
.earn { color: #F96141; font-weight: 800; font-size: 13px; }
</style>
