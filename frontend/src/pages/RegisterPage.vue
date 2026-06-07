<template>
  <div class="reg-wrap">
    <div class="reg-card">
      <div class="reg-header">
        <h1 class="reg-header__title">{{ app.volunteerLabel }} Registration</h1>
        <p class="reg-header__sub">{{ app.orgName }}</p>
      </div>

      <AppSteps :steps="stepLabels" :current="step" class="reg-steps" />

      <!-- Step 0: Personal Info -->
      <div v-if="step === 0" class="reg-body">
        <div class="grid-3">
          <AppInput v-model="form.first_name"  label="First Name"   placeholder="John"    :error="e.first_name"  required />
          <AppInput v-model="form.middle_name" label="Middle Name"  placeholder="M." />
          <AppInput v-model="form.last_name"   label="Last Name"    placeholder="Doe"     :error="e.last_name"   required />
        </div>
        <div class="grid-3 mt">
          <AppInput  v-model="form.date_of_birth" label="Date of Birth" type="date" :error="e.dob" required />
          <AppSelect v-model="form.gender" label="Gender" :options="genders" placeholder="Select gender..." />
          <AppSelect v-model="form.nationality" label="Nationality" :options="countries" placeholder="Select…" value-key="name" label-key="country_name" />
        </div>
        <div class="grid-2 mt">
          <AppInput v-model="form.primary_phone" label="Primary Phone" type="tel" placeholder="+254700000000" :prefix-icon="Phone" :error="e.phone" required />
          <AppInput v-model="form.email_address" label="Email Address" type="email" placeholder="you@example.com" :prefix-icon="Mail" :error="e.email" />
        </div>
        <div class="section-divider"><span>Emergency Contact</span></div>
        <div class="grid-3 mt">
          <AppInput v-model="form.emergency_contact_name"         label="Contact Name"  placeholder="Jane Doe"   required />
          <AppInput v-model="form.emergency_contact_relationship" label="Relationship"  placeholder="Spouse"     required />
          <AppInput v-model="form.emergency_contact_phone"        label="Phone"         type="tel" placeholder="+254..." required />
        </div>
      </div>

      <!-- Step 1: Location -->
      <div v-if="step === 1" class="reg-body">
        <GeoSelector :levels="app.geoLevels" v-model="form.home_geo_node" />
        <div class="mt">
          <AppTextarea v-model="form.physical_address" label="Physical Address" placeholder="Street, building, landmark…" :rows="3" />
        </div>
      </div>

      <!-- Step 2: Skills & Availability -->
      <div v-if="step === 2" class="reg-body">
        <div class="section-label">Skills</div>
        <div v-for="(sk, i) in form.skills" :key="i" class="repeater-row">
          <AppSelect v-model="sk.skill" :options="skillTypes" placeholder="Select skill…" value-key="name" label-key="skill_name" class="flex-2" />
          <AppSelect v-model="sk.proficiency_level" :options="proficiencies" placeholder="Level…" class="flex-1" />
          <button class="repeater-remove" @click="form.skills.splice(i,1)" type="button" aria-label="Remove"><X :size="16"/></button>
        </div>
        <button class="repeater-add" @click="form.skills.push({skill:'',proficiency_level:''})" type="button">+ Add Skill</button>

        <div class="section-label mt-6">Languages</div>
        <div v-for="(lang, i) in form.languages" :key="i" class="repeater-row">
          <AppInput v-model="lang.language" placeholder="Language name…" class="flex-2" />
          <AppSelect v-model="lang.spoken_proficiency" :options="langLevels" placeholder="Spoken…" class="flex-1" />
          <button class="repeater-remove" @click="form.languages.splice(i,1)" type="button" aria-label="Remove"><X :size="16"/></button>
        </div>
        <button class="repeater-add" @click="form.languages.push({language:'',spoken_proficiency:'',written_proficiency:'Conversational'})" type="button">+ Add Language</button>

        <div class="section-label mt-6">Availability</div>
        <AppSelect v-model="form.availability_status" label="Current Availability Status" :options="availStatuses" placeholder="Select status…" />
      </div>

      <!-- Step 3: Consent & Review -->
      <div v-if="step === 3" class="reg-body">
        <AppCard class="review-card">
          <template #header><span class="review-card__title">Review Your Information</span></template>
          <div class="review-grid">
            <div><label>Full Name</label><strong>{{ [form.first_name, form.middle_name, form.last_name].filter(Boolean).join(' ') }}</strong></div>
            <div><label>Phone</label><strong>{{ form.primary_phone || '—' }}</strong></div>
            <div><label>Email</label><strong>{{ form.email_address || '—' }}</strong></div>
            <div><label>Skills</label><strong>{{ form.skills.length }} added</strong></div>
            <div><label>Languages</label><strong>{{ form.languages.length }} added</strong></div>
            <div><label>Availability</label><strong>{{ form.availability_status || '—' }}</strong></div>
          </div>
        </AppCard>

        <div class="consent-block">
          <p class="consent-text">{{ app.consent.biodata_text || 'I consent to the use of my biodata for deployment purposes by ' + app.orgName + '.' }}</p>
          <label class="consent-check" :class="{ 'consent-check--error': e.consent1 }">
            <input type="checkbox" v-model="form.consent_to_use_of_bio_data" />
            <span>I consent to the use of my biodata for deployment purposes</span>
          </label>
          <label class="consent-check mt-2" :class="{ 'consent-check--error': e.consent2 }">
            <input type="checkbox" v-model="form.accepted_volunteer_terms" />
            <span>I accept the {{ app.volunteerLabel }} Terms and Conditions</span>
          </label>
          <p v-if="e.consent1 || e.consent2" class="consent-error">Both consent boxes are required to proceed.</p>
        </div>
        <AppAlert v-if="submitError" variant="error" class="mt-4">{{ submitError }}</AppAlert>
      </div>

      <!-- Step 4: Success -->
      <div v-if="step === 4" class="success-screen">
        <div class="success-icon"><CheckCircle2 :size="56" /></div>
        <h2>Application Submitted!</h2>
        <p class="success-sub">Your application has been received and will be reviewed by our team shortly. You will be contacted once a decision is made.</p>
        <div class="success-id">
          <label>Your Reference ID</label>
          <strong>{{ submittedId }}</strong>
        </div>
        <div class="success-next">
          <div class="next-item"><Clock :size="18" /> <span>Review takes 3–5 business days</span></div>
          <div class="next-item"><Bell :size="18" /> <span>You'll receive an SMS or email notification</span></div>
          <div class="next-item"><User :size="18" /> <span>Keep your phone accessible for follow-up</span></div>
        </div>
        <router-link to="/login" class="success-btn">Sign In to Your Account</router-link>
      </div>

      <!-- Navigation -->
      <div v-if="step < 4" class="reg-nav">
        <AppButton v-if="step > 0" variant="ghost" size="md" @click="step--">Back</AppButton>
        <div class="reg-nav__spacer" />
        <AppButton v-if="step < 3" variant="primary" size="md" @click="nextStep">
          Continue <ArrowRight :size="16" />
        </AppButton>
        <AppButton v-if="step === 3" variant="primary" size="md" :loading="submitting" @click="submit">
          Submit Application
        </AppButton>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Phone, Mail, X, CheckCircle2, Clock, Bell, User, ArrowRight } from 'lucide-vue-next'
import { useAppStore } from '../stores/app'
import http from '../lib/axios'
import AppInput from '../components/ui/AppInput.vue'
import AppSelect from '../components/ui/AppSelect.vue'
import AppTextarea from '../components/ui/AppTextarea.vue'
import AppButton from '../components/ui/AppButton.vue'
import AppCard from '../components/ui/AppCard.vue'
import AppAlert from '../components/ui/AppAlert.vue'
import AppSteps from '../components/ui/AppSteps.vue'
import GeoSelector from '../components/ui/GeoSelector.vue'

const app = useAppStore()
const step = ref(0), submitting = ref(false), submittedId = ref(''), submitError = ref('')
const e = ref({})
const stepLabels = ['Personal Info', 'Location', 'Skills & Availability', 'Consent & Review']
const genders = ref([])
const proficiencies = ['Beginner', 'Intermediate', 'Advanced', 'Expert']
const langLevels = ['Basic', 'Conversational', 'Fluent', 'Native']
const availStatuses = ['Available', 'Unavailable', 'On Leave', 'On Deployment']
const skillTypes = ref([])
const countries = ref([])

const form = ref({
  first_name: '', middle_name: '', last_name: '', date_of_birth: '',
  gender: '', nationality: '', primary_phone: '', email_address: '',
  emergency_contact_name: '', emergency_contact_relationship: '', emergency_contact_phone: '',
  physical_address: '', home_geo_node: '', availability_status: '',
  skills: [], languages: [],
  consent_to_use_of_bio_data: false, accepted_volunteer_terms: false,
})

onMounted(async () => {
  try {
    const [skRes, cRes] = await Promise.all([
      http.get('/api/resource/Skill Type', { params: { fields: '["name","skill_name"]', filters: '{"is_active":1}', limit: 200 } }),
      http.get('/api/resource/Country', { params: { fields: '["name","name"]', limit: 300 } }),
    ])
    skillTypes.value = skRes.data.data || []
    countries.value  = (cRes.data.data || []).map(c => ({ name: c.name, country_name: c.name }))
  } catch {}

  try {
    const gRes = await http.get('/api/resource/Gender', {
      params: { fields: JSON.stringify(['name']), limit: 50 }
    })
    genders.value = (gRes.data.data || []).map(g => g.name)
  } catch {
    genders.value = ['Male', 'Female', 'Other']
  }
})

function nextStep() {
  e.value = {}
  if (step.value === 0) {
    if (!form.value.first_name)   { e.value.first_name = 'Required'; return }
    if (!form.value.last_name)    { e.value.last_name  = 'Required'; return }
    if (!form.value.date_of_birth){ e.value.dob        = 'Required'; return }
    const ph = form.value.primary_phone || ''
    if (ph.length < 7)            { e.value.phone      = 'Enter a valid phone number'; return }
    if (form.value.email_address && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.value.email_address)) {
      e.value.email = 'Enter a valid email'; return
    }
  }
  step.value++
}

async function submit() {
  e.value = {}; submitError.value = ''
  if (!form.value.consent_to_use_of_bio_data) { e.value.consent1 = true }
  if (!form.value.accepted_volunteer_terms)   { e.value.consent2 = true }
  if (e.value.consent1 || e.value.consent2) return

  submitting.value = true
  try {
    const payload = { ...form.value, consent_to_use_of_bio_data: 1, accepted_volunteer_terms: 1 }
    const params = new URLSearchParams()
    params.append('data', JSON.stringify(payload))
    const res = await http.post(
      '/api/method/onerc_vmms.api.volunteer.register_volunteer',
      params
    )
    submittedId.value = res.data.message.name
    step.value = 4
  } catch (err) {
    submitError.value = err.response?.data?.exception?.split('\n').pop() || 'Submission failed. Please try again.'
  } finally { submitting.value = false }
}
</script>

<style scoped>
.reg-wrap { display: flex; justify-content: center; padding: 32px 16px 64px; flex: 1; }
.reg-card { width: 100%; max-width: 680px; background: var(--c-surface); border-radius: var(--radius-xl); border: 1px solid var(--c-border); box-shadow: var(--shadow-md); }
.reg-header { padding: 28px 32px 0; }
.reg-header__title { font-size: 22px; font-weight: 800; color: var(--c-text); }
.reg-header__sub { font-size: 13px; color: var(--c-text-muted); margin-top: 3px; }
.reg-steps { padding: 24px 32px 0; }
.reg-body { padding: 24px 32px; min-height: 320px; }
.grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.mt { margin-top: 14px; }
.mt-2 { margin-top: 8px; }
.mt-4 { margin-top: 16px; }
.mt-6 { margin-top: 24px; }
.section-divider { display: flex; align-items: center; gap: 12px; margin: 22px 0 0; }
.section-divider::before, .section-divider::after { content: ''; flex: 1; height: 1px; background: var(--c-border); }
.section-divider span { font-size: 12px; font-weight: 600; color: var(--c-text-muted); text-transform: uppercase; letter-spacing: 0.05em; white-space: nowrap; }
.section-label { font-size: 13px; font-weight: 700; color: var(--c-text); text-transform: uppercase; letter-spacing: 0.04em; }

.repeater-row { display: flex; gap: 10px; align-items: flex-end; margin-top: 10px; }
.flex-2 { flex: 2; }
.flex-1 { flex: 1; }
.repeater-remove { width: 36px; height: 36px; border-radius: var(--radius-md); border: 1px solid var(--c-border); background: none; color: var(--c-text-muted); display: flex; align-items: center; justify-content: center; cursor: pointer; flex-shrink: 0; margin-bottom: 0; transition: all var(--t-fast); }
.repeater-remove:hover { border-color: var(--c-error); color: var(--c-error); background: var(--c-error-subtle); }
.repeater-add { margin-top: 10px; background: none; border: 1.5px dashed var(--c-primary); color: var(--c-primary); border-radius: var(--radius-md); padding: 7px 16px; font-size: 13px; font-weight: 600; cursor: pointer; transition: background var(--t-fast); }
.repeater-add:hover { background: var(--c-primary-subtle); }

.review-card .review-card__title { font-weight: 700; font-size: 14px; color: var(--c-text); }
.review-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.review-grid div { display: flex; flex-direction: column; gap: 2px; }
.review-grid label { font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: var(--c-text-muted); }
.review-grid strong { font-size: 14px; color: var(--c-text); }

.consent-block { margin-top: 20px; background: var(--c-secondary-subtle); border-radius: var(--radius-md); padding: 20px; }
.consent-text { font-size: 13px; color: var(--c-text-secondary); line-height: 1.6; margin-bottom: 16px; }
.consent-check { display: flex; align-items: flex-start; gap: 10px; font-size: 14px; cursor: pointer; line-height: 1.5; }
.consent-check input { margin-top: 3px; accent-color: var(--c-primary); width: 16px; height: 16px; flex-shrink: 0; }
.consent-check--error span { color: var(--c-error); }
.consent-error { font-size: 12px; color: var(--c-error); margin-top: 10px; font-weight: 500; }

/* Success */
.success-screen { padding: 48px 32px; text-align: center; }
.success-icon { color: var(--c-success); margin-bottom: 20px; }
.success-screen h2 { font-size: 26px; font-weight: 800; color: var(--c-text); margin-bottom: 10px; }
.success-sub { font-size: 14px; color: var(--c-text-muted); max-width: 440px; margin: 0 auto 24px; line-height: 1.6; }
.success-id { background: var(--c-border-subtle); border: 1px solid var(--c-border); border-radius: var(--radius-md); padding: 14px 20px; display: inline-flex; flex-direction: column; gap: 2px; margin-bottom: 28px; }
.success-id label { font-size: 11px; font-weight: 600; text-transform: uppercase; color: var(--c-text-muted); }
.success-id strong { font-size: 20px; font-weight: 800; color: var(--c-primary); font-family: var(--font-mono); }
.success-next { display: flex; flex-direction: column; gap: 10px; text-align: left; max-width: 320px; margin: 0 auto 28px; }
.next-item { display: flex; align-items: center; gap: 10px; font-size: 13px; color: var(--c-text-secondary); }
.next-item svg { color: var(--c-primary); flex-shrink: 0; }
.success-btn { display: inline-block; background: var(--c-primary); color: #fff; padding: 12px 28px; border-radius: var(--radius-md); font-size: 14px; font-weight: 700; text-decoration: none; transition: background var(--t-base); }
.success-btn:hover { background: var(--c-primary-hover); }

.reg-nav { display: flex; align-items: center; padding: 20px 32px; border-top: 1px solid var(--c-border); background: var(--c-border-subtle); border-radius: 0 0 var(--radius-xl) var(--radius-xl); }
.reg-nav__spacer { flex: 1; }

@media (max-width: 600px) {
  .reg-card { border-radius: var(--radius-lg); }
  .grid-3 { grid-template-columns: 1fr; }
  .grid-2 { grid-template-columns: 1fr; }
  .reg-body, .reg-header { padding: 20px 18px; }
  .reg-steps { padding: 16px 18px 0; }
  .reg-nav { padding: 16px 18px; }
  .review-grid { grid-template-columns: 1fr; }
}
</style>
