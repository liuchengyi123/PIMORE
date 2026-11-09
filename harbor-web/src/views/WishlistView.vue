<template>
  <AgShell tabs="me">
    <header class="hero">
      <div class="row">
        <div>
          <h1>{{ tx('心愿单', 'Wishlist') }}</h1>
          <p>{{ tx('把喜欢的小物留下来', 'Save the little things you love') }} ♥</p>
        </div>
        <button type="button" class="edit" @click="editing = !editing">{{ editing ? tx('完成', 'Done') : tx('编辑', 'Edit') }}</button>
      </div>
    </header>

    <div class="body">
      <div class="tools">
        <button type="button" class="all" @click="toggleAll">
          <span class="radio" :class="{ on: allOn }" />
          <span>
            <b>{{ tx('全选', 'Select all') }}</b>
            <small>{{ tx(`已选 ${picked.size} 件`, `${picked.size} items selected`) }}</small>
          </span>
        </button>
        <button type="button" class="remove" :disabled="!picked.size" @click="removePicked">
          <Trash2 :size="15" :stroke-width="2" /> {{ tx('移除', 'Remove') }}
        </button>
      </div>

      <p v-if="toast" class="ag-toast">{{ toast }}</p>
      <div v-if="loading" class="ag-empty"><p>{{ tx('加载中…', 'Loading…') }}</p></div>
      <div v-else-if="loginRequired" class="ag-empty">
        <h3>{{ tx('登录后同步心愿单', 'Sign in to sync your wishlist') }}</h3>
        <router-link class="ag-cta" style="margin-top:14px" :to="{ path: '/login', query: { next: '/wishlist' } }">{{ tx('登录', 'Sign in') }}</router-link>
      </div>
      <div v-else-if="!visible.length" class="ag-empty">
        <Heart :size="36" color="#F96141" />
        <h3>{{ tx('心愿单还是空的', 'Nothing saved yet') }}</h3>
        <p>{{ tx('在商品页点收藏，小物会出现在这里。', 'Tap the heart on a product and it will land here.') }}</p>
      </div>
      <div v-else class="grid">
        <article v-for="p in visible" :key="p.sku" class="card">
          <button type="button" class="photo" @click="open(p)">
            <img v-if="p.image" :src="p.image" :alt="p.name" />
            <span v-else class="ph">{{ p.name.slice(0, 8) }}</span>
          </button>
          <button type="button" class="heart" :aria-label="tx('移除', 'Remove')" @click="hide(p.sku)">
            <Heart :size="16" :stroke-width="2" color="#fff" fill="#F96141" />
          </button>
          <button v-if="editing" type="button" class="tick" :class="{ on: picked.has(p.sku) }" @click="toggle(p.sku)" />
          <div class="meta" @click="open(p)">
            <div class="nm">{{ p.name }}</div>
            <div class="spec">{{ p.blurb || p.category || tx('家居好物', 'Home essential') }}</div>
            <div class="price">{{ money(p.price) }}</div>
          </div>
          <button type="button" class="add" @click="add(p)">
            <ShoppingCart :size="15" :stroke-width="2" /> {{ tx('加入购物车', 'Add to cart') }}
          </button>
        </article>
      </div>
    </div>
  </AgShell>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Heart, ShoppingCart, Trash2 } from 'lucide-vue-next'
import AgShell from '@/components/account/AgShell.vue'
import { fetchWishlistHtml } from '@/api/accountApi'
import { money, parseFeedCards, type Product } from '@/api/products'
import { useCart } from '@/composables/cart'
import { useZh } from '@/composables/zh'

const HIDE = 'harbor_wish_hidden'
const { tx } = useZh()
const router = useRouter()
const cart = useCart()
const products = ref<Product[]>([])
const loading = ref(true)
const loginRequired = ref(false)
const editing = ref(false)
const picked = ref(new Set<string>())
const hidden = ref(new Set<string>())
const toast = ref('')

const visible = computed(() => products.value.filter((p) => !hidden.value.has(p.sku)))
const allOn = computed(() => visible.value.length > 0 && visible.value.every((p) => picked.value.has(p.sku)))

onMounted(async () => {
  try {
    hidden.value = new Set(JSON.parse(localStorage.getItem(HIDE) || '[]'))
  } catch { /* ignore */ }
  try {
    const html = await fetchWishlistHtml()
    if (/name=["']password["']/i.test(html) && !/class=["']card["']/i.test(html)) {
      loginRequired.value = true
      return
    }
    products.value = parseFeedCards(html)
  } finally { loading.value = false }
})

function persistHide() {
  try { localStorage.setItem(HIDE, JSON.stringify([...hidden.value])) } catch { /* ignore */ }
}
function toggle(sku: string) {
  const next = new Set(picked.value)
  if (next.has(sku)) next.delete(sku)
  else next.add(sku)
  picked.value = next
}
function toggleAll() {
  picked.value = allOn.value ? new Set() : new Set(visible.value.map((p) => p.sku))
}
function hide(sku: string) {
  hidden.value = new Set([...hidden.value, sku])
  const next = new Set(picked.value)
  next.delete(sku)
  picked.value = next
  persistHide()
}
function removePicked() {
  hidden.value = new Set([...hidden.value, ...picked.value])
  picked.value = new Set()
  persistHide()
  toast.value = tx('已从心愿单移除', 'Removed from wishlist')
}
function open(p: Product) {
  router.push({ path: '/pdp', query: { sku: p.sku } })
}
function add(p: Product) {
  cart.add(p)
  toast.value = tx('已加入购物车', 'Added to cart')
}
</script>

<style scoped>
.hero {
  background: #F96141; color: #fff;
  padding: 18px 16px 20px;
  padding-top: calc(18px + env(safe-area-inset-top));
}
.row { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
.hero h1 { margin: 0; font-size: 32px; font-weight: 800; letter-spacing: -0.045em; }
.hero p { margin: 4px 0 0; font-size: 14px; opacity: 0.92; }
.edit { border: 0; background: transparent; color: #fff; font-size: 16px; font-weight: 650; cursor: pointer; padding: 6px 0; }
.body { padding: 14px 16px 8px; }
.tools { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.all { display: flex; align-items: center; gap: 10px; border: 0; background: transparent; text-align: left; cursor: pointer; color: inherit; padding: 0; }
.all b { display: block; font-size: 14px; }
.all small { display: block; color: #8B919A; font-size: 12px; margin-top: 2px; }
.radio { width: 22px; height: 22px; border-radius: 50%; border: 1.5px solid #D5D0CA; box-sizing: border-box; }
.radio.on { border: 6px solid #F96141; }
.remove {
  display: inline-flex; align-items: center; gap: 6px; height: 36px; padding: 0 14px;
  border: 0; border-radius: 999px; background: #FFF1EC; color: #F96141; font-weight: 700; cursor: pointer;
}
.remove:disabled { opacity: 0.45; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.card { position: relative; background: #fff; border-radius: 18px; padding: 8px 8px 12px; box-shadow: 0 8px 24px rgba(28,36,48,0.05); }
.photo {
  display: block; width: 100%; aspect-ratio: 1.05; border: 0; border-radius: 14px; overflow: hidden;
  background: #F3EEE8; padding: 0; cursor: pointer; position: relative;
}
.photo img { width: 100%; height: 100%; object-fit: cover; display: block; }
.ph { position: absolute; inset: 0; display: grid; place-items: center; color: #fff; font-weight: 700; background: linear-gradient(160deg, #F7C7B8, #F96141); }
.heart, .tick {
  position: absolute; top: 16px; width: 28px; height: 28px; border: 0; border-radius: 50%;
  display: grid; place-items: center; cursor: pointer;
}
.heart { right: 16px; background: transparent; padding: 0; }
.tick { left: 16px; background: #fff; border: 1.5px solid #E5E0DA; }
.tick.on { background: #F96141; border-color: #F96141; box-shadow: inset 0 0 0 4px #fff; }
.meta { padding: 8px 4px 0; cursor: pointer; }
.nm { font-size: 14px; font-weight: 800; line-height: 1.3; min-height: 36px; }
.spec { margin-top: 2px; font-size: 12px; color: #8B919A; min-height: 16px; }
.price { margin-top: 6px; color: #F96141; font-size: 18px; font-weight: 800; }
.add {
  margin-top: 8px; width: 100%; height: 38px; border: 0; border-radius: 999px; background: #F96141; color: #fff;
  font-weight: 750; font-size: 13.5px; display: inline-flex; align-items: center; justify-content: center; gap: 6px; cursor: pointer;
}
</style>
