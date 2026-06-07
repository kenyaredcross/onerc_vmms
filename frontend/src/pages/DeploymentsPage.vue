<template>
  <div>
    <div class="page-header">
      <div>
        <h1 class="page-title">Deployments</h1>
        <p class="page-sub">Your mission assignments and deployment history</p>
      </div>
    </div>

    <!-- Filter tabs -->
    <div class="tab-bar">
      <button v-for="tab in tabs" :key="tab.key" class="tab-bar__tab" :class="{ active: activeTab === tab.key }" @click="activeTab = tab.key">
        {{ tab.label }}
        <span v-if="tab.count !== undefined" class="tab-bar__count">{{ tab.count }}</span>
      </button>
    </div>

    <AppSpinner v-if="loading" size="md" class="loading-center" />

    <div v-else-if="filtered.length === 0" class="empty-state">
      <Send :size="36" class="empty-state__icon" />
      <h3>No deployments here</h3>
      <p>Deployment requests will appear here once assigned.</p>
    </div>

    <div v-else class="deploy-grid">
      <router-link v-for="d in filtered" :key="d.name" :to="`/deployments/${d.name}`" class="deploy-card">
        <div class="deploy-card__top">
          <h3 class="deploy-card__title">{{ d.project_name || d.name }}</h3>
          <AppBadge :variant="statusVariant(d.deployment_status)" dot size="sm">{{ d.deployment_status }}</AppBadge>
        </div>
        <div class="deploy-card__meta">
          <span><MapPin :size="13" /> {{ d.location || 'Location TBD' }}</span>
          <span v-if="d.expected_start_date"><Calendar :size="13" /> {{ d.expected_start_date }}</span>
          <span v-if="d.expected_end_date">→ {{ d.expected_end_date }}</span>
        </div>
        <p v-if="d.notes" class="deploy-card__notes">{{ d.notes }}</p>
        <div class="deploy-card__footer">
          <span class="deploy-card__cta">View Details <ArrowRight :size="14" /></span>
        </div>
      </router-link>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Send, MapPin, Calendar, ArrowRight } from 'lucide-vue-next'
import http from '../lib/axios'
import AppBadge from '../components/ui/AppBadge.vue'
import AppSpinner from '../components/ui/AppSpinner.vue'

const loading = ref(true)
const all = ref([])
const activeTab = ref('all')

const tabs = computed(() => [
  { key: 'all',      label: 'All',              count: all.value.length },
  { key: 'Pending',  label: 'Pending Response', count: all.value.filter(d => d.deployment_status === 'Pending').length },
  { key: 'Accepted', label: 'Active',           count: all.value.filter(d => d.deployment_status === 'Accepted').length },
  { key: 'Rejected', label: 'Declined',         count: all.value.filter(d => d.deployment_status === 'Rejected').length },
])

const filtered = computed(() => activeTab.value === 'all' ? all.value : all.value.filter(d => d.deployment_status === activeTab.value))

function statusVariant(s) {
  return { Pending: 'warning', Accepted: 'success', Rejected: 'error', Completed: 'info' }[s] || 'neutral'
}

onMounted(async () => {
  try {
    const r = await http.get('/api/method/onerc_vmms.volunteer_and_member_management.api.projects.get_all_deployed_projects')
    all.value = r.data.message || []
  } catch { all.value = [] }
  finally { loading.value = false }
})
</script>

<style scoped>
.page-header { margin-bottom: 22px; }
.page-title { font-size: 22px; font-weight: 800; color: var(--c-text); }
.page-sub   { font-size: 13px; color: var(--c-text-muted); margin-top: 3px; }

.tab-bar { display: flex; gap: 2px; background: var(--c-surface); border: 1px solid var(--c-border); border-radius: var(--radius-md); padding: 4px; margin-bottom: 20px; overflow-x: auto; }
.tab-bar__tab { padding: 7px 16px; border-radius: var(--radius-sm); font-size: 13px; font-weight: 500; color: var(--c-text-muted); cursor: pointer; white-space: nowrap; display: flex; align-items: center; gap: 6px; transition: all var(--t-fast); }
.tab-bar__tab.active { background: var(--c-primary-subtle); color: var(--c-primary); font-weight: 700; }
.tab-bar__tab:hover:not(.active) { background: var(--c-border-subtle); color: var(--c-text); }
.tab-bar__count { background: var(--c-border); color: var(--c-text-muted); font-size: 11px; padding: 1px 7px; border-radius: var(--radius-full); font-weight: 700; }
.tab-bar__tab.active .tab-bar__count { background: var(--c-primary-subtle); color: var(--c-primary); border: 1px solid var(--c-primary); }

.loading-center { display: flex; justify-content: center; padding: 48px; }
.empty-state { text-align: center; padding: 64px 20px; background: var(--c-surface); border: 1px solid var(--c-border); border-radius: var(--radius-xl); }
.empty-state__icon { color: var(--c-text-muted); margin: 0 auto 16px; }
.empty-state h3 { font-size: 18px; font-weight: 700; color: var(--c-text); margin-bottom: 8px; }
.empty-state p  { font-size: 14px; color: var(--c-text-muted); }

.deploy-grid { display: flex; flex-direction: column; gap: 10px; }
.deploy-card { background: var(--c-surface); border: 1px solid var(--c-border); border-radius: var(--radius-lg); padding: 18px 20px; display: block; text-decoration: none; transition: all var(--t-base); }
.deploy-card:hover { border-color: var(--c-primary); box-shadow: var(--shadow-md); transform: translateX(2px); }
.deploy-card__top { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: 10px; }
.deploy-card__title { font-size: 15px; font-weight: 700; color: var(--c-text); flex: 1; }
.deploy-card__meta { display: flex; flex-wrap: wrap; gap: 12px; font-size: 12px; color: var(--c-text-muted); }
.deploy-card__meta span { display: flex; align-items: center; gap: 4px; }
.deploy-card__notes { font-size: 13px; color: var(--c-text-muted); margin-top: 10px; }
.deploy-card__footer { margin-top: 12px; display: flex; justify-content: flex-end; }
.deploy-card__cta { display: flex; align-items: center; gap: 5px; font-size: 13px; font-weight: 600; color: var(--c-primary); }
</style>
