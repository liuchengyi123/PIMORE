/**
 * Catalog language hint for shop product titles.
 * Reads harbor_app_locale from storage (same key as i18n composable).
 * Returns "zh" when App UI is Simplified/Traditional Chinese.
 */
export const LOCALE_STORAGE_KEY = 'harbor_app_locale'

export function catalogLangHint(): '' | 'zh' {
  try {
    const raw = String(uni.getStorageSync(LOCALE_STORAGE_KEY) || '')
    const key = raw.replace(/_/g, '-').toLowerCase()
    if (
      key === 'zh' ||
      key === 'zh-hans' ||
      key === 'zh-hant' ||
      key === 'zh-cn' ||
      key === 'zh-tw' ||
      key.startsWith('zh-')
    ) {
      return 'zh'
    }
  } catch {
    /* ignore */
  }
  return ''
}

/** Append hl=zh when needed; preserve existing query. */
export function withCatalogLang(url: string): string {
  const hl = catalogLangHint()
  if (!hl) return url
  if (/[?&]hl=/i.test(url)) return url
  return url + (url.includes('?') ? '&' : '?') + 'hl=' + encodeURIComponent(hl)
}

export function catalogLangHeaders(): Record<string, string> {
  const hl = catalogLangHint()
  return hl ? { 'X-Harbor-Lang': hl } : {}
}
