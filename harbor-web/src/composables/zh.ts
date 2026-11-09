import { computed } from 'vue'
import { useI18n } from './i18n'

/** Account Growth copy: simplified Chinese by default, English when the locale is en. */
export function useZh() {
  const { lang } = useI18n()
  const zh = computed(() => String(lang.value).startsWith('zh'))
  function tx(hans: string, en: string) {
    return zh.value ? hans : en
  }
  return { zh, tx, lang }
}
