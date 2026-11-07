import './styles/fn-page.css'
﻿import { syncHarborLangCookie } from '@/api/catalogLang'
import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './styles/theme.scss'

try {
  syncHarborLangCookie()
} catch (_) {}

createApp(App).use(router).mount('#app')
