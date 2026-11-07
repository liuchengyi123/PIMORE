<template>
  <div class="page">
    <header class="status" aria-hidden="true"></header>
    <div class="center">
      <div class="icon">H</div>
      <h1>Install Harbor</h1>
      <p>Add to Home Screen for faster browsing, order tracking, and chat.</p>
      <button type="button" class="primary" @click="install">Install / Add to Home</button>
      <button type="button" class="later" @click="$router.back()">Maybe later</button>
    </div>
  </div>
</template>
<script setup lang="ts">
async function install() {
  const def = (window as any).deferredInstallPrompt
  if (def?.prompt) {
    try {
      await def.prompt()
      return
    } catch { /* */ }
  }
  alert('Use your browser menu → Add to Home Screen / Install app.')
}
</script>
<style scoped>
.page {
  min-height: 100vh; background: #F7F4EF; color: #0F2744;
  padding: 12px 28px 40px; padding-top: calc(12px + env(safe-area-inset-top));
}
.center { margin-top: 48px; text-align: center; }
.icon {
  width: 72px; height: 72px; margin: 0 auto; border-radius: 18px; background: #0F2744;
  color: #fff; font-size: 28px; font-weight: 800; display: flex; align-items: center; justify-content: center;
}
h1 { margin: 16px 0 0; font-size: 22px; font-weight: 700; }
p { margin: 10px auto 0; max-width: 334px; font-size: 14px; line-height: 1.5; color: #6B7280; }
.primary {
  display: block; width: 100%; max-width: 334px; margin: 24px auto 0; height: 41px; border: 0; border-radius: 12px;
  background: #0F2744; color: #fff; font-size: 14px; font-weight: 600; cursor: pointer;
}
.later {
  display: block; width: 100%; max-width: 334px; margin: 10px auto 0; height: 43px; border-radius: 12px;
  border: 1px solid #E8E4DC; background: #fff; color: #0F2744; font-size: 14px; font-weight: 600; cursor: pointer;
}
</style>
