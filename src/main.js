import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import 'element-plus/dist/index.css'

import App from './App.vue'
import router from './router'
import { registerIcons } from './icons'
import { useAuthStore } from './store/auth'
import { setExpireHandler, startIdleWatch } from './utils/idleSession'
import './styles/main.css'

const app = createApp(App)
registerIcons(app)

const pinia = createPinia()
app.use(pinia)
app.use(router)
setExpireHandler(() => {
  const auth = useAuthStore(pinia)
  const current = router.currentRoute.value
  auth.logout()
  if (current.name !== 'login') {
    router.push({ name: 'login', query: { expired: '1', redirect: current.fullPath } })
  }
})
startIdleWatch()
app.use(ElementPlus, { locale: zhCn })
app.mount('#app')
