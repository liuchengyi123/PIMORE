<template>
  <AgShell>
    <header class="top ag-top ag-pad">
      <AgBrand wave />
      <div class="side">{{ tx('每天发现\n花得更少', 'EVERYDAY FINDS\nFOR LESS') }} ✦</div>
    </header>
    <div class="ag-pad center">
      <h1>{{ tx('把 Harbor 加到\n主屏幕', 'Add Harbor to\nYour Home Screen') }}</h1>
      <p>{{ tx('打开更快、优惠更早知道，喜欢的家居好物一键再买。', 'Get faster access, special offers, and an easier way to reorder your favorite home goods — all in one tap.') }}</p>

      <div class="phone" aria-hidden="true">
        <div class="screen">
          <div class="app">
            <b>H</b>
            <span>Harbor</span>
          </div>
        </div>
        <em>{{ tx('就一下！', 'Just one tap!') }}</em>
      </div>

      <div class="perks">
        <div><span class="ag-icon"><Zap :size="18" /></span><b>{{ tx('更快', 'Faster') }}</b><small>{{ tx('马上打开 Harbor，不用找应用商店。', 'Open Harbor instantly, no app store needed.') }}</small></div>
        <div><span class="ag-icon"><Tag :size="18" /></span><b>{{ tx('优惠', 'Offers') }}</b><small>{{ tx('第一时间知道专属折扣和新品。', 'Be the first to know about exclusive deals and new finds.') }}</small></div>
        <div><span class="ag-icon"><ShoppingCart :size="18" /></span><b>{{ tx('轻松复购', 'Easy reorder') }}</b><small>{{ tx('把喜欢的留在手边，一键再买。', 'Keep your favorites close and reorder with one tap.') }}</small></div>
      </div>

      <button type="button" class="ag-cta pill" @click="install"><Upload :size="16" /> {{ tx('安装 / 添加到主屏幕', 'Install / Add to Home Screen') }}</button>
      <button type="button" class="later" @click="router.back()">{{ tx('以后再说', 'Maybe later') }}</button>
      <p class="slogan">✦ {{ tx('小价格，大时刻。', 'SMALL PRICES. BIG MOMENTS.') }} ✦</p>
    </div>
  </AgShell>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { ShoppingCart, Tag, Upload, Zap } from 'lucide-vue-next'
import AgBrand from '@/components/account/AgBrand.vue'
import AgShell from '@/components/account/AgShell.vue'
import { useZh } from '@/composables/zh'

const { tx, zh } = useZh()
const router = useRouter()

async function install() {
  const def = (window as unknown as { deferredInstallPrompt?: { prompt: () => Promise<void> } }).deferredInstallPrompt
  if (def?.prompt) {
    try { await def.prompt(); return } catch { /* menu fallback */ }
  }
  window.alert(zh.value ? '请用浏览器菜单：添加到主屏幕 / 安装应用。' : 'Use your browser menu → Add to Home Screen / Install app.')
}
</script>

<style scoped>
.top { display: flex; justify-content: space-between; align-items: flex-start; }
.side { font-size: 10px; font-weight: 800; letter-spacing: 0.06em; color: #8B919A; text-align: right; white-space: pre-line; }
.center { text-align: center; }
h1 { margin: 18px 0 0; font-size: 32px; font-weight: 800; letter-spacing: -0.045em; white-space: pre-line; line-height: 1.12; }
.center > p { color: #5C6570; font-size: 14.5px; line-height: 1.5; }
.phone { position: relative; width: 180px; height: 280px; margin: 18px auto; border: 8px solid #1C2430; border-radius: 28px; background: linear-gradient(#FFE1D6, #F7B59A); }
.screen { height: 100%; display: grid; place-items: center; }
.app b { width: 64px; height: 64px; border-radius: 16px; background: #F96141; color: #fff; display: grid; place-items: center; font-size: 28px; margin: 0 auto 6px; }
.app span { font-weight: 800; font-size: 13px; }
.phone em { position: absolute; right: -78px; top: 36px; color: #F96141; font-family: 'Segoe Script', cursive; font-size: 16px; transform: rotate(12deg); }
.perks { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; text-align: center; margin: 8px 0 16px; }
.perks .ag-icon { margin: 0 auto 6px; }
.perks b { display: block; font-size: 14px; }
.perks small { display: block; margin-top: 4px; color: #8B919A; font-size: 11px; line-height: 1.35; }
.later { margin-top: 8px; border: 0; background: transparent; color: #1C2430; text-decoration: underline; cursor: pointer; font-weight: 650; }
.slogan { color: #F96141; font-size: 12px; letter-spacing: 0.08em; font-weight: 800; }
</style>
