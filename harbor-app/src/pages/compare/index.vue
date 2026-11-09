<template>
  <view class="page" data-figma="1:20">
    <view class="top">
      <view class="status">
        <text class="time">9:41</text>
        <view class="status-right">
          <view class="sig"><view /><view /><view /><view /></view>
          <view class="wifi" />
          <view class="batt"><view class="batt-fill" /></view>
        </view>
      </view>
      <view class="nav">
        <view class="back" @click="goBack">
          <view class="chev" />
        </view>
        <text class="nav-title">Compare</text>
        <view class="nav-spacer" />
      </view>
    </view>

    <view class="body">
      <view class="intro">
        <text class="headline">Find the best fit for your home</text>
        <text class="sub">Compare products side by side and choose what works for you.</text>
      </view>

      <view class="cards">
        <view v-for="p in items" :key="p.id" class="card">
          <view class="thumb" @click="open(p)">
            <image class="img" :src="p.image" mode="aspectFill" />
          </view>
          <text class="nm">{{ p.name }}</text>
          <text class="price">${{ p.price.toFixed(2) }}</text>
          <view class="rating">
            <view class="stars">
              <text
                v-for="n in 5"
                :key="n"
                class="star"
                :class="starClass(p.rating, n)"
              >★</text>
            </view>
            <text class="count">({{ formatCount(p.reviews) }})</text>
          </view>
          <view class="add" @click="addOne(p)">Add to Cart</view>
        </view>
      </view>

      <view class="table">
        <view v-for="row in rows" :key="row.key" class="tr">
          <view class="th">
            <view class="ico" :class="'ico-' + row.key" />
            <text class="th-lab">{{ row.label }}</text>
          </view>
          <view v-for="p in items" :key="p.id + row.key" class="td">
            <text>{{ cell(p, row.key) }}</text>
          </view>
        </view>
      </view>

      <view class="banner">
        <image class="banner-ico" src="/static/figma/compare/banner_icon.png" mode="aspectFit" />
        <view class="banner-copy">
          <text class="banner-title">Everyday home goods. Great value.</text>
          <text class="banner-sub">Quality finds from $1 – $10.</text>
        </view>
      </view>

    </view>

    <view class="tab-spacer" />
    <view class="tab-bar">
      <view class="tab on" @click="goTab('/pages/home/index')">
        <view class="t-ico home-ico" />
        <text class="t-lab on">Home</text>
      </view>
      <view class="tab" @click="goTab('/pages/browse/index')">
        <view class="t-ico search-ico" />
        <text class="t-lab">Browse</text>
      </view>
      <view class="tab" @click="goTab('/pages/cart/index')">
        <view class="t-ico cart-ico">
          <view class="badge"><text>2</text></view>
        </view>
        <text class="t-lab">Cart</text>
      </view>
      <view class="tab" @click="goTab('/pages/me/index')">
        <view class="t-ico me-ico" />
        <text class="t-lab">Me</text>
      </view>
      <view class="homeind" />
    </view>
  </view>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { listCompareProducts, type Product } from '@/api/products'
import { useCart } from '@/composables/cart'

type CompareItem = {
  id: string
  sku: string
  name: string
  price: number
  rating: number
  reviews: number
  image: string
  material: string
  size: string
  color: string
  live?: Product
}

const { add } = useCart()

/** Figma 1:20 fixture — photos cropped from the flattened Compare frame. */
const FIGMA_ITEMS: CompareItem[] = [
  {
    id: 'figma-compare-1',
    sku: 'CERAMIC-SUCCULENT',
    name: 'Ceramic Succulent Planter',
    price: 3.99,
    rating: 4.5,
    reviews: 482,
    image: '/static/figma/compare/p1.png',
    material: 'Ceramic',
    size: '4.5" H x 4.0" W (plant pot)',
    color: 'White',
  },
  {
    id: 'figma-compare-2',
    sku: 'MICROFIBER-TOWELS-4',
    name: 'Microfiber Cleaning Towels (4-Pack)',
    price: 5.99,
    rating: 5.0,
    reviews: 1206,
    image: '/static/figma/compare/p2.png',
    material: 'Microfiber (Polyester)',
    size: '12" x 12" (each towel)',
    color: 'Gray',
  },
  {
    id: 'figma-compare-3',
    sku: 'TEXTURED-PILLOW',
    name: 'Textured Throw Pillow Cover',
    price: 7.99,
    rating: 4.5,
    reviews: 713,
    image: '/static/figma/compare/p3.png',
    material: 'Cotton & Linen Blend',
    size: '18" x 18" (pillow cover)',
    color: 'Beige / Stripe',
  },
]

const rows = [
  { key: 'material', label: 'Material' },
  { key: 'size', label: 'Size' },
  { key: 'color', label: 'Color' },
  { key: 'rating', label: 'Rating' },
  { key: 'price', label: 'Price' },
] as const

const items = ref<CompareItem[]>(FIGMA_ITEMS.map((p) => ({ ...p })))

function formatCount(n: number) {
  return n.toLocaleString('en-US')
}

function starClass(rating: number, n: number) {
  if (rating >= n) return 'full'
  if (rating >= n - 0.5) return 'half'
  return 'empty'
}

function cell(p: CompareItem, key: string) {
  if (key === 'material') return p.material
  if (key === 'size') return p.size
  if (key === 'color') return p.color
  if (key === 'rating') return `${p.rating.toFixed(1)} / 5 (${formatCount(p.reviews)})`
  if (key === 'price') return `$${p.price.toFixed(2)}`
  return ''
}

function toCartProduct(p: CompareItem): Product {
  if (p.live) return p.live
  return {
    id: p.id,
    sku: p.sku,
    name: p.name,
    price: p.price,
    category: 'Home',
    image: p.image,
    material: p.material,
    live: false,
  }
}

function open(p: CompareItem) {
  const sku = p.live?.sku || p.sku
  uni.navigateTo({ url: '/pages/pdp/index?sku=' + encodeURIComponent(String(sku)) })
}

async function addOne(p: CompareItem) {
  const prod = toCartProduct(p)
  const size = prod.sizes?.[0] || prod.offers?.[0]?.label || 'default'
  const res = await add(prod, size, 1)
  uni.showToast({ title: res.message || 'Added', icon: 'none' })
}


function goTab(url: string) {
  uni.reLaunch({ url })
}
function goBack() {
  uni.navigateBack({ fail: () => uni.reLaunch({ url: '/pages/home/index' }) })
}

onMounted(async () => {
  try {
    const res = await listCompareProducts()
    const live = res?.products || []
    // Keep Figma presentation 1:1; only attach live PDP/cart handles when names align.
    if (live.length) {
      items.value = FIGMA_ITEMS.map((fig, i) => {
        const match =
          live.find((l) => l.name.toLowerCase().includes(fig.name.split(' ')[0].toLowerCase())) ||
          live[i]
        if (!match) return { ...fig }
        return {
          ...fig,
          live: match,
          sku: match.sku || fig.sku,
          id: match.id || fig.id,
        }
      })
    }
  } catch {
    /* keep Figma fixtures */
  }
})
</script>

<style scoped lang="scss">
@import '@/styles/theme.scss';

.page {
  min-height: 100vh;
  background: #ffffff;
  color: #2a2f36;
}

.top {
  background: $hb-coral;
  color: #fff;
  padding-top: env(safe-area-inset-top);
}

.status {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 18px 0;
  height: 28px;
  box-sizing: border-box;
}
.time {
  font-size: 14px;
  font-weight: 600;
  letter-spacing: -0.2px;
}
.status-right {
  display: flex;
  align-items: center;
  gap: 6px;
}
.sig {
  display: flex;
  align-items: flex-end;
  gap: 1.5px;
  height: 10px;
}
.sig view {
  width: 3px;
  background: #fff;
  border-radius: 1px;
}
.sig view:nth-child(1) { height: 3px; }
.sig view:nth-child(2) { height: 5px; }
.sig view:nth-child(3) { height: 7px; }
.sig view:nth-child(4) { height: 10px; }
.wifi {
  width: 13px;
  height: 10px;
  border: 2px solid #fff;
  border-top: none;
  border-radius: 0 0 8px 8px;
  box-sizing: border-box;
  position: relative;
}
.wifi::before {
  content: '';
  position: absolute;
  left: 2px;
  top: -5px;
  width: 5px;
  height: 5px;
  border: 2px solid #fff;
  border-bottom: none;
  border-radius: 6px 6px 0 0;
  box-sizing: border-box;
}
.batt {
  width: 22px;
  height: 11px;
  border: 1.5px solid #fff;
  border-radius: 3px;
  padding: 1px;
  box-sizing: border-box;
  position: relative;
}
.batt::after {
  content: '';
  position: absolute;
  right: -3px;
  top: 3px;
  width: 2px;
  height: 4px;
  background: #fff;
  border-radius: 0 1px 1px 0;
}
.batt-fill {
  width: 70%;
  height: 100%;
  background: #fff;
  border-radius: 1px;
}

.nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 44px;
  padding: 0 8px 6px;
}
.back {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.chev {
  width: 10px;
  height: 10px;
  border-left: 2.5px solid #fff;
  border-bottom: 2.5px solid #fff;
  transform: rotate(45deg);
  margin-left: 4px;
}
.nav-title {
  flex: 1;
  text-align: center;
  font-size: 17px;
  font-weight: 700;
  letter-spacing: -0.2px;
}
.nav-spacer { width: 40px; }

.body {
  padding-bottom: 8px;
}

.intro {
  padding: 18px 16px 10px;
}
.headline {
  display: block;
  font-size: 24px;
  font-weight: 800;
  line-height: 1.2;
  letter-spacing: -0.4px;
  color: #1f2430;
}
.sub {
  display: block;
  margin-top: 8px;
  font-size: 13px;
  line-height: 1.4;
  color: #8b93a1;
}

.cards {
  display: flex;
  gap: 8px;
  padding: 8px 12px 4px;
}
.card {
  flex: 1;
  min-width: 0;
  background: #fff;
}
.thumb {
  width: 100%;
  aspect-ratio: 1;
  border-radius: 10px;
  overflow: hidden;
  background: #f3efe8;
}
.img {
  width: 100%;
  height: 100%;
}
.nm {
  display: block;
  margin-top: 8px;
  font-size: 11px;
  font-weight: 700;
  line-height: 1.25;
  color: #1f2430;
  min-height: 28px;
}
.price {
  display: block;
  margin-top: 4px;
  font-size: 15px;
  font-weight: 800;
  color: $hb-coral;
}
.rating {
  display: flex;
  align-items: center;
  gap: 2px;
  margin-top: 2px;
  flex-wrap: nowrap;
}
.stars {
  display: flex;
  gap: 0;
}
.star {
  font-size: 9px;
  line-height: 1;
  color: #e5e7eb;
}
.star.full { color: $hb-coral; }
.star.half {
  color: $hb-coral;
  opacity: 0.55;
}
.count {
  font-size: 9px;
  color: #9aa3b2;
  margin-left: 1px;
}
.add {
  margin-top: 8px;
  height: 30px;
  border-radius: 8px;
  background: $hb-coral;
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}

.table {
  margin: 14px 12px 0;
  border: 1px solid #eceff3;
  border-radius: 4px;
  overflow: hidden;
}
.tr {
  display: flex;
  border-bottom: 1px solid #eceff3;
}
.tr:last-child { border-bottom: none; }
.th {
  width: 72px;
  flex-shrink: 0;
  background: #f7f3ec;
  padding: 10px 6px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  border-right: 1px solid #eceff3;
  box-sizing: border-box;
}
.th-lab {
  font-size: 10px;
  color: #6b7280;
  font-weight: 600;
}
.td {
  flex: 1;
  min-width: 0;
  padding: 10px 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  font-size: 10px;
  line-height: 1.3;
  color: #374151;
  border-right: 1px solid #eceff3;
  box-sizing: border-box;
}
.td:last-child { border-right: none; }

/* Row icons — simple line glyphs matching Figma labels */
.ico {
  width: 16px;
  height: 16px;
  position: relative;
}
.ico-material {
  border: 1.5px solid #9aa3b2;
  border-radius: 0 10px 10px 10px;
  transform: rotate(-30deg);
  width: 12px;
  height: 14px;
}
.ico-size {
  border: 1.5px solid #9aa3b2;
  width: 12px;
  height: 12px;
  border-radius: 1px;
}
.ico-size::before,
.ico-size::after {
  content: '';
  position: absolute;
  background: #9aa3b2;
}
.ico-size::before {
  left: 4px; top: -3px; width: 1.5px; height: 16px;
}
.ico-size::after {
  top: 4px; left: -3px; width: 16px; height: 1.5px;
}
.ico-color {
  width: 14px;
  height: 12px;
  border: 1.5px solid #9aa3b2;
  border-radius: 3px 3px 6px 6px;
  box-sizing: border-box;
}
.ico-color::before {
  content: '';
  position: absolute;
  left: 3px;
  top: -3px;
  width: 5px;
  height: 5px;
  border: 1.5px solid #9aa3b2;
  border-radius: 99px;
  box-sizing: border-box;
}
.ico-rating {
  width: 0;
  height: 0;
  border-left: 7px solid transparent;
  border-right: 7px solid transparent;
  border-bottom: 5px solid #9aa3b2;
  transform: rotate(35deg);
  margin-top: 2px;
}
.ico-price {
  width: 12px;
  height: 14px;
  border: 1.5px solid #9aa3b2;
  border-radius: 2px 2px 3px 3px;
  box-sizing: border-box;
  transform: rotate(-12deg);
}
.ico-price::before {
  content: '';
  position: absolute;
  left: 3px;
  top: 2px;
  width: 4px;
  height: 4px;
  border-radius: 99px;
  border: 1.5px solid #9aa3b2;
  box-sizing: border-box;
}

.banner {
  margin: 16px 16px 0;
  padding: 14px 14px;
  background: #f7f3ec;
  border-radius: 14px;
  display: flex;
  align-items: center;
  gap: 12px;
}
.banner-ico {
  width: 40px;
  height: 40px;
  flex-shrink: 0;
}
.banner-copy { flex: 1; min-width: 0; }
.banner-title {
  display: block;
  font-size: 13px;
  font-weight: 800;
  color: #1f2430;
  line-height: 1.3;
}
.banner-sub {
  display: block;
  margin-top: 2px;
  font-size: 12px;
  color: #8b93a1;
}


.tab-spacer {
  height: calc(64px + env(safe-area-inset-bottom));
}
.tab-bar {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  padding: 8px 8px calc(12px + env(safe-area-inset-bottom));
  background: #fff;
  border-top: 1px solid #eef1f6;
  display: flex;
  justify-content: space-around;
  align-items: flex-end;
  z-index: 100;
}
.tab {
  width: 64px;
  text-align: center;
  padding: 4px 0;
}
.t-ico {
  width: 24px;
  height: 24px;
  margin: 0 auto 2px;
  position: relative;
}
.t-lab {
  font-size: 11px;
  font-weight: 500;
  color: #9aa3b2;
}
.t-lab.on { color: #ff6b4a; font-weight: 700; }

.home-ico {
  background:
    linear-gradient(#ff6b4a,#ff6b4a) center 14px / 12px 2px no-repeat;
  border: none;
}
.home-ico::before {
  content: '';
  position: absolute;
  left: 3px; top: 3px;
  width: 0; height: 0;
  border-left: 9px solid transparent;
  border-right: 9px solid transparent;
  border-bottom: 8px solid #ff6b4a;
}
.home-ico::after {
  content: '';
  position: absolute;
  left: 6px; top: 10px;
  width: 12px; height: 10px;
  border: 2px solid #ff6b4a;
  border-top: none;
  box-sizing: border-box;
}

.search-ico {
  border: 2px solid #9aa3b2;
  border-radius: 99px;
  width: 14px;
  height: 14px;
  margin-top: 2px;
  box-sizing: border-box;
}
.search-ico::after {
  content: '';
  position: absolute;
  right: -3px; bottom: -3px;
  width: 7px; height: 2px;
  background: #9aa3b2;
  transform: rotate(45deg);
  border-radius: 2px;
}

.cart-ico {
  width: 20px;
  height: 18px;
  margin-top: 4px;
  border: 2px solid #9aa3b2;
  border-top: none;
  border-radius: 0 0 4px 4px;
  box-sizing: border-box;
}
.cart-ico::before {
  content: '';
  position: absolute;
  left: -3px; top: -5px;
  width: 22px; height: 2px;
  background: #9aa3b2;
  border-radius: 2px;
}
.cart-ico::after {
  content: '';
  position: absolute;
  left: 2px; top: -9px;
  width: 12px; height: 6px;
  border: 2px solid #9aa3b2;
  border-bottom: none;
  border-radius: 8px 8px 0 0;
  box-sizing: border-box;
}
.badge {
  position: absolute;
  top: -12px;
  right: -10px;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  border-radius: 99px;
  background: #ff6b4a;
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 16px;
  z-index: 2;
}

.me-ico::before {
  content: '';
  position: absolute;
  left: 7px; top: 1px;
  width: 8px; height: 8px;
  border-radius: 99px;
  border: 2px solid #9aa3b2;
  box-sizing: border-box;
}
.me-ico::after {
  content: '';
  position: absolute;
  left: 3px; bottom: 1px;
  width: 16px; height: 8px;
  border: 2px solid #9aa3b2;
  border-bottom: none;
  border-radius: 10px 10px 0 0;
  box-sizing: border-box;
}

.homeind {
  position: absolute;
  left: 50%;
  bottom: 6px;
  width: 128px;
  height: 5px;
  margin-left: -64px;
  border-radius: 99px;
  background: #1b2b4a;
}
</style>
