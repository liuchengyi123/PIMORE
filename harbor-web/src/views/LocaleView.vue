<template>
  <AgShell tabs="me">
    <header class="top ag-top ag-pad">
      <AgBrand />
      <div class="ag-tagline">{{ tx('每天的家 · $1–$10', 'EVERYDAY HOME · $1 – $10') }}</div>
    </header>
    <div class="title ag-pad">
      <button type="button" class="ag-back ink" @click="router.back()" :aria-label="tx('返回', 'Back')"><ChevronLeft :size="24" /></button>
      <div>
        <h1 class="ag-h1">{{ tx('国家 / 地区与语言', 'Locale / Region & Language') }}</h1>
        <p class="ag-sub">{{ tx('设置国家、货币和语言，购物更顺手。', 'Set your country, currency and language for a better shopping experience.') }}</p>
      </div>
    </div>

    <div class="ag-pad">
      <button type="button" class="row ag-card" @click="open = open === 'c' ? '' : 'c'">
        <span class="flag">{{ flag(country) }}</span>
        <span class="mid"><small>{{ tx('国家 / 地区', 'Country / Region') }}</small><b>{{ countryName }}</b></span>
        <ChevronRight :size="18" color="#C5C0BA" />
      </button>
      <div v-if="open === 'c'" class="pick">
        <button v-for="c in options" :key="c.code" type="button" :class="{ on: c.code === country }" @click="country = c.code; open = ''">
          <span>{{ c.flag }} {{ c.zh }}</span><span>{{ c.en }}</span>
        </button>
      </div>

      <button type="button" class="row ag-card" @click="open = open === 'm' ? '' : 'm'">
        <span class="ag-icon"><CircleDollarSign :size="18" /></span>
        <span class="mid"><small>{{ tx('货币', 'Currency') }}</small><b>{{ currency }} ({{ currencyName }})</b></span>
        <ChevronRight :size="18" color="#C5C0BA" />
      </button>
      <p v-if="open === 'm'" class="ag-note hint">{{ tx('货币跟着国家走。换国家就会换货币。', 'Currency follows the country you pick.') }}</p>

      <button type="button" class="row ag-card" @click="open = open === 'l' ? '' : 'l'">
        <span class="ag-icon"><MessageCircle :size="18" /></span>
        <span class="mid">
          <small>{{ tx('语言', 'Language') }}</small>
          <b>{{ langLabel }}</b>
          <em>{{ tx('（随你的地区自动选择）', '(Auto by your region)') }}</em>
        </span>
        <ChevronRight :size="18" color="#C5C0BA" />
      </button>

      <p v-if="msg" class="ag-toast">{{ msg }}</p>
      <button type="button" class="ag-cta" :disabled="busy" @click="save">{{ busy ? '…' : tx('保存偏好', 'Save preferences') }}</button>
      <p class="foot"><Info :size="14" /> {{ tx('你可以随时在账户里修改这些设置。', 'You can change these settings anytime in your account.') }}</p>
    </div>
  </AgShell>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ChevronLeft, ChevronRight, CircleDollarSign, Info, MessageCircle } from 'lucide-vue-next'
import AgBrand from '@/components/account/AgBrand.vue'
import AgShell from '@/components/account/AgShell.vue'
import { currencyForCountry, defaultCountry, langForCountry } from '@/api/countryLocale'
import { postLocale } from '@/api/accountApi'
import { useI18n } from '@/composables/i18n'
import { useZh } from '@/composables/zh'

const { tx, zh } = useZh()
const { setCountry } = useI18n()
const router = useRouter()
const country = ref(defaultCountry() || 'CN')
const open = ref<'' | 'c' | 'm' | 'l'>('')
const busy = ref(false)
const msg = ref('')

const options = [
  { code: 'CN', zh: '中国', en: 'China', flag: '🇨🇳', lang: '简体中文' },
  { code: 'US', zh: '美国', en: 'United States', flag: '🇺🇸', lang: 'English' },
  { code: 'JP', zh: '日本', en: 'Japan', flag: '🇯🇵', lang: '日本語' },
  { code: 'GB', zh: '英国', en: 'United Kingdom', flag: '🇬🇧', lang: 'English' },
  { code: 'DE', zh: '德国', en: 'Germany', flag: '🇩🇪', lang: 'Deutsch' },
  { code: 'CA', zh: '加拿大', en: 'Canada', flag: '🇨🇦', lang: 'English' },
  { code: 'TW', zh: '台湾', en: 'Taiwan', flag: '🇹🇼', lang: '繁體中文' },
  { code: 'HK', zh: '香港', en: 'Hong Kong', flag: '🇭🇰', lang: '繁體中文' },
]
const current = computed(() => options.find((c) => c.code === country.value) || options[0])
const countryName = computed(() => zh.value ? current.value.zh : current.value.en)
const currency = computed(() => currencyForCountry(country.value))
const currencyName = computed(() => ({ USD: 'US Dollar', CNY: zh.value ? '人民币' : 'Yuan', JPY: zh.value ? '日元' : 'Yen', GBP: 'Pound', EUR: 'Euro', CAD: 'Canadian Dollar', TWD: zh.value ? '新台币' : 'Taiwan Dollar', HKD: zh.value ? '港币' : 'Hong Kong Dollar' }[currency.value] || currency.value))
const langLabel = computed(() => current.value.lang)
function flag(code: string) { return options.find((c) => c.code === code)?.flag || '🌐' }

async function save() {
  busy.value = true
  msg.value = ''
  try {
    setCountry(country.value)
    await postLocale(langForCountry(country.value), currency.value, country.value)
    msg.value = tx('已保存', 'Saved')
  } catch {
    msg.value = tx('已保存在本机', 'Saved on this device')
  } finally { busy.value = false }
}
</script>

<style scoped>
.top { margin-bottom: 8px; }
.title { display: grid; grid-template-columns: 32px 1fr; gap: 4px; align-items: start; margin-bottom: 14px; }
.row { width: 100%; display: flex; align-items: center; gap: 12px; padding: 14px; margin-bottom: 10px; text-align: left; cursor: pointer; color: inherit; border: 1px solid #F1ECE6; }
.flag { font-size: 28px; width: 42px; text-align: center; }
.mid { flex: 1; }
.mid small, .mid em { display: block; color: #8B919A; font-size: 12px; font-style: normal; }
.mid b { display: block; font-size: 16px; margin-top: 2px; }
.pick { background: #fff; border-radius: 16px; overflow: hidden; margin: -4px 0 10px; border: 1px solid #F1ECE6; }
.pick button { width: 100%; display: flex; justify-content: space-between; padding: 12px 14px; border: 0; border-bottom: 1px solid #F6F1EC; background: #fff; cursor: pointer; font-size: 14px; }
.pick button.on { color: #F96141; font-weight: 800; }
.hint { margin: -4px 4px 10px; }
.ag-cta { margin-top: 8px; }
.foot { display: flex; gap: 6px; align-items: flex-start; color: #8B919A; font-size: 12.5px; }
</style>
