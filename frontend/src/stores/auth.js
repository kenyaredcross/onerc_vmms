import { defineStore } from 'pinia'
import http from '../lib/axios'

export const useAuthStore = defineStore('auth', {
  state: () => ({ user: null, isLoggedIn: false, checking: true, loading: false }),
  actions: {
    async check() {
      try {
        const { data } = await http.get('/api/method/frappe.auth.get_logged_user')
        const u = data.message
        this.isLoggedIn = !!(u && u !== 'Guest')
        this.user = this.isLoggedIn ? u : null
      } catch {
        this.isLoggedIn = false
        this.user = null
      } finally {
        this.checking = false
      }
    },
    async login(usr, pwd) {
      this.loading = true
      try {
        const params = new URLSearchParams()
        params.append('usr', usr)
        params.append('pwd', pwd)
        await http.post('/api/method/login', params)
        await this.check()
      } finally {
        this.loading = false
      }
    },
    async logout() {
      await http.get('/api/method/logout')
      this.user = null
      this.isLoggedIn = false
    }
  }
})
