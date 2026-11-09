<template>
  <AgShell tabs="me">
    <header class="brand ag-top ag-pad">
      <div>
        <AgBrand />
        <div class="ag-tagline">{{ tx('每天发现，家更开心。', 'Everyday Finds. Happier Homes.') }}</div>
      </div>
      <div class="tools">
        <button type="button" class="ag-gear" @click="router.push('/help')" :aria-label="tx('通知', 'Notices')"><Bell :size="20" /></button>
        <button type="button" class="ag-gear" @click="router.push('/locale')" :aria-label="tx('设置', 'Settings')"><Settings :size="20" /></button>
      </div>
    </header>

    <div class="ag-pad">
      <h1 class="ag-h1">{{ tx('奖励广场', 'Rewards Plaza') }}</h1>
      <p class="ag-sub">{{ tx('多买多赚，好礼相随。', 'Shop more. Earn more. Get rewarded.') }}</p>

      <section class="hero">
        <div class="crown"><Crown :size="14" /> {{ tx('我的积分', 'Your Points Balance') }}</div>
        <div class="pts">{{ points.toLocaleString('zh-CN') }}</div>
        <div class="val">≈ {{ valueText }}</div>
        <router-link class="view" to="/balance">{{ tx('查看奖励', 'View Rewards') }} ›</router-link>
        <div class="aside">
          <Coins :size="42" color="#F6C445" />
          <em>{{ tx('小积分，\n大幸福。', 'Small points.\nBig home happiness.') }}</em>
        </div>
      </section>

      <div class="ag-sec">
        <div>
          <h2>{{ tx('做任务赚积分', 'Complete Tasks & Earn Points') }}</h2>
          <p>{{ tx('简单动作，真实奖励。', 'Easy actions. Real rewards.') }}</p>
        </div>
      </div>
      <button v-for="t in tasks" :key="t.to" type="button" class="task ag-card" @click="router.push(t.to)">
        <span class="ag-icon"><component :is="t.icon" :size="18" /></span>
        <span class="mid">
          <b>{{ t.title }}</b>
          <small>{{ t.sub }}</small>
        </span>
        <span class="pts-pill">{{ t.pts }}</span>
        <ChevronRight :size="16" color="#C5C0BA" />
      </button>

      <div class="ag-sec">
        <div>
          <h2>{{ tx('兑换积分', 'Redeem Your Points') }}</h2>
          <p>{{ tx('积分可换优惠券或精选好物。', 'Use your points for coupons or great products.') }}</p>
        </div>
        <button type="button" class="ag-link" @click="router.push('/browse')">{{ tx('查看全部', 'View All') }} ›</button>
      </div>
      <div class="ag-tabs">
        <button type="button" :class="{ on: redeem === 'coupon' }" @click="redeem = 'coupon'">{{ tx('优惠券', 'Coupons') }}</button>
        <button type="button" :class="{ on: redeem === 'product' }" @click="redeem = 'product'">{{ tx('商品', 'Products') }}</button>
      </div>

      <div v-if="redeem === 'coupon'" class="redeem">
        <article v-for="c in couponOffers" :key="c.title" class="tile ag-card">
          <div class="thumb soft"><Ticket :size="28" color="#F96141" /></div>
          <span class="cost">{{ c.cost }}</span>
          <b>{{ c.title }}</b>
          <small>{{ c.sub }}</small>
          <router-link to="/coupons">{{ tx('兑换', 'Redeem') }}</router-link>
        </article>
      </div>
      <div v-else class="redeem">
        <article v-for="p in products" :key="p.sku" class="tile ag-card">
          <div class="thumb">
            <img v-if="p.image" :src="p.image" :alt="p.name" />
          </div>
          <span class="cost">{{ Math.max(100, Math.round((p.price || 1) * 100)) }} {{ tx('积分', 'pts') }}</span>
          <b>{{ p.name }}</b>
          <small>{{ p.category }}</small>
          <button type="button" @click="router.push({ path: '/pdp', query: { sku: p.sku } })">{{ tx('兑换', 'Redeem') }}</button>
        </article>
        <p v-if="!products.length" class="ag-note">{{ tx('商品加载后会出现在这里。', 'Products show up here once the catalog loads.') }}</p>
      </div>
    </div>
  </AgShell>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Bell, CalendarCheck, ChevronRight, Coins, Crown, PenLine, Settings, Ticket, UserPlus } from 'lucide-vue-next'
import AgBrand from '@/components/account/AgBrand.vue'
import AgShell from '@/components/account/AgShell.vue'
import { fetchBalancePanel } from '@/api/accountApi'
import { listProducts, type Product } from '@/api/products'
import { useZh } from '@/composables/zh'

const { tx, zh } = useZh()
const router = useRouter()
const balance = ref(0)
const products = ref<Product[]>([])
const redeem = ref<'coupon' | 'product'>('coupon')
const points = computed(() => Math.max(0, Math.round(balance.value * 100)))
const valueText = computed(() => {
  const n = balance.value
  return Number.isFinite(n) && n > 0 ? `$${n.toFixed(2)}` : (zh.value ? '以余额为准' : 'from your balance')
})

const tasks = computed(() => [
  { to: '/checkin', icon: CalendarCheck, title: tx('每日签到', 'Daily Check-in'), sub: tx('明天再来，积分继续涨', 'Come back tomorrow for more points!'), pts: tx('+10 积分', '+10 pts') },
  { to: '/contact', icon: PenLine, title: tx('写评价', 'Write a Review'), sub: tx('分享想法，帮助其他人', 'Share your thoughts and help others!'), pts: tx('+50 积分', '+50 pts') },
  { to: '/invite', icon: UserPlus, title: tx('邀请好友', 'Invite Friends'), sub: tx('他们购物，双方都有奖励', 'They shop, you both earn!'), pts: tx('+200 积分', '+200 pts') },
])
const couponOffers = computed(() => [
  { title: tx('$5 优惠', '$5 Off'), sub: tx('满 $20 可用', 'Any Order Over $20'), cost: tx('500 积分', '500 pts') },
  { title: tx('$3 优惠', '$3 Off'), sub: tx('满 $15 可用', 'Any Order Over $15'), cost: tx('300 积分', '300 pts') },
  { title: tx('包邮券', 'Free ship'), sub: tx('满 $40 可用', 'Orders over $40'), cost: tx('400 积分', '400 pts') },
])

onMounted(async () => {
  try {
    const b = await fetchBalancePanel()
    const m = String(b.balanceText || '').replace(/,/g, '').match(/(\d+(?:\.\d+)?)/)
    balance.value = m ? Number(m[1]) : 0
  } catch { /* guest */ }
  try { products.value = (await listProducts('recommended', 1)).slice(0, 3) } catch { /* offline */ }
})
</script>

<style scoped>
.brand { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 12px; }
.tools { display: flex; }
.hero {
  position: relative; margin-top: 14px; border-radius: 22px; padding: 16px 16px 14px; color: #fff; overflow: hidden;
  background: linear-gradient(145deg, #FF8A6A, #F96141 60%, #F04A2A);
}
.crown { display: flex; align-items: center; gap: 6px; font-weight: 700; }
.pts { margin-top: 6px; font-size: 40px; font-weight: 800; letter-spacing: -0.04em; line-height: 1; }
.val { margin-top: 4px; opacity: 0.9; font-size: 13px; }
.view {
  margin-top: 14px; display: flex; align-items: center; justify-content: center; height: 42px; border-radius: 999px;
  background: #fff; color: #1C2430; font-weight: 800; text-decoration: none;
}
.aside { position: absolute; right: 14px; top: 18px; text-align: right; }
.aside em { display: block; margin-top: 4px; font-style: normal; font-family: 'Segoe Script', cursive; font-size: 13px; white-space: pre-line; line-height: 1.15; }
.task {
  width: 100%; display: flex; align-items: center; gap: 10px; padding: 12px; margin-bottom: 10px;
  border: 1px solid #F1ECE6; cursor: pointer; text-align: left; color: inherit;
}
.mid { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.mid b { font-size: 14.5px; }
.mid small { color: #8B919A; font-size: 12px; margin-top: 2px; }
.pts-pill { background: #F96141; color: #fff; border-radius: 999px; padding: 6px 10px; font-size: 12px; font-weight: 800; white-space: nowrap; }
.redeem { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-top: 12px; }
.tile { padding: 8px 8px 10px; display: flex; flex-direction: column; gap: 4px; }
.thumb { height: 78px; border-radius: 12px; background: #F6F1EC; overflow: hidden; }
.thumb.soft { display: grid; place-items: center; background: #FFF1EC; }
.thumb img { width: 100%; height: 100%; object-fit: cover; }
.cost { align-self: flex-start; background: #F96141; color: #fff; font-size: 10px; font-weight: 800; border-radius: 999px; padding: 2px 6px; }
.tile b { font-size: 12.5px; line-height: 1.25; }
.tile small { color: #8B919A; font-size: 11px; }
.tile a, .tile button {
  margin-top: auto; height: 30px; border: 0; border-radius: 999px; background: #F96141; color: #fff;
  font-weight: 750; font-size: 12px; text-decoration: none; display: grid; place-items: center; cursor: pointer;
}
</style>
