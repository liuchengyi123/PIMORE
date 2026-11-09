<template>
  <div class="page" data-figma="1:42">
    <header class="top">
      <router-link to="/home" class="brand">
        <span class="mark" aria-hidden="true"><Home :size="16" :stroke-width="2.2" /></span>
        <span>
          <span class="logo">Harbor</span>
          <span class="tag">{{ zh ? '小物见喜，家里更暖' : 'Small finds. Big home.' }}</span>
        </span>
      </router-link>
    </header>
    <div class="head">
      <div>
        <h1>{{ zh ? '浏览记录' : 'Browsing history' }}</h1>
        <p>{{ zh ? '你最近看过的商品' : "Items you've recently viewed" }}</p>
      </div>
      <button v-if="items.length" type="button" class="clear" @click="clearLocal">{{ zh ? '清空' : 'Clear all' }}</button>
    </div>

    <div v-if="loading" class="state">{{ zh ? '加载中…' : 'Loading…' }}</div>
    <div v-else-if="!groups.length" class="state">{{ zh ? '还没有浏览记录' : 'No browsing history yet.' }}</div>
    <template v-else>
      <section v-for="(group, gi) in groups" :key="group.key" class="group">
        <div class="sec">
          <h2>{{ group.label }}</h2>
          <span>{{ group.stamp }}</span>
        </div>
        <div v-if="gi === 0 && group.horizontal" class="hrow">
          <article v-for="p in group.items" :key="p.sku" class="mini" @click="go(p)">
            <div class="shot">
              <img v-if="p.image" :src="p.image" :alt="p.name" />
              <span v-if="pack(p)" class="pack">{{ pack(p) }}</span>
            </div>
            <div class="nm">{{ p.name }}</div>
            <div class="price">{{ money(p.price) }}</div>
          </article>
        </div>
        <div v-else class="list">
          <button v-for="p in group.items" :key="p.sku" type="button" class="line" @click="go(p)">
            <img v-if="p.image" :src="p.image" alt="" />
            <span class="meta">
              <span class="nm">{{ p.name }}</span>
              <span class="price">{{ money(p.price) }}</span>
            </span>
            <ChevronRight :size="18" />
          </button>
        </div>
      </section>
    </template>
    <AppTabBar active="me" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ChevronRight, Home } from 'lucide-vue-next'
import { fetchHistoryHtml } from '@/api/accountApi'
import { money, parseFeedCards } from '@/api/products'
import { clearBrowseHistory, loadBrowseHistory } from '@/composables/browseHistory'
import { useI18n } from '@/composables/i18n'
import AppTabBar from '@/components/AppTabBar.vue'

interface HistItem {
  sku: string
  name: string
  image?: string
  price: number
  ts: number
}

const { lang } = useI18n()
const zh = computed(() => String(lang.value).startsWith('zh'))
const router = useRouter()
const items = ref<HistItem[]>([])
const loading = ref(true)

const groups = computed(() => {
  const buckets = new Map<string, HistItem[]>()
  for (const item of items.value) {
    const key = dayKey(item.ts)
    const list = buckets.get(key) || []
    list.push(item)
    buckets.set(key, list)
  }
  return [...buckets.entries()]
    .sort((a, b) => b[1][0].ts - a[1][0].ts)
    .map(([key, list], index) => ({
      key,
      label: dayLabel(list[0].ts),
      stamp: dayStamp(list[0].ts),
      horizontal: index === 0 && isToday(list[0].ts),
      items: list,
    }))
})

function dayKey(ts: number) {
  const d = new Date(ts)
  return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`
}
function startOfDay(offset = 0) {
  const d = new Date()
  d.setHours(0, 0, 0, 0)
  return d.getTime() - offset * 86400000
}
function isToday(ts: number) { return ts >= startOfDay(0) }
function dayLabel(ts: number) {
  if (ts >= startOfDay(0)) return zh.value ? '今天' : 'Today'
  if (ts >= startOfDay(1)) return zh.value ? '昨天' : 'Yesterday'
  return new Date(ts).toLocaleDateString(zh.value ? 'zh-CN' : 'en-US', { month: 'long', day: 'numeric' })
}
function dayStamp(ts: number) {
  return new Date(ts).toLocaleDateString(zh.value ? 'zh-CN' : 'en-US', { year: 'numeric', month: 'short', day: 'numeric' })
}
function pack(p: HistItem) {
  const m = p.name.match(/(\d+)\s*(件|条|套|pack|pcs)/i)
  return m ? `${m[1]} ${zh.value ? '件' : 'pack'}` : ''
}
function go(p: HistItem) { router.push({ path: '/pdp', query: { sku: p.sku } }) }
function clearLocal() {
  try { clearBrowseHistory() } catch { /* */ }
  items.value = []
}

onMounted(async () => {
  const local = loadBrowseHistory().map((b) => ({
    sku: b.sku,
    name: b.name,
    image: b.image || '',
    price: Number(b.price) || 0,
    ts: b.ts || Date.now(),
  }))
  const bySku = new Map(local.map((b) => [b.sku, b]))
  try {
    const remote = parseFeedCards(await fetchHistoryHtml())
    remote.forEach((p, i) => {
      if (bySku.has(p.sku)) return
      bySku.set(p.sku, {
        sku: p.sku,
        name: p.name,
        image: p.image || '',
        price: Number(p.price) || 0,
        ts: Date.now() - i * 1000,
      })
    })
  } catch { /* local history still shown */ }
  items.value = [...bySku.values()].sort((a, b) => b.ts - a.ts)
  loading.value = false
})
</script>

<style lang="scss" scoped>
.page {
  min-height: 100vh; background: #FCFAF8; color: #1C2430;
  padding: calc(12px + env(safe-area-inset-top)) 16px 8px;
  font-family: "Plus Jakarta Sans", "PingFang SC", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
.brand { display: flex; align-items: center; gap: 8px; color: inherit; }
.mark {
  width: 32px; height: 32px; border-radius: 10px; background: #F96141; color: #fff;
  display: inline-flex; align-items: center; justify-content: center;
}
.logo { display: block; font-size: 20px; font-weight: 800; letter-spacing: -0.04em; line-height: 1; color: #F96141; }
.tag { display: block; margin-top: 2px; font-size: 11px; color: #8B919A; }
.head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; margin-top: 12px; }
h1 { margin: 0; font-size: 24px; letter-spacing: -0.04em; font-weight: 800; line-height: 1.1; }
.head p { margin: 2px 0 0; color: #8B919A; font-size: 13px; }
.clear { border: 0; background: transparent; color: #F96141; font-weight: 750; font-size: 14px; cursor: pointer; padding: 2px 0; }
.state { text-align: center; color: #8B919A; padding: 36px 8px; }
.group { margin-top: 14px; }
.sec { display: flex; align-items: baseline; justify-content: space-between; }
.sec h2 { margin: 0; font-size: 16px; font-weight: 800; }
.sec span { color: #8B919A; font-size: 12px; }
.hrow { display: flex; gap: 8px; overflow-x: auto; margin-top: 8px; padding-bottom: 2px; scrollbar-width: none; }
.hrow::-webkit-scrollbar { display: none; }
.mini { flex: 0 0 84px; cursor: pointer; }
.shot { position: relative; aspect-ratio: 1; border-radius: 12px; overflow: hidden; background: #F6F4F2; }
.shot img, .line img { width: 100%; height: 100%; object-fit: cover; display: block; }
.pack {
  position: absolute; left: 6px; top: 6px; background: #F96141; color: #fff;
  font-size: 10px; font-weight: 800; border-radius: 999px; padding: 2px 6px;
}
.mini .nm {
  margin-top: 4px; font-size: 11px; font-weight: 650; line-height: 1.25; min-height: 2.5em;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.price { color: #F96141; font-weight: 800; font-size: 13px; letter-spacing: -0.02em; }
.list { margin-top: 4px; }
.line {
  width: 100%; display: flex; align-items: center; gap: 10px; padding: 8px 0;
  border: 0; border-bottom: 1px solid #F1EEEA; background: transparent; text-align: left; cursor: pointer; color: inherit;
}
.line img { width: 56px; height: 56px; border-radius: 10px; object-fit: cover; background: #F6F4F2; flex: none; }
.meta { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.line .nm {
  font-size: 14px; font-weight: 700; line-height: 1.25;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.line :deep(svg) { color: #C4C8CE; flex: none; }
</style>
