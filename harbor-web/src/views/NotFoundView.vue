<template>
  <div class="page" data-figma="1:60">
    <header class="top">
      <router-link to="/home" class="brand">
        <span class="mark" aria-hidden="true"><Home :size="16" :stroke-width="2.2" /></span>
        <span>
          <span class="logo">Harbor</span>
          <span class="tag">{{ zh ? '家居好物 · $1–$10' : 'Home goods · $1–$10' }}</span>
        </span>
      </router-link>
      <div class="tools">
        <router-link to="/search" aria-label="搜索"><Search :size="22" /></router-link>
        <router-link to="/cart" class="cart" aria-label="购物车">
          <ShoppingCart :size="22" />
          <i v-if="count">{{ count > 99 ? '99+' : count }}</i>
        </router-link>
      </div>
    </header>

    <div class="stage">
      <div class="code" aria-hidden="true">
        <i class="spark a" /><i class="spark b" /><i class="spark c" /><i class="spark d" />
        404
      </div>
      <div class="still" aria-hidden="true">
        <img class="pot" :src="pot" alt="" />
        <img class="soft" :src="soft" alt="" />
        <img class="basket" :src="basket" alt="" />
      </div>
      <h1>{{ zh ? '页面不存在' : 'Page not found' }}</h1>
      <p class="lead">{{ zh ? '你要找的页面不存在，或已经搬走了。' : "Looks like the page you're looking for doesn't exist (or moved)." }}</p>
      <p class="soft-copy">{{ zh ? '别担心，我们带你回去淘家居好物。' : "No worries — let's get you back to great home finds!" }}</p>
      <router-link class="btn solid" to="/home"><Home :size="16" /> {{ zh ? '回首页' : 'Back to home' }}</router-link>
      <router-link class="btn ghost" to="/browse"><LayoutGrid :size="16" /> {{ zh ? '逛逛家居' : 'Browse home goods' }}</router-link>
      <div class="foot">
        <span class="house"><Home :size="16" /></span>
        <p>{{ zh ? '好物，一点就到。' : 'Great finds are just a tap away!' }}</p>
      </div>
    </div>
    <AppTabBar active="home" variant="wish" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Home, LayoutGrid, Search, ShoppingCart } from 'lucide-vue-next'
import { useCart } from '@/composables/cart'
import { useI18n } from '@/composables/i18n'
import AppTabBar from '@/components/AppTabBar.vue'
import pot from '@/assets/home/just-1.jpg'
import soft from '@/assets/home/new-2.jpg'
import basket from '@/assets/home/new-3.jpg'

const { lang } = useI18n()
const zh = computed(() => String(lang.value).startsWith('zh'))
const cart = useCart()
const count = computed(() => cart.count.value)
</script>

<style lang="scss" scoped>
.page {
  min-height: 100vh; background: #FCFAF8; color: #1C2430;
  padding: calc(14px + env(safe-area-inset-top)) 16px 0;
  font-family: "Plus Jakarta Sans", "PingFang SC", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
.top { display: flex; align-items: center; justify-content: space-between; }
.brand { display: flex; align-items: center; gap: 8px; color: inherit; }
.mark {
  width: 32px; height: 32px; border-radius: 10px; background: #F96141; color: #fff;
  display: inline-flex; align-items: center; justify-content: center;
}
.logo { display: block; font-size: 20px; font-weight: 800; letter-spacing: -0.04em; line-height: 1; color: #F96141; }
.tag { display: block; margin-top: 2px; font-size: 10px; letter-spacing: 0.06em; color: #8B919A; text-transform: uppercase; }
.tools { display: flex; gap: 14px; color: #1C2430; }
.cart { position: relative; color: inherit; }
.cart i {
  position: absolute; top: -6px; right: -8px; min-width: 16px; height: 16px; padding: 0 4px;
  border-radius: 99px; background: #F96141; color: #fff; font-size: 10px; font-style: normal; font-weight: 800;
  display: grid; place-items: center;
}
.stage { display: flex; flex-direction: column; align-items: center; text-align: center; padding: 8px 4px 8px; }
.code {
  position: relative; font-size: 72px; line-height: 0.85; font-weight: 800; letter-spacing: -0.06em; color: #F96141;
}
.spark {
  position: absolute; background: #F96141; border-radius: 99px;
}
.spark.a { width: 16px; height: 3px; left: -18px; top: 16px; transform: rotate(-28deg); }
.spark.b { width: 8px; height: 3px; left: -14px; top: 30px; }
.spark.c { width: 16px; height: 3px; right: -18px; top: 16px; transform: rotate(28deg); }
.spark.d { width: 8px; height: 3px; right: -14px; top: 30px; }
.still { position: relative; width: 196px; height: 96px; margin-top: 2px; }
.still img { position: absolute; object-fit: cover; border-radius: 14px; box-shadow: 0 6px 16px rgba(28,36,48,0.08); }
.pot { width: 64px; height: 74px; left: 4px; bottom: 0; }
.soft { width: 86px; height: 64px; left: 54px; bottom: 14px; }
.basket { width: 70px; height: 70px; right: 0; bottom: 0; }
h1 { margin: 10px 0 0; font-size: 24px; letter-spacing: -0.03em; font-weight: 800; line-height: 1.15; }
.lead, .soft-copy { margin: 6px 0 0; max-width: 280px; color: #5C6570; font-size: 13px; line-height: 1.35; }
.soft-copy { margin-top: 4px; color: #8B919A; }
.btn {
  display: flex; align-items: center; justify-content: center; gap: 8px;
  width: min(100%, 320px); height: 46px; margin-top: 8px; border-radius: 999px; font-weight: 750; font-size: 15px;
}
.solid { margin-top: 12px; background: #F96141; color: #fff; }
.ghost { border: 1.5px solid #F96141; color: #F96141; background: #fff; }
.foot { margin-top: 14px; color: #8B919A; font-size: 13px; }
.house {
  width: 32px; height: 32px; margin: 0 auto 6px; border-radius: 10px; background: #FFF1EC; color: #F96141;
  display: grid; place-items: center;
}
.foot p { margin: 0; }
</style>
