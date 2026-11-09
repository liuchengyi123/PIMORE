<template>
  <div class="page">
    <header class="head">
      <button type="button" class="back" @click="$router.back()" aria-label="back">‹</button>
      <h1 class="title">发票</h1>
    </header>
    <div v-if="loading" class="state">加载中…</div>
    <section v-else class="sheet">
      <div class="brand">Pimo</div>
      <div class="hl">发票</div>
      <div class="meta">订单 {{ orderId || '—' }} · {{ dateLabel }}</div>
      <div class="rule" />
      <div v-if="!lines.length" class="state">暂无明细</div>
      <div v-for="(l, i) in lines" :key="i" class="line">
        <span class="left">{{ l }}</span>
      </div>
      <div class="rule" />
      <div class="total">
        <span>合计</span>
        <span class="amt">{{ totalLabel }}</span>
      </div>
      <a
        v-if="orderId"
        class="cta"
        :href="shopPath('/orders/' + encodeURIComponent(orderId) + '/invoice')"
        target="_blank"
        rel="noopener"
      >下载 / 分享</a>
    </section>
  </div>
</template>
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { fetchInvoiceHtml, shopPath } from '@/api/accountApi'
const route = useRoute()
const orderId = ref(String(route.query.id || route.params.id || ''))
const lines = ref<string[]>([])
const loading = ref(false)
onMounted(async () => {
  if (!orderId.value) return
  loading.value = true
  try {
    const html = await fetchInvoiceHtml(orderId.value)
    const out: string[] = []
    const h1 = html.match(/<h1>([\s\S]*?)<\/h1>/i)
    if (h1) out.push(h1[1].replace(/<[^>]+>/g, ' ').trim())
    for (const m of html.matchAll(/<p>([\s\S]*?)<\/p>/gi)) {
      const t = m[1].replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim()
      if (t) out.push(t)
    }
    for (const m of html.matchAll(/<tr>\s*<th>([\s\S]*?)<\/th>\s*<td>([\s\S]*?)<\/td>/gi)) {
      out.push(`${m[1].replace(/<[^>]+>/g, '').trim()} · ${m[2].replace(/<[^>]+>/g, '').trim()}`)
    }
    lines.value = out.slice(0, 20)
  } finally { loading.value = false }
})

const dateLabel = computed(() => new Date().toLocaleDateString('zh-CN', { month: 'short', day: 'numeric', year: 'numeric' }))
const totalLabel = computed(() => {
  const hit = (lines.value || []).find((l: string) => /\$[0-9]/.test(String(l)))
  const m = hit && String(hit).match(/\$[0-9.,]+/)
  return m ? m[0] : ''
})

</script>
<style scoped>
.page { min-height: 100vh; background: #F7F8FA; color: #1C2430; padding: 12px 16px 40px; padding-top: calc(12px + env(safe-area-inset-top)); }
.head { display: flex; gap: 10px; align-items: center; margin-bottom: 12px; }
.back { border: 0; background: transparent; font-size: 22px; font-weight: 700; cursor: pointer; color: #1C2430; }
.title { font-size: 17px; font-weight: 700; margin: 0; }
.sheet { background: #fff; border: 1px solid #E8EAF0; border-radius: 16px; padding: 16px; }
.brand { font-size: 13px; font-weight: 800; color: #F96141; letter-spacing: -0.02em; }
.hl { margin-top: 4px; font-size: 20px; font-weight: 800; }
.meta { margin-top: 8px; font-size: 11px; color: #6B7280; }
.rule { height: 1px; background: #E8EAF0; margin: 14px 0; }
.line { font-size: 13px; padding: 4px 0; line-height: 1.4; }
.total { display: flex; justify-content: space-between; align-items: baseline; font-size: 16px; font-weight: 700; }
.amt { color: #F96141; font-size: 18px; }
.cta {
  display: flex; align-items: center; justify-content: center; margin-top: 14px; height: 41px;
  border-radius: 12px; background: #F96141; color: #fff; font-size: 14px; font-weight: 600; text-decoration: none;
}
.state { text-align: center; color: #6B7280; padding: 20px 8px; }
</style>
