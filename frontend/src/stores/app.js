import { defineStore } from 'pinia'
import axios from 'axios'

export const useAppStore = defineStore('app', {
  state: () => ({
    organization: {},
    labels: {},
    geo: {},
    loaded: false
  }),

  actions: {
    async loadBootstrap() {
      try {
        const res = await axios.get(
          '/api/method/onerc_vmms.api.bootstrap.get_app_bootstrap'
        )
        const data = res.data.message
        this.organization = data.organization
        this.labels = data.labels
        this.geo = data.geo
        this.loaded = true
        this.applyTheme()
      } catch (e) {
        console.error('Bootstrap failed', e)
      }
    },

    applyTheme() {
      const root = document.documentElement
      if (this.organization.primary_color) {
        root.style.setProperty('--primary', this.organization.primary_color)
      }
      if (this.organization.secondary_color) {
        root.style.setProperty('--secondary', this.organization.secondary_color)
      }
    }
  }
})
