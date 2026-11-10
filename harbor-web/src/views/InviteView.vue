<template>
  <div class="page">
    <header class="head">
      <button type="button" class="back" @click="$router.back()" aria-label="back">‹</button>
      <h1 class="title">{{ zh ? '邀请好友' : 'Invite friends' }}</h1>
    </header>
    <section class="hero">
      <div class="eyebrow">{{ zh ? '分享 Harbor' : 'Share Harbor' }}</div>
      <div class="hl">{{ zh ? '邀请好友，奖励进余额' : 'Invite friends, earn rewards' }}</div>
      <div class="code-box">{{ zh ? '你的邀请码' : 'Your code' }} <strong>{{ code }}</strong></div>
    </section>
    <button type="button" class="primary" @click="copy">{{ zh ? '复制邀请链接' : 'Copy invite link' }}</button>
    <button type="button" class="secondary" @click="share">{{ zh ? '分享' : 'Share' }}</button>
    <section class="how">
      <div class="h">{{ zh ? '怎么用' : 'How it works' }}</div>
      <ol>
        <li>{{ zh ? '分享你的链接' : 'Share your link' }}</li>
        <li>{{ zh ? '好友完成一笔订单' : 'Friend places an order' }}</li>
        <li>{{ zh ? '奖励进入余额' : 'Reward lands in Balance' }}</li>
      </ol>
    </section>
    <p v-if="msg" class="msg">{{ msg }}</p>
  </div>
</template>
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from '@/composables/i18n'
const { lang } = useI18n()
const zh = computed(() => String(lang.value).startsWith('zh'))
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
    msg.value = zh.value ? '已复制' : 'Copied'
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
.page { min-height: 100vh; background: var(--hb-page); color: var(--hb-ink); padding: 12px 16px 40px; padding-top: calc(12px + env(safe-area-inset-top)); }
.head { display: flex; gap: 10px; align-items: center; margin-bottom: 12px; }
.back { border: 0; background: transparent; font-size: 22px; font-weight: 700; cursor: pointer; color: var(--hb-ink); }
.title { font-size: 22px; font-weight: 800; letter-spacing: -0.03em; margin: 0; }
.hero {
  border-radius: 18px; padding: 20px; color: var(--hb-on-primary); margin-bottom: 14px;
  background-image: linear-gradient(161deg, var(--hb-primary) 4%, var(--hb-primary-pressed) 96%);
}
.eyebrow { font-size: 13px; opacity: 0.85; }
.hl { margin-top: 6px; font-size: 22px; font-weight: 800; line-height: 1.25; }
.code-box {
  margin-top: 14px; background: rgba(255,255,255,0.12); border-radius: 12px; padding: 12px;
  font-size: 13px;
}
.code-box strong { letter-spacing: 0.08em; }
.primary {
  width: 100%; height: 46px; border: 0; border-radius: 999px; background: var(--hb-primary); color: var(--hb-on-primary);
  font-size: 14px; font-weight: 600; cursor: pointer; margin-bottom: 10px;
}
.secondary {
  width: 100%; height: 46px; border-radius: 999px; border: 1px solid var(--hb-line); background: var(--hb-surface);
  color: var(--hb-ink); font-size: 14px; font-weight: 600; cursor: pointer;
}
.how {
  margin-top: 14px; background: var(--hb-surface); border: 1px solid var(--hb-line); border-radius: 16px; padding: 14px;
}
.how .h { font-size: 14px; font-weight: 700; }
.how ol { margin: 8px 0 0; padding-left: 18px; color: var(--hb-muted); font-size: 11px; line-height: 1.6; }
.msg { margin-top: 10px; font-size: 12px; color: #0E7490; }
</style>
