<template>
  <div class="register-wrap">
    <div class="register-card">
      <div class="register-header">
        <h2>{{ appStore.labels.volunteer }} Registration</h2>
        <p>{{ appStore.organization.name }}</p>
      </div>

      <div class="steps">
        <div v-for="(step, index) in steps" :key="index" class="step" :class="{ active: currentStep === index, done: currentStep > index }">
          <div class="step-circle">{{ index + 1 }}</div>
          <div class="step-label">{{ step }}</div>
        </div>
      </div>

      <div v-if="currentStep === 0" class="step-content">
        <div class="form-row">
          <div class="form-group">
            <label>First Name *</label>
            <input v-model="form.first_name" type="text" placeholder="First name" />
          </div>
          <div class="form-group">
            <label>Middle Name</label>
            <input v-model="form.middle_name" type="text" placeholder="Middle name" />
          </div>
          <div class="form-group">
            <label>Last Name *</label>
            <input v-model="form.last_name" type="text" placeholder="Last name" />
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>Date of Birth *</label>
            <input v-model="form.date_of_birth" type="date" />
          </div>
          <div class="form-group">
            <label>Gender *</label>
            <select v-model="form.gender">
              <option value="">Select</option>
              <option>Male</option>
              <option>Female</option>
              <option>Other</option>
            </select>
          </div>
          <div class="form-group">
            <label>Nationality</label>
            <input v-model="form.nationality" type="text" />
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>Primary Phone *</label>
            <input v-model="form.primary_phone" type="tel" placeholder="+255..." />
          </div>
          <div class="form-group">
            <label>Email Address</label>
            <input v-model="form.email_address" type="email" />
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>Emergency Contact *</label>
            <input v-model="form.emergency_contact_name" type="text" />
          </div>
          <div class="form-group">
            <label>Relationship *</label>
            <input v-model="form.emergency_contact_relationship" type="text" />
          </div>
          <div class="form-group">
            <label>Emergency Phone *</label>
            <input v-model="form.emergency_contact_phone" type="tel" />
          </div>
        </div>
      </div>

      <div v-if="currentStep === 1" class="step-content">
        <p class="step-desc">Select your location from highest level down.</p>
        <div v-for="(level, index) in appStore.geo.levels" :key="level.level_key" class="form-group">
          <label>{{ level.level_name }}</label>
          <select v-model="geoSelections[index]" @change="onGeoChange(index)">
            <option value="">Select {{ level.level_name }}</option>
            <option v-for="node in geoOptions[index]" :key="node.name" :value="node.name">
              {{ node.node_name }}
            </option>
          </select>
        </div>
        <div class="form-group">
          <label>Physical Address</label>
          <textarea v-model="form.physical_address" rows="3"></textarea>
        </div>
      </div>

      <div v-if="currentStep === 2" class="step-content">
        <div class="section-title">Skills</div>
        <div v-for="(skill, i) in form.skills" :key="i" class="repeater-row">
          <input v-model="skill.skill" placeholder="Skill name" />
          <select v-model="skill.proficiency_level">
            <option value="">Proficiency</option>
            <option>Beginner</option>
            <option>Intermediate</option>
            <option>Advanced</option>
            <option>Expert</option>
          </select>
          <button class="btn-remove" @click="removeItem(form.skills, i)">Remove</button>
        </div>
        <button class="btn-add" @click="addSkill">+ Add Skill</button>

        <div class="section-title" style="margin-top:24px">Languages</div>
        <div v-for="(lang, i) in form.languages" :key="i" class="repeater-row">
          <input v-model="lang.language" placeholder="Language" />
          <select v-model="lang.spoken_proficiency">
            <option value="">Spoken level</option>
            <option>Basic</option>
            <option>Conversational</option>
            <option>Fluent</option>
            <option>Native</option>
          </select>
          <button class="btn-remove" @click="removeItem(form.languages, i)">Remove</button>
        </div>
        <button class="btn-add" @click="addLanguage">+ Add Language</button>
      </div>

      <div v-if="currentStep === 3" class="step-content">
        <div class="form-group">
          <label>Availability Status</label>
          <select v-model="form.availability_status">
            <option value="">Select</option>
            <option>Available</option>
            <option>Unavailable</option>
            <option>On Leave</option>
          </select>
        </div>
        <div class="section-title">Availability Windows</div>
        <div v-for="(avail, i) in form.availability" :key="i" class="repeater-row">
          <select v-model="avail.availability_type">
            <option value="">Type</option>
            <option>Full Time</option>
            <option>Part Time</option>
            <option>Weekends Only</option>
            <option>On Call</option>
          </select>
          <input v-model="avail.from_date" type="date" />
          <input v-model="avail.to_date" type="date" />
          <button class="btn-remove" @click="removeItem(form.availability, i)">Remove</button>
        </div>
        <button class="btn-add" @click="addAvailability">+ Add Window</button>
      </div>

      <div v-if="currentStep === 4" class="success-screen">
        <div class="success-icon">✓</div>
        <h3>Application Submitted!</h3>
        <p>Your application has been received and will be reviewed shortly.</p>
        <p><strong>Reference: {{ submittedId }}</strong></p>
        <router-link to="/" class="btn-home">Back to Home</router-link>
      </div>

      <div v-if="error" class="error-box">{{ error }}</div>

      <div v-if="currentStep < 4" class="step-nav">
        <button v-if="currentStep > 0" class="btn-back" @click="currentStep--">Back</button>
        <button v-if="currentStep < 3" class="btn-next" @click="nextStep">Next</button>
        <button v-if="currentStep === 3" class="btn-submit" @click="submit" :disabled="loading">
          {{ loading ? 'Submitting...' : 'Submit Application' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAppStore } from '../stores/app'
import axios from 'axios'
import { frappeCall } from '../utils/frappe.js'

const appStore = useAppStore()
const steps = ['Personal Info', 'Location', 'Skills & Languages', 'Availability']
const currentStep = ref(0)
const loading = ref(false)
const error = ref('')
const submittedId = ref('')
const geoSelections = ref([])
const geoOptions = ref([])

const form = ref({
  first_name: '', middle_name: '', last_name: '',
  date_of_birth: '', gender: '', nationality: '',
  primary_phone: '', email_address: '',
  emergency_contact_name: '', emergency_contact_relationship: '', emergency_contact_phone: '',
  physical_address: '', home_geo_node: '', availability_status: '',
  skills: [], languages: [], availability: []
})

onMounted(async () => {
  const levels = appStore.geo.levels || []
  geoSelections.value = levels.map(() => '')
  geoOptions.value = levels.map(() => [])
  if (levels.length > 0) await loadGeoOptions(0, null)
})

async function loadGeoOptions(levelIndex, parentNode) {
  try {
    const params = { geo_level: appStore.geo.levels[levelIndex].name }
    if (parentNode) params.parent_geo_node = parentNode
    const res = await axios.get('/api/method/onerc_vmms.api.geo.get_geo_nodes', { params })
    geoOptions.value[levelIndex] = res.data.message
  } catch(e) { console.error(e) }
}

async function onGeoChange(levelIndex) {
  const selected = geoSelections.value[levelIndex]
  for (let i = levelIndex + 1; i < appStore.geo.levels.length; i++) {
    geoSelections.value[i] = ''
    geoOptions.value[i] = []
  }
  if (selected && levelIndex + 1 < appStore.geo.levels.length) {
    await loadGeoOptions(levelIndex + 1, selected)
  }
  const lastSelected = [...geoSelections.value].reverse().find(v => v)
  form.value.home_geo_node = lastSelected || ''
}

function nextStep() {
  error.value = ''
  if (currentStep.value === 0) {
    if (!form.value.first_name || !form.value.last_name || !form.value.date_of_birth || !form.value.gender || !form.value.primary_phone) {
      error.value = 'Please fill in all required fields.'
      return
    }
  }
  currentStep.value++
}

function addSkill() { form.value.skills.push({ skill: '', proficiency_level: '' }) }
function addLanguage() { form.value.languages.push({ language: '', spoken_proficiency: '' }) }
function addAvailability() { form.value.availability.push({ availability_type: '', from_date: '', to_date: '' }) }
function removeItem(arr, i) { arr.splice(i, 1) }

async function submit() {
  error.value = ''
  loading.value = true
  try {
    const result = await frappeCall(
      'onerc_vmms.api.volunteer.register_volunteer',
      { data: form.value }
    )
    submittedId.value = result.name
    currentStep.value = 4
  } catch(e) {
    error.value = 'Submission failed. Please try again.'
    console.error(e)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.register-wrap { display: flex; justify-content: center; padding: 20px 0; }
.register-card { background: white; border-radius: var(--radius); padding: 40px; width: 100%; max-width: 760px; box-shadow: var(--shadow); }
.register-header { margin-bottom: 30px; }
.register-header h2 { font-size: 24px; font-weight: 700; color: var(--secondary); }
.register-header p { font-size: 14px; color: var(--text-muted); }
.steps { display: flex; margin-bottom: 36px; }
.step { flex: 1; display: flex; flex-direction: column; align-items: center; gap: 6px; position: relative; }
.step:not(:last-child)::after { content: ''; position: absolute; top: 16px; left: 60%; width: 80%; height: 2px; background: var(--border); }
.step.done:not(:last-child)::after { background: var(--primary); }
.step-circle { width: 32px; height: 32px; border-radius: 50%; border: 2px solid var(--border); display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: 700; color: var(--text-muted); background: white; z-index: 1; }
.step.active .step-circle { border-color: var(--primary); color: var(--primary); }
.step.done .step-circle { background: var(--primary); border-color: var(--primary); color: white; }
.step-label { font-size: 11px; color: var(--text-muted); text-align: center; }
.step.active .step-label { color: var(--primary); font-weight: 600; }
.step-content { min-height: 300px; }
.step-desc { font-size: 14px; color: var(--text-muted); margin-bottom: 20px; }
.form-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 16px; }
.form-group { margin-bottom: 16px; }
.form-group label { display: block; font-size: 13px; font-weight: 600; color: var(--secondary); margin-bottom: 6px; }
.form-group input, .form-group select, .form-group textarea { width: 100%; padding: 10px 14px; border: 1px solid var(--border); border-radius: var(--radius); font-size: 14px; outline: none; }
.form-group input:focus, .form-group select:focus { border-color: var(--primary); }
.section-title { font-size: 15px; font-weight: 700; color: var(--secondary); margin-bottom: 12px; padding-bottom: 6px; border-bottom: 2px solid var(--primary); }
.repeater-row { display: flex; gap: 10px; margin-bottom: 10px; align-items: center; }
.repeater-row input, .repeater-row select { flex: 1; padding: 8px 12px; border: 1px solid var(--border); border-radius: var(--radius); font-size: 14px; outline: none; }
.btn-add { background: none; border: 1px dashed var(--primary); color: var(--primary); padding: 8px 16px; border-radius: var(--radius); font-size: 13px; font-weight: 600; }
.btn-remove { background: none; border: 1px solid var(--border); color: var(--text-muted); padding: 6px 12px; border-radius: var(--radius); font-size: 12px; }
.step-nav { display: flex; justify-content: flex-end; gap: 12px; margin-top: 32px; padding-top: 20px; border-top: 1px solid var(--border); }
.btn-back { background: none; border: 1px solid var(--border); color: var(--text-muted); padding: 10px 24px; border-radius: var(--radius); font-size: 14px; }
.btn-next, .btn-submit { background: var(--primary); color: white; border: none; padding: 10px 28px; border-radius: var(--radius); font-size: 14px; font-weight: 600; }
.btn-next:hover, .btn-submit:hover { opacity: 0.9; }
.btn-submit:disabled { opacity: 0.6; }
.success-screen { text-align: center; padding: 60px 20px; }
.success-icon { width: 64px; height: 64px; background: #E8F5EE; color: #0F6E56; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 28px; font-weight: 700; margin: 0 auto 20px; }
.success-screen h3 { font-size: 24px; color: var(--secondary); margin-bottom: 10px; }
.success-screen p { font-size: 15px; color: var(--text-muted); margin-bottom: 8px; }
.btn-home { display: inline-block; margin-top: 20px; background: var(--primary); color: white; padding: 10px 28px; border-radius: var(--radius); font-weight: 600; }
.error-box { background: #FCEAEA; color: #EE2435; padding: 10px 14px; border-radius: var(--radius); font-size: 13px; margin-top: 16px; }
</style>
