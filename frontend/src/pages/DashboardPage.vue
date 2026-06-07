<template>
  <div class="dash">
    <!-- Greeting header -->
    <div class="dash__greeting">
      <div>
        <h1 class="dash__hello">{{ greeting }}, {{ firstName }}</h1>
        <p class="dash__date">{{ todayStr }}</p>
      </div>
      <AppBadge :variant="availVariant" dot>{{ availText }}</AppBadge>
    </div>

    <!-- Stat cards -->
    <div class="stat-grid">
      <div v-for="s in stats" :key="s.label" class="stat-card">
        <div class="stat-card__icon" :class="`stat-card__icon--${s.color}`">
          <component :is="s.icon" :size="20" />
        </div>
        <div class="stat-card__body">
          <p class="stat-card__value">{{ loading ? '—' : s.value }}</p>
          <p class="stat-card__label">{{ s.label }}</p>
        </div>
      </div>
    </div>

    <div class="dash-cols">
      <!-- Pending deployments -->
      <div class="dash-col">
        <div class="section-head">
          <h2>Pending Deployment Requests</h2>
          <router-link to="/deployments" class="section-link">View all</router-link>
        </div>
        <AppSpinner v-if="loadingDeploy" size="md" class="center-spin" />
        <div v-else-if="pending.length === 0" class="empty-state">
          <Send :size="28" class="empty-state__icon" />
          <p>No pending deployment requests</p>
        </div>
        <div v-else class="deploy-list">
          <router-link v-for="d in pending.slice(0,3)" :key="d.name" :to="`/deployments/${d.name}`" class="deploy-item">
            <div class="deploy-item__meta">
              <span class="deploy-item__title">{{ d.project_name || d.name }}</span>
              <AppBadge variant="warning" size="sm">Pending</AppBadge>
            </div>
            <div class="deploy-item__sub">
              <MapPin :size="12" /> {{ d.location || 'Location TBD' }} &bull;
              <Calendar :size="12" /> {{ d.expected_start_date || 'Date TBD' }}
            </div>
          </router-link>
        </div>
      </div>

      <!-- Quick actions -->
      <div class="dash-col">
        <div class="section-head"><h2>Quick Actions</h2></div>
        <div class="action-list">
          <router-link to="/profile" class="action-item">
            <div class="action-item__icon action-item__icon--blue"><UserCog :size="18" /></div>
            <div><p class="action-item__label">Update Profile</p><p class="action-item__sub">Edit personal details and availability</p></div>
            <ChevronRight :size="16" class="action-item__arrow" />
          </router-link>
          <router-link to="/deployments" class="action-item">
            <div class="action-item__icon action-item__icon--red"><Send :size="18" /></div>
            <div><p class="action-item__label">My Deployments</p><p class="action-item__sub">View and respond to assignments</p></div>
            <ChevronRight :size="16" class="action-item__arrow" />
          </router-link>
          <router-link v-if="app.features.membership_enabled" to="/membership" class="action-item">
            <div class="action-item__icon action-item__icon--green"><CreditCard :size="18" /></div>
            <div><p class="action-item__label">Membership</p><p class="action-item__sub">View or renew your membership</p></div>
            <ChevronRight :size="16" class="action-item__arrow" />
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Send, UserCog, CreditCard, MapPin, Calendar, ChevronRight, Briefcase, Clock, CheckCircle2 } from 'lucide-vue-next'
import { useAppStore } from '../stores/app'
import { useAuthStore } from '../stores/auth'
import AppBadge from '../components/ui/AppBadge.vue'
import AppSpinner from '../components/ui/AppSpinner.vue'
import http from '../lib/axios'

const app  = useAppStore()
const auth = useAuthStore()
const loading = ref(true), loadingDeploy = ref(true)
const deployStats = ref({})
const pending = ref([])

const firstName = computed(() => (auth.user || '').split('@')[0].split('.')[0] || 'Volunteer')
const todayStr  = computed(() => new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' }))
const greeting  = computed(() => { const h = new Date().getHours(); return h < 12 ? 'Good morning' : h < 18 ? 'Good afternoon' : 'Good evening' })
const availText    = ref('Available')
const availVariant = ref('success')

const stats = computed(() => [
  { label: 'Total Deployments', value: deployStats.value.total_projects_deployed ?? 0,    icon: Briefcase, color: 'primary' },
  { label: 'Pending Response',  value: deployStats.value.pending_response ?? 0,            icon: Clock,     color: 'warning' },
  { label: 'Active',            value: deployStats.value.active ?? 0,                      icon: Send,      color: 'info' },
  { label: 'Completed',         value: deployStats.value.closed ?? 0,                      icon: CheckCircle2, color: 'success' },
])

onMounted(async () => {
  try {
    const r = await http.get('/api/method/onerc_vmms.volunteer_and_member_management.api.volunteer.get_dashboard_stats')
    deployStats.value = r.data.message || {}
  } catch {} finally { loading.value = false }

  try {
    const r = await http.get('/api/method/onerc_vmms.volunteer_and_member_management.api.projects.get_all_deployed_projects')
    pending.value = (r.data.message || []).filter(d => d.deployment_status === 'Pending')
  } catch {} finally { loadingDeploy.value = false }
})
</script>

<style scoped>
.dash {}
.dash__greeting { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: var(--space-6); flex-wrap: wrap; gap: 12px; }
.dash__hello { font-size: 24px; font-weight: 800; color: var(--c-text); }
.dash__date  { font-size: 13px; color: var(--c-text-muted); margin-top: 3px; }

.stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; margin-bottom: var(--space-8); }
.stat-card { background: var(--c-surface); border: 1px solid var(--c-border); border-radius: var(--radius-lg); padding: 18px; display: flex; align-items: center; gap: 14px; box-shadow: var(--shadow-sm); }
.stat-card__icon { width: 40px; height: 40px; border-radius: var(--radius-md); display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.stat-card__icon--primary { background: var(--c-primary-subtle); color: var(--c-primary); }
.stat-card__icon--warning  { background: var(--c-warning-subtle); color: var(--c-warning); }
.stat-card__icon--info     { background: var(--c-info-subtle);    color: var(--c-info); }
.stat-card__icon--success  { background: var(--c-success-subtle); color: var(--c-success); }
.stat-card__value { font-size: 28px; font-weight: 800; color: var(--c-text); line-height: 1; }
.stat-card__label { font-size: 12px; color: var(--c-text-muted); margin-top: 3px; }

.dash-cols { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-6); }
.section-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.section-head h2 { font-size: 15px; font-weight: 700; color: var(--c-text); }
.section-link { font-size: 13px; color: var(--c-primary); font-weight: 500; }

.empty-state { text-align: center; padding: 32px 16px; background: var(--c-surface); border: 1px solid var(--c-border); border-radius: var(--radius-lg); }
.empty-state__icon { color: var(--c-text-muted); margin: 0 auto 10px; }
.empty-state p { font-size: 13px; color: var(--c-text-muted); }
.center-spin { display: flex; justify-content: center; padding: 32px; }

.deploy-list { display: flex; flex-direction: column; gap: 8px; }
.deploy-item { display: block; background: var(--c-surface); border: 1px solid var(--c-border); border-radius: var(--radius-md); padding: 12px 14px; text-decoration: none; transition: all var(--t-base); }
.deploy-item:hover { border-color: var(--c-primary); box-shadow: var(--shadow-sm); }
.deploy-item__meta { display: flex; align-items: center; justify-content: space-between; margin-bottom: 5px; }
.deploy-item__title { font-size: 14px; font-weight: 600; color: var(--c-text); }
.deploy-item__sub { font-size: 12px; color: var(--c-text-muted); display: flex; align-items: center; gap: 5px; }

.action-list { display: flex; flex-direction: column; gap: 2px; background: var(--c-surface); border: 1px solid var(--c-border); border-radius: var(--radius-lg); overflow: hidden; }
.action-item { display: flex; align-items: center; gap: 12px; padding: 14px 16px; text-decoration: none; transition: background var(--t-fast); border-bottom: 1px solid var(--c-border-subtle); }
.action-item:last-child { border-bottom: none; }
.action-item:hover { background: var(--c-border-subtle); }
.action-item__icon { width: 36px; height: 36px; border-radius: var(--radius-md); display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.action-item__icon--red   { background: var(--c-primary-subtle); color: var(--c-primary); }
.action-item__icon--blue  { background: var(--c-info-subtle);    color: var(--c-info); }
.action-item__icon--green { background: var(--c-success-subtle); color: var(--c-success); }
.action-item__label { font-size: 14px; font-weight: 600; color: var(--c-text); }
.action-item__sub   { font-size: 12px; color: var(--c-text-muted); margin-top: 1px; }
.action-item__arrow { color: var(--c-text-muted); margin-left: auto; flex-shrink: 0; }

@media (max-width: 900px) { .dash-cols { grid-template-columns: 1fr; } }
@media (max-width: 600px) { .stat-grid { grid-template-columns: 1fr 1fr; } }
</style>
