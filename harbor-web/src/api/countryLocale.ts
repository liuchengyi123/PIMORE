/** Country → language / currency. Language follows country (no separate zh picker). */
export const COUNTRY_STORAGE_KEY = 'harbor_app_country'
export const CURRENCY_STORAGE_KEY = 'harbor_app_currency'

export type UiLang = 'zh' | 'zh-Hant' | 'en' | 'de' | 'fr' | 'es' | 'pt' | 'ja'

/** Storefront countries shown in locale / shipping pickers. */
export const STORE_COUNTRIES = [
  'US', 'CN', 'TW', 'HK', 'GB', 'CA', 'DE', 'FR', 'ES', 'PT', 'BR', 'MX', 'JP',
] as const

export type StoreCountry = (typeof STORE_COUNTRIES)[number]

const ZH_HANS = new Set(['CN', 'SG'])
const ZH_HANT = new Set(['TW', 'HK', 'MO'])
const DE = new Set(['DE', 'AT'])
const FR = new Set(['FR'])
const ES = new Set(['ES', 'MX', 'AR', 'CO', 'CL', 'PE'])
const PT = new Set(['PT', 'BR'])
const JA = new Set(['JP'])

export function langForCountry(country: string): UiLang {
  const code = String(country || 'US').toUpperCase().slice(0, 2)
  if (ZH_HANT.has(code)) return 'zh-Hant'
  if (ZH_HANS.has(code)) return 'zh'
  if (DE.has(code)) return 'de'
  if (FR.has(code)) return 'fr'
  if (ES.has(code)) return 'es'
  if (PT.has(code)) return 'pt'
  if (JA.has(code)) return 'ja'
  return 'en'
}

/** H5 chrome: zh (简体) / zh-Hant (繁體) / en for everything else. */
export function h5LangForCountry(country: string): 'zh' | 'zh-Hant' | 'en' {
  const lang = langForCountry(country)
  if (lang === 'zh' || lang === 'zh-Hant') return lang
  return 'en'
}

export function currencyForCountry(country: string): string {
  const code = String(country || 'US').toUpperCase().slice(0, 2)
  if (code === 'GB') return 'GBP'
  if (code === 'JP') return 'JPY'
  if (code === 'BR') return 'BRL'
  if (code === 'MX') return 'MXN'
  if (code === 'CA') return 'CAD'
  if (code === 'TW') return 'TWD'
  if (code === 'HK') return 'HKD'
  if (code === 'CN' || code === 'MO') return 'CNY'
  if (['AT','BE','HR','CY','EE','FI','FR','DE','GR','IE','IT','LV','LT','LU','MT','NL','PT','SK','SI','ES'].includes(code)) {
    return 'EUR'
  }
  return 'USD'
}

export function currencyMark(country: string): string {
  const cur = currencyForCountry(country)
  const marks: Record<string, string> = {
    USD: '$', CNY: '¥', TWD: 'NT$', HKD: 'HK$', GBP: '£', CAD: 'CA$',
    EUR: '€', BRL: 'R$', MXN: 'MX$', JPY: '円',
  }
  return marks[cur] || cur
}

export function readStoredCountry(): string {
  try {
    const raw = String(localStorage.getItem(COUNTRY_STORAGE_KEY) || '').toUpperCase().slice(0, 2)
    if (raw && (STORE_COUNTRIES as readonly string[]).includes(raw)) return raw
  } catch { /* ignore */ }
  return ''
}

export function defaultCountry(): string {
  const stored = readStoredCountry()
  if (stored) return stored
  try {
    const nav = (navigator.language || '').toLowerCase().replace('_', '-')
    // Region-aware Chinese browsers
    if (nav.startsWith('zh-tw')) return 'TW'
    if (nav.startsWith('zh-hk') || nav.startsWith('zh-mo')) return 'HK'
    if (nav.startsWith('zh')) return 'CN'
  } catch { /* ignore */ }
  return 'US'
}

export function persistCountry(country: string): { country: string; lang: UiLang; h5Lang: 'zh' | 'zh-Hant' | 'en'; currency: string } {
  const code = String(country || 'US').toUpperCase().slice(0, 2)
  const picked = (STORE_COUNTRIES as readonly string[]).includes(code) ? code : 'US'
  const lang = langForCountry(picked)
  const h5Lang = h5LangForCountry(picked)
  const currency = currencyForCountry(picked)
  try {
    localStorage.setItem(COUNTRY_STORAGE_KEY, picked)
    localStorage.setItem(CURRENCY_STORAGE_KEY, currency)
  } catch { /* ignore */ }
  try {
    const maxAge = 31536000
    document.cookie = `locale=${encodeURIComponent(picked)}; path=/; max-age=${maxAge}; samesite=lax`
    document.cookie = `harbor_hl=${encodeURIComponent(lang)}; path=/; max-age=${maxAge}; samesite=lax`
  } catch { /* ignore */ }
  return { country: picked, lang, h5Lang, currency }
}
