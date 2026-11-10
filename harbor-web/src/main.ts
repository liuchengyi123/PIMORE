import './styles/theme.scss'
import './styles/fn-page.css'
import { syncHarborLangCookie } from '@/api/catalogLang'
import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { applyBuyerTheme } from './theme/applyBuyerTheme'

try {
  syncHarborLangCookie()
} catch (_) {}

function mount() {
  createApp(App).use(router).mount('#app')
}

const theme = applyBuyerTheme()
const timeout = new Promise((resolve) => setTimeout(resolve, 1200))
Promise.race([theme, timeout]).finally(mount)
