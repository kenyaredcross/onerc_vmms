import { createRouter, createWebHistory } from 'vue-router'

import Home from './views/Home.vue'
import Register from './views/Register.vue'
import Directory from './views/Directory.vue'
import Login from './views/Login.vue'

const routes = [
  { path: '/', component: Home },
  { path: '/register', component: Register },
  { path: '/directory', component: Directory },
  { path: '/login', component: Login },
]

export default createRouter({
  history: createWebHistory(),
  routes
})