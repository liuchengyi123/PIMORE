<script setup lang="ts">
import { onLaunch } from '@dcloudio/uni-app'
import { initI18n } from '@/composables/i18n'

onLaunch(() => {
  initI18n()
  console.log('Harbor App launch')
})
</script>

<style lang="scss">
@import '@/styles/theme.scss';

page {
  background-color: $hb-paper;
  color: $hb-ink;
  font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', Roboto,
    'Helvetica Neue', Arial, sans-serif;
  font-size: 14px;
  box-sizing: border-box;
  -webkit-font-smoothing: antialiased;
}

view,
text {
  box-sizing: border-box;
}
</style>
