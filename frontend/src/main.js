import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import './utils/axios'
import App from './App.vue'
import './style.css'

import Home from './views/Home.vue'
import Register from './views/Register.vue'
import Directory from './views/Directory.vue'
import Login from './views/Login.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: Home },
    { path: '/register', component: Register },
    { path: '/directory', component: Directory },
    { path: '/login', component: Login },
  ]
})

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
