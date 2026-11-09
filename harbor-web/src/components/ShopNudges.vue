<template>
  <div v-if="kind" class="mask" @click.self="close">
    <div class="card" role="dialog" aria-modal="true">
      <button type="button" class="x" @click="close">×</button>

      <template v-if="kind === 'gift'">
        <h2>{{ zh ? '满额包邮' : 'Free shipping gift' }}</h2>
        <p>{{ zh ? '再凑一点，这笔订单就可以包邮。' : 'Add a little more and this order ships free.' }}</p>
        <router-link class="ok" to="/ship-lp" @click="close">{{ zh ? '去凑单' : 'Shop ship deals' }}</router-link>
      </template>

      <template v-else-if="kind === 'pwa'">
        <h2>{{ zh ? '添加到主屏幕' : 'Install Harbor' }}</h2>
        <p>{{ ios ? (zh ? '点分享，再选「添加到主屏幕」。' : 'Tap Share, then Add to Home Screen.') : (zh ? '安装后可以更快打开订单和客服。' : 'Install for faster orders and chat.') }}</p>
        <button type="button" class="ok" @click="install">{{ zh ? '安装' : 'Install' }}</button>
      </template>

      <template v-else-if="kind === 'checkin'">
        <h2>{{ zh ? '今日签到' : 'Check in today' }}</h2>
        <p>{{ zh ? '签到领取今日奖励。' : 'Claim today’s perk.' }}</p>
        <button type="button" class="ok" :disabled="busy" @click="checkin">{{ zh ? '去签到' : 'Check in' }}</button>
      </template>

      <template v-else-if="kind === 'invite'">
        <h2>{{ zh ? '邀请好友' : 'Invite friends' }}</h2>
        <p>{{ zh ? '分享链接，好友下单后奖励进余额。' : 'Share your link. Rewards land in Balance.' }}</p>
        <button type="button" class="ok" @click="share">{{ zh ? '去分享' : 'Share' }}</button>
      </template>

      <template v-else-if="kind === 'locale'">
        <h2>{{ zh ? '国家与货币' : 'Country & currency' }}</h2>
        <button v-for="c in countries" :key="c.code" type="button" class="row" @click="pick(c.code)">
          <span>{{ c.name }}</span><b>{{ c.currency }}</b>
        </button>
      </template>

      <button type="button" class="later" @click="close">{{ zh ? '以后再说' : 'Not now' }}</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from '@/composables/i18n'
import { postCheckIn } from '@/api/accountApi'

const { lang, setCountry } = useI18n()
const route = useRoute()
const router = useRouter()
const zh = computed(() => String(lang.value).startsWith('zh'))
const kind = ref('')
const busy = ref(false)
const ios = /iphone|ipad|ipod/i.test(navigator.userAgent || '')

const countries = [
  { code: 'CN', name: '中国', currency: 'CNY' },
  { code: 'US', name: 'United States', currency: 'USD' },
  { code: 'JP', name: '日本', currency: 'JPY' },
  { code: 'DE', name: 'Deutschland', currency: 'EUR' },
]

const queue = ['gift', 'pwa', 'checkin', 'invite']

function seen(id: string) {
  try { return sessionStorage.getItem('hb-nudge-' + id) === '1' } catch { return false }
}
function mark(id: string) {
  try { sessionStorage.setItem('hb-nudge-' + id, '1') } catch { /* */ }
}

function openNext() {
  if (route.query.locale) {
    kind.value = 'locale'
    return
  }
  const name = String(route.name || '')
  if (name !== 'home' && name !== 'root') {
    kind.value = ''
    return
  }
  const next = queue.find((id) => !seen(id))
  kind.value = next || ''
}

function close() {
  if (kind.value && kind.value !== 'locale') mark(kind.value)
  kind.value = ''
  if (route.query.locale) {
    const q = { ...route.query }
    delete q.locale
    router.replace({ query: q })
  }
}

async function install() {
  const def = (window as any).deferredInstallPrompt
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
    if (navigator.share) await navigator.share({ title: 'Harbor', url: link })
    else await navigator.clipboard.writeText(link)
  } catch { /* */ }
  close()
  router.push('/invite')
}

function pick(code: string) {
  setCountry(code)
  close()
}

onMounted(openNext)
watch(() => [route.name, route.query.locale], openNext)
</script>

<style scoped>
.mask {
  position: fixed; inset: 0; z-index: 120; background: rgba(28,36,48,0.45);
  display: flex; align-items: flex-end; justify-content: center;
}
.card {
  width: min(100%, 768px); background: #fff; border-radius: 20px 20px 0 0;
  padding: 18px 16px calc(18px + env(safe-area-inset-bottom)); position: relative;
  box-shadow: 0 -12px 32px rgba(28,36,48,0.08);
}
.x { position: absolute; right: 12px; top: 8px; border: 0; background: transparent; font-size: 22px; cursor: pointer; color: #8B919A; }
h2 { margin: 8px 0; font-size: 20px; color: #1C2430; }
p { margin: 0 0 14px; color: #5C6570; line-height: 1.45; }
.ok, .later, .row {
  display: flex; align-items: center; justify-content: center; width: 100%;
  height: 46px; border-radius: 999px; font-weight: 700; cursor: pointer; text-decoration: none;
}
.ok { border: 0; background: #F96141; color: #fff; }
.later { margin-top: 8px; border: 0; background: transparent; color: #8B919A; }
.row { justify-content: space-between; padding: 0 14px; margin-bottom: 8px; background: #F7F8FA; border: 0; color: #1C2430; }
</style>
