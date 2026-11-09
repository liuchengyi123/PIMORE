<template>
  <form class="search-bar" :class="{ compact }" @submit.prevent="go">
    <Search :size="18" :stroke-width="1.7" class="ico" aria-hidden="true" />
    <input
      ref="inputEl"
      v-model="q"
      class="input"
      type="search"
      enterkeyhint="search"
      :placeholder="placeholder || t('search_placeholder')"
      :aria-label="t('search_action')"
      @focus="onFocus"
    />
    <button v-if="showButton" type="submit" class="go">{{ t('search_action') }}</button>
  </form>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Search } from 'lucide-vue-next'
import { useI18n } from '@/composables/i18n'

const props = withDefaults(defineProps<{
  modelValue?: string
  placeholder?: string
  compact?: boolean
  showButton?: boolean
  navigateOnFocus?: boolean
  inplace?: boolean
  autofocus?: boolean
}>(), {
  modelValue: '',
  compact: false,
  showButton: false,
  navigateOnFocus: false,
  inplace: false,
  autofocus: false,
})

const emit = defineEmits<{
  'update:modelValue': [string]
  search: [string]
}>()
const router = useRouter()
const route = useRoute()
const { t } = useI18n()
const q = ref(props.modelValue || '')
const inputEl = ref<HTMLInputElement | null>(null)

watch(() => props.modelValue, (v) => { if (v !== q.value) q.value = v || '' })
watch(q, (v) => emit('update:modelValue', v))

function go() {
  const query = q.value.trim()
  emit('search', query)
  if (props.inplace) return
  if (route.path === '/search') {
    router.replace(query ? { path: '/search', query: { q: query } } : { path: '/search' })
    return
  }
  router.push(query ? { path: '/search', query: { q: query } } : { path: '/search' })
}
function onFocus() {
  if (props.navigateOnFocus && route.path !== '/search') {
    router.push({ path: '/search', query: q.value.trim() ? { q: q.value.trim() } : {} })
  }
}
onMounted(() => {
  if (props.autofocus) inputEl.value?.focus()
})
</script>

<style lang="scss" scoped>
@import '@/styles/theme.scss';
.search-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  min-height: 44px;
  padding: 0 12px 0 14px;
  border-radius: $hb-radius-pill;
  background: $hb-white;
  border: 1px solid $hb-line;
  box-shadow: none;
}
.search-bar:focus-within {
  border-color: $hb-coral;
  box-shadow: 0 0 0 3px rgba(249, 97, 65, 0.16);
}
.search-bar.compact { min-height: 40px; padding: 0 10px 0 12px; }
.ico { flex: 0 0 auto; color: $hb-muted; }
.input {
  flex: 1;
  min-width: 0;
  border: 0;
  outline: none;
  background: transparent;
  font-size: $hb-type-16;
  color: $hb-ink;
  height: 44px;
  box-shadow: none;
}
.input::placeholder { color: $hb-muted; }
.search-bar .input:focus { box-shadow: none; border-color: transparent; }
.go {
  flex: 0 0 auto;
  border: 0;
  background: $hb-coral;
  color: #fff;
  font-size: $hb-type-13;
  font-weight: 700;
  height: $hb-cta-36;
  padding: 0 12px;
  border-radius: $hb-radius-pill;
  cursor: pointer;
}
.go:hover { background: $hb-coral-hot; }
</style>
