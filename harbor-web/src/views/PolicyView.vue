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
function kindFromRoute() {
  const path = route.path
  if (path.endsWith('/privacy') || route.query.kind === 'privacy') return 'privacy'
  if (path.endsWith('/terms') || route.query.kind === 'terms') return 'terms'
  return 'shipping'
}
function switchKind(k: string) {
  router.replace({ path: `/policy/${k}` })
}
onMounted(() => {
  kind.value = kindFromRoute()
  load()
})
watch(() => route.fullPath, () => {
  const next = kindFromRoute()
  if (next === kind.value) return
  kind.value = next
  load()
})
</script>
<style lang="scss" scoped>

@import '@/styles/theme.scss';
.page { min-height: 100vh; background: $hb-paper; padding: 10px 16px 32px; padding-top: calc(10px + env(safe-area-inset-top)); }
.head { display: flex; gap: 8px; align-items: center; margin-bottom: 10px; }
.back { width: 34px; height: 34px; border: 0; border-radius: 12px; background: var(--hb-surface); color: var(--hb-ink); display: inline-flex; align-items: center; justify-content: center; cursor: pointer; padding: 0; }
.title { font-size: 20px; font-weight: 800; letter-spacing: -0.03em; line-height: 1.15; color: var(--hb-ink); }
.sub { font-size: 12px; color: var(--hb-muted); margin-top: 2px; }
.state { text-align: center; color: $hb-muted; padding: 36px 8px; }
.card { background: $hb-white; border-radius: 20px; padding: 16px; box-shadow: $hb-shadow-soft; }
.btn { display: inline-flex; align-items: center; justify-content: center; border: 0; border-radius: 16px; padding: 14px 16px; background: $hb-forest; color: var(--hb-on-primary); font-weight: 720; cursor: pointer; width: 100%; margin-top: 12px; text-decoration: none; box-sizing: border-box; }
.btn.soft { background: $hb-soft; color: $hb-forest; }
.btn.coral { background: $hb-coral; color: var(--hb-on-primary); }
.shop { display: block; margin-top: 12px; text-align: center; color: $hb-forest; font-weight: 680; font-size: 13px; }

.tabs { display: flex; gap: 6px; margin-bottom: 8px; }
.tab { flex: 1; height: 34px; border: 0; text-align: center; padding: 0 8px; border-radius: 999px; background: var(--hb-surface); color: var(--hb-ink); font-size: 13px; font-weight: 700; cursor: pointer; }
.tab.on { background: var(--hb-primary-soft); color: var(--hb-primary); }
.pd { background: $hb-white; border: 1px solid var(--hb-line); border-radius: 14px; padding: 10px 12px; margin-bottom: 6px; }
.bt { font-size: 14px; font-weight: 800; color: var(--hb-primary); margin-bottom: 4px; line-height: 1.25; }
.bb { font-size: 12px; color: var(--hb-muted); line-height: 1.4; }

.fn-page { --ink:var(--hb-ink); --teal:var(--hb-primary); --amber:var(--hb-sale); --sand:var(--hb-page); }
</style>
