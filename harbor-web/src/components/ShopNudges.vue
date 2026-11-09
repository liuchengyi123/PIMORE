<template>
  <div v-if="kind" class="mask" :class="{ dock: iosInstall }" @click.self="close">
    <div class="card" :class="[kind, { ios: iosInstall }]" role="dialog" aria-modal="true" :data-figma="figmaId">
      <button v-if="kind === 'locale'" type="button" class="x" @click="close" aria-label="关闭">×</button>

      <template v-if="kind === 'gift'">
        <div class="grab" aria-hidden="true"></div>
        <span class="pill">{{ zh ? '免费赠品已解锁' : 'Free gift unlocked' }}</span>
        <div class="gift-stage" aria-hidden="true">
          <img v-if="giftImage" class="gift-photo" :src="giftImage" alt="" />
          <svg v-else class="gift-art" viewBox="0 0 180 96" width="180" height="96">
            <rect x="22" y="28" width="58" height="46" rx="6" fill="#FFF1EC" stroke="#F96141" stroke-width="2" />
            <path d="M22 46h58M51 28v46" stroke="#F96141" stroke-width="2" />
            <rect x="96" y="18" width="62" height="62" rx="8" fill="#fff" stroke="#E7E1D8" />
            <circle cx="127" cy="46" r="16" fill="#FF6B4A" />
            <path d="M127 36v20M117 46h20" stroke="#fff" stroke-width="2" stroke-linecap="round" />
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
          <svg viewBox="0 0 168 132" width="168" height="132">
            <rect x="52" y="6" width="64" height="108" rx="12" fill="#fff" />
            <rect x="74" y="12" width="20" height="4" rx="2" fill="#D5D8DE" />
            <rect x="62" y="24" width="44" height="52" rx="8" fill="#10243A" />
            <circle cx="84" cy="42" r="7" fill="#fff" />
            <path d="M84 38v9M80 42h8M81.5 49.5c1.6 2.4 2.5 2.4 2.5 2.4s.9 0 2.5-2.4" fill="none" stroke="#10243A" stroke-width="1.4" stroke-linecap="round" />
            <circle cx="84" cy="90" r="9" fill="#FF6B4A" />
            <path d="M118 64c10 1 18 10 16 20-2 8-9 11-16 8l-4 14c-1 4-6 5-8 2l-8-16 7-3-9 7c-3 2-7 0-7-4l2-9 8-2-8 4c-3 1-6-2-5-5l3-9 8-1-6 2c-4 1-7-3-5-6l6-14c2-6 12-8 18-2z" fill="#F6D2B5" stroke="#E2B394" stroke-width="1" />
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
          <svg viewBox="0 0 48 48" width="48" height="48">
            <rect x="7" y="11" width="34" height="30" rx="7" fill="none" stroke="#FF6B4A" stroke-width="2.4" />
            <path d="M16 7v8M32 7v8" stroke="#FF6B4A" stroke-width="2.4" stroke-linecap="round" />
            <path d="M16 28l6 6 12-13" fill="none" stroke="#FF6B4A" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </div>
        <p class="kicker">{{ zh ? '每日签到' : 'Daily check-in' }}</p>
        <h2 class="center">{{ zh ? '盖章领取今日奖励' : 'Stamp today for rewards' }}</h2>
        <div class="stamps" aria-hidden="true">
          <span class="stamp-badge">
            <svg viewBox="0 0 32 32" width="28" height="28"><rect x="5" y="8" width="22" height="18" rx="4" fill="none" stroke="#FF6B4A" stroke-width="1.8"/><path d="M11 5v6M21 5v6" stroke="#FF6B4A" stroke-width="1.8" stroke-linecap="round"/><text x="16" y="22" text-anchor="middle" font-size="11" font-weight="700" fill="#FF6B4A">1</text></svg>
          </span>
          <span v-for="n in 8" :key="n" class="stamp"></span>
        </div>
        <button type="button" class="ok" :disabled="busy" @click="checkin">{{ zh ? '立即盖章' : 'Stamp now' }}</button>
        <button type="button" class="later" @click="close">{{ zh ? '以后再说' : 'Later' }}</button>
      </template>

      <template v-else-if="kind === 'invite'">
        <div class="invite-art" aria-hidden="true">
          <svg viewBox="0 0 168 78" width="168" height="78">
            <path d="M28 14l2 5 5 .6-4 3.2 1.2 4.8L28 25l-4.2 2.6 1.2-4.8-4-3.2 5-.6z" fill="#FF6B4A"/>
            <path d="M78 6l2.2 5.2 5.4.6-4.2 3.4 1.3 5.2L78 17.6l-4.7 2.8 1.3-5.2-4.2-3.4 5.4-.6z" fill="#FF8A6A"/>
            <path d="M132 12l2 4.4 4.6.5-3.6 2.8 1.1 4.4-4.1-2.4-4.1 2.4 1.1-4.4-3.6-2.8 4.6-.5z" fill="#F96141"/>
            <rect x="16" y="36" width="40" height="32" rx="4" fill="#FF8A6A"/>
            <rect x="64" y="26" width="44" height="42" rx="4" fill="#FF6B4A"/>
            <rect x="116" y="38" width="36" height="30" rx="4" fill="#FF8A6A"/>
            <path d="M16 50h40M36 36v32M64 46h44M86 26v42M116 52h36M134 38v30" stroke="#fff" stroke-width="3"/>
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
const giftImage = computed(() => gift.value?.image || '')
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
  width: min(100%, 380px); background: #fff; border-radius: 24px; position: relative;
  padding: 22px 18px 14px; box-shadow: 0 18px 48px rgba(28, 36, 48, 0.18); text-align: center;
}
.card.pwa:not(.ios) { background: #10243A; color: #fff; padding: 28px 22px 16px; }
.card.ios { width: min(100%, 768px); border-radius: 28px 28px 0 0; padding: 12px 12px calc(12px + env(safe-area-inset-bottom)); text-align: left; }
.grab { width: 36px; height: 4px; border-radius: 99px; background: #E6E2DC; margin: 0 auto 12px; }
.x {
  position: absolute; right: 14px; top: 12px; border: 0; background: transparent;
  color: #FF6B4A; font-size: 26px; line-height: 1; cursor: pointer;
}
.pill {
  display: inline-flex; align-items: center; height: 28px; padding: 0 10px; border-radius: 8px;
  background: #FF6B4A; color: #fff; font-size: 13px; font-weight: 800;
}
.gift-stage { min-height: 96px; display: grid; place-items: center; margin: 12px 0; }
.gift-photo { width: 148px; height: 96px; object-fit: contain; }
.kicker { margin: 8px 0 4px; font-size: 13px; font-weight: 800; letter-spacing: 0.06em; color: #FF6B4A; }
.kicker.light, .sub.light, .later.light { color: rgba(255,255,255,0.82); }
h2 { margin: 0 0 8px; font-size: 26px; line-height: 1.2; letter-spacing: -0.03em; color: #1C2430; }
.card.pwa:not(.ios) h2 { color: #fff; font-size: 28px; }
.card.gift h2 { font-size: 20px; text-align: left; }
.sub { margin: 0 0 16px; color: #5C6570; line-height: 1.45; font-size: 15px; }
.center { text-align: center; }
.gift-name { text-align: left; }
.gift-meta { display: flex; align-items: baseline; gap: 8px; margin: 0 0 16px; color: #8B919A; font-size: 14px; }
.gift-meta b { margin-left: auto; color: #FF6B4A; font-size: 22px; letter-spacing: 0.04em; }
.gift-meta s { color: #9AA0A8; }
.ok, .later {
  display: flex; align-items: center; justify-content: center; width: 100%;
  height: 48px; border-radius: 999px; font-weight: 800; font-size: 16px; cursor: pointer; text-decoration: none;
}
.ok { border: 0; background: #FF6B4A; color: #fff; }
.ok:disabled { opacity: 0.6; }
.later { margin-top: 4px; border: 0; background: transparent; color: #1C2430; }
.phone-art, .cal-art, .invite-art { display: grid; place-items: center; }
.cal-art { margin-bottom: 4px; }
.stamps {
  display: grid; grid-template-columns: repeat(6, 1fr); gap: 12px 8px;
  align-items: center; justify-items: center; margin: 8px 0 18px;
}
.stamp { width: 28px; height: 28px; border-radius: 50%; border: 2px solid #1C2430; }
.stamp:nth-child(7) { grid-column: 2; }
.locales { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-top: 8px; text-align: left; }
.ccy {
  position: relative; height: 64px; border-radius: 14px; border: 1px solid #E6E2DC; background: #fff;
  display: flex; align-items: center; justify-content: center; gap: 8px; cursor: pointer; color: #1C2430;
}
.ccy.on { border: 2px solid #FF6B4A; background: #FFF6F3; }
.ccy b { font-size: 14px; }
.tick {
  position: absolute; top: -6px; right: -6px; width: 16px; height: 16px; border-radius: 50%;
  background: #FF6B4A; color: #fff; font-size: 10px; display: grid; place-items: center;
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
