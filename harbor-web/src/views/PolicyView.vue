<template>
  <AgShell>
    <header class="bar" :class="kind">
      <button type="button" class="ag-back" :class="kind === 'privacy' || kind === 'terms' ? 'light' : 'ink'" @click="router.back()" :aria-label="tx('返回', 'Back')">
        <ChevronLeft :size="24" />
      </button>
      <div class="brand">
        <AgBrand :light="kind !== 'shipping'" :wave="kind === 'shipping'" />
        <div v-if="kind !== 'shipping'" class="tag oncoral">
          {{ kind === 'privacy' ? tx('家居好物 · 好价格', 'HOME GOODS · GREAT PRICES') : tx('家居好物 · 每天都值', 'HOME GOODS · EVERYDAY VALUE') }}
        </div>
      </div>
      <button type="button" class="cart" @click="router.push('/cart')" :aria-label="tx('购物车', 'Cart')">
        <ShoppingBag :size="20" />
        <i v-if="count">{{ count }}</i>
      </button>
    </header>

    <div class="ag-pad">
      <div class="kicker">{{ kind === 'privacy' ? tx('法律', 'LEGAL') : tx('政策', 'POLICY') }}</div>
      <div class="hero" :class="kind">
        <div>
          <h1>{{ title }}</h1>
          <p>{{ lead }}</p>
          <p v-if="kind === 'privacy'" class="when">{{ tx('最近更新：2025年4月28日', 'Last updated: April 28, 2025') }}</p>
        </div>
        <div v-if="kind === 'shipping'" class="parcel" aria-hidden="true">Harbor</div>
      </div>

      <div v-if="kind === 'terms'" class="banner">
        <Shield :size="16" color="#F96141" />
        <div><b>{{ tx('简单、公平，为每天而做。', 'Simple. Fair. Built for everyday.') }}</b><span>{{ tx('感谢你成为 Harbor 的一员。', 'Thanks for being part of the Harbor community.') }}</span></div>
      </div>

      <button v-for="(b, i) in sections" :key="b.t" type="button" class="block" :class="{ line: kind === 'shipping' }" @click="open = open === i ? -1 : i">
        <span class="ag-icon" :class="{ solid: kind === 'shipping' }"><component :is="b.icon" :size="18" /></span>
        <span class="copy">
          <b>{{ b.t }}</b>
          <span v-if="kind !== 'terms' || open === i">{{ b.d }}</span>
          <span v-if="kind === 'shipping' && b.more" class="more">{{ b.more }}</span>
        </span>
        <ChevronRight v-if="kind !== 'shipping'" :size="16" color="#C5C0BA" />
      </button>

      <section v-if="kind === 'terms'" class="long">
        <div class="kicker">{{ tx('服务条款', 'TERMS OF SERVICE') }}</div>
        <h2><UserRound :size="18" /> {{ tx('账户', 'Account') }}</h2>
        <h3>1. {{ tx('创建账户', 'Account Creation') }}</h3>
        <p>{{ tx('购买或使用部分功能时，你可能需要创建账户。你同意提供准确、完整、最新的信息，并妥善保管账户安全。你对账户下发生的活动负责。', 'To make a purchase or access certain features, you may need to create an account. You agree to provide accurate, complete and current information and to keep it up to date. You are responsible for maintaining the security of your account and for all activities that occur under it.') }}</p>
        <h3>2. {{ tx('账户资格', 'Account Eligibility') }}</h3>
        <p>{{ tx('你需年满 18 岁（或你所在地区的成年年龄）才能创建账户并使用服务。创建账户即表示你确认满足这一要求。', 'You must be at least 18 years old (or the age of majority in your region) to create an account and use our services. By creating an account, you confirm you meet this requirement.') }}</p>
        <h3>3. {{ tx('账户终止', 'Account Termination') }}</h3>
        <p>{{ tx('我们可能在任何时候暂停或终止你的账户，包括我们认为你违反了这些条款或政策，或账户长期未使用。', 'We may suspend or terminate your account at any time, for any reason, including if we believe you have violated these terms or our policies, or if your account is inactive for an extended period.') }}</p>
      </section>

      <section v-if="kind === 'privacy'" class="trust">
        <Shield :size="18" color="#F96141" />
        <div>
          <b>{{ tx('你的信任就是一切', 'Your trust means everything') }}</b>
          <p>{{ tx('我们承诺保护你的信息，并每天赢得你的信心。', "We're committed to protecting your information and earning your confidence, every day.") }}</p>
        </div>
      </section>

      <div v-if="loading" class="ag-note">{{ tx('正在同步店铺政策…', 'Loading the store policy…') }}</div>
      <article v-for="(b, i) in live" :key="'live'+i" class="live ag-card">
        <b>{{ b.title }}</b>
        <p>{{ b.body }}</p>
      </article>
    </div>

    <nav class="pnav">
      <button type="button" @click="router.push('/home')"><Home :size="20" /><span>{{ tx('首页', 'Home') }}</span></button>
      <button type="button" @click="router.push('/browse')"><LayoutGrid :size="20" /><span>{{ kind === 'shipping' ? tx('选购', 'Shop') : tx('分类', 'Categories') }}</span></button>
      <button v-if="kind === 'shipping'" type="button" @click="router.push('/wishlist')"><Heart :size="20" /><span>{{ tx('收藏', 'Favorites') }}</span></button>
      <button v-else-if="kind === 'terms'" type="button" class="fab" @click="router.push('/cart')"><ShoppingBag :size="22" /></button>
      <button v-else type="button" class="on" @click="stay"><Heart :size="20" /><span>{{ tx('政策', 'Policy') }}</span></button>
      <button v-if="kind === 'shipping'" type="button" class="on" @click="stay"><FileText :size="20" /><span>{{ tx('政策', 'Policy') }}</span></button>
      <button v-else-if="kind === 'terms'" type="button" @click="router.push('/wishlist')"><Heart :size="20" /><span>{{ tx('心愿单', 'Wish List') }}</span></button>
      <button v-else type="button" @click="router.push('/me')"><UserRound :size="20" /><span>{{ tx('账户', 'Account') }}</span></button>
      <button v-if="kind === 'privacy'" type="button" @click="router.push('/cart')"><ShoppingBag :size="20" /><span>{{ tx('购物车', 'Cart') }}</span></button>
      <button v-else type="button" @click="router.push('/me')"><UserRound :size="20" /><span>{{ tx('账户', 'Account') }}</span></button>
    </nav>
  </AgShell>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ChevronLeft, Clock, Cookie, FileText, Heart, Home, LayoutGrid, Mail, MapPin, Package, RotateCcw, Settings, Shield, ShoppingBag, Tag, Truck, UserRound } from 'lucide-vue-next'
import AgBrand from '@/components/account/AgBrand.vue'
import AgShell from '@/components/account/AgShell.vue'
import { fetchHtmlPath, parsePolicyBlocks } from '@/api/accountApi'
import { useCart } from '@/composables/cart'
import { useZh } from '@/composables/zh'

const { tx } = useZh()
const route = useRoute()
const router = useRouter()
const cart = useCart()
const count = computed(() => cart.count.value)
const open = ref(0)
const live = ref<{ title: string; body: string }[]>([])
const loading = ref(false)

const kind = computed<'shipping' | 'privacy' | 'terms'>(() => {
  const p = route.path
  if (p.includes('privacy') || route.query.kind === 'privacy') return 'privacy'
  if (p.includes('terms') || route.query.kind === 'terms') return 'terms'
  return 'shipping'
})
const title = computed(() => kind.value === 'privacy' ? tx('隐私政策', 'Privacy Policy') : kind.value === 'terms' ? tx('服务条款', 'Terms of Service') : tx('物流政策', 'Shipping Policy'))
const lead = computed(() => {
  if (kind.value === 'privacy') return tx('你的隐私对我们很重要。本政策说明我们收集什么、如何使用，以及你可以做的选择。我们承诺让个人信息安全、透明。', 'Your privacy matters to us. This Privacy Policy explains what information we collect, how we use it, and the choices you have. We are committed to keeping your personal data safe and transparent.')
  if (kind.value === 'terms') return tx('本服务条款约束你对 Harbor 应用和网站的使用。访问或使用服务，即表示你同意受这些条款约束。', 'These Terms of Service govern your use of the Harbor app and website. By accessing or using our services, you agree to be bound by these terms.')
  return tx('我们快速、实惠、小心地寄出日用和家居好物。下面是你需要知道的物流说明。', 'We ship everyday essentials and home goods — quickly, affordably and with care. Here is everything you need to know about our shipping process.')
})

const sections = computed((): { icon: object; t: string; d: string; more?: string }[] => {
  if (kind.value === 'privacy') return [
    { icon: UserRound, t: tx('我们收集的信息', 'Data we collect'), d: tx('我们收集你主动提供的信息、活动信息，以及帮助我们把服务做得更好的技术数据。', 'We collect information you provide, information about your activity, and technical data to help us serve you better.') },
    { icon: Settings, t: tx('如何使用', 'How we use it'), d: tx('我们用这些数据处理订单、个性化体验、改进产品和服务，并与你沟通。', 'We use your data to process orders, personalize your experience, improve our products and services, and communicate with you.') },
    { icon: Cookie, t: 'Cookies', d: tx('我们使用 Cookie 和类似技术记住偏好、分析使用情况，并让购物更顺畅。', 'We use cookies and similar technologies to remember your preferences, analyze site usage, and provide a smoother shopping experience.') },
    { icon: Shield, t: tx('你的权利', 'Your rights'), d: tx('你可以访问、更正、删除或限制使用你的个人数据，也可以拒绝部分用途，例如定向广告。', 'You have the right to access, correct, delete, or restrict your personal data. You can also opt out of certain uses, like targeted advertising.') },
    { icon: Mail, t: tx('联系', 'Contact'), d: tx('有问题？我们在。请写信给隐私团队：privacy@harborhome.com。', 'Questions or concerns? We are here to help. Reach our privacy team at privacy@harborhome.com.') },
  ]
  if (kind.value === 'terms') return [
    { icon: UserRound, t: tx('账户', 'Account'), d: tx('创建和管理你的账户。', 'Creating and managing your account.') },
    { icon: Package, t: tx('订单', 'Orders'), d: tx('下单、处理和配送。', 'Placing orders, order processing and delivery.') },
    { icon: Tag, t: tx('价格', 'Pricing'), d: tx('我们如何定价和展示价格。', 'How we set and apply prices.') },
    { icon: RotateCcw, t: tx('退货', 'Returns'), d: tx('退回商品并拿回款项。', 'Returning items and getting your money back.') },
    { icon: Shield, t: tx('责任', 'Liability'), d: tx('我们的界限和你的责任。', 'Our limits and your responsibilities.') },
  ]
  return [
    { icon: Truck, t: tx('满 $40 包邮', 'Free shipping over $40'), d: tx('订单满 $40 可享美国境内标准包邮，无需优惠码，结算时自动生效。', 'Orders over $40 qualify for free standard shipping in the US. No promo codes needed — it is applied automatically at checkout.'), more: tx('未满 $40 的订单收取 $5.99 固定运费。', 'Orders under $40 have a flat shipping fee of $5.99.') },
    { icon: Clock, t: tx('送达时间（美国）', 'Delivery times (US)'), d: tx('我们从美国履约中心发货，多数订单发出后 3–7 个工作日送达。时效会因地区、天气和运力变化。', 'We ship from our US fulfillment centers, and most orders arrive within 3–7 business days after your order ships. Times may vary by location, weather or carrier volume.'), more: tx('阿拉斯加、夏威夷和美国属地可能需要 7–14 天。', 'Alaska, Hawaii and U.S. territories may take 7–14 days.') },
    { icon: MapPin, t: tx('物流追踪', 'Tracking'), d: tx('订单发出后你会收到追踪号邮件，也可以随时在应用的「订单」里查看。', 'Once your order ships, you will receive a tracking number by email. You can also check status in Orders.'), more: tx('追踪信息可能在发货后 24 小时内更新。', 'Tracking updates can take up to 24 hours to appear after your order ships.') },
    { icon: Package, t: tx('破损包裹', 'Damaged packages'), d: tx('我们会小心打包。如果商品送达时破损，请在 7 天内联系我们，附上订单号和照片，我们会补发或退款。', 'We pack every order with care, but if your item arrives damaged, contact us within 7 days with your order number and photos, and we will make it right with a replacement or refund.'), more: tx('你的满意对我们很重要。', 'We are here to help — your satisfaction matters.') },
  ]
})

async function load() {
  loading.value = true
  try {
    const path = kind.value === 'privacy' ? '/policies/privacy' : kind.value === 'terms' ? '/policies/terms' : '/policies/shipping'
    live.value = parsePolicyBlocks(await fetchHtmlPath(path)).slice(0, 4)
  } catch { live.value = [] } finally { loading.value = false }
}
function stay() { router.replace(kind.value === 'shipping' ? '/policy/shipping' : `/policy/${kind.value}`) }
onMounted(load)
watch(kind, load)
</script>

<style scoped>
.bar { display: grid; grid-template-columns: 44px 1fr 44px; align-items: center; padding: 8px; padding-top: calc(8px + env(safe-area-inset-top)); }
.bar.privacy, .bar.terms { background: #F96141; color: #fff; }
.brand { text-align: center; }
.tag { font-size: 10px; letter-spacing: 0.08em; font-weight: 700; }
.tag.oncoral { color: rgba(255,255,255,0.88); }
.cart { position: relative; border: 0; background: transparent; color: inherit; cursor: pointer; }
.cart i { position: absolute; top: -4px; right: -6px; min-width: 16px; height: 16px; border-radius: 999px; background: #F96141; color: #fff; font-style: normal; font-size: 10px; display: grid; place-items: center; }
.bar.privacy .cart i, .bar.terms .cart i { background: #fff; color: #F96141; }
.kicker { color: #F96141; font-size: 12px; font-weight: 800; letter-spacing: 0.12em; margin-top: 8px; }
.hero { display: flex; gap: 8px; align-items: flex-start; }
.hero h1 { margin: 4px 0 0; font-size: 30px; font-weight: 800; letter-spacing: -0.04em; }
.hero p { margin: 8px 0 0; color: #5C6570; font-size: 14px; line-height: 1.45; }
.when { font-size: 12.5px !important; }
.parcel { flex: 0 0 92px; height: 78px; border-radius: 10px; background: #F96141; color: #fff; display: grid; place-items: center; font-weight: 800; margin-top: 18px; }
.banner { display: flex; gap: 8px; background: #FFF1EC; border-radius: 14px; padding: 12px; margin: 12px 0; }
.banner b, .banner span { display: block; }
.banner span { color: #8B919A; font-size: 12.5px; }
.block { width: 100%; display: flex; gap: 12px; align-items: flex-start; text-align: left; border: 0; border-bottom: 1px solid #F1ECE6; background: transparent; padding: 14px 0; cursor: pointer; color: inherit; }
.block.line { border-bottom: 0; border-left: 3px solid #F96141; padding-left: 12px; margin-top: 8px; }
.copy { flex: 1; }
.copy b { display: block; font-size: 16px; }
.copy span { display: block; margin-top: 4px; color: #5C6570; font-size: 13.5px; line-height: 1.45; }
.more { color: #8B919A !important; }
.long { margin-top: 16px; }
.long h2 { display: flex; align-items: center; gap: 6px; font-size: 22px; }
.long h3 { margin: 12px 0 4px; font-size: 15px; }
.long p { margin: 0; color: #5C6570; font-size: 13.5px; line-height: 1.5; }
.trust { margin-top: 14px; display: flex; gap: 10px; background: #FFF1EC; border-radius: 16px; padding: 14px; }
.trust p { margin: 4px 0 0; color: #5C6570; font-size: 13px; }
.live { margin-top: 10px; padding: 12px 14px; }
.live p { margin: 6px 0 0; color: #5C6570; font-size: 13px; line-height: 1.45; }
.pnav {
  position: sticky; bottom: 0; display: grid; grid-template-columns: repeat(5, 1fr);
  background: #fff; border-top: 1px solid #F1ECE6; padding: 8px 4px calc(8px + env(safe-area-inset-bottom));
  margin-top: 18px;
}
.pnav button { border: 0; background: transparent; color: #9AA0A8; display: flex; flex-direction: column; align-items: center; gap: 2px; font-size: 10px; cursor: pointer; }
.pnav button.on { color: #F96141; }
.pnav .fab { width: 52px; height: 52px; border-radius: 50%; background: #F96141; color: #fff; margin: -22px auto 0; }
</style>
