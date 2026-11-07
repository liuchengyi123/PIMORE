<template>
  <view class="page">
    <view class="status hb-status"><text>9:41</text><text>●●● 5G</text></view>
    <view class="nav">
      <text class="back" @click="goBack">‹</text>
      <text class="title">Invite friends</text>
    </view>
    <view class="hero">
      <text class="hl">Earn rewards</text>
      <view class="code-box"><text>{{ codeLabel }}</text></view>
    </view>
    <view class="cta" @click="copy">Copy invite link</view>
    <view class="cta soft" @click="openSite">Share</view>
  </view>
</template>
<script setup lang="ts">
import { useI18n } from '@/composables/i18n'
import { computed, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { fetchShareHtml, openHarborWeb, LIVE_ORIGIN } from '@/api/accountApi'
const { t } = useI18n()
const shareLink = ref('')
const offers = ref<string[]>([])
const codeLabel = computed(() => {
  const s = shareLink.value || ''
  const m = s.match(/HARBOR[-_A-Z0-9]+/i) || s.match(/\/r\/([A-Za-z0-9_-]+)/)
  if (m) return m[0].startsWith('HARBOR') ? m[0] : `HARBOR-${m[1] || m[0]}`
  return s || 'HARBOR'
})
async function refresh() {
  try {
    const html = await fetchShareHtml()
    const strong = html.match(/class=["']offer["'][\s\S]*?<strong>([\s\S]*?)<\/strong>/i)
    const href = html.match(/https?:\/\/[^"'<\s]+\/r\/[A-Za-z0-9_-]+/i)
    shareLink.value = (strong?.[1] || href?.[0] || '').replace(/<[^>]+>/g, '').trim()
    const found: string[] = []
    const re = /class="nm"[^>]*>([\s\S]*?)<\/div>/gi
    let m: RegExpExecArray | null
    while ((m = re.exec(html))) {
      const x = m[1].replace(/<[^>]+>/g, '').trim()
      if (x) found.push(x)
    }
    offers.value = found.slice(0, 6)
  } catch {
    shareLink.value = LIVE_ORIGIN + '/share'
  }
}
function copy() {
  const text = shareLink.value || LIVE_ORIGIN + '/share'
  uni.setClipboardData({ data: text, success: () => uni.showToast({ title: t('invite_copied'), icon: 'none' }) })
}
function openSite() { openHarborWeb('/share', 'Share') }
function goBack() { uni.navigateBack({ fail: () => uni.reLaunch({ url: '/pages/me/index' }) }) }
onShow(() => refresh())
</script>
<style scoped>
.page { min-height: 100vh; background: #F7F4EF; color: #0F2744; padding: 0 16px 40px; padding-top: env(safe-area-inset-top); }
.status { display: flex; justify-content: space-between; padding: 14px 12px 0; font-size: 12px; font-weight: 700; }
.nav { display: flex; align-items: center; gap: 10px; padding: 8px 0 12px; }
.back { font-size: 18px; font-weight: 700; }
.title { font-size: 17px; font-weight: 700; }
.hero {
  margin-top: 4px; border-radius: 18px; padding: 20px; color: #fff;
  background-image: linear-gradient(165deg, #0F2744 4%, #0E7490 96%);
}
.hl { display: block; font-size: 20px; font-weight: 800; }
.code-box { margin-top: 10px; background: rgba(255,255,255,0.12); border-radius: 10px; padding: 10px; }
.code-box text { font-size: 13px; color: #fff; }
.cta { margin-top: 14px; height: 41px; border-radius: 12px; background: #0F2744; color: #fff; font-size: 14px; font-weight: 600; display: flex; align-items: center; justify-content: center; }
.cta.soft { background: #fff; color: #0F2744; border: 1px solid #E8E4DC; }
</style>
