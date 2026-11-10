<template>
  <div class="page">
    <header class="head">
      <button type="button" class="back" @click="$router.back()" aria-label="back">‹</button>
      <h1 class="title">{{ zh ? '国家与货币' : 'Country & currency' }}</h1>
    </header>
    <p class="hint">{{ zh ? '语言和货币跟着所选国家走。' : 'Language and currency follow the country you pick.' }}</p>
    <button
      v-for="c in countries"
      :key="c.code"
      type="button"
      class="card"
      :class="{ on: country === c.code }"
      @click="pick(c.code)"
    >
      <span class="left">
        <span class="nm">{{ c.name }}</span>
        <span class="meta">{{ c.langLabel }} · {{ c.currency }}</span>
      </span>
      <span class="radio">{{ country === c.code ? '●' : '○' }}</span>
    </button>
    <p v-if="msg" class="msg">{{ msg }}</p>
    <button type="button" class="cta" :disabled="busy" @click="save">{{ busy ? '…' : (zh ? '保存' : 'Save') }}</button>
  </div>
</template>
<script setup lang="ts">
import { computed, ref } from 'vue'
import { defaultCountry } from '@/api/countryLocale'
import { useI18n } from '@/composables/i18n'

const { setCountry, lang } = useI18n()
const zh = computed(() => String(lang.value).startsWith('zh'))
const busy = ref(false)
const msg = ref('')
const country = ref(defaultCountry() || 'US')

const countries = [
  { code: 'US', name: 'United States', langLabel: 'English', currency: 'USD' },
  { code: 'CN', name: '中国', langLabel: '简体中文', currency: 'CNY' },
  { code: 'JP', name: '日本', langLabel: '日本語', currency: 'JPY' },
  { code: 'DE', name: 'Deutschland', langLabel: 'Deutsch', currency: 'EUR' },
  { code: 'GB', name: 'United Kingdom', langLabel: 'English', currency: 'GBP' },
  { code: 'CA', name: 'Canada', langLabel: 'English', currency: 'CAD' },
  { code: 'TW', name: '台灣', langLabel: '繁體中文', currency: 'TWD' },
  { code: 'HK', name: '香港', langLabel: '繁體中文', currency: 'HKD' },
]

function pick(code: string) {
  country.value = code
  try { setCountry(code) } catch { /* */ }
}

async function save() {
  busy.value = true
  msg.value = ''
  try {
    setCountry(country.value)
    msg.value = zh.value ? '已保存' : 'Saved'
  } catch {
    msg.value = zh.value ? '已保存在本机' : 'Saved locally'
  } finally {
    busy.value = false
  }
}
</script>
<style scoped>
.page { min-height: 100vh; background: var(--hb-page); color: var(--hb-ink); padding: 10px 16px 32px; padding-top: calc(10px + env(safe-area-inset-top)); }
.head { display: flex; gap: 8px; align-items: center; margin-bottom: 6px; }
.back { border: 0; background: transparent; font-size: 22px; font-weight: 700; cursor: pointer; color: var(--hb-ink); padding: 0; }
.title { font-size: 20px; font-weight: 800; letter-spacing: -0.03em; margin: 0; }
.hint { font-size: 12px; color: var(--hb-muted); margin: 0 0 8px; line-height: 1.35; }
.card {
  width: 100%; display: flex; justify-content: space-between; align-items: center; text-align: left;
  background: var(--hb-surface); border: 1px solid var(--hb-line); border-radius: 14px; padding: 8px 12px; margin-bottom: 6px;
  min-height: 44px; cursor: pointer; color: inherit;
}
.card.on { border-color: var(--hb-primary); background: var(--hb-primary-soft); }
.card.on .radio { color: var(--hb-primary); }
.left { display: flex; flex-direction: column; gap: 1px; }
.nm { font-size: 14px; font-weight: 700; line-height: 1.25; }
.meta { font-size: 11px; color: var(--hb-muted); }
.radio { font-size: 16px; color: #C5C9D1; }
.msg { font-size: 12px; color: var(--hb-primary); margin: 6px 0; }
.cta {
  width: 100%; height: 40px; border: 0; border-radius: 999px; background: var(--hb-primary); color: var(--hb-on-primary);
  font-size: 14px; font-weight: 700; cursor: pointer; margin-top: 6px;
}
.cta:disabled { opacity: 0.7; }
</style>
