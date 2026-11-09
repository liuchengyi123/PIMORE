<template>
  <div class="page" data-figma="1:20">
    <header class="bar">
      <button type="button" class="back" @click="$router.back()" aria-label="返回">
        <ChevronLeft :size="22" />
      </button>
      <h1>{{ zh ? '对比' : 'Compare' }}</h1>
      <span />
    </header>
    <div class="body">
      <h2>{{ zh ? '挑一件更适合家里的' : 'Find the best fit for your home' }}</h2>
      <p class="lead">{{ zh ? '并排看看，选你真正用得上的。' : 'Compare products side by side and choose what works for you.' }}</p>

      <div v-if="loading" class="state">{{ zh ? '加载中…' : 'Loading…' }}</div>
      <div v-else-if="!shown.length" class="state">
        <div>{{ zh ? '还没有可对比的商品' : 'Nothing to compare yet.' }}</div>
        <router-link class="go" to="/browse">{{ zh ? '去逛逛' : 'Browse products' }}</router-link>
      </div>
      <template v-else>
        <div class="scroller">
          <div class="cols" :style="{ gridTemplateColumns: shown.length > 3 ? `repeat(${shown.length}, 148px)` : `repeat(${shown.length}, minmax(0, 1fr))` }">
            <article v-for="p in shown" :key="p.sku" class="card">
              <div class="shot" @click="open(p)"><img v-if="p.image" :src="p.image" :alt="p.name" /></div>
              <div class="nm" @click="open(p)">{{ p.name }}</div>
              <div class="price">{{ money(p.price) }}</div>
              <button type="button" class="add" @click="add(p)">{{ zh ? '加入购物车' : 'Add to cart' }}</button>
            </article>
          </div>
          <table>
            <tbody>
              <tr v-for="row in rows" :key="row.key">
                <th>
                  <component :is="row.icon" :size="14" />
                  {{ row.label }}
                </th>
                <td v-for="p in shown" :key="row.key + p.sku">{{ row.cell(p) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="note">
          <span class="house" aria-hidden="true"><Home :size="16" /></span>
          <div>
            <b>{{ zh ? '日常家居，价格实在。' : 'Everyday home goods. Great value.' }}</b>
            <p>{{ zh ? '好物从 $1 到 $10。' : 'Quality finds from $1 – $10.' }}</p>
          </div>
        </div>
      </template>
    </div>
    <AppTabBar active="home" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ChevronLeft, Home, Leaf, Ruler, Tag, Truck } from 'lucide-vue-next'
import { listCompareProducts, money, type Product } from '@/api/products'
import { shelf } from '@/catalog/shelf'
import { useCart } from '@/composables/cart'
import { useI18n } from '@/composables/i18n'
import AppTabBar from '@/components/AppTabBar.vue'

const { lang } = useI18n()
const zh = computed(() => String(lang.value).startsWith('zh'))
const cart = useCart()
const router = useRouter()
const products = ref<Product[]>([])
const loading = ref(true)
const shown = computed(() => products.value.slice(0, 4))

const rows = computed(() => {
  const list = [
    { key: 'material', icon: Leaf, label: zh.value ? '材质' : 'Material', cell: (p: Product) => p.material || '—' },
    {
      key: 'size', icon: Ruler, label: zh.value ? '规格' : 'Size',
      cell: (p: Product) => (p.sizes && p.sizes.length ? p.sizes.join(' / ') : (p.offers?.map((o) => o.label).join(' / ') || '—')),
    },
    { key: 'price', icon: Tag, label: zh.value ? '价格' : 'Price', cell: (p: Product) => money(p.price) },
    { key: 'ship', icon: Truck, label: zh.value ? '物流' : 'Shipping', cell: (p: Product) => p.shipsIn || (zh.value ? '可追踪' : 'Tracked') },
  ]
  return list
})

function open(p: Product) { router.push({ path: '/pdp', query: { sku: p.sku } }) }
function add(p: Product) { cart.add(p) }

onMounted(async () => {
  try {
    const res = await listCompareProducts()
    const live = Array.isArray(res) ? res : (res?.products || [])
    products.value = live.length ? live : shelf.filter((p) => p.material).slice(0, 3)
  } catch {
    products.value = []
  } finally {
    loading.value = false
  }
})
</script>

<style lang="scss" scoped>
.page {
  min-height: 100vh; background: #FCFAF8; color: #1C2430;
  font-family: "Plus Jakarta Sans", "PingFang SC", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
.bar {
  display: grid; grid-template-columns: 40px 1fr 40px; align-items: center;
  background: #F96141; color: #fff; padding: calc(10px + env(safe-area-inset-top)) 8px 12px;
}
.back { border: 0; background: transparent; color: #fff; width: 40px; height: 36px; cursor: pointer; }
h1 { margin: 0; text-align: center; font-size: 17px; font-weight: 800; }
.body { padding: 16px; }
h2 { margin: 0; font-size: 20px; letter-spacing: -0.03em; }
.lead { margin: 6px 0 0; color: #8B919A; font-size: 13px; line-height: 1.45; }
.state { text-align: center; color: #8B919A; padding: 36px 8px; }
.go { display: inline-block; margin-top: 10px; color: #F96141; font-weight: 700; }
.scroller { overflow-x: auto; margin-top: 16px; }
.cols { display: grid; gap: 10px; min-width: 100%; }
.card { min-width: 0; }
.shot { aspect-ratio: 1; border-radius: 14px; overflow: hidden; background: #F6F4F2; cursor: pointer; }
.shot img { width: 100%; height: 100%; object-fit: cover; display: block; }
.nm { margin-top: 8px; font-size: 12px; font-weight: 700; line-height: 1.35; min-height: 2.6em; cursor: pointer; }
.price { margin-top: 4px; color: #F96141; font-size: 16px; font-weight: 800; }
.add {
  margin-top: 8px; width: 100%; height: 34px; border: 0; border-radius: 999px;
  background: #F96141; color: #fff; font-weight: 750; font-size: 12px; cursor: pointer;
  padding: 0 4px; white-space: nowrap;
}
table { width: 100%; border-collapse: collapse; margin-top: 8px; }
th, td { border-bottom: 1px solid #F1EEEA; padding: 12px 8px; font-size: 12px; text-align: center; vertical-align: middle; }
th { text-align: left; color: #5C6570; font-weight: 700; white-space: nowrap; }
th :deep(svg) { color: #F96141; vertical-align: -2px; margin-right: 4px; }
.note {
  margin-top: 16px; background: #FFF6F3; border-radius: 16px; padding: 12px;
  display: flex; gap: 10px; align-items: center;
}
.house {
  width: 36px; height: 36px; border-radius: 12px; background: #fff; color: #F96141;
  display: grid; place-items: center; flex: none;
}
.note b { display: block; font-size: 13px; }
.note p { margin: 2px 0 0; color: #8B919A; font-size: 12px; }
</style>
