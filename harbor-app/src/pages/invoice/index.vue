<template>
  <view class="page">
    <view class="head">
      <view class="back" @click="goBack">←</view>
      <view>
        <text class="title">{{ t('invoice_title') }}</text>
        <text class="sub">{{ orderId }}</text>
      </view>
    </view>
    <view v-if="loading" class="state">{{ t('nav_loading') }}</view>
    <view v-else class="card">
      <text class="line" v-for="(l, i) in lines" :key="i">{{ l }}</text>
      <view class="btn" @click="openSite">{{ t('invoice_open') }}</view>
    </view>
  </view>
</template>
<script setup lang="ts">
import { useI18n } from '@/composables/i18n'
import { ref } from 'vue'
import { onLoad, onShow } from '@dcloudio/uni-app'
import { fetchInvoiceHtml, openHarborWeb } from '@/api/accountApi'
const { t } = useI18n()
const orderId = ref('')
const lines = ref<string[]>([])
const loading = ref(false)
async function load() {
  if (!orderId.value) return
  loading.value = true
  try {
    const html = await fetchInvoiceHtml(orderId.value)
    const out: string[] = []
    const h1 = html.match(/<h1>([\s\S]*?)<\/h1>/i)
    if (h1) out.push(h1[1].replace(/<[^>]+>/g, ' ').trim())
    for (const m of html.matchAll(/<p>([\s\S]*?)<\/p>/gi)) {
      const t = m[1].replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim()
      if (t) out.push(t)
    }
    for (const m of html.matchAll(/<tr>\s*<th>([\s\S]*?)<\/th>\s*<td>([\s\S]*?)<\/td>/gi)) {
      out.push(`${m[1].replace(/<[^>]+>/g, '').trim()} × ${m[2].replace(/<[^>]+>/g, '').trim()}`)
    }
    lines.value = out.slice(0, 20)
  } finally { loading.value = false }
}
function openSite() { openHarborWeb('/orders/' + encodeURIComponent(orderId.value) + '/invoice', 'Invoice') }
function goBack() { uni.navigateBack({ fail: () => uni.navigateTo({ url: '/pages/order-detail/index?id=' + encodeURIComponent(orderId.value) }) }) }
onLoad((q) => { orderId.value = q?.id ? decodeURIComponent(q.id) : ''; load() })

onShow(() => {
  uni.setNavigationBarTitle({ title: t('invoice_title') })
})
</script>
<style lang="scss" scoped>
@import '@/styles/theme.scss';
.page { min-height: 100vh; background: $hb-paper; padding: 12px 16px 40px; padding-top: calc(12px + env(safe-area-inset-top)); }
.head { display: flex; gap: 12px; align-items: center; margin-bottom: 16px; }
.back { width: 36px; height: 36px; border-radius: 12px; background: $hb-white; text-align: center; line-height: 36px; box-shadow: $hb-shadow-soft; }
.title { display: block; font-size: 24px; font-weight: 720; }
.sub { display: block; font-size: 12px; color: $hb-muted; margin-top: 2px; word-break: break-all; }
.card { background: $hb-white; border-radius: 20px; padding: 16px; box-shadow: $hb-shadow-soft; }
.line { display: block; font-size: 13px; color: $hb-ink; margin-bottom: 8px; line-height: 1.4; }
.btn { margin-top: 12px; text-align: center; padding: 14px; border-radius: 16px; background: $hb-forest; color: #fff; font-weight: 720; }
.state { text-align: center; color: $hb-muted; padding: 36px; }
</style>
