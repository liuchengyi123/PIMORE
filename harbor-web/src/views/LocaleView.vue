<template>
  <div class="page">
    <header class="head">
      <button type="button" class="back" @click="$router.back()" aria-label="back">‹</button>
      <h1 class="title">Country & currency</h1>
    </header>
    <p class="hint">Language and currency follow the country you pick.</p>
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
    <button type="button" class="cta" :disabled="busy" @click="save">{{ busy ? '…' : 'Save' }}</button>
  </div>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { defaultCountry } from '@/api/countryLocale'
import { useI18n } from '@/composables/i18n'

const { setCountry } = useI18n()
const busy = ref(false)
const msg = ref('')
const country = ref(defaultCountry() || 'US')

const countries = [
  { code: 'US', name: 'United States', langLabel: 'English', currency: 'USD' },
  { code: 'CN', name: '中国 mainland', langLabel: '简体中文', currency: 'CNY' },
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
    msg.value = 'Saved'
  } catch {
    msg.value = 'Saved locally'
  } finally {
    busy.value = false
  }
}
</script>
<style scoped>
.page { min-height: 100vh; background: #F7F4EF; color: #0F2744; padding: 12px 16px 40px; padding-top: calc(12px + env(safe-area-inset-top)); }
.head { display: flex; gap: 10px; align-items: center; margin-bottom: 8px; }
.back { border: 0; background: transparent; font-size: 22px; font-weight: 700; cursor: pointer; color: #0F2744; }
.title { font-size: 17px; font-weight: 700; margin: 0; }
.hint { font-size: 11px; color: #6B7280; margin: 0 0 12px; }
.card {
  width: 100%; display: flex; justify-content: space-between; align-items: center; text-align: left;
  background: #fff; border: 1px solid #E8E4DC; border-radius: 16px; padding: 14px; margin-bottom: 8px;
  cursor: pointer; color: inherit;
}
.card.on { border: 2px solid #0F2744; }
.left { display: flex; flex-direction: column; gap: 2px; }
.nm { font-size: 16px; font-weight: 700; }
.meta { font-size: 11px; color: #6B7280; }
.radio { font-size: 16px; color: #0F2744; }
.msg { font-size: 12px; color: #0E7490; margin: 8px 0; }
.cta {
  width: 100%; height: 41px; border: 0; border-radius: 12px; background: #0F2744; color: #fff;
  font-size: 14px; font-weight: 600; cursor: pointer; margin-top: 8px;
}
.cta:disabled { opacity: 0.7; }
</style>
