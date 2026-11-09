<template>
  <div class="page">
    <header class="head">
      <button type="button" class="back" @click="$router.back()" aria-label="back">‹</button>
      <h1 class="title">{{ zh ? '帮助中心' : 'Help Center' }}</h1>
    </header>
    <div class="search-wrap">
      <AppSearchBar :placeholder="zh ? '搜索帮助…' : 'Search help…'" />
    </div>
    <div v-if="!blocks.length" class="state">{{ zh ? '加载帮助…' : 'Loading help…' }}</div>
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
    <router-link class="contact" to="/contact">{{ zh ? '还需要帮助？联系我们' : 'Still need help? Contact us' }}</router-link>
  </div>
</template>
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import AppSearchBar from '@/components/AppSearchBar.vue'
import { fetchHtmlPath, parsePolicyBlocks } from '@/api/accountApi'
import { useI18n } from '@/composables/i18n'
const { lang } = useI18n()
const zh = computed(() => String(lang.value).startsWith('zh'))
const blocks = ref<{ title: string; body: string }[]>([])
const open = ref(0)
onMounted(async () => {
  try { blocks.value = parsePolicyBlocks(await fetchHtmlPath('/help')) } catch { /* */ }
  if (!blocks.value.length) {
    blocks.value = [
      { title: zh.value ? '订单与物流' : 'Orders & shipping', body: zh.value ? '在「我的 → 订单」里查看物流。时效看收货国家。' : 'Track orders from Me → Orders. Shipping times depend on destination.' },
      { title: zh.value ? '退货' : 'Returns', body: zh.value ? '在订单详情里发起退货，窗口期内有效。' : 'Start a return from the order detail page within the return window.' },
      { title: zh.value ? '支付' : 'Payments', body: zh.value ? '支持 PayPal、银行卡（Stripe）和连连，以结账页为准。' : 'We accept PayPal, cards (Stripe), and LianLian where available.' },
    ]
  }
})
</script>
<style scoped>
.page { min-height: 100vh; background: #FCFAF8; color: #1C2430; padding: 12px 16px 40px; padding-top: calc(12px + env(safe-area-inset-top)); }
.head { display: flex; gap: 10px; align-items: center; margin-bottom: 12px; }
.back { border: 0; background: transparent; font-size: 22px; font-weight: 700; cursor: pointer; color: #1C2430; }
.title { font-size: 22px; font-weight: 800; letter-spacing: -0.03em; margin: 0; }
.search-wrap { margin-bottom: 12px; }
.state { text-align: center; color: #6B7280; padding: 24px 8px; }
.faqs { display: flex; flex-direction: column; gap: 8px; }
.faq {
  text-align: left; width: 100%; background: #fff; border: 1px solid #E8E4DC; border-radius: 16px;
  padding: 14px; cursor: pointer; color: inherit;
}
.row { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.q { font-size: 14px; font-weight: 700; }
.chev { color: #F96141; font-size: 14px; }
.a { margin: 10px 0 0; font-size: 13px; line-height: 1.45; color: #6B7280; }
.contact {
  display: block; margin-top: 16px; text-align: center; color: #F96141; font-size: 13px; font-weight: 700;
  text-decoration: none;
}
</style>
