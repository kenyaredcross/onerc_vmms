import { defineStore } from 'pinia'
import http from '../lib/axios'

export const useAppStore = defineStore('app', {
  state: () => ({
    org: {}, labels: {}, geo: {}, features: {}, consent: {},
    loaded: false, error: null
  }),
  getters: {
    orgName: s => s.org.name || 'OneRC',
    logo: s => s.org.logo || null,
    primary: s => s.org.primary_color || '#EE2435',
    secondary: s => s.org.secondary_color || '#011E41',
    volunteerLabel: s => s.labels.volunteer || 'Volunteer',
    memberLabel: s => s.labels.member || 'Member',
    geoLevels: s => s.geo.levels || [],
  },
  actions: {
    async load() {
      try {
        const { data } = await http.get('/api/method/onerc_vmms.api.bootstrap.get_app_bootstrap')
        const d = data.message
        this.org = d.organization
        this.labels = d.labels
        this.geo = d.geo
        this.features = d.features
        this.consent = d.consent
        this.loaded = true
        this.applyTheme()
      } catch { this.loaded = true }
    },
    applyTheme() {
      const r = document.documentElement
      if (this.org.primary_color) r.style.setProperty('--c-primary', this.org.primary_color)
      if (this.org.secondary_color) r.style.setProperty('--c-secondary', this.org.secondary_color)
      if (this.org.accent_color) r.style.setProperty('--c-accent', this.org.accent_color)
      if (this.org.background) r.style.setProperty('--c-bg', this.org.background)
    }
  }
})
