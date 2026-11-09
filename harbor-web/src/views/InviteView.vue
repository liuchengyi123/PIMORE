<template>
  <div class="page">
    <header class="head">
      <button type="button" class="back" @click="$router.back()" aria-label="back">‹</button>
      <h1 class="title">Invite friends</h1>
    </header>
    <section class="hero">
      <div class="eyebrow">Share Harbor</div>
      <div class="hl">Invite friends, earn rewards</div>
      <div class="code-box">Your code <strong>{{ code }}</strong></div>
    </section>
    <button type="button" class="primary" @click="copy">Copy invite link</button>
    <button type="button" class="secondary" @click="share">Share</button>
    <section class="how">
      <div class="h">How it works</div>
      <ol>
        <li>Share your link</li>
        <li>Friend places an order</li>
        <li>Reward lands in Balance</li>
      </ol>
    </section>
    <p v-if="msg" class="msg">{{ msg }}</p>
  </div>
</template>
<script setup lang="ts">
import { onMounted, ref } from 'vue'
const code = ref('HARBOR')
const link = ref('')
const msg = ref('')
onMounted(() => {
  try {
    const u = localStorage.getItem('harbor_invite_code')
    if (u) code.value = u
  } catch { /* */ }
  link.value = `${location.origin}/?ref=${encodeURIComponent(code.value)}`
})
async function copy() {
  try {
    await navigator.clipboard.writeText(link.value || code.value)
    msg.value = 'Copied'
  } catch { msg.value = link.value || code.value }
}
async function share() {
  const data = { title: 'Harbor', text: 'Shop Harbor with me', url: link.value }
  if ((navigator as any).share) {
    try { await (navigator as any).share(data); return } catch { /* */ }
  }
  await copy()
}
</script>
<style scoped>
.page { min-height: 100vh; background: #F4F7FB; color: #1B2B4A; padding: 12px 16px 40px; padding-top: calc(12px + env(safe-area-inset-top)); }
.head { display: flex; gap: 10px; align-items: center; margin-bottom: 12px; }
.back { border: 0; background: transparent; font-size: 22px; font-weight: 700; cursor: pointer; color: #1B2B4A; }
.title { font-size: 17px; font-weight: 700; margin: 0; }
.hero {
  border-radius: 18px; padding: 20px; color: #fff; margin-bottom: 14px;
  background-image: linear-gradient(161deg, #1B2B4A 4%, #FF6B4A 96%);
}
.eyebrow { font-size: 13px; opacity: 0.85; }
.hl { margin-top: 6px; font-size: 22px; font-weight: 800; line-height: 1.25; }
.code-box {
  margin-top: 14px; background: rgba(255,255,255,0.12); border-radius: 12px; padding: 12px;
  font-size: 13px;
}
.code-box strong { letter-spacing: 0.08em; }
.primary {
  width: 100%; height: 41px; border: 0; border-radius: 12px; background: #1B2B4A; color: #fff;
  font-size: 14px; font-weight: 600; cursor: pointer; margin-bottom: 10px;
}
.secondary {
  width: 100%; height: 43px; border-radius: 12px; border: 1px solid #E7ECF3; background: #fff;
  color: #1B2B4A; font-size: 14px; font-weight: 600; cursor: pointer;
}
.how {
  margin-top: 14px; background: #fff; border: 1px solid #E7ECF3; border-radius: 16px; padding: 14px;
}
.how .h { font-size: 14px; font-weight: 700; }
.how ol { margin: 8px 0 0; padding-left: 18px; color: #6B7280; font-size: 11px; line-height: 1.6; }
.msg { margin-top: 10px; font-size: 12px; color: #FF6B4A; }
</style>
