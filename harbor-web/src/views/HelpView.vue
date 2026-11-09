<template>
  <AgShell tabs="home">
    <header class="top ag-top ag-pad">
      <AgBrand />
      <div class="side">{{ tx('每天的家居好物\n花得更少', 'EVERYDAY HOME GOODS\nFOR LESS') }}</div>
    </header>
    <div class="ag-pad">
      <h1 class="ag-h1">{{ tx('帮助中心', 'Help Center') }}</h1>
      <p class="ag-sub">{{ tx('查找答案，或联系客服。', 'Find answers to your questions or get in touch with our support team.') }}</p>
      <label class="ag-search">
        <Search :size="16" />
        <input v-model="q" :placeholder="tx('搜索常见问题（例如物流、退货、支付…）', 'Search FAQs (e.g. shipping, returns, payment...)')" />
      </label>

      <div class="cats">
        <button v-for="c in cats" :key="c.to" type="button" @click="router.push(c.to)">
          <span class="ag-icon solid"><component :is="c.icon" :size="18" /></span>
          <b>{{ c.t }} <ChevronRight :size="14" /></b>
          <small>{{ c.d }}</small>
        </button>
      </div>

      <h2>{{ tx('热门问题', 'Popular questions') }}</h2>
      <button v-for="(f, i) in filtered" :key="f.q" type="button" class="faq" @click="open = open === i ? -1 : i">
        <span>{{ f.q }}</span>
        <ChevronRight :size="16" :class="{ turn: open === i }" />
        <p v-if="open === i">{{ f.a }}</p>
      </button>

      <router-link class="ag-cta" to="/contact"><Headphones :size="18" /> {{ tx('联系客服', 'Contact support') }}</router-link>
      <p class="foot">{{ tx('还需要帮助？我们在这里。', 'Still need help? Our team is here for you.') }}</p>
    </div>
  </AgShell>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ChevronRight, CreditCard, Headphones, Package, RotateCcw, Search, Truck, UserRound } from 'lucide-vue-next'
import AgBrand from '@/components/account/AgBrand.vue'
import AgShell from '@/components/account/AgShell.vue'
import { fetchHtmlPath, parsePolicyBlocks } from '@/api/accountApi'
import { useZh } from '@/composables/zh'

const { tx } = useZh()
const router = useRouter()
const q = ref('')
const open = ref(-1)
const extra = ref<{ q: string; a: string }[]>([])

const cats = computed(() => [
  { to: '/orders', icon: Package, t: tx('订单', 'Orders'), d: tx('查询、修改、看详情', 'Track, modify, view details') },
  { to: '/policy/shipping', icon: Truck, t: tx('物流', 'Shipping'), d: tx('时效、运费、地区', 'Delivery times, fees, locations') },
  { to: '/return', icon: RotateCcw, t: tx('退货', 'Returns'), d: tx('流程、面单、退款', 'Process, labels, refunds') },
  { to: '/payments', icon: CreditCard, t: tx('支付', 'Payments'), d: tx('卡、方式、安全', 'Cards, methods, security') },
  { to: '/me', icon: UserRound, t: tx('账户', 'Account'), d: tx('登录、资料、偏好', 'Login, profile, preferences') },
])
const faqs = computed(() => [
  { q: tx('我的订单在哪里？', 'Where is my order?'), a: tx('打开「我的 → 订单」查看状态和物流。时效看收货国家。', 'Open Me → Orders to see status and tracking. Times depend on the destination.') },
  { q: tx('物流要多久？', 'How long does shipping take?'), a: tx('多数美国订单发货后 3–7 个工作日送达。偏远地区可能 7–14 天。', 'Most US orders arrive 3–7 business days after they ship. Remote areas may take 7–14 days.') },
  { q: tx('可以退货吗？', 'Can I return an item?'), a: tx('可以。在订单详情里于窗口期内发起退货。', 'Yes. Start a return from the order detail page within the return window.') },
  { q: tx('支持哪些支付方式？', 'What payment methods do you accept?'), a: tx('支持 PayPal、银行卡（Stripe）和连连，以结账页为准。', 'PayPal, cards (Stripe), and LianLian, as shown at checkout.') },
  { q: tx('怎么重置密码？', 'How do I reset my password?'), a: tx('在登录页选择重置密码，我们会把链接发到你的邮箱。', 'Choose reset password on the sign-in page and we will email you a link.') },
  ...extra.value,
])
const filtered = computed(() => {
  const s = q.value.trim().toLowerCase()
  if (!s) return faqs.value
  return faqs.value.filter((f) => (f.q + f.a).toLowerCase().includes(s))
})

onMounted(async () => {
  try {
    extra.value = parsePolicyBlocks(await fetchHtmlPath('/help')).slice(0, 6).map((b) => ({ q: b.title, a: b.body }))
  } catch { /* keep designed faqs */ }
})
</script>

<style scoped>
.top { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 8px; }
.side { color: #F96141; font-size: 10px; font-weight: 800; letter-spacing: 0.06em; text-align: right; white-space: pre-line; line-height: 1.25; }
.ag-search { margin-top: 14px; }
.cats { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; margin-top: 14px; }
.cats button { text-align: left; border: 0; background: #fff; border-radius: 16px; padding: 12px; cursor: pointer; color: inherit; box-shadow: 0 6px 18px rgba(28,36,48,0.04); }
.cats button:nth-child(4), .cats button:nth-child(5) { grid-column: span 1; }
.cats b { display: flex; align-items: center; gap: 2px; margin-top: 8px; font-size: 14px; }
.cats small { display: block; margin-top: 4px; color: #8B919A; font-size: 11.5px; line-height: 1.3; }
h2 { margin: 20px 0 8px; font-size: 18px; font-weight: 800; }
.faq { width: 100%; text-align: left; border: 0; border-bottom: 1px solid #F1ECE6; background: transparent; padding: 14px 0; cursor: pointer; color: inherit; display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; font-size: 15px; font-weight: 650; }
.faq p { flex: 1 0 100%; margin: 8px 0 0; color: #5C6570; font-weight: 450; font-size: 13.5px; line-height: 1.45; }
.turn { transform: rotate(90deg); }
.ag-cta { margin-top: 18px; }
.foot { text-align: center; color: #8B919A; font-size: 12.5px; }
</style>
