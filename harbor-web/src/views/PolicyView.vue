<template>
  <div class="fn-page page" data-figma="M36">
    <header class="head">
      <button type="button" class="back" @click="$router.back()" aria-label="back"><ChevronLeft :size="22" :stroke-width="1.75" /></button>
      <div><div class="title">{{ title }}</div><div class="sub">政策说明</div></div>
    </header>
    <div class="tabs">
      <button type="button" class="tab" :class="{ on: kind === 'shipping' }" @click="switchKind('shipping')">物流</button>
      <button type="button" class="tab" :class="{ on: kind === 'privacy' }" @click="switchKind('privacy')">隐私</button>
      <button type="button" class="tab" :class="{ on: kind === 'terms' }" @click="switchKind('terms')">条款</button>
    </div>
    <div v-if="loading" class="state">加载中…</div>
    <div v-for="(b, i) in blocks" :key="i" class="pd">
      <div class="bt">{{ b.title }}</div>
      <div class="bb">{{ b.body }}</div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ChevronLeft } from 'lucide-vue-next'
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { fetchHtmlPath, parsePolicyBlocks } from '@/api/accountApi'
const route = useRoute()
const router = useRouter()
const kind = ref('shipping')
const title = ref('物流政策')
const blocks = ref<{ title: string; body: string }[]>([])
const loading = ref(false)
async function load() {
  loading.value = true
  title.value = kind.value === 'privacy' ? '隐私政策' : kind.value === 'terms' ? '服务条款' : '物流政策'
  try {
    const path = kind.value === 'privacy' ? '/policies/privacy' : kind.value === 'terms' ? '/policies/terms' : '/policies/shipping'
    blocks.value = parsePolicyBlocks(await fetchHtmlPath(path))
  } finally { loading.value = false }
}
function switchKind(k: string) {
  kind.value = k
  router.replace({ path: '/policy', query: { kind: k } })
  load()
}
onMounted(() => {
  kind.value = route.query.kind === 'privacy' ? 'privacy' : route.query.kind === 'terms' ? 'terms' : 'shipping'
  load()
})
watch(() => route.query.kind, (v) => {
  kind.value = v === 'privacy' ? 'privacy' : v === 'terms' ? 'terms' : 'shipping'
  load()
})
</script>
<style lang="scss" scoped>

@import '@/styles/theme.scss';
.page { min-height: 100vh; background: $hb-paper; padding: 12px 16px 40px; padding-top: calc(12px + env(safe-area-inset-top)); }
.head { display: flex; gap: 12px; align-items: center; margin-bottom: 16px; }
.back { width: 40px; height: 40px; border: 0; border-radius: 14px; background: #fff; color: #121816; display: inline-flex; align-items: center; justify-content: center; box-shadow: 0 4px 16px rgba(18,24,22,0.06); cursor: pointer; }
.title { font-size: 24px; font-weight: 720; }
.sub { font-size: 12px; color: $hb-muted; margin-top: 2px; }
.state { text-align: center; color: $hb-muted; padding: 36px 8px; }
.card { background: $hb-white; border-radius: 20px; padding: 16px; box-shadow: $hb-shadow-soft; }
.btn { display: inline-flex; align-items: center; justify-content: center; border: 0; border-radius: 16px; padding: 14px 16px; background: $hb-forest; color: #fff; font-weight: 720; cursor: pointer; width: 100%; margin-top: 12px; text-decoration: none; box-sizing: border-box; }
.btn.soft { background: $hb-soft; color: $hb-forest; }
.btn.coral { background: $hb-coral; color: #fff; }
.shop { display: block; margin-top: 12px; text-align: center; color: $hb-forest; font-weight: 680; font-size: 13px; }

.tabs { display: flex; gap: 8px; margin-bottom: 14px; }
.tab { flex: 1; border: 0; text-align: center; padding: 12px; border-radius: 999px; background: $hb-white; font-weight: 650; box-shadow: $hb-shadow-soft; cursor: pointer; }
.tab.on { background: $hb-forest; color: #fff; }
.pd { background: $hb-white; border-radius: 16px; padding: 14px; margin-bottom: 10px; box-shadow: $hb-shadow-soft; }
.bt { font-weight: 720; color: $hb-forest; margin-bottom: 6px; }
.bb { font-size: 13px; color: $hb-muted; line-height: 1.45; }

.fn-page { --ink:#1C2430; --teal:#0E7490; --amber:#F96141; --sand:#FCFAF8; }
</style>
