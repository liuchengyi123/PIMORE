<template>
  <div class="fn-page page" data-figma="M23">
    <header class="sticky">
      <div class="head">
        <div>
          <h1>{{ t('cart_title') }} <small v-if="cart.syncing">…</small></h1>
          <p v-if="lines.length" class="count">{{ lines.length }}</p>
        </div>
        <button v-if="lines.length" type="button" class="clear" @click="clear">{{ t('cart_clear') || '清空' }}</button>
      </div>
      <AppSearchBar compact navigate-on-focus />
    </header>

    <div v-if="!lines.length" class="empty">
      <ShoppingBag :size="40" :stroke-width="1.5" class="empty-ico" />
      <p>{{ t('cart_empty') }}</p>
      <router-link class="btn" to="/home">去逛逛</router-link>
    </div>

    <div v-else class="list">
      <div v-for="line in lines" :key="line.sku + '|' + line.offer" class="row">
        <img v-if="line.image" class="img" :src="line.image" alt="" @click="open(line.sku)" />
        <div class="body" @click="open(line.sku)">
          <div class="name">{{ line.name }}</div>
          <div class="meta">{{ line.size || line.offer || 'default' }}</div>
          <div class="price">{{ money(line.price) }}</div>
        </div>
        <div class="qty">
          <button type="button" @click="bump(line, -1)" aria-label="minus"><Minus :size="14" :stroke-width="2" /></button>
          <span>{{ line.qty }}</span>
          <button type="button" @click="bump(line, 1)" aria-label="plus"><Plus :size="14" :stroke-width="2" /></button>
          <button type="button" class="trash" @click="bump(line, -line.qty)" aria-label="remove">×</button>
        </div>
      </div>
    </div>

    <div v-if="lines.length && minOrder > 0" class="ship-card">
      <div class="ship-row"><span>Minimum order</span><span class="tiny">{{ money(Math.max(0, minOrder - subtotal)) }} more</span></div>
      <div class="ship-bar"><i :style="{ width: Math.min(100, Math.round(subtotal / minOrder * 100)) + '%' }"></i></div>
      <div class="tiny">{{ subtotal >= minOrder ? 'Minimum met · free shipping' : ('Minimum order ' + money(minOrder) + ' · free shipping') }}</div>
    </div>
    <div v-else-if="lines.length" class="ship-card">
      <div class="tiny">Free shipping on this order</div>
    </div>
    <div v-if="lines.length" class="footer">
      <div class="sum">合计 <b>{{ money(subtotal) }}</b></div>
      <button type="button" class="checkout" @click="$router.push('/checkout')">去结算</button>
    </div>
    <AppTabBar active="cart" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Minus, Plus, ShoppingBag } from 'lucide-vue-next'
import { money } from '@/api/products'
import { useCart, type LocalCartLine } from '@/composables/cart'
import { useI18n } from '@/composables/i18n'
import AppTabBar from '@/components/AppTabBar.vue'
import AppSearchBar from '@/components/AppSearchBar.vue'

const { t } = useI18n()
const cart = useCart()
const router = useRouter()
const lines = computed(() => cart.lines.value)
const subtotal = computed(() => cart.subtotal.value)
/** Minimum checkout amount from live cart snapshot; 0 = no minimum. */
const minOrder = computed(() => Number(cart.minOrderAmount?.value ?? cart.freeShipThreshold?.value ?? 0) || 0)

function bump(line: LocalCartLine, delta: number) {
  cart.setQty(line.sku, line.offer || '', line.qty + delta)
}
function clear() {
  cart.clear()
}
function open(sku: string) {
  router.push({ path: '/pdp', query: { sku } })
}
onMounted(() => {
  cart.refreshFromServer()
})
</script>

<style lang="scss" scoped>
@import '@/styles/theme.scss';
.page { min-height: 100vh; background: $hb-paper; padding: 0 16px 120px; }
.sticky {
  position: sticky; top: 0; z-index: 20;
  background: rgba(247,244,239,0.94); backdrop-filter: blur(14px);
  padding: calc(12px + env(safe-area-inset-top)) 0 10px;
}
.head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
h1 { margin: 0; font-size: 24px; color: $hb-ink; font-weight: 780; }
h1 small { font-size: 12px; color: $hb-muted; font-weight: 600; }
.count { margin: 2px 0 0; font-size: 13px; color: $hb-muted; }
.trash { border: 0; background: transparent; color: #9AA0A8; font-size: 18px; cursor: pointer; }
.clear { border: 0; background: transparent; color: $hb-muted; cursor: pointer; font-weight: 650; }
.empty { text-align: center; padding: 64px 12px; color: $hb-muted; }
.empty-ico { color: $hb-muted; opacity: 0.55; margin-bottom: 10px; }
.btn {
  display: inline-block; margin-top: 14px; padding: 11px 18px; border-radius: 14px;
  background: $hb-coral; color: #fff; font-weight: 720;
}
.list { display: flex; flex-direction: column; gap: 10px; margin-top: 12px; }
.row {
  display: flex; gap: 10px; align-items: center; background: $hb-white; border-radius: 18px;
  padding: 12px; box-shadow: $hb-shadow-soft;
}
.img { width: 74px; height: 74px; border-radius: 14px; object-fit: cover; background: $hb-soft; }
.body { flex: 1; min-width: 0; }
.name { font-weight: 680; font-size: 14px; color: $hb-ink; }
.meta { font-size: 12px; color: $hb-muted; margin-top: 2px; }
.price { margin-top: 6px; color: $hb-ink; font-weight: 760; }
.qty { display: flex; align-items: center; gap: 8px; }
.qty button {
  width: 30px; height: 30px; border: 0; border-radius: 10px; background: $hb-paper; cursor: pointer;
  display: inline-flex; align-items: center; justify-content: center; color: $hb-ink;
}
.footer {
  position: fixed; left: 50%; transform: translateX(-50%);
  width: min(100vw, 768px);
  bottom: calc(58px + env(safe-area-inset-bottom));
  background: #F96141; padding: 12px 16px;
  display: flex; align-items: center; gap: 10px; z-index: 90; color: #fff;
}
.sum { flex: 1; font-size: 14px; }
.sum b { color: #fff; font-size: 20px; }
.checkout {
  border: 0; height: 44px; padding: 0 18px; border-radius: 999px; background: #fff; color: #F96141;
  font-weight: 740; cursor: pointer;
}
.ship-card {
  margin: 12px 16px; background: #fff; border: 1px solid $hb-line; border-radius: 16px; padding: 14px;
}
.ship-row { display: flex; justify-content: space-between; font-size: 13px; font-weight: 600; color: $hb-ink; }
.ship-bar { margin-top: 8px; height: 8px; background: #E8E4DC; border-radius: 4px; overflow: hidden; }
.ship-bar > i { display: block; height: 100%; background: $hb-deep; }
.tiny { font-size: 11px; color: $hb-muted; margin-top: 6px; }
.footer .checkout { background: $hb-ink !important; }
.price { color: $hb-price !important; }
.empty { padding: 80px 24px; text-align: center; }
.empty .btn { background: $hb-ink; color: #fff; border-radius: 999px; padding: 10px 18px; text-decoration: none; font-weight: 700; display: inline-block; margin-top: 16px; }

.fn-page { --ink:#1C2430; --teal:#0E7490; --amber:#F96141; --sand:#FCFAF8; }
</style>
