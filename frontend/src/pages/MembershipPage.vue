<template>
  <div>
    <div class="page-header">
      <h1 class="page-title">Membership</h1>
      <p class="page-sub">{{ app.memberLabel }} status and subscription management</p>
    </div>

    <div v-if="loading" class="loading-center"><AppSpinner size="md" /></div>

    <template v-else>

      <!-- Active / Expired card -->
      <template v-if="myMembership?.membership_status === 'Active' || myMembership?.membership_status === 'Expired'">
        <div class="mem-card-wrap">
          <div class="mem-card" :class="myMembership.membership_status === 'Active' ? 'mem-card--active' : 'mem-card--expired'">
            <div class="mem-card__header">
              <div class="mem-card__org">
                <div class="rc-cross"><div class="rc-v"/><div class="rc-h"/></div>
                <span class="mem-card__org-name">{{ app.orgName }}</span>
              </div>
              <AppBadge :variant="myMembership.membership_status === 'Active' ? 'success' : 'error'" size="sm">
                {{ myMembership.membership_status }}
              </AppBadge>
            </div>
            <div class="mem-card__body">
              <AppAvatar :name="myMembership.full_name" :photo="myMembership.photo" size="xl" />
              <div class="mem-card__info">
                <p class="mem-card__name">{{ myMembership.full_name }}</p>
                <p class="mem-card__plan">{{ sub?.plan }}</p>
                <p class="mem-card__id mono">{{ myMembership.member }}</p>
              </div>
              <div v-if="sub?.qr_code" class="mem-card__qr">
                <img :src="sub.qr_code" alt="QR Code" />
              </div>
            </div>
            <div class="mem-card__dates">
              <div v-if="sub?.from_date">
                <span class="date-label">From</span>
                <span class="date-val">{{ fmtDate(sub.from_date) }}</span>
              </div>
              <span class="date-sep">→</span>
              <div v-if="sub?.to_date">
                <span class="date-label">Until</span>
                <span class="date-val">{{ fmtDate(sub.to_date) }}</span>
              </div>
            </div>
          </div>
        </div>
        <div class="card-actions">
          <AppButton v-if="sub?.certificate" variant="outline" size="sm" :href="sub.certificate">Download Certificate</AppButton>
          <AppButton v-if="myMembership.membership_status === 'Expired'" variant="primary" size="sm" @click="startRenew">Renew Membership</AppButton>
        </div>
      </template>

      <!-- Pending payment -->
      <template v-else-if="myMembership?.membership_status === 'Pending'">
        <AppAlert variant="warning" title="Awaiting Payment Confirmation" class="mb-4">
          Your membership application is pending payment confirmation. Please complete your payment and contact support if not confirmed within 24 hours.
        </AppAlert>
        <div class="sub-details">
          <div class="sub-grid">
            <div><label>Plan</label><strong>{{ sub?.plan }}</strong></div>
            <div><label>Amount</label><strong>{{ sub?.amount }} {{ sub?.currency }}</strong></div>
            <div><label>Payment Method</label><strong>{{ sub?.payment_method }}</strong></div>
            <div><label>Reference</label><strong>{{ sub?.payment_reference || '—' }}</strong></div>
          </div>
        </div>
      </template>

      <!-- No membership — show plans -->
      <template v-else>
        <AppAlert v-if="applySuccess" variant="success" dismissible class="mb-4">{{ applySuccess }}</AppAlert>

        <div v-if="loadingPlans" class="loading-center"><AppSpinner size="sm" /></div>
        <div v-else-if="!plans.length" class="empty-state">
          <CreditCard :size="36" class="empty-icon" />
          <h3>No Plans Available</h3>
          <p>No membership plans are currently available. Check back later.</p>
        </div>
        <div v-else>
          <p class="plans-intro">Choose a membership plan to get started.</p>
          <div class="plans-grid">
            <div v-for="plan in plans" :key="plan.name" class="plan-card">
              <div class="plan-card__head">
                <h3 class="plan-card__name">{{ plan.plan_name }}</h3>
                <div class="plan-card__price">
                  <span class="plan-card__amount">{{ plan.annual_fee }}</span>
                  <span class="plan-card__currency"> {{ plan.currency }}</span>
                  <span class="plan-card__period">/yr</span>
                </div>
              </div>
              <p v-if="plan.description" class="plan-card__desc">{{ plan.description }}</p>
              <ul v-if="plan.benefits?.length" class="plan-card__benefits">
                <li v-for="b in plan.benefits" :key="b.benefit">
                  <CheckCircle2 :size="14" class="benefit-icon" /> {{ b.benefit }}
                </li>
              </ul>
              <AppButton variant="primary" full class="plan-card__btn" @click="openApply(plan)">Apply</AppButton>
            </div>
          </div>
        </div>
      </template>

    </template>

    <!-- Apply Modal -->
    <AppModal v-model="showApply" title="Apply for Membership" size="sm">
      <p class="modal-plan-name">{{ selectedPlan?.plan_name }}</p>
      <p class="modal-plan-fee">{{ selectedPlan?.annual_fee }} {{ selectedPlan?.currency }} / year</p>
      <div class="form-stack mt-4">
        <AppSelect v-model="applyForm.payment_method" label="Payment Method" :options="payMethods" placeholder="Select method…" required />
        <div>
          <label class="field-label">Payment Reference <span class="req">*</span></label>
          <input v-model="applyForm.payment_reference" class="text-input" placeholder="M-Pesa code, bank ref, etc." />
        </div>
      </div>
      <AppAlert v-if="applyError" variant="error" class="mt-3">{{ applyError }}</AppAlert>
      <template #footer>
        <AppButton variant="ghost" size="sm" @click="showApply = false">Cancel</AppButton>
        <AppButton variant="primary" size="sm" :loading="applying"
          :disabled="!applyForm.payment_method || !applyForm.payment_reference.trim()"
          @click="submitApply">
          Submit Application
        </AppButton>
      </template>
    </AppModal>

    <Teleport to="body">
      <div v-if="toast" class="toast-wrap">
        <AppAlert :variant="toast.type">{{ toast.message }}</AppAlert>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { CreditCard, CheckCircle2 } from 'lucide-vue-next'
import { useAppStore } from '../stores/app'
import http from '../lib/axios'
import AppSpinner from '../components/ui/AppSpinner.vue'
import AppAlert   from '../components/ui/AppAlert.vue'
import AppBadge   from '../components/ui/AppBadge.vue'
import AppButton  from '../components/ui/AppButton.vue'
import AppModal   from '../components/ui/AppModal.vue'
import AppSelect  from '../components/ui/AppSelect.vue'
import AppAvatar  from '../components/ui/AppAvatar.vue'

const app = useAppStore()

const loading      = ref(true)
const loadingPlans = ref(true)
const myMembership = ref(null)
const plans        = ref([])

const sub = computed(() => myMembership.value?.subscription)

const showApply    = ref(false)
const selectedPlan = ref(null)
const applying     = ref(false)
const applyError   = ref('')
const applySuccess = ref('')
const applyForm    = ref({ payment_method: '', payment_reference: '' })
const payMethods   = ['M-Pesa', 'Bank Transfer', 'Cash', 'Other']

const toast = ref(null)
function showToast(type, message) {
  toast.value = null
  nextTick(() => { toast.value = { type, message }; setTimeout(() => toast.value = null, 4000) })
}

function fmtDate(d) {
  if (!d) return '—'
  return new Date(d).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
}

function openApply(plan) {
  selectedPlan.value = plan
  applyForm.value = { payment_method: '', payment_reference: '' }
  applyError.value = ''
  showApply.value = true
}

function startRenew() {
  if (plans.value.length) openApply(plans.value[0])
  else showToast('info', 'Loading plans…')
}

async function submitApply() {
  applyError.value = ''
  applying.value = true
  try {
    const params = new URLSearchParams()
    params.append('plan', selectedPlan.value.name)
    params.append('payment_method', applyForm.value.payment_method)
    params.append('payment_reference', applyForm.value.payment_reference)
    await http.post('/api/method/onerc_vmms.api.membership.apply_for_membership', params)
    showApply.value = false
    applySuccess.value = 'Your application has been submitted. Awaiting payment confirmation.'
    await loadMyMembership()
  } catch (err) {
    applyError.value = err.response?.data?.exception?.split('\n').pop() || 'Submission failed.'
  } finally { applying.value = false }
}

async function loadMyMembership() {
  try {
    const r = await http.get('/api/method/onerc_vmms.api.membership.get_my_membership')
    myMembership.value = r.data.message
  } catch { myMembership.value = null }
}

onMounted(async () => {
  await loadMyMembership()
  loading.value = false
  try {
    const r = await http.get('/api/method/onerc_vmms.api.membership.get_membership_plans')
    plans.value = r.data.message || []
  } catch { plans.value = [] } finally { loadingPlans.value = false }
})
</script>

<style scoped>
.page-header { margin-bottom: 22px; }
.page-title  { font-size: 22px; font-weight: 800; color: var(--c-text); }
.page-sub    { font-size: 13px; color: var(--c-text-muted); margin-top: 3px; }
.loading-center { display: flex; justify-content: center; padding: 48px; }
.mb-4 { margin-bottom: 16px; }
.mt-3 { margin-top: 12px; }
.mt-4 { margin-top: 16px; }

/* Membership card */
.mem-card-wrap { display: flex; justify-content: center; margin-bottom: 16px; }
.mem-card {
  width: 100%; max-width: 480px; border-radius: var(--radius-xl);
  overflow: hidden; box-shadow: var(--shadow-lg); border: 1px solid var(--c-border);
}
.mem-card--active  { background: linear-gradient(135deg, var(--c-secondary, #1e3a5f) 0%, #0f1f36 100%); }
.mem-card--expired { background: linear-gradient(135deg, #374151 0%, #1f2937 100%); }

.mem-card__header { padding: 16px 20px 10px; display: flex; align-items: center; justify-content: space-between; }
.mem-card__org { display: flex; align-items: center; gap: 8px; }
.rc-cross { position: relative; width: 20px; height: 20px; flex-shrink: 0; }
.rc-v { position: absolute; left: 50%; top: 0; transform: translateX(-50%); width: 7px; height: 100%; background: var(--c-primary); border-radius: 2px; }
.rc-h { position: absolute; top: 50%; left: 0; transform: translateY(-50%); width: 100%; height: 7px; background: var(--c-primary); border-radius: 2px; }
.mem-card__org-name { font-size: 12px; font-weight: 700; color: rgba(255,255,255,0.7); text-transform: uppercase; letter-spacing: 0.06em; }

.mem-card__body { padding: 10px 20px 14px; display: flex; align-items: center; gap: 14px; }
.mem-card__info { flex: 1; }
.mem-card__name { font-size: 18px; font-weight: 800; color: #fff; margin-bottom: 2px; }
.mem-card__plan { font-size: 12px; color: rgba(255,255,255,0.6); margin-bottom: 4px; }
.mem-card__id   { font-size: 13px; color: rgba(255,255,255,0.8); }
.mem-card__qr img { width: 64px; height: 64px; border-radius: var(--radius-md); background: #fff; padding: 4px; }
.mono { font-family: var(--font-mono, monospace); }

.mem-card__dates { padding: 12px 20px; border-top: 1px solid rgba(255,255,255,0.1); display: flex; align-items: center; gap: 14px; }
.date-label { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: rgba(255,255,255,0.5); display: block; }
.date-val   { font-size: 13px; font-weight: 700; color: #fff; }
.date-sep   { font-size: 16px; color: rgba(255,255,255,0.3); }

.card-actions { display: flex; justify-content: center; gap: 10px; margin-bottom: 24px; }

/* Pending */
.sub-details { background: var(--c-surface); border: 1px solid var(--c-border); border-radius: var(--radius-lg); padding: 20px; }
.sub-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.sub-grid div { display: flex; flex-direction: column; gap: 3px; }
.sub-grid label { font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: var(--c-text-muted); }
.sub-grid strong { font-size: 14px; color: var(--c-text); }

/* Plans */
.plans-intro { font-size: 14px; color: var(--c-text-muted); margin-bottom: 16px; }
.plans-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }
.plan-card {
  background: var(--c-surface); border: 1px solid var(--c-border);
  border-radius: var(--radius-lg); padding: 20px;
  display: flex; flex-direction: column; gap: 12px;
  box-shadow: var(--shadow-sm); transition: box-shadow var(--t-base), border-color var(--t-base);
}
.plan-card:hover { box-shadow: var(--shadow-md); border-color: var(--c-primary); }
.plan-card__head { display: flex; align-items: flex-start; justify-content: space-between; gap: 8px; }
.plan-card__name   { font-size: 16px; font-weight: 800; color: var(--c-text); }
.plan-card__price  { text-align: right; flex-shrink: 0; }
.plan-card__amount { font-size: 22px; font-weight: 800; color: var(--c-primary); }
.plan-card__currency, .plan-card__period { font-size: 12px; color: var(--c-text-muted); }
.plan-card__desc { font-size: 13px; color: var(--c-text-muted); line-height: 1.5; }
.plan-card__benefits { list-style: none; display: flex; flex-direction: column; gap: 6px; flex: 1; }
.plan-card__benefits li { display: flex; align-items: flex-start; gap: 7px; font-size: 13px; color: var(--c-text-secondary); }
.benefit-icon { color: var(--c-success); flex-shrink: 0; margin-top: 1px; }
.plan-card__btn { margin-top: auto; }

.empty-state { text-align: center; padding: 64px 20px; background: var(--c-surface); border: 1px solid var(--c-border); border-radius: var(--radius-xl); }
.empty-icon { color: var(--c-text-muted); margin: 0 auto 16px; }
.empty-state h3 { font-size: 18px; font-weight: 700; color: var(--c-text); margin-bottom: 8px; }
.empty-state p  { font-size: 14px; color: var(--c-text-muted); }

/* Modal */
.modal-plan-name { font-size: 16px; font-weight: 800; color: var(--c-text); }
.modal-plan-fee  { font-size: 13px; color: var(--c-text-muted); margin-top: 2px; }
.form-stack { display: flex; flex-direction: column; gap: 14px; }
.field-label { font-size: 13px; font-weight: 600; color: var(--c-text); display: block; margin-bottom: 6px; }
.req { color: var(--c-primary); }
.text-input {
  width: 100%; padding: 9px 13px; border: 1.5px solid var(--c-border);
  border-radius: var(--radius-md); background: var(--c-surface); color: var(--c-text);
  font-size: 14px; outline: none; transition: border-color var(--t-base);
}
.text-input:focus { border-color: var(--c-primary); }

.toast-wrap { position: fixed; bottom: 24px; right: 24px; z-index: 600; width: 340px; max-width: calc(100vw - 48px); }

@media (max-width: 500px) {
  .mem-card__body { flex-direction: column; align-items: flex-start; }
  .sub-grid { grid-template-columns: 1fr; }
}
</style>
