<template>
  <view class="page">
    <view class="head">
      <view class="back" @click="goBack">←</view>
      <view class="grow">
        <text class="title">{{ title }}</text>
        <text class="sub">{{ live ? t('nav_live_from_harbor') : t('nav_loading') }}{{ sub ? ' · ' + subLabel : '' }}</text>
      </view>
    </view>
    <scroll-view scroll-x class="chips" :show-scrollbar="false">
      <view class="chip" :class="{ on: !sub }" @click="pickSub('')">{{ t('cat_all') }}</view>
      <view
        v-for="s in subs"
        :key="s.id"
        class="chip"
        :class="{ on: sub === s.id }"
        @click="pickSub(s.id)"
      >{{ subcatLabel(s.id) }}</view>
    </scroll-view>
    <view v-if="loading" class="state">{{ t('nav_loading') }}</view>
    <view v-else-if="!products.length" class="state">{{ t('nav_empty_aisle') }}</view>
    <view v-else class="grid">
      <HbProductCard v-for="p in products" :key="p.id" :product="p" />
    </view>
    <view v-if="products.length && hasMore" class="more" @click="loadMore">{{ t('nav_load_more') }}</view>
    <HbLucky />
  </view>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { handleLuckyBack } from '@/composables/lucky'
import { onLoad, onShow } from '@dcloudio/uni-app'
import {
  SUBCATEGORIES,
  listCategoryPage,
  type Product,
} from '@/api/products'
import HbProductCard from '@/components/HbProductCard.vue'
import { useI18n } from '@/composables/i18n'

const { t, catLabel, subcatLabel } = useI18n()
const cat = ref('')
const sub = ref('')
const products = ref<Product[]>([])
const loading = ref(false)
const live = ref(false)
const page = ref(1)
const hasMore = ref(false)

const title = computed(() => catLabel(cat.value) || t('nav_category'))
const subs = computed(() => SUBCATEGORIES[cat.value] || [])
const subLabel = computed(() => (sub.value ? subcatLabel(sub.value) : ''))

async function load(reset = true) {
  if (!cat.value) return
  loading.value = true
  if (reset) page.value = 1
  try {
    const res = await listCategoryPage(cat.value, sub.value, page.value)
    products.value = reset ? res.items : products.value.concat(res.items)
    hasMore.value = res.hasMore
    live.value = res.live || res.items.some((p) => p.live)
  } finally {
    loading.value = false
  }
}

function pickSub(id: string) {
  sub.value = id
  load(true)
}

async function loadMore() {
  page.value += 1
  await load(false)
}

function goBack() {
  if (handleLuckyBack()) return
  uni.navigateBack({ fail: () => uni.navigateTo({ url: '/pages/categories/index' }) })
}

function syncNavTitle() {
  uni.setNavigationBarTitle({ title: title.value })
}

watch(title, () => syncNavTitle())

onLoad((q) => {
  cat.value = q?.cat ? decodeURIComponent(q.cat) : ''
  sub.value = q?.sub ? decodeURIComponent(q.sub) : ''
  load(true)
  syncNavTitle()
})

onShow(() => syncNavTitle())
</script>

<style lang="scss" scoped>
@import '@/styles/theme.scss';
.page { min-height: 100vh; background: $hb-paper; padding: 12px 16px 40px; padding-top: calc(12px + env(safe-area-inset-top)); }
.head { display: flex; gap: 12px; align-items: center; margin-bottom: 12px; }
.back { width: 36px; height: 36px; border-radius: 12px; background: $hb-white; text-align: center; line-height: 36px; box-shadow: $hb-shadow-soft; flex: none; }
.grow { flex: 1; }
.title { display: block; font-size: 24px; font-weight: 720; letter-spacing: -0.5px; }
.sub { display: block; font-size: 12px; color: $hb-muted; margin-top: 2px; }
.chips { white-space: nowrap; margin-bottom: 14px; }
.chip { display: inline-block; padding: 10px 14px; margin-right: 8px; border-radius: 999px; background: $hb-white; font-size: 13px; font-weight: 600; box-shadow: $hb-shadow-soft; }
.chip.on { background: $hb-forest; color: #fff; box-shadow: none; }
.state { text-align: center; color: $hb-muted; padding: 40px 8px; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.more { margin: 18px auto 0; width: 140px; text-align: center; padding: 12px; border-radius: 999px; background: $hb-white; color: $hb-forest; font-weight: 700; box-shadow: $hb-shadow-soft; }
</style>
