<template>
  <div class="page">
    <header class="head">
      <button type="button" class="back" @click="$router.back()" aria-label="back">‹</button>
      <h1 class="title">Help Center</h1>
    </header>
    <div class="search-wrap">
      <AppSearchBar placeholder="Search help…" />
    </div>
    <div v-if="!blocks.length" class="state">Loading help…</div>
    <div v-else class="faqs">
      <button
        v-for="(b, i) in blocks" :key="i" type="button" class="faq"
        :class="{ open: open === i }" @click="open = open === i ? -1 : i"
      >
        <div class="row">
          <span class="q">{{ b.title }}</span>
          <span class="chev">{{ open === i ? '▾' : '›' }}</span>
        </div>
        <p v-if="open === i" class="a">{{ b.body }}</p>
      </button>
    </div>
    <router-link class="contact" to="/contact">Still need help? Contact us</router-link>
  </div>
</template>
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import AppSearchBar from '@/components/AppSearchBar.vue'
import { fetchHtmlPath, parsePolicyBlocks } from '@/api/accountApi'
const blocks = ref<{ title: string; body: string }[]>([])
const open = ref(0)
onMounted(async () => {
  try { blocks.value = parsePolicyBlocks(await fetchHtmlPath('/help')) } catch { /* */ }
  if (!blocks.value.length) {
    blocks.value = [
      { title: 'Orders & shipping', body: 'Track orders from Me → Orders. Shipping times depend on destination.' },
      { title: 'Returns', body: 'Start a return from the order detail page within the return window.' },
      { title: 'Payments', body: 'We accept PayPal, cards (Stripe), and LianLian where available.' },
    ]
  }
})
</script>
<style scoped>
.page { min-height: 100vh; background: #F7F4EF; color: #0F2744; padding: 12px 16px 40px; padding-top: calc(12px + env(safe-area-inset-top)); }
.head { display: flex; gap: 10px; align-items: center; margin-bottom: 12px; }
.back { border: 0; background: transparent; font-size: 22px; font-weight: 700; cursor: pointer; color: #0F2744; }
.title { font-size: 17px; font-weight: 700; margin: 0; }
.search-wrap { margin-bottom: 12px; }
.state { text-align: center; color: #6B7280; padding: 24px 8px; }
.faqs { display: flex; flex-direction: column; gap: 8px; }
.faq {
  text-align: left; width: 100%; background: #fff; border: 1px solid #E8E4DC; border-radius: 16px;
  padding: 14px; cursor: pointer; color: inherit;
}
.row { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.q { font-size: 14px; font-weight: 700; }
.chev { color: #0E7490; font-size: 14px; }
.a { margin: 10px 0 0; font-size: 13px; line-height: 1.45; color: #6B7280; }
.contact {
  display: block; margin-top: 16px; text-align: center; color: #0E7490; font-size: 13px; font-weight: 600;
  text-decoration: none;
}
</style>
