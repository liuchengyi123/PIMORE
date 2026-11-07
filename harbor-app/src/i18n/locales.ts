export type LocaleId =
  | 'en'
  | 'es'
  | 'fr'
  | 'pt'
  | 'ru'
  | 'ar'
  | 'ko'
  | 'zh-Hans'
  | 'zh-Hant'

export interface LocaleOption {
  id: LocaleId
  native: string
  /** Code sent to Harbor /locale API */
  api: string
  dir: 'ltr' | 'rtl'
}

export const DEFAULT_LOCALE: LocaleId = 'en'
export const LOCALE_STORAGE_KEY = 'harbor_app_locale'

export const LOCALE_OPTIONS: LocaleOption[] = [
  { id: 'en', native: 'English', api: 'en', dir: 'ltr' },
  { id: 'es', native: 'Español', api: 'es', dir: 'ltr' },
  { id: 'fr', native: 'Français', api: 'fr', dir: 'ltr' },
  { id: 'pt', native: 'Português', api: 'pt', dir: 'ltr' },
  { id: 'ru', native: 'Русский', api: 'ru', dir: 'ltr' },
  { id: 'ar', native: 'العربية', api: 'ar', dir: 'rtl' },
  { id: 'ko', native: '한국어', api: 'ko', dir: 'ltr' },
  { id: 'zh-Hans', native: '简体中文', api: 'zh', dir: 'ltr' },
  { id: 'zh-Hant', native: '繁體中文', api: 'zh-TW', dir: 'ltr' },
]

export function isLocaleId(v: unknown): v is LocaleId {
  return typeof v === 'string' && LOCALE_OPTIONS.some((o) => o.id === v)
}

export function localeMeta(id: LocaleId): LocaleOption {
  return LOCALE_OPTIONS.find((o) => o.id === id) || LOCALE_OPTIONS[0]
}

export function toApiLang(id: LocaleId): string {
  return localeMeta(id).api
}
