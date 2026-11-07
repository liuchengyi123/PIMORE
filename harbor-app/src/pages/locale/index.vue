<template>
  <view class="page">
    <view class="status hb-status"><text>9:41</text><text>●●● 5G</text></view>
    <view class="nav">
      <text class="back" @click="goBack">‹</text>
      <text class="title">Country & currency</text>
    </view>
    <text class="hint">Language and currency follow the country you pick.</text>
    <view
      v-for="c in countries" :key="c.code"
      class="card" :class="{ on: selected === c.code }"
      @click="pick(c)"
    >
      <view class="left">
        <text class="nm">{{ c.name }}</text>
        <text class="meta">{{ c.langLabel }} · {{ c.currency }}</text>
      </view>
      <text class="radio">{{ selected === c.code ? '●' : '○' }}</text>
    </view>
    <view class="cta" @click="save">Save</view>
  </view>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { postLocale, openHarborWeb } from '@/api/accountApi'
import { useI18n } from '@/composables/i18n'
import type { LocaleId } from '@/i18n/locales'

const { t, setLocale, toApiLang } = useI18n()

type Country = { code: string; name: string; lang: LocaleId; langLabel: string; currency: string }
const countries: Country[] = [
  { code: 'US', name: 'United States', lang: 'en', langLabel: 'English', currency: 'USD' },
  { code: 'CN', name: '中国 mainland', lang: 'zh-Hans', langLabel: '简体中文', currency: 'CNY' },
  { code: 'JP', name: '日本', lang: 'en', langLabel: '日本語', currency: 'JPY' },
  { code: 'DE', name: 'Deutschland', lang: 'en', langLabel: 'Deutsch', currency: 'EUR' },
  { code: 'GB', name: 'United Kingdom', lang: 'en', langLabel: 'English', currency: 'GBP' },
  { code: 'CA', name: 'Canada', lang: 'en', langLabel: 'English', currency: 'CAD' },
]

const selected = ref('US')
const draft = ref<Country>(countries[0])

function pick(c: Country) {
  selected.value = c.code
  draft.value = c
}
async function save() {
  // language follows country
  try { setLocale(draft.value.lang) } catch { /* if locale unsupported, keep */ }
  try {
    const res = await postLocale(toApiLang(draft.value.lang as any), draft.value.currency)
    uni.showToast({ title: res.statusCode < 400 ? t('locale_saved_toast') : t('common_open_harbor'), icon: 'none' })
    if (res.statusCode >= 400) openHarborWeb('/account', t('locale_title'))
  } catch {
    uni.showToast({ title: t('locale_saved_toast'), icon: 'none' })
  }
}
function goBack() { uni.navigateBack({ fail: () => uni.reLaunch({ url: '/pages/me/index' }) }) }
onShow(() => uni.setNavigationBarTitle({ title: t('locale_title') }))
</script>
<style scoped>
.page { min-height: 100vh; background: #F7F4EF; color: #0F2744; padding: 0 16px 40px; padding-top: env(safe-area-inset-top); }
.status { display: flex; justify-content: space-between; padding: 14px 12px 0; font-size: 12px; font-weight: 700; }
.nav { display: flex; align-items: center; gap: 10px; padding: 8px 0 12px; }
.back { font-size: 18px; font-weight: 700; }
.title { font-size: 17px; font-weight: 700; }
.hint { display: block; font-size: 11px; color: #6B7280; margin-bottom: 12px; }
.card {
  display: flex; justify-content: space-between; align-items: center;
  background: #fff; border: 1px solid #E8E4DC; border-radius: 16px; padding: 14px; margin-bottom: 8px;
}
.card.on { border: 2px solid #0F2744; }
.nm { display: block; font-size: 16px; font-weight: 700; }
.meta { display: block; margin-top: 2px; font-size: 11px; color: #6B7280; }
.radio { font-size: 16px; color: #0F2744; }
.cta { margin-top: 12px; height: 41px; border-radius: 12px; background: #0F2744; color: #fff; font-weight: 600; display: flex; align-items: center; justify-content: center; }
</style>
