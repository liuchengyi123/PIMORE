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
.center { margin-top: 48px; text-align: center; }
.icon {
  width: 72px; height: 72px; margin: 0 auto; border-radius: 18px; background: #F96141;
  color: #fff; font-size: 28px; font-weight: 800; display: flex; align-items: center; justify-content: center;
}
h1 { margin: 16px 0 0; font-size: 22px; font-weight: 700; }
p { margin: 10px auto 0; max-width: 334px; font-size: 14px; line-height: 1.5; color: #6B7280; }
.primary {
  display: block; width: 100%; max-width: 334px; margin: 24px auto 0; height: 46px; border: 0; border-radius: 999px;
  background: #F96141; color: #fff; font-size: 14px; font-weight: 600; cursor: pointer;
}
.later {
  display: block; width: 100%; max-width: 334px; margin: 10px auto 0; height: 46px; border-radius: 999px;
  border: 1px solid #E8E4DC; background: #fff; color: #1C2430; font-size: 14px; font-weight: 600; cursor: pointer;
}
</style>
