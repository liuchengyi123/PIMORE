/**
 * Catalog / shop language + country hints.
 * Language follows selected country (CN → zh; TW/HK → zh-Hant; US → en).
 */
import {
  COUNTRY_STORAGE_KEY,
  defaultCountry,
  h5LangForCountry,
  langForCountry,
  persistCountry,
  readStoredCountry,
} from './countryLocale'

export const LOCALE_STORAGE_KEY = 'harbor_app_locale'

export function catalogLangHint(): '' | 'zh' | 'zh-Hant' | 'en' | 'de' | 'fr' | 'es' | 'pt' | 'ja' {
  try {
    const country = readStoredCountry() || defaultCountry()
    return langForCountry(country)
  } catch {
    /* ignore */
  }
  return ''
}

export function withCatalogLang(url: string): string {
  let out = url
  const country = (() => {
    try { return readStoredCountry() || defaultCountry() } catch { return 'US' }
  })()
  const hl = catalogLangHint() || langForCountry(country)
  if (hl && !/[?&]hl=/i.test(out) && !/[?&]lang=/i.test(out)) {
    out += (out.includes('?') ? '&' : '?') + 'hl=' + encodeURIComponent(hl) + '&lang=' + encodeURIComponent(hl)
  }
  if (country && !/[?&]country=/i.test(out)) {
    out += (out.includes('?') ? '&' : '?') + 'country=' + encodeURIComponent(country)
  }
  return out
}

export function catalogLangHeaders(): Record<string, string> {
  const hl = catalogLangHint()
  return hl ? { 'X-Harbor-Lang': hl } : {}
}

/** Append hl + country for shop HTML pages so 8787 chrome follows H5 country. */
export function withShopLang(url: string): string {
  return withCatalogLang(url)
}

/** Persist harbor_hl + locale cookies from the selected country. */
export function syncHarborLangCookie(): void {
  try {
    const country = readStoredCountry() || defaultCountry()
    persistCountry(country)
    // Keep locale storage aligned with country-derived H5 language
    localStorage.setItem(LOCALE_STORAGE_KEY, h5LangForCountry(country))
  } catch {
    /* ignore */
  }
}

export { COUNTRY_STORAGE_KEY }
