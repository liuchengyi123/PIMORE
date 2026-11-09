<template>
  <AgShell tabs="me">
    <header class="top ag-top ag-pad">
      <div>
        <AgBrand />
        <div class="ag-tagline">{{ tx('小发现，大家庭。', 'Small finds. Big home.') }}</div>
      </div>
    </header>
    <div class="ag-pad">
      <div class="title">
        <div>
          <h1 class="ag-h1">{{ tx('浏览记录', 'Browsing history') }}</h1>
          <p class="ag-sub">{{ tx('你最近看过的商品', "Items you've recently viewed") }}</p>
        </div>
        <button v-if="products.length" type="button" class="ag-link" @click="clearAll">{{ tx('清空', 'Clear all') }}</button>
      </div>

      <div v-if="loading" class="ag-empty"><p>{{ tx('加载中…', 'Loading…') }}</p></div>
      <div v-else-if="!products.length" class="ag-card ag-empty">
        <h3>{{ tx('还没有浏览记录', 'No browsing history yet') }}</h3>
        <p>{{ note }}</p>
      </div>
      <section v-for="g in groups" :key="g.key">
        <div class="ag-sec">
          <h2>{{ g.label }}</h2>
          <span class="ag-note">{{ g.date }}</span>
        </div>
        <div v-if="g.grid" class="grid">
          <button v-for="p in g.items" :key="p.sku + g.key" type="button" class="cell" @click="open(p)">
            <span class="ph"><img v-if="p.image" :src="p.image" :alt="p.name" /></span>
            <b>{{ p.name }}</b>
            <strong>{{ money(p.price) }}</strong>
          </button>
        </div>
        <button v-for="p in g.list" :key="p.sku + 'r'" type="button" class="row" @click="open(p)">
          <span class="ph"><img v-if="p.image" :src="p.image" :alt="p.name" /></span>
          <span class="mid"><b>{{ p.name }}</b><strong>{{ money(p.price) }}</strong></span>
          <ChevronRight :size="16" color="#C5C0BA" />
        </button>
      </section>
    </div>
  </AgShell>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ChevronRight } from 'lucide-vue-next'
import AgBrand from '@/components/account/AgBrand.vue'
import AgShell from '@/components/account/AgShell.vue'
import { fetchHistoryHtml } from '@/api/accountApi'
import { money, parseFeedCards, type Product } from '@/api/products'
import { clearBrowseHistory, loadBrowseHistory } from '@/composables/browseHistory'
import { useZh } from '@/composables/zh'

interface Item extends Product { ts: number }
const { tx, zh } = useZh()
const router = useRouter()
const products = ref<Item[]>([])
const loading = ref(true)
const note = ref('')

function dayKey(ts: number) {
  const d = new Date(ts)
  return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`
}
const groups = computed(() => {
  const map = new Map<string, Item[]>()
  for (const p of products.value) {
    const k = dayKey(p.ts || Date.now())
    map.set(k, [...(map.get(k) || []), p])
  }
  const today = dayKey(Date.now())
  const y = new Date(); y.setDate(y.getDate() - 1)
  const yday = dayKey(y.getTime())
  return [...map.entries()].map(([key, items], idx) => {
    const label = key === today ? tx('今天', 'Today') : key === yday ? tx('昨天', 'Yesterday') : tx('更早', 'Earlier')
    const date = new Date(items[0].ts || Date.now()).toLocaleDateString(zh.value ? 'zh-CN' : 'en-US', { month: 'short', day: 'numeric', year: 'numeric' })
    const grid = idx === 0 && items.length <= 4
    return { key, label, date, items, grid, list: grid ? [] : items }
  })
})

onMounted(async () => {
  const local = () => loadBrowseHistory().map((b) => ({
    id: b.sku, sku: b.sku, name: b.name, price: Number(b.price) || 0, category: 'Harbor',
    image: b.image || '', images: b.image ? [b.image] : [], live: false, ts: b.ts,
  }))
  try {
    const html = await fetchHistoryHtml()
    const parsed = parseFeedCards(html).map((p, i) => ({ ...p, ts: Date.now() - i * 3600_000 }))
    products.value = parsed.length ? parsed : local()
    note.value = products.value.length ? '' : tx('去逛逛，看过的商品会留在这里。', 'Browse a few items and they will stay here.')
  } catch {
    products.value = local()
    note.value = products.value.length ? tx('这是本机记录', 'Saved on this device') : tx('暂时离线', 'Offline')
  } finally { loading.value = false }
})

function open(p: Product) { router.push({ path: '/pdp', query: { sku: p.sku } }) }
function clearAll() {
  try { clearBrowseHistory() } catch { /* ignore */ }
  products.value = []
  note.value = tx('浏览记录已清空', 'History cleared')
}
</script>

<style scoped>
.top { margin-bottom: 8px; }
.title { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
.grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
.cell, .row { border: 0; background: transparent; padding: 0; text-align: left; cursor: pointer; color: inherit; }
.ph { display: block; background: #F3EEE8; border-radius: 12px; overflow: hidden; }
.cell .ph { aspect-ratio: 1; }
.cell b, .row b { display: block; margin-top: 6px; font-size: 12px; line-height: 1.3; font-weight: 650; }
.cell strong, .row strong { display: block; margin-top: 4px; color: #F96141; font-size: 13px; }
.row { width: 100%; display: flex; align-items: center; gap: 10px; padding: 10px 0; border-bottom: 1px solid #F1ECE6; }
.row .ph { width: 64px; height: 64px; flex: 0 0 auto; }
.row .ph img, .cell .ph img { width: 100%; height: 100%; object-fit: cover; display: block; }
.mid { flex: 1; min-width: 0; }
.row b { margin-top: 0; font-size: 14px; }
</style>
