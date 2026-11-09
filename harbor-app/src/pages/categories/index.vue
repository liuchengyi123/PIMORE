<template>
  <view class="page" data-figma="1:12">
    <view class="head">
      <text class="title">Categories</text>
      <view class="search" @click="goSearch">
        <view class="mag" />
      </view>
    </view>
    <view class="split">
      <scroll-view scroll-y class="rail" :show-scrollbar="false">
        <view
          v-for="c in cats"
          :key="c.id"
          class="rail-item"
          :class="{ on: active === c.id }"
          @click="active = c.id"
        >
          <view class="rail-ico" />
          <text>{{ catLabel(c.id) }}</text>
        </view>
      </scroll-view>
      <scroll-view scroll-y class="pane" :show-scrollbar="false">
        <view class="tiles">
          <view v-for="(s, i) in subs" :key="s.id" class="tile" @click="openSub(s.id)">
            <view class="tile-pic">
              <image v-if="shot(i)" class="tile-img" :src="shot(i)" mode="aspectFill" />
            </view>
            <text class="tile-name">{{ subcatLabel(s.id) }}</text>
          </view>
        </view>
      </scroll-view>
    </view>
    <HbTabBar active="browse" />
  </view>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { onLoad, onShow } from '@dcloudio/uni-app'
import { useI18n } from '@/composables/i18n'
import { ALL_CATEGORIES, SUBCATEGORIES, listByCategory } from '@/api/products'
import HbTabBar from '@/components/HbTabBar.vue'

const { t, catLabel, subcatLabel } = useI18n()
const cats = ALL_CATEGORIES
const active = ref(cats[0]?.id || 'kitchen')
const shots = ref<string[]>([])
const subs = computed(() => SUBCATEGORIES[active.value] || [])

watch(active, async (id) => {
  try {
    const rows = await listByCategory(id)
    shots.value = rows.map((p) => p.image).filter((src): src is string => !!src)
  } catch {
    shots.value = []
  }
}, { immediate: true })

function shot(i: number) {
  if (!shots.value.length) return ''
  return shots.value[i % shots.value.length]
}

function chipPreview(id: string) {
  const kids = SUBCATEGORIES[id] || []
  return kids.slice(0, 3).map((k) => k.name).join(' · ') || t('home_see_all')
}

function openCat(id: string) {
  uni.navigateTo({ url: '/pages/category/index?cat=' + encodeURIComponent(id) })
}

function openSub(id: string) {
  uni.navigateTo({
    url: '/pages/category/index?cat=' + encodeURIComponent(active.value) + '&sub=' + encodeURIComponent(id),
  })
}

function goSearch() {
  uni.navigateTo({ url: '/pages/search/index' })
}

function goBack() {
  uni.navigateBack({ fail: () => uni.reLaunch({ url: '/pages/home/index' }) })
}

onLoad((q) => {
  if (q?.cat) active.value = decodeURIComponent(q.cat)
})

onShow(() => {
  uni.setNavigationBarTitle({ title: t('categories_title') })
})

void chipPreview
void openCat
void goBack
</script>

<style lang="scss" scoped>
@import '@/styles/theme.scss';
.page {
  min-height: 100vh;
  background: #F7F8FB;
  display: flex;
  flex-direction: column;
  padding-top: env(safe-area-inset-top);
}
.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px 8px;
}
.title { font-size: 28px; font-weight: 800; letter-spacing: -0.6px; color: #1B2B4A; }
.search {
  width: 36px; height: 36px; display: flex; align-items: center; justify-content: center;
}
.mag {
  width: 16px; height: 16px; border: 2px solid #FF6B4A; border-radius: 99px; position: relative;
}
.mag::after {
  content: '';
  position: absolute; right: -5px; bottom: -3px; width: 7px; height: 2px; background: #FF6B4A;
  transform: rotate(45deg);
}
.split { flex: 1; display: flex; min-height: 0; padding-bottom: calc(64px + env(safe-area-inset-bottom)); }
.rail { width: 92px; background: #F3F5F8; height: 100%; }
.rail-item {
  min-height: 72px;
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px;
  color: #8B95A7; font-size: 11px; font-weight: 600; text-align: center; padding: 8px 6px;
}
.rail-item.on {
  background: #FF6B4A; color: #fff; border-radius: 16px; margin: 6px;
}
.rail-ico {
  width: 18px; height: 14px; border: 1.7px solid currentColor; border-radius: 4px 4px 3px 3px;
}
.pane { flex: 1; height: 100%; background: #F7F8FB; }
.tiles { display: grid; grid-template-columns: 1fr 1fr; gap: 14px 10px; padding: 8px 12px 24px; }
.tile { text-align: center; }
.tile-pic {
  background: #F3EFE8; border-radius: 16px; aspect-ratio: 1; overflow: hidden;
}
.tile-img { width: 100%; height: 100%; }
.tile-name { display: block; margin-top: 8px; font-size: 13px; font-weight: 600; color: #1B2B4A; }
</style>
