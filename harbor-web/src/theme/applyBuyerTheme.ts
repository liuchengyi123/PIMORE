import { harborRequest } from '@/api/http'

/** CSS custom properties harbor-web paints. Native clients use the JSON keys. */
const TOKEN_VARS: Record<string, string> = {
  'color.primary': '--hb-primary',
  'color.primarySoft': '--hb-primary-soft',
  'color.page': '--hb-page',
  'color.ink': '--hb-ink',
  'color.muted': '--hb-muted',
  'color.onPrimary': '--hb-on-primary',
  'color.surface': '--hb-surface',
  'color.sale': '--hb-sale',
  'color.badge': '--hb-badge',
}

const DERIVED_VARS: Record<string, string> = {
  'color.primaryHover': '--hb-primary-hover',
  'color.primaryPressed': '--hb-primary-pressed',
  'color.primaryDisabled': '--hb-primary-disabled',
}

const HEX = /^#[0-9A-Fa-f]{6}$/

interface ThemePack {
  tokens?: Record<string, string>
  derived?: Record<string, string>
}

interface ThemeResponse {
  ok?: boolean
  pack?: ThemePack
}

function paint(pack: ThemePack | undefined) {
  if (!pack || typeof document === 'undefined') return
  const root = document.documentElement
  const tokens = pack.tokens || {}
  for (const [key, cssName] of Object.entries(TOKEN_VARS)) {
    const value = String(tokens[key] || '').toUpperCase()
    if (HEX.test(value)) root.style.setProperty(cssName, value)
  }
  const derived = pack.derived || {}
  for (const [key, cssName] of Object.entries(DERIVED_VARS)) {
    const value = String(derived[key] || '').toUpperCase()
    if (HEX.test(value)) root.style.setProperty(cssName, value)
  }
  const primary = String(tokens['color.primary'] || '').toUpperCase()
  if (HEX.test(primary)) {
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', primary)
  }
}

/** Fetch the active pack and paint it. Defaults in theme.scss cover a failed fetch. */
export async function applyBuyerTheme(): Promise<void> {
  try {
    const res = await harborRequest<ThemeResponse>('/api/buyer-theme', { json: true })
    if (res.statusCode !== 200 || !res.data || typeof res.data !== 'object') return
    paint(res.data.pack)
  } catch {
    /* compiled Coral Market defaults stay */
  }
}
