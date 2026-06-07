import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './styles/base.css'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')

import { useAppStore } from './stores/app'
import { useAuthStore } from './stores/auth'

const appStore  = useAppStore()
const authStore = useAuthStore()
Promise.all([appStore.load(), authStore.check()])
