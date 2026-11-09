<template>
  <div class="page">
    <header class="status" aria-hidden="true"></header>
    <div class="center">
      <div class="icon">H</div>
      <h1>{{ zh ? '安装 Pimo' : 'Install Harbor' }}</h1>
      <p>{{ zh ? '添加到主屏幕后，浏览、查订单和找客服会更快。' : 'Add to Home Screen for faster browsing, order tracking, and chat.' }}</p>
      <button type="button" class="primary" @click="install">{{ zh ? '安装 / 添加到主屏幕' : 'Install / Add to Home' }}</button>
      <button type="button" class="later" @click="$router.back()">{{ zh ? '以后再说' : 'Maybe later' }}</button>
    </div>
  </div>
</template>
<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from '@/composables/i18n'
const { lang } = useI18n()
const zh = computed(() => String(lang.value).startsWith('zh'))
async function install() {
  const def = (window as any).deferredInstallPrompt
  if (def?.prompt) {
    try {
      await def.prompt()
      return
    } catch { /* */ }
  }
  alert(zh.value ? '请用浏览器菜单：添加到主屏幕 / 安装应用。' : 'Use your browser menu → Add to Home Screen / Install app.')
}
</script>
<style scoped>
.page {
  min-height: 100vh; background: #FCFAF8; color: #1C2430;
  padding: 12px 28px 40px; padding-top: calc(12px + env(safe-area-inset-top));
}
.center { margin-top: 32px; text-align: center; }
.icon {
  width: 64px; height: 64px; margin: 0 auto; border-radius: 16px; background: #F96141;
  color: #fff; font-size: 24px; font-weight: 800; display: flex; align-items: center; justify-content: center;
}
h1 { margin: 12px 0 0; font-size: 20px; font-weight: 800; letter-spacing: -0.03em; }
p { margin: 8px auto 0; max-width: 320px; font-size: 13px; line-height: 1.4; color: #8B919A; }
.primary {
  display: block; width: 100%; max-width: 320px; margin: 16px auto 0; height: 40px; border: 0; border-radius: 999px;
  background: #F96141; color: #fff; font-size: 14px; font-weight: 700; cursor: pointer;
}
.later {
  display: block; width: 100%; max-width: 320px; margin: 8px auto 0; height: 36px; border-radius: 999px;
  border: 1px solid #F1EEEA; background: #fff; color: #1C2430; font-size: 14px; font-weight: 700; cursor: pointer;
}
</style>
