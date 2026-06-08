<template>
  <div v-if="loading" class="page-center"><AppSpinner size="lg" /></div>

  <div v-else-if="error" class="page-center">
    <AppAlert variant="error" class="max-w">{{ error }}</AppAlert>
    <router-link to="/deployments" class="back-link mt-4">← Back to Deployments</router-link>
  </div>

  <div v-else class="detail">

    <button class="back-btn" @click="router.push('/deployments')">
      <ArrowLeft :size="16" /> Deployments
    </button>

    <!-- Mission header -->
    <div class="mission-card">
      <div class="mission-card__title-row">
        <h1 class="mission-card__title">{{ detail.mission.title }}</h1>
        <AppBadge :variant="typeVariant(detail.mission.type)">{{ detail.mission.type }}</AppBadge>
      </div>
      <div class="mission-meta">
        <span v-if="detail.mission.location"><MapPin :size="13" />{{ detail.mission.location }}</span>
        <span v-if="detail.mission.start_date"><Calendar :size="13" />{{ fmtDate(detail.mission.start_date) }}</span>
        <span v-if="detail.mission.end_date">→ {{ fmtDate(detail.mission.end_date) }}</span>
        <span v-if="detail.mission.duration_days"><Clock :size="13" />{{ detail.mission.duration_days }} days</span>
      </div>
    </div>

    <!-- Response banner -->
    <div class="banner" :class="`banner--${responseClass}`">
      <div class="banner__left">
        <component :is="responseIcon" :size="22" class="banner__icon" />
        <div>
          <p class="banner__status">{{ responseLabel }}</p>
          <p v-if="detail.my_response === 'Pending' && daysLeft !== null" class="banner__sub">
            {{ daysLeft > 0 ? `Respond within ${daysLeft} day${daysLeft === 1 ? '' : 's'}` : 'Response deadline has passed' }}
          </p>
        </div>
      </div>
      <div class="banner__actions">
        <template v-if="detail.my_response === 'Pending'">
          <AppButton variant="danger"  size="sm" @click="showDecline = true">Decline</AppButton>
          <AppButton variant="primary" size="sm" @click="showAccept  = true">Accept</AppButton>
        </template>
        <AppButton v-if="detail.my_response === 'Accepted'" variant="ghost" size="sm" @click="showWithdraw = true">
          Withdraw
        </AppButton>
      </div>
    </div>

    <!-- Tabs -->
    <div class="tab-bar">
      <button v-for="t in tabs" :key="t" class="tab-bar__btn" :class="{ active: activeTab === t }" @click="activeTab = t">{{ t }}</button>
    </div>

    <!-- Overview -->
    <div v-if="activeTab === 'Overview'" class="tab-body">
      <div v-if="detail.message_from_manager" class="msg-box">
        <p class="section-label">Message from Manager</p>
        <div class="rich-text" v-html="detail.message_from_manager" />
      </div>
      <div v-if="detail.mission.background" :class="detail.message_from_manager ? 'mt-6' : ''">
        <p class="section-label">Background</p>
        <div class="rich-text" v-html="detail.mission.background" />
      </div>
      <div v-if="detail.mission.objectives" class="mt-6">
        <p class="section-label">Objectives</p>
        <div class="rich-text" v-html="detail.mission.objectives" />
      </div>
      <div v-if="detail.mission.expected_output" class="mt-6">
        <p class="section-label">Expected Output</p>
        <div class="rich-text" v-html="detail.mission.expected_output" />
      </div>
      <div v-if="!detail.message_from_manager && !detail.mission.background && !detail.mission.objectives" class="empty-state">
        <FileText :size="28" class="empty-icon" /><p>No overview content available yet.</p>
      </div>
    </div>

    <!-- Itinerary -->
    <div v-if="activeTab === 'Itinerary'" class="tab-body">
      <div v-if="detail.itinerary && detail.itinerary.length" class="itin-wrap">
        <table class="itin-table">
          <thead>
            <tr><th>Date</th><th>Time</th><th>Activity</th><th>Responsible</th><th>Venue</th></tr>
          </thead>
          <tbody>
            <tr v-for="(row, i) in detail.itinerary" :key="i">
              <td>{{ fmtDate(row.date) || '—' }}</td>
              <td>{{ row.start_time ? row.start_time.slice(0,5) : '—' }}{{ row.end_time ? '–' + row.end_time.slice(0,5) : '' }}</td>
              <td>{{ row.activity || '—' }}</td>
              <td>{{ row.person_responsible || '—' }}</td>
              <td>{{ row.venue || '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="empty-state">
        <CalendarDays :size="28" class="empty-icon" /><p>No itinerary has been added yet.</p>
      </div>
    </div>

    <!-- People -->
    <div v-if="activeTab === 'People'" class="tab-body">
      <div class="empty-state">
        <Users :size="28" class="empty-icon" /><p>People details will be shared by your manager.</p>
      </div>
    </div>

    <!-- Accept Modal -->
    <AppModal v-model="showAccept" title="Accept Deployment" size="sm">
      <p class="modal-intro">Please confirm you have reviewed this deployment request.</p>
      <label class="check-label mt-3">
        <input type="checkbox" v-model="confirmRead" />
        <span>I have read and understood the Terms of Reference for this deployment.</span>
      </label>
      <template #footer>
        <AppButton variant="ghost" size="sm" @click="showAccept = false">Cancel</AppButton>
        <AppButton variant="primary" size="sm" :loading="submitting" :disabled="!confirmRead" @click="respond('Accepted')">Confirm Accept</AppButton>
      </template>
    </AppModal>

    <!-- Decline Modal -->
    <AppModal v-model="showDecline" title="Decline Deployment" size="sm">
      <p class="modal-intro">Please provide a reason for declining.</p>
      <label class="field-label mt-3">Reason <span class="req">*</span></label>
      <textarea v-model="declineReason" class="reason-input" rows="3" placeholder="Please explain why you are unable to accept this deployment…" />
      <template #footer>
        <AppButton variant="ghost" size="sm" @click="showDecline = false">Cancel</AppButton>
        <AppButton variant="danger" size="sm" :loading="submitting" :disabled="!declineReason.trim()" @click="respond('Declined', declineReason)">Confirm Decline</AppButton>
      </template>
    </AppModal>

    <!-- Withdraw Modal -->
    <AppModal v-model="showWithdraw" title="Withdraw Acceptance" size="sm">
      <AppAlert variant="warning" class="mb-3">Withdrawing should only be done if absolutely necessary.</AppAlert>
      <label class="field-label mt-3">Withdrawal Reason <span class="req">*</span></label>
      <textarea v-model="withdrawReason" class="reason-input" rows="3" placeholder="Please explain your reason for withdrawing…" />
      <template #footer>
        <AppButton variant="ghost" size="sm" @click="showWithdraw = false">Cancel</AppButton>
        <AppButton variant="danger" size="sm" :loading="submitting" :disabled="!withdrawReason.trim()" @click="respond('Withdrawn', withdrawReason)">Confirm Withdraw</AppButton>
      </template>
    </AppModal>

    <!-- Toast -->
    <Teleport to="body">
      <div v-if="toast" class="toast-wrap">
        <AppAlert :variant="toast.type">{{ toast.message }}</AppAlert>
      </div>
    </Teleport>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, MapPin, Calendar, Clock, CheckCircle2, XCircle, MinusCircle, AlertCircle, FileText, CalendarDays, Users } from 'lucide-vue-next'
import http from '../lib/axios'
import AppSpinner from '../components/ui/AppSpinner.vue'
import AppAlert   from '../components/ui/AppAlert.vue'
import AppBadge   from '../components/ui/AppBadge.vue'
import AppButton  from '../components/ui/AppButton.vue'
import AppModal   from '../components/ui/AppModal.vue'

const route  = useRoute()
const router = useRouter()

const loading  = ref(true)
const error    = ref('')
const detail   = ref(null)
const activeTab = ref('Overview')
const tabs = ['Overview', 'Itinerary', 'People']

const showAccept   = ref(false)
const showDecline  = ref(false)
const showWithdraw = ref(false)
const confirmRead  = ref(false)
const declineReason  = ref('')
const withdrawReason = ref('')
const submitting = ref(false)
const toast = ref(null)

function showToast(type, message) {
  toast.value = null
  nextTick(() => { toast.value = { type, message }; setTimeout(() => toast.value = null, 4000) })
}

const responseClass = computed(() => ({
  Pending: 'warning', Accepted: 'success', Declined: 'error', Withdrawn: 'neutral'
}[detail.value?.my_response] || 'neutral'))

const responseLabel = computed(() => ({
  Pending:   'Response Required',
  Accepted:  'You accepted this deployment',
  Declined:  'You declined this deployment',
  Withdrawn: 'You withdrew from this deployment',
}[detail.value?.my_response] || ''))

const responseIcon = computed(() => ({
  Pending: AlertCircle, Accepted: CheckCircle2, Declined: XCircle, Withdrawn: MinusCircle
}[detail.value?.my_response] || AlertCircle))

const daysLeft = computed(() => {
  if (!detail.value?.response_deadline) return null
  const diff = new Date(detail.value.response_deadline) - new Date()
  return diff < 0 ? 0 : Math.ceil(diff / 86400000)
})

function typeVariant(t) {
  return { Emergency: 'error', Routine: 'info', Training: 'primary', Assessment: 'warning' }[t] || 'neutral'
}

function fmtDate(d) {
  if (!d) return ''
  return new Date(d).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
}

async function respond(response, reason) {
  submitting.value = true
  try {
    const params = new URLSearchParams()
    params.append('assignment_row', detail.value.assignment_row)
    params.append('response', response)
    if (reason) params.append('reason', reason)
    await http.post('/api/method/onerc_vmms.api.deployment.respond_to_deployment', params)
    detail.value.my_response = response
    showAccept.value = false; showDecline.value = false; showWithdraw.value = false
    showToast('success', `Your response has been recorded: ${response}`)
  } catch (err) {
    showToast('error', err.response?.data?.exception?.split('\n').pop() || 'Failed to submit response.')
  } finally { submitting.value = false }
}

onMounted(async () => {
  try {
    const r = await http.get('/api/method/onerc_vmms.api.deployment.get_deployment_detail', {
      params: { deployment_request: route.params.id }
    })
    detail.value = r.data.message
  } catch (err) {
    error.value = err.response?.status === 403
      ? 'You are not assigned to this deployment.'
      : 'Failed to load deployment details.'
  } finally { loading.value = false }
})
</script>

<style scoped>
.page-center { display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 60vh; gap: 16px; }
.max-w { max-width: 480px; }
.back-link { font-size: 13px; color: var(--c-primary); font-weight: 600; text-decoration: none; }
.mt-4 { margin-top: 16px; }

.detail { max-width: 760px; margin: 0 auto; }

.back-btn {
  display: inline-flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 600;
  color: var(--c-text-muted); background: none; border: none; cursor: pointer;
  padding: 0; margin-bottom: 18px; transition: color var(--t-fast);
}
.back-btn:hover { color: var(--c-text); }

.mission-card {
  background: var(--c-surface); border: 1px solid var(--c-border);
  border-radius: var(--radius-lg); padding: 20px 22px; margin-bottom: 14px;
  box-shadow: var(--shadow-sm);
}
.mission-card__title-row { display: flex; align-items: flex-start; gap: 12px; flex-wrap: wrap; margin-bottom: 10px; }
.mission-card__title { font-size: 20px; font-weight: 800; color: var(--c-text); flex: 1; line-height: 1.3; }
.mission-meta { display: flex; flex-wrap: wrap; gap: 14px; font-size: 12px; color: var(--c-text-muted); }
.mission-meta span { display: flex; align-items: center; gap: 4px; }

.banner {
  border-radius: var(--radius-lg); padding: 14px 18px; margin-bottom: 18px;
  display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap;
}
.banner--warning { background: var(--c-warning-subtle); border: 1px solid color-mix(in srgb, var(--c-warning) 30%, transparent); }
.banner--success { background: var(--c-success-subtle); border: 1px solid color-mix(in srgb, var(--c-success) 30%, transparent); }
.banner--error   { background: var(--c-error-subtle);   border: 1px solid color-mix(in srgb, var(--c-error)   30%, transparent); }
.banner--neutral { background: var(--c-border-subtle);  border: 1px solid var(--c-border); }
.banner__left { display: flex; align-items: flex-start; gap: 10px; }
.banner--warning .banner__icon { color: var(--c-warning); }
.banner--success .banner__icon { color: var(--c-success); }
.banner--error   .banner__icon { color: var(--c-error); }
.banner--neutral .banner__icon { color: var(--c-text-muted); }
.banner__status { font-size: 14px; font-weight: 700; color: var(--c-text); }
.banner__sub { font-size: 12px; color: var(--c-text-muted); margin-top: 2px; }
.banner__actions { display: flex; gap: 8px; flex-shrink: 0; }

.tab-bar { display: flex; gap: 2px; background: var(--c-surface); border: 1px solid var(--c-border); border-radius: var(--radius-md); padding: 4px; margin-bottom: 18px; }
.tab-bar__btn { padding: 7px 18px; border-radius: var(--radius-sm); font-size: 13px; font-weight: 500; color: var(--c-text-muted); cursor: pointer; white-space: nowrap; }
.tab-bar__btn.active { background: var(--c-primary-subtle); color: var(--c-primary); font-weight: 700; }
.tab-bar__btn:hover:not(.active) { background: var(--c-border-subtle); color: var(--c-text); }

.tab-body { background: var(--c-surface); border: 1px solid var(--c-border); border-radius: var(--radius-lg); padding: 22px; }
.section-label { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: var(--c-text-muted); margin-bottom: 8px; }
.rich-text { font-size: 14px; color: var(--c-text-secondary); line-height: 1.7; }
.mt-6 { margin-top: 24px; }
.msg-box { background: var(--c-primary-subtle); border-radius: var(--radius-md); padding: 14px 16px; }

.itin-wrap { overflow-x: auto; }
.itin-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.itin-table th { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--c-text-muted); padding: 8px 10px; border-bottom: 1.5px solid var(--c-border); text-align: left; white-space: nowrap; }
.itin-table td { padding: 10px; border-bottom: 1px solid var(--c-border-subtle); color: var(--c-text); vertical-align: top; }
.itin-table tr:last-child td { border-bottom: none; }
.itin-table tr:hover td { background: var(--c-border-subtle); }

.empty-state { text-align: center; padding: 40px 16px; }
.empty-icon { color: var(--c-text-muted); margin: 0 auto 12px; }
.empty-state p { font-size: 14px; color: var(--c-text-muted); }

/* Modal internals */
.modal-intro { font-size: 14px; color: var(--c-text-secondary); line-height: 1.5; }
.check-label { display: flex; align-items: flex-start; gap: 10px; font-size: 14px; cursor: pointer; line-height: 1.5; }
.check-label input { margin-top: 3px; accent-color: var(--c-primary); width: 16px; height: 16px; flex-shrink: 0; }
.mt-3 { margin-top: 12px; }
.mb-3 { margin-bottom: 12px; }
.field-label { font-size: 13px; font-weight: 600; color: var(--c-text); display: block; margin-bottom: 6px; }
.req { color: var(--c-primary); }
.reason-input {
  width: 100%; padding: 9px 12px; border: 1.5px solid var(--c-border);
  border-radius: var(--radius-md); background: var(--c-surface); color: var(--c-text);
  font-size: 14px; font-family: var(--font, sans-serif); resize: vertical; outline: none;
  transition: border-color var(--t-base);
}
.reason-input:focus { border-color: var(--c-primary); }

.toast-wrap { position: fixed; bottom: 24px; right: 24px; z-index: 600; width: 340px; max-width: calc(100vw - 48px); }

@media (max-width: 600px) {
  .detail { max-width: 100%; }
  .mission-card { padding: 16px; }
  .tab-body { padding: 16px; }
  .banner { flex-direction: column; align-items: flex-start; }
}
</style>
