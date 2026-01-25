import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { useAuthStore } from './stores/auth'
import App from './App.vue'
import router from './router'
import './style.css'   // если у тебя tailwind/global css

const app = createApp(App)
app.use(createPinia())
app.use(router)
const authStore = useAuthStore(createPinia())
authStore.init()
app.mount('#app')
if (typeof window !== 'undefined') {
  const preventDefault = (e) => e.preventDefault()

  window.addEventListener('dragover', preventDefault)
  window.addEventListener('drop', preventDefault)

  // Опционально: убираем при unmount (но в SPA это не обязательно)
  // window.addEventListener('beforeunload', () => {
  //   window.removeEventListener('dragover', preventDefault)
  //   window.removeEventListener('drop', preventDefault)
  // })
}