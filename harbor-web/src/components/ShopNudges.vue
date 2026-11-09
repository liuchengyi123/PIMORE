<template>
  <div v-if="kind" class="mask" :class="{ dock: iosInstall }" @click.self="close">
    <div class="card" :class="[kind, { ios: iosInstall }]" role="dialog" aria-modal="true" :data-figma="figmaId">
      <button v-if="kind === 'locale'" type="button" class="x" @click="close" aria-label="关闭">×</button>

      <template v-if="kind === 'gift'">
        <div class="grab" aria-hidden="true"></div>
        <span class="pill">{{ zh ? '免费赠品已解锁' : 'Free gift unlocked' }}</span>
        <div class="gift-stage" aria-hidden="true">
          <svg class="gift-art" viewBox="0 0 240 128" width="220" height="118">
            <ellipse cx="124" cy="118" rx="86" ry="7" fill="#F4E8E3" />
            <path d="M28 46 L62 30 L108 48 L74 64 Z" fill="#F7F5F2" />
            <path d="M28 46 L28 96 L74 114 L74 64 Z" fill="#E4EDF7" />
            <path d="M74 64 L74 114 L108 96 L108 48 Z" fill="#D3E2F3" />
            <path d="M62 30 L62 18 L90 30 L90 48" fill="none" stroke="#F96141" stroke-width="2" />
            <rect x="40" y="68" width="30" height="20" rx="2" fill="#1C3148" />
            <text x="55" y="81" text-anchor="middle" font-size="8" font-weight="700" fill="#fff">Pimo</text>
            <ellipse cx="168" cy="108" rx="30" ry="6" fill="#E8E0D8" />
            <path d="M142 52 h52 v46 c0 10-12 16-26 16 s-26-6-26-16 Z" fill="#F7F2EC" />
            <ellipse cx="168" cy="52" rx="26" ry="7" fill="#EFE6DE" />
            <rect x="150" y="66" width="36" height="20" rx="2" fill="#1C3148" />
            <text x="168" y="79" text-anchor="middle" font-size="8" font-weight="700" fill="#fff">Pimo</text>
            <rect x="165" y="34" width="6" height="16" rx="1" fill="#E7D3C2" />
            <path d="M168 22c5 5 6 10 0 13c-6-3-5-8 0-13z" fill="#FFB020" />
            <path d="M168 26c2 2 2 4 0 5c-2-1-2-3 0-5z" fill="#FFF4D2" />
          </svg>
        </div>
        <h2 class="gift-name">{{ giftName }}</h2>
        <div class="gift-meta">
          <span>{{ giftSize }}</span>
          <b>{{ zh ? '免费' : 'FREE' }}</b>
          <s v-if="giftWas">{{ giftWas }}</s>
        </div>
        <router-link class="ok" :to="giftTo" @click="close">{{ zh ? '领取赠品' : 'Add free gift' }}</router-link>
        <button type="button" class="later" @click="close">{{ zh ? '以后再说' : 'Maybe later' }}</button>
      </template>

      <template v-else-if="iosInstall">
        <div class="ios-hero">
          <h2>{{ zh ? '安装 Pimo' : 'Install Harbor' }}</h2>
        </div>
        <ol class="ios-steps">
          <li>
            <span>{{ zh ? '第 1 步：点分享' : 'Step 1: Tap Share' }}</span>
            <i class="ios-ico" aria-hidden="true">
              <svg viewBox="0 0 24 24" width="18" height="18"><path d="M12 3v11M8 7l4-4 4 4" fill="none" stroke="#1C2430" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/><path d="M6 12v7h12v-7" fill="none" stroke="#1C2430" stroke-width="1.8" stroke-linecap="round"/></svg>
            </i>
          </li>
          <li>
            <span>{{ zh ? '第 2 步：添加到主屏幕' : 'Step 2: Add to Home Screen' }}</span>
            <i class="ios-ico" aria-hidden="true">
              <svg viewBox="0 0 24 24" width="18" height="18"><rect x="4" y="4" width="16" height="16" rx="4" fill="none" stroke="#1C2430" stroke-width="1.8"/><path d="M12 8v8M8 12h8" stroke="#1C2430" stroke-width="1.8" stroke-linecap="round"/></svg>
            </i>
          </li>
          <li class="confirm">
            <span>{{ zh ? '第 3 步：确认' : 'Step 3: Confirm' }}</span>
            <div class="ios-app">
              <span class="app-mark" aria-hidden="true">P</span>
              <b>Pimo</b>
              <em>{{ zh ? '添加' : 'Add' }}</em>
            </div>
          </li>
        </ol>
        <button type="button" class="ok" @click="install">{{ zh ? '知道了' : 'Got it' }}</button>
      </template>

      <template v-else-if="kind === 'pwa'">
        <div class="phone-art" aria-hidden="true">
          <svg viewBox="0 0 200 148" width="200" height="148">
            <rect x="46" y="6" width="78" height="128" rx="16" fill="#fff" />
            <rect x="72" y="12" width="26" height="5" rx="2.5" fill="#D5DAE1" />
            <rect x="58" y="26" width="54" height="64" rx="8" fill="#16324A" />
            <g fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="85" cy="48" r="7" />
              <path d="M85 55v11M77 62h16" />
              <path d="M80 66c0 6 4 9 5 9s5-3 5-9" />
            </g>
            <circle cx="85" cy="108" r="12" fill="#FF6B4A" />
            <g transform="translate(108,72)">
              <rect x="6" y="4" width="16" height="42" rx="8" fill="#F6CDB4" transform="rotate(-32 14 24)" />
              <ellipse cx="34" cy="46" rx="20" ry="15" fill="#F8D4BC" />
              <rect x="22" y="28" width="12" height="22" rx="6" fill="#F3C6AA" transform="rotate(18 28 40)" />
              <rect x="34" y="26" width="11" height="20" rx="5.5" fill="#F6CDB4" />
              <ellipse cx="18" cy="38" rx="7" ry="11" fill="#F0C0A2" transform="rotate(-50 18 38)" />
            </g>
          </svg>
        </div>
        <p class="kicker light">{{ zh ? '安装 Pimo' : 'Install Harbor' }}</p>
        <h2>{{ zh ? '用应用更快购物' : 'Shop faster as an app' }}</h2>
        <p class="sub light">{{ zh ? '打开更快，结算更顺，还有专属优惠。' : 'Get instant access, faster checkout and exclusive deals.' }}</p>
        <button type="button" class="ok" @click="install">{{ zh ? '添加到主屏幕' : 'Add to Home Screen' }}</button>
        <button type="button" class="later light" @click="close">{{ zh ? '以后再说' : 'Later' }}</button>
      </template>

      <template v-else-if="kind === 'checkin'">
        <div class="cal-art" aria-hidden="true">
          <svg viewBox="0 0 56 56" width="56" height="56">
            <rect x="8" y="14" width="40" height="34" rx="8" fill="#FFF6F3" stroke="#FF6B4A" stroke-width="2.4" />
            <path d="M8 24h40" stroke="#FF6B4A" stroke-width="2" />
            <path d="M20 8v10M36 8v10" stroke="#FF6B4A" stroke-width="2.6" stroke-linecap="round" />
            <circle cx="20" cy="12" r="2" fill="#FF6B4A" />
            <circle cx="36" cy="12" r="2" fill="#FF6B4A" />
            <path d="M18 36l7 7 14-15" fill="none" stroke="#FF6B4A" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </div>
        <p class="kicker">{{ zh ? '每日签到' : 'Daily check-in' }}</p>
        <h2 class="center">{{ zh ? '盖章领取今日奖励' : 'Stamp today for rewards' }}</h2>
        <div class="stamps" aria-hidden="true">
          <span class="stamp-badge">
            <svg viewBox="0 0 32 32" width="30" height="30"><rect x="4" y="8" width="24" height="20" rx="5" fill="#FFF6F3" stroke="#FF6B4A" stroke-width="1.7"/><path d="M4 15h24" stroke="#FF6B4A" stroke-width="1.4"/><path d="M11 4v7M21 4v7" stroke="#FF6B4A" stroke-width="1.7" stroke-linecap="round"/><text x="16" y="25" text-anchor="middle" font-size="11" font-weight="700" fill="#FF6B4A">1</text></svg>
          </span>
          <span v-for="n in 8" :key="n" class="stamp"></span>
        </div>
        <button type="button" class="ok" :disabled="busy" @click="checkin">{{ zh ? '立即盖章' : 'Stamp now' }}</button>
        <button type="button" class="later" @click="close">{{ zh ? '以后再说' : 'Later' }}</button>
      </template>

      <template v-else-if="kind === 'invite'">
        <div class="invite-art" aria-hidden="true">
          <svg viewBox="0 0 210 108" width="196" height="100">
            <g fill="#FF8A6A">
              <path d="M46 16l1.4 3.4h3.6l-2.9 2.1 1.1 3.4-3.2-2.2-3.2 2.2 1.1-3.4-2.9-2.1h3.6z"/>
              <path d="M104 6l1.8 4.2h4.4l-3.6 2.6 1.4 4.2-4-2.8-4 2.8 1.4-4.2L98 10.2h4.4z"/>
              <path d="M164 14l1.3 3.2h3.4l-2.7 2 1 3.2-3-2-3 2 1-3.2-2.7-2h3.4z"/>
            </g>
            <g fill="none" stroke="#FFB199" stroke-width="1.6" stroke-linecap="round">
              <path d="M28 22c4 3 4 7 0 9"/>
              <path d="M78 18c5 4 5 8 0 11"/>
              <path d="M138 12c5 3 5 8 0 10"/>
              <path d="M186 24c3 2 3 5 0 7"/>
            </g>
            <g>
              <rect x="18" y="52" width="48" height="40" rx="5" fill="#FF9A7A"/>
              <path d="M18 68h48M42 52v40" stroke="#fff" stroke-width="3.2"/>
              <path d="M42 52c-8 0-14-9-7-12 4 3 7 7 7 12 0-5 3-9 7-12 7 3 1 12-7 12z" fill="#FF8A6A" stroke="#fff" stroke-width="1.6"/>
            </g>
            <g>
              <rect x="78" y="40" width="56" height="52" rx="5" fill="#FF6B4A"/>
              <path d="M78 60h56M106 40v52" stroke="#fff" stroke-width="3.4"/>
              <path d="M106 40c-10 0-16-11-8-14 5 4 8 8 8 14 0-6 3-10 8-14 8 3 2 14-8 14z" fill="#FF6B4A" stroke="#fff" stroke-width="1.8"/>
            </g>
            <g>
              <rect x="146" y="56" width="46" height="36" rx="5" fill="#FF8A6A"/>
              <path d="M146 70h46M169 56v36" stroke="#fff" stroke-width="3.2"/>
              <path d="M169 56c-8 0-13-8-6-11 4 3 6 6 6 11 0-5 2-8 6-11 7 3 2 11-6 11z" fill="#FF9A7A" stroke="#fff" stroke-width="1.6"/>
            </g>
          </svg>
        </div>
        <p class="kicker">{{ zh ? '邀请好友' : 'Invite friends' }}</p>
        <h2 class="center">{{ zh ? '分享就能拿奖励' : 'Share and earn rewards' }}</h2>
        <p class="sub center">{{ zh ? '好友注册并完成首单，你就能拿到专属奖励。' : 'Get a perk for every friend who joins and makes a first purchase.' }}</p>
        <button type="button" class="ok" @click="share">{{ zh ? '分享邀请' : 'Share invite' }}</button>
        <button type="button" class="later" @click="close">{{ zh ? '以后再说' : 'Later' }}</button>
      </template>

      <template v-else-if="kind === 'locale'">
        <h2 class="center">{{ zh ? '地区' : 'Locale' }}</h2>
        <p class="sub center">{{ zh ? '选择常用的货币和国家。' : 'Select your preferred currency and country.' }}</p>
        <div class="locales">
          <button
            v-for="c in locales"
            :key="c.code"
            type="button"
            class="ccy"
            :class="{ on: c.currency === currentCurrency }"
            @click="pick(c.code)"
          >
            <span v-if="c.currency === currentCurrency" class="tick" aria-hidden="true">✓</span>
            <FlagMark :code="c.flag" />
            <b>{{ c.currency }}</b>
          </button>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, defineComponent, h, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from '@/composables/i18n'
import { postCheckIn } from '@/api/accountApi'
import { currencyForCountry, readStoredCountry } from '@/api/countryLocale'
import { listProducts, money, type Product } from '@/api/products'

const FlagMark = defineComponent({
  props: { code: { type: String, required: true } },
  setup(props) {
    return () => {
      const id = `hb-flag-${props.code}`
      const common = { viewBox: '0 0 32 32', width: '28', height: '28', 'aria-hidden': 'true' }
      if (props.code === 'us') {
        return h('svg', common, [
          h('defs', [h('clipPath', { id }, [h('circle', { cx: 16, cy: 16, r: 16 })])]),
          h('g', { 'clip-path': `url(#${id})` }, [
            h('rect', { width: 32, height: 32, fill: '#BF0A30' }),
            h('path', { stroke: '#fff', 'stroke-width': '2.4', d: 'M0 4.5h32M0 9.5h32M0 14.5h32M0 19.5h32M0 24.5h32M0 29.5h32' }),
            h('rect', { width: 14, height: 14, fill: '#1C2430' }),
          ]),
        ])
      }
      if (props.code === 'eu') {
        return h('svg', common, [
          h('circle', { cx: 16, cy: 16, r: 16, fill: '#1D4ED8' }),
          ...Array.from({ length: 8 }, (_, i) => {
            const a = (Math.PI * 2 * i) / 8 - Math.PI / 2
            return h('circle', { cx: 16 + Math.cos(a) * 8, cy: 16 + Math.sin(a) * 8, r: 1.3, fill: '#FBBF24' })
          }),
        ])
      }
      if (props.code === 'gb') {
        return h('svg', common, [
          h('defs', [h('clipPath', { id }, [h('circle', { cx: 16, cy: 16, r: 16 })])]),
          h('g', { 'clip-path': `url(#${id})` }, [
            h('rect', { width: 32, height: 32, fill: '#012169' }),
            h('path', { stroke: '#fff', 'stroke-width': '8', d: 'M16 0v32M0 16h32' }),
            h('path', { stroke: '#C8102E', 'stroke-width': '4', d: 'M16 0v32M0 16h32' }),
          ]),
        ])
      }
      if (props.code === 'jp') {
        return h('svg', common, [
          h('circle', { cx: 16, cy: 16, r: 16, fill: '#fff', stroke: '#E5E7EB' }),
          h('circle', { cx: 16, cy: 16, r: 6, fill: '#BC002D' }),
        ])
      }
      if (props.code === 'ca') {
        return h('svg', common, [
          h('defs', [h('clipPath', { id }, [h('circle', { cx: 16, cy: 16, r: 16 })])]),
          h('g', { 'clip-path': `url(#${id})` }, [
            h('rect', { width: 32, height: 32, fill: '#fff' }),
            h('rect', { width: 8, height: 32, fill: '#FF0000' }),
            h('rect', { x: 24, width: 8, height: 32, fill: '#FF0000' }),
            h('path', { d: 'M16 8l1.6 4.4H22l-3.4 2.6 1.3 4.4L16 17l-3.9 2.4 1.3-4.4L10 12.4h4.4z', fill: '#FF0000' }),
          ]),
        ])
      }
      return h('svg', common, [
        h('circle', { cx: 16, cy: 16, r: 16, fill: '#012169' }),
        h('circle', { cx: 22, cy: 18, r: 2.1, fill: '#fff' }),
        h('circle', { cx: 12, cy: 12, r: 1.2, fill: '#fff' }),
        h('circle', { cx: 11, cy: 20, r: 1.1, fill: '#fff' }),
        h('circle', { cx: 18, cy: 10, r: 1, fill: '#fff' }),
        h('circle', { cx: 24, cy: 12, r: 1, fill: '#fff' }),
      ])
    }
  },
})

const { lang, setCountry } = useI18n()
const route = useRoute()
const router = useRouter()
const zh = computed(() => String(lang.value).startsWith('zh'))
const kind = ref('')
const busy = ref(false)
const ios = /iphone|ipad|ipod/i.test(navigator.userAgent || '')
const iosInstall = computed(() => kind.value === 'pwa' && ios)
const gift = ref<Product | null>(null)
const currentCountry = ref(readStoredCountry() || 'US')
const currentCurrency = computed(() => currencyForCountry(currentCountry.value))

const locales = [
  { code: 'US', currency: 'USD', flag: 'us' },
  { code: 'DE', currency: 'EUR', flag: 'eu' },
  { code: 'GB', currency: 'GBP', flag: 'gb' },
  { code: 'JP', currency: 'JPY', flag: 'jp' },
  { code: 'CA', currency: 'CAD', flag: 'ca' },
  { code: 'AU', currency: 'AUD', flag: 'au' },
]

const figmaId = computed(() => ({
  gift: '5:3',
  pwa: ios ? '5:13' : '5:4',
  checkin: '5:5',
  invite: '5:6',
  locale: '5:7',
}[kind.value] || ''))

const giftName = computed(() => gift.value?.name || (zh.value ? '满额赠品' : 'Free gift'))
const giftSize = computed(() => gift.value?.offers?.[0]?.label || gift.value?.sizes?.[0] || (zh.value ? '默认规格' : 'Default'))
const giftWas = computed(() => (gift.value?.price ? money(gift.value.price) : ''))
const giftTo = computed(() => (gift.value?.sku ? { path: '/pdp', query: { sku: gift.value.sku } } : '/ship-lp'))

const queue = ['gift', 'pwa', 'checkin', 'invite']

function seen(id: string) {
  try { return sessionStorage.getItem('hb-nudge-' + id) === '1' } catch { return false }
}
function remember(id: string) {
  try { sessionStorage.setItem('hb-nudge-' + id, '1') } catch { /* */ }
}

function openNext() {
  const nudge = String(route.query.nudge || '')
  if (nudge === 'gift' || nudge === 'pwa' || nudge === 'checkin' || nudge === 'invite') {
    kind.value = nudge
    return
  }
  if (route.query.locale) {
    kind.value = 'locale'
    return
  }
  const name = String(route.name || '')
  if (name !== 'home' && name !== 'root') {
    kind.value = ''
    return
  }
  kind.value = queue.find((id) => !seen(id)) || ''
}

function close() {
  if (kind.value && kind.value !== 'locale') remember(kind.value)
  kind.value = ''
  if (route.query.locale || route.query.nudge) {
    const q = { ...route.query }
    delete q.locale
    delete q.nudge
    router.replace({ query: q })
  }
}

async function loadGift() {
  try {
    const list = await listProducts('recommended')
    gift.value = list[0] || null
  } catch {
    gift.value = null
  }
}

async function install() {
  const def = (window as unknown as { deferredInstallPrompt?: { prompt: () => Promise<void> } }).deferredInstallPrompt
  if (def?.prompt) {
    try { await def.prompt() } catch { /* */ }
  }
  close()
}

async function checkin() {
  busy.value = true
  try { await postCheckIn() } catch { /* page still explains it */ }
  busy.value = false
  close()
  router.push('/checkin')
}

async function share() {
  const link = `${location.origin}/?ref=harbor`
  try {
    if (navigator.share) await navigator.share({ title: 'Pimo', url: link })
    else await navigator.clipboard.writeText(link)
  } catch { /* */ }
  close()
  router.push('/invite')
}

function pick(code: string) {
  setCountry(code)
  currentCountry.value = code
  close()
}

onMounted(openNext)
watch(() => [route.name, route.query.locale, route.query.nudge], openNext)
watch(kind, (k) => { if (k === 'gift') loadGift() })
</script>

<style scoped>
.mask {
  position: fixed; inset: 0; z-index: 120; background: rgba(28, 36, 48, 0.48);
  display: flex; align-items: center; justify-content: center; padding: 24px 16px;
}
.mask.dock { align-items: flex-end; padding: 0; }
.card {
  width: min(100%, 360px); background: #fff; border-radius: 22px; position: relative;
  padding: 22px 22px 12px; box-shadow: 0 18px 48px rgba(28, 36, 48, 0.18); text-align: center;
}
.card.gift { width: min(100%, 340px); padding: 12px 20px 8px; text-align: left; }
.card.checkin { padding: 26px 24px 8px; }
.card.invite { padding: 20px 24px 8px; }
.card.locale { width: min(100%, 336px); padding: 16px 14px 14px; }
.card.pwa:not(.ios) { background: #10243A; color: #fff; padding: 22px 24px 8px; border-radius: 20px; }
.card.ios { width: min(100%, 768px); border-radius: 28px 28px 0 0; padding: 12px 12px calc(12px + env(safe-area-inset-bottom)); text-align: left; }
.grab { width: 36px; height: 4px; border-radius: 99px; background: #E6E2DC; margin: 2px auto 14px; }
.x {
  position: absolute; right: 14px; top: 12px; border: 0; background: transparent;
  color: #FF6B4A; font-size: 26px; line-height: 1; cursor: pointer;
}
.pill {
  display: inline-flex; align-items: center; height: 26px; padding: 0 10px; border-radius: 7px;
  background: #FF6B4A; color: #fff; font-size: 12px; font-weight: 750; letter-spacing: 0.01em;
}
.gift-stage { display: grid; place-items: center; margin: 16px 0 10px; }
.kicker { margin: 10px 0 6px; font-size: 13px; font-weight: 750; letter-spacing: 0.04em; color: #FF6B4A; }
.kicker.light, .sub.light, .later.light { color: rgba(255,255,255,0.78); }
h2 { margin: 0 0 8px; font-size: 26px; line-height: 1.22; letter-spacing: -0.03em; font-weight: 800; color: #1C2430; }
.card.pwa:not(.ios) .kicker { margin-top: 12px; font-size: 13px; font-weight: 600; letter-spacing: 0; }
.card.pwa:not(.ios) h2 { color: #fff; font-size: 30px; line-height: 1.15; margin: 0 0 10px; }
.card.pwa:not(.ios) .sub { max-width: 280px; margin: 0 auto 18px; font-size: 15px; line-height: 1.45; }
.card.checkin .kicker { font-size: 12px; letter-spacing: 0.16em; font-weight: 750; margin: 10px 0 8px; }
.card.checkin h2 { font-size: 26px; line-height: 1.2; max-width: 240px; margin: 0 auto 18px; }
.card.invite .kicker { font-size: 16px; font-weight: 750; letter-spacing: 0; margin: 8px 0 6px; }
.card.invite h2 { font-size: 24px; line-height: 1.25; margin: 0 0 10px; }
.card.invite .sub { max-width: 268px; margin: 0 auto 18px; font-size: 15px; line-height: 1.5; }
.card.gift h2 { font-size: 20px; line-height: 1.3; font-weight: 780; text-align: left; margin: 0 0 6px; letter-spacing: -0.02em; }
.card.locale h2 { font-size: 22px; line-height: 1.2; margin: 0 28px 4px; }
.card.locale .sub { font-size: 13px; line-height: 1.35; margin: 0 8px 10px; color: #5C6570; }
.card.locale .x { top: 8px; right: 8px; width: 28px; height: 28px; font-size: 22px; }
.sub { margin: 0 0 16px; color: #5C6570; line-height: 1.45; font-size: 15px; }
.center { text-align: center; }
.gift-name { text-align: left; }
.gift-meta { display: flex; align-items: baseline; gap: 8px; margin: 0 0 18px; color: #8B919A; font-size: 13px; font-weight: 500; }
.gift-meta b { margin-left: auto; color: #FF6B4A; font-size: 22px; font-weight: 800; letter-spacing: 0.06em; }
.gift-meta s { color: #B0B6BE; font-size: 13px; }
.ok, .later {
  display: flex; align-items: center; justify-content: center; width: 100%;
  height: 48px; border-radius: 999px; font-weight: 800; font-size: 16px; cursor: pointer; text-decoration: none;
}
.ok { border: 0; background: #FF6B4A; color: #fff; }
.ok:disabled { opacity: 0.6; }
.later { margin-top: 2px; height: 40px; border: 0; background: transparent; color: #1C2430; font-size: 15px; font-weight: 700; }
.phone-art, .cal-art, .invite-art { display: grid; place-items: center; }
.phone-art { margin-top: 4px; }
.cal-art { margin-top: 2px; }
.stamps {
  display: grid; grid-template-columns: repeat(6, 1fr); gap: 14px 10px;
  align-items: center; justify-items: center; margin: 0 4px 20px;
}
.stamp { width: 26px; height: 26px; border-radius: 50%; border: 2px solid #1C2430; box-sizing: border-box; }
.stamp:nth-child(7) { grid-column: 2; }
.locales { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-top: 0; text-align: left; }
.ccy {
  position: relative; height: 52px; border-radius: 12px; border: 1px solid #E6E2DC; background: #fff;
  display: flex; align-items: center; justify-content: center; gap: 6px; cursor: pointer; color: #1C2430;
}
.ccy svg { width: 26px; height: 26px; flex: 0 0 auto; }
.ccy.on { border: 2px solid #FF6B4A; background: #FFF1EC; }
.ccy b { font-size: 15px; font-weight: 800; letter-spacing: 0.01em; }
.tick {
  position: absolute; top: -6px; right: -6px; width: 16px; height: 16px; border-radius: 50%;
  background: #FF6B4A; color: #fff; font-size: 10px; font-weight: 800; display: grid; place-items: center;
}
.ios-hero { background: #FF6B4A; color: #fff; border-radius: 22px; padding: 22px 16px 18px; text-align: center; }
.ios-hero h2 { color: #fff; margin: 0; font-size: 26px; }
.ios-steps { list-style: none; margin: 12px 0; padding: 0; display: flex; flex-direction: column; gap: 10px; }
.ios-steps li {
  background: #fff; border-radius: 16px; min-height: 56px; padding: 12px 14px;
  display: flex; align-items: center; justify-content: space-between; gap: 10px;
  box-shadow: 0 6px 16px rgba(28,36,48,0.06); font-weight: 700; color: #1C2430;
}
.ios-steps .confirm { align-items: flex-start; flex-direction: column; }
.ios-ico {
  width: 36px; height: 36px; border-radius: 10px; border: 1px solid #E6E2DC;
  display: grid; place-items: center; flex: 0 0 auto;
}
.ios-app { width: 100%; display: flex; align-items: center; gap: 10px; }
.app-mark {
  width: 36px; height: 36px; border-radius: 10px; background: #FF6B4A; color: #fff;
  display: grid; place-items: center; font-weight: 800;
}
.ios-app em { margin-left: auto; font-style: normal; color: #8B919A; font-weight: 650; }
.card.ios .ok { margin-top: 4px; }
</style>
