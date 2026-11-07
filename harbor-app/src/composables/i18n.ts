import { computed, reactive } from 'vue'
import {
  DEFAULT_LOCALE,
  LOCALE_OPTIONS,
  LOCALE_STORAGE_KEY,
  isLocaleId,
  localeMeta,
  toApiLang,
  type LocaleId,
} from '@/i18n/locales'
import { messages, type MessageKey } from '@/i18n/messages'
import { clearProductCache } from '@/api/products'

type Params = Record<string, string | number>

const state = reactive({
  locale: DEFAULT_LOCALE as LocaleId,
  ready: false,
})

function readStored(): LocaleId {
  try {
    const raw = uni.getStorageSync(LOCALE_STORAGE_KEY)
    if (isLocaleId(raw)) return raw
  } catch {
    /* ignore */
  }
  return DEFAULT_LOCALE
}

function applyDocumentDir(id: LocaleId) {
  try {
    const meta = localeMeta(id)
    if (typeof document !== 'undefined' && document.documentElement) {
      document.documentElement.setAttribute('dir', meta.dir)
      document.documentElement.setAttribute(
        'lang',
        id === 'zh-Hans' ? 'zh-CN' : id === 'zh-Hant' ? 'zh-TW' : id,
      )
    }
  } catch {
    /* ignore */
  }
}

export function initI18n() {
  if (state.ready) return state.locale
  const id = readStored()
  state.locale = id
  state.ready = true
  applyDocumentDir(id)
  return id
}

export function setLocale(id: LocaleId) {
  if (!isLocaleId(id)) return
  const prev = state.locale
  state.locale = id
  try {
    uni.setStorageSync(LOCALE_STORAGE_KEY, id)
  } catch {
    /* ignore */
  }
  applyDocumentDir(id)
  if (prev !== id) {
    try {
      clearProductCache()
    } catch {
      /* ignore */
    }
  }
}

export function t(key: MessageKey | string, params?: Params): string {
  const loc = state.locale
  const dict = messages[loc] || messages.en
  let s = (dict as Record<string, string>)[key] ?? messages.en[key as MessageKey] ?? key
  if (params) {
    Object.keys(params).forEach((k) => {
      s = s.split('{' + k + '}').join(String(params[k]))
    })
  }
  return s
}

export function useI18n() {
  initI18n()
  const locale = computed(() => state.locale)
  const localeNative = computed(() => localeMeta(state.locale).native)
  const isRtl = computed(() => localeMeta(state.locale).dir === 'rtl')
  const options = LOCALE_OPTIONS

  function catLabel(id: string) {
    if (!id || id === 'All' || id === 'all') return t('cat_all')
    const key = ('cat_' + id) as MessageKey
    const translated = t(key)
    return translated === key ? id : translated
  }

  function subcatLabel(id: string) {
    if (!id || id === 'All' || id === 'all') return t('cat_all')
    const key = ('sub_' + id) as MessageKey
    const translated = t(key)
    return translated === key ? id : translated
  }

  return {
    t,
    locale,
    localeNative,
    isRtl,
    options,
    setLocale,
    toApiLang,
    localeMeta,
    catLabel,
    subcatLabel,
  }
}

// ensure storage is read on first import in app entry
initI18n()
