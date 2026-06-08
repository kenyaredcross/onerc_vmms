<template>
  <div>
    <div v-if="loading" class="loading-center"><AppSpinner size="lg" /></div>

    <template v-else>
      <!-- Profile Header -->
      <div class="prof-header">
        <div class="prof-header__avatar-wrap">
          <AppAvatar :name="fullName" :photo="profile.photo" size="2xl" />
          <button class="photo-btn" @click="showPhotoModal = true" title="Change photo">
            <Camera :size="14" />
          </button>
        </div>
        <div class="prof-header__info">
          <h1 class="prof-name">{{ fullName || 'My Profile' }}</h1>
          <p v-if="profile.vol_id" class="prof-id mono">{{ profile.vol_id }}</p>
          <AppBadge v-if="profile.availability_status" :variant="availVariant(profile.availability_status)" size="sm" class="prof-badge">
            {{ profile.availability_status }}
          </AppBadge>
        </div>
      </div>

      <!-- Tabs -->
      <div class="tab-bar">
        <button v-for="t in tabs" :key="t" class="tab-bar__btn" :class="{ active: activeTab === t }" @click="activeTab = t">{{ t }}</button>
      </div>

      <!-- Personal -->
      <div v-if="activeTab === 'Personal'" class="tab-body">
        <div class="form-section">
          <p class="section-label">Basic Information</p>
          <div class="grid-3">
            <AppInput v-model="personal.first_name"  label="First Name"  placeholder="John"  required />
            <AppInput v-model="personal.middle_name" label="Middle Name" placeholder="M." />
            <AppInput v-model="personal.last_name"   label="Last Name"   placeholder="Doe"   required />
          </div>
          <div class="grid-3 mt">
            <AppInput  v-model="personal.date_of_birth" label="Date of Birth" type="date" />
            <AppSelect v-model="personal.gender"        label="Gender"         :options="genders"   placeholder="Select…" />
            <AppSelect v-model="personal.nationality"   label="Nationality"    :options="countries" placeholder="Select…" value-key="name" label-key="country_name" />
          </div>
          <div class="grid-2 mt">
            <AppInput v-model="personal.primary_phone" label="Primary Phone" type="tel" placeholder="+254700000000" :prefix-icon="Phone" />
            <AppInput v-model="personal.email_address" label="Email Address" type="email" placeholder="you@example.com" :prefix-icon="Mail" />
          </div>
        </div>

        <div class="form-section mt-6">
          <p class="section-label">Emergency Contact</p>
          <div class="grid-3">
            <AppInput v-model="personal.emergency_contact_name"         label="Contact Name" placeholder="Jane Doe" />
            <AppInput v-model="personal.emergency_contact_relationship" label="Relationship" placeholder="Spouse" />
            <AppInput v-model="personal.emergency_contact_phone"        label="Phone"        type="tel" placeholder="+254…" />
          </div>
        </div>

        <div class="tab-footer">
          <AppButton variant="primary" :loading="saving === 'personal'" @click="save('personal')">Save Personal Info</AppButton>
        </div>
      </div>

      <!-- Location -->
      <div v-if="activeTab === 'Location'" class="tab-body">
        <GeoSelector :levels="app.geoLevels" v-model="location.home_geo_node" />
        <div class="mt">
          <AppTextarea v-model="location.physical_address" label="Physical Address" placeholder="Street, building, landmark…" :rows="3" />
        </div>
        <div class="tab-footer">
          <AppButton variant="primary" :loading="saving === 'location'" @click="save('location')">Save Location</AppButton>
        </div>
      </div>

      <!-- Professional -->
      <div v-if="activeTab === 'Professional'" class="tab-body">
        <!-- Education -->
        <div class="form-section">
          <div class="section-row">
            <p class="section-label">Education</p>
            <button class="repeater-add" @click="professional.education.push({ institution: '', qualification: '', field: '', year: '' })">+ Add</button>
          </div>
          <template v-if="professional.education.length">
            <div class="repeater-head grid-4col">
              <span>Institution</span><span>Qualification</span><span>Field</span><span>Year</span><span></span>
            </div>
            <div v-for="(row, i) in professional.education" :key="i" class="repeater-row grid-4col">
              <AppInput v-model="row.institution"   placeholder="University / School" />
              <AppInput v-model="row.qualification" placeholder="Degree / Certificate" />
              <AppInput v-model="row.field"         placeholder="Field of Study" />
              <AppInput v-model="row.year"          placeholder="Year" type="number" />
              <button class="repeater-remove" @click="professional.education.splice(i,1)"><X :size="15" /></button>
            </div>
          </template>
          <p v-else class="empty-hint">No education records yet.</p>
        </div>

        <!-- Work Experience -->
        <div class="form-section mt-6">
          <div class="section-row">
            <p class="section-label">Work Experience</p>
            <button class="repeater-add" @click="professional.experience.push({ employer: '', role: '', from_date: '', to_date: '' })">+ Add</button>
          </div>
          <template v-if="professional.experience.length">
            <div class="repeater-head grid-4col">
              <span>Employer</span><span>Role</span><span>From</span><span>To</span><span></span>
            </div>
            <div v-for="(row, i) in professional.experience" :key="i" class="repeater-row grid-4col">
              <AppInput v-model="row.employer"  placeholder="Employer name" />
              <AppInput v-model="row.role"      placeholder="Job title" />
              <AppInput v-model="row.from_date" type="date" />
              <AppInput v-model="row.to_date"   type="date" />
              <button class="repeater-remove" @click="professional.experience.splice(i,1)"><X :size="15" /></button>
            </div>
          </template>
          <p v-else class="empty-hint">No work experience records yet.</p>
        </div>

        <!-- Training -->
        <div class="form-section mt-6">
          <div class="section-row">
            <p class="section-label">Training &amp; Certifications</p>
            <button class="repeater-add" @click="professional.training.push({ training_name: '', provider: '', date: '', certificate: '' })">+ Add</button>
          </div>
          <template v-if="professional.training.length">
            <div class="repeater-head grid-4col">
              <span>Training</span><span>Provider</span><span>Date</span><span>Certificate No.</span><span></span>
            </div>
            <div v-for="(row, i) in professional.training" :key="i" class="repeater-row grid-4col">
              <AppInput v-model="row.training_name" placeholder="Training name" />
              <AppInput v-model="row.provider"      placeholder="Provider" />
              <AppInput v-model="row.date"          type="date" />
              <AppInput v-model="row.certificate"   placeholder="Certificate #" />
              <button class="repeater-remove" @click="professional.training.splice(i,1)"><X :size="15" /></button>
            </div>
          </template>
          <p v-else class="empty-hint">No training records yet.</p>
        </div>

        <div class="tab-footer">
          <AppButton variant="primary" :loading="saving === 'professional'" @click="save('professional')">Save Professional Info</AppButton>
        </div>
      </div>

      <!-- Skills -->
      <div v-if="activeTab === 'Skills'" class="tab-body">
        <div class="section-row">
          <p class="section-label">Skills</p>
          <button class="repeater-add" @click="skills.push({ skill: '', proficiency_level: '' })">+ Add</button>
        </div>
        <template v-if="skills.length">
          <div class="repeater-head grid-2col">
            <span>Skill</span><span>Proficiency</span><span></span>
          </div>
          <div v-for="(row, i) in skills" :key="i" class="repeater-row grid-2col">
            <AppSelect v-model="row.skill"              :options="skillTypes"   placeholder="Select skill…" value-key="name" label-key="skill_name" />
            <AppSelect v-model="row.proficiency_level"  :options="proficiencies" placeholder="Level…" />
            <button class="repeater-remove" @click="skills.splice(i,1)"><X :size="15" /></button>
          </div>
        </template>
        <p v-else class="empty-hint">No skills added yet.</p>
        <div class="tab-footer">
          <AppButton variant="primary" :loading="saving === 'skills'" @click="save('skills')">Save Skills</AppButton>
        </div>
      </div>

      <!-- Languages -->
      <div v-if="activeTab === 'Languages'" class="tab-body">
        <div class="section-row">
          <p class="section-label">Languages</p>
          <button class="repeater-add" @click="languages.push({ language: '', spoken_proficiency: '', written_proficiency: '' })">+ Add</button>
        </div>
        <template v-if="languages.length">
          <div class="repeater-head grid-3col">
            <span>Language</span><span>Spoken</span><span>Written</span><span></span>
          </div>
          <div v-for="(row, i) in languages" :key="i" class="repeater-row grid-3col">
            <AppInput  v-model="row.language"            placeholder="Language…" />
            <AppSelect v-model="row.spoken_proficiency"  :options="langLevels" placeholder="Spoken level…" />
            <AppSelect v-model="row.written_proficiency" :options="langLevels" placeholder="Written level…" />
            <button class="repeater-remove" @click="languages.splice(i,1)"><X :size="15" /></button>
          </div>
        </template>
        <p v-else class="empty-hint">No languages added yet.</p>
        <div class="tab-footer">
          <AppButton variant="primary" :loading="saving === 'languages'" @click="save('languages')">Save Languages</AppButton>
        </div>
      </div>

      <!-- Availability -->
      <div v-if="activeTab === 'Availability'" class="tab-body">
        <AppSelect v-model="availability.availability_status" label="Current Availability Status" :options="availStatuses" placeholder="Select status…" />
        <div class="mt-6">
          <div class="section-row">
            <p class="section-label">Availability Windows</p>
            <button class="repeater-add" @click="availability.windows.push({ day: '', from_time: '', to_time: '' })">+ Add</button>
          </div>
          <template v-if="availability.windows.length">
            <div class="repeater-head grid-3col">
              <span>Day</span><span>From</span><span>To</span><span></span>
            </div>
            <div v-for="(row, i) in availability.windows" :key="i" class="repeater-row grid-3col">
              <AppSelect v-model="row.day"       :options="weekdays" placeholder="Day…" />
              <AppInput  v-model="row.from_time" type="time" />
              <AppInput  v-model="row.to_time"   type="time" />
              <button class="repeater-remove" @click="availability.windows.splice(i,1)"><X :size="15" /></button>
            </div>
          </template>
          <p v-else class="empty-hint">No availability windows set.</p>
        </div>
        <div class="tab-footer">
          <AppButton variant="primary" :loading="saving === 'availability'" @click="save('availability')">Save Availability</AppButton>
        </div>
      </div>
    </template>

    <!-- Photo Modal (stub) -->
    <AppModal v-model="showPhotoModal" title="Update Profile Photo" size="sm">
      <p class="modal-hint">Photo upload will be available in a future update.</p>
      <template #footer>
        <AppButton variant="primary" size="sm" @click="showPhotoModal = false">Close</AppButton>
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
import { Phone, Mail, Camera, X } from 'lucide-vue-next'
import { useAppStore } from '../stores/app'
import http from '../lib/axios'
import AppSpinner  from '../components/ui/AppSpinner.vue'
import AppAlert    from '../components/ui/AppAlert.vue'
import AppBadge    from '../components/ui/AppBadge.vue'
import AppButton   from '../components/ui/AppButton.vue'
import AppAvatar   from '../components/ui/AppAvatar.vue'
import AppInput    from '../components/ui/AppInput.vue'
import AppSelect   from '../components/ui/AppSelect.vue'
import AppTextarea from '../components/ui/AppTextarea.vue'
import AppModal    from '../components/ui/AppModal.vue'
import GeoSelector from '../components/ui/GeoSelector.vue'

const app = useAppStore()

const loading        = ref(true)
const saving         = ref('')
const profile        = ref({})
const showPhotoModal = ref(false)
const toast          = ref(null)

const tabs     = ['Personal', 'Location', 'Professional', 'Skills', 'Languages', 'Availability']
const activeTab = ref('Personal')

const personal     = ref({ first_name: '', middle_name: '', last_name: '', date_of_birth: '', gender: '', nationality: '', primary_phone: '', email_address: '', emergency_contact_name: '', emergency_contact_relationship: '', emergency_contact_phone: '' })
const location     = ref({ home_geo_node: '', physical_address: '' })
const professional = ref({ education: [], experience: [], training: [] })
const skills       = ref([])
const languages    = ref([])
const availability = ref({ availability_status: '', windows: [] })

const genders       = ['Male', 'Female', 'Other', 'Prefer not to say']
const countries     = ref([])
const skillTypes    = ref([])
const proficiencies = ['Beginner', 'Intermediate', 'Advanced', 'Expert']
const langLevels    = ['Basic', 'Conversational', 'Fluent', 'Native']
const availStatuses = ['Available', 'Partially Available', 'Unavailable', 'On Leave']
const weekdays      = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

const fullName = computed(() =>
  [personal.value.first_name, personal.value.middle_name, personal.value.last_name].filter(Boolean).join(' ')
)

function availVariant(s) {
  return { Available: 'success', 'Partially Available': 'warning', Unavailable: 'error', 'On Leave': 'neutral' }[s] || 'neutral'
}

function showToast(type, message) {
  toast.value = null
  nextTick(() => { toast.value = { type, message }; setTimeout(() => toast.value = null, 4000) })
}

function populateForms(p) {
  Object.assign(personal.value, {
    first_name: p.first_name || '', middle_name: p.middle_name || '', last_name: p.last_name || '',
    date_of_birth: p.date_of_birth || '', gender: p.gender || '', nationality: p.nationality || '',
    primary_phone: p.primary_phone || '', email_address: p.email_address || '',
    emergency_contact_name: p.emergency_contact_name || '',
    emergency_contact_relationship: p.emergency_contact_relationship || '',
    emergency_contact_phone: p.emergency_contact_phone || '',
  })
  location.value = { home_geo_node: p.home_geo_node || '', physical_address: p.physical_address || '' }
  professional.value = {
    education:  (p.education  || []).map(r => ({ ...r })),
    experience: (p.experience || []).map(r => ({ ...r })),
    training:   (p.training   || []).map(r => ({ ...r })),
  }
  skills.value    = (p.skills    || []).map(r => ({ ...r }))
  languages.value = (p.languages || []).map(r => ({ ...r }))
  availability.value = {
    availability_status: p.availability_status || '',
    windows: (p.availability_windows || []).map(r => ({ ...r })),
  }
}

async function save(section) {
  saving.value = section
  try {
    let data = {}
    if (section === 'personal')      data = { ...personal.value }
    else if (section === 'location') data = { ...location.value }
    else if (section === 'professional') data = { ...professional.value }
    else if (section === 'skills')   data = { skills: skills.value }
    else if (section === 'languages') data = { languages: languages.value }
    else if (section === 'availability') data = { availability_status: availability.value.availability_status, availability_windows: availability.value.windows }

    await http.post('/api/method/onerc_vmms.api.volunteer.update_volunteer_profile', { section, data: JSON.stringify(data) })
    showToast('success', 'Saved successfully.')
  } catch (err) {
    showToast('error', err.response?.data?.exception?.split('\n').pop() || 'Failed to save.')
  } finally { saving.value = '' }
}

onMounted(async () => {
  const [profileRes, countriesRes, skillsRes] = await Promise.allSettled([
    http.get('/api/method/onerc_vmms.api.volunteer.get_my_profile'),
    http.get('/api/method/frappe.client.get_list', { params: { doctype: 'Country', fields: JSON.stringify(['name', 'country_name']), limit_page_length: 300 } }),
    http.get('/api/method/onerc_vmms.api.bootstrap.get_skill_types'),
  ])
  if (profileRes.status === 'fulfilled') {
    profile.value = profileRes.value.data.message || {}
    populateForms(profile.value)
  }
  if (countriesRes.status === 'fulfilled') countries.value = countriesRes.value.data.message || []
  if (skillsRes.status  === 'fulfilled')   skillTypes.value = skillsRes.value.data.message || []
  loading.value = false
})
</script>

<style scoped>
.loading-center { display: flex; justify-content: center; padding: 64px; }

/* Profile header */
.prof-header {
  display: flex; align-items: flex-end; gap: 20px;
  background: var(--c-surface); border: 1px solid var(--c-border);
  border-radius: var(--radius-xl); padding: 24px; margin-bottom: 20px;
  box-shadow: var(--shadow-sm);
}
.prof-header__avatar-wrap { position: relative; flex-shrink: 0; }
.photo-btn {
  position: absolute; bottom: 0; right: 0;
  width: 28px; height: 28px; border-radius: 50%;
  background: var(--c-primary); color: #fff;
  border: 2px solid var(--c-surface); cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: background var(--t-fast);
}
.photo-btn:hover { background: color-mix(in srgb, var(--c-primary) 80%, #000); }
.prof-header__info { flex: 1; min-width: 0; }
.prof-name  { font-size: 22px; font-weight: 800; color: var(--c-text); line-height: 1.2; }
.prof-id    { font-size: 13px; color: var(--c-text-muted); margin-top: 4px; }
.prof-badge { margin-top: 8px; display: inline-flex; }
.mono       { font-family: var(--font-mono, monospace); }

/* Tabs */
.tab-bar { display: flex; gap: 2px; background: var(--c-surface); border: 1px solid var(--c-border); border-radius: var(--radius-md); padding: 4px; margin-bottom: 16px; overflow-x: auto; }
.tab-bar__btn { padding: 7px 16px; border-radius: var(--radius-sm); font-size: 13px; font-weight: 500; color: var(--c-text-muted); cursor: pointer; white-space: nowrap; background: none; border: none; }
.tab-bar__btn.active { background: var(--c-primary-subtle); color: var(--c-primary); font-weight: 700; }
.tab-bar__btn:hover:not(.active) { background: var(--c-border-subtle); color: var(--c-text); }

/* Tab body */
.tab-body { background: var(--c-surface); border: 1px solid var(--c-border); border-radius: var(--radius-lg); padding: 24px; }
.tab-footer { display: flex; justify-content: flex-end; margin-top: 24px; padding-top: 18px; border-top: 1px solid var(--c-border); }

/* Sections */
.section-label { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: var(--c-text-muted); margin-bottom: 12px; }
.section-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.section-row .section-label { margin-bottom: 0; }
.mt    { margin-top: 14px; }
.mt-6  { margin-top: 24px; }

/* Grids */
.grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 14px; }
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }

/* Repeater */
.repeater-head, .repeater-row {
  display: grid; gap: 10px; align-items: start;
}
.repeater-head {
  font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;
  color: var(--c-text-muted); padding-bottom: 6px;
  border-bottom: 1px solid var(--c-border); margin-bottom: 4px;
}
.grid-4col { grid-template-columns: repeat(4, 1fr) 28px; }
.grid-3col { grid-template-columns: repeat(3, 1fr) 28px; }
.grid-2col { grid-template-columns: repeat(2, 1fr) 28px; }

.repeater-remove {
  width: 28px; height: 28px; display: flex; align-items: center; justify-content: center;
  border: none; background: none; cursor: pointer; color: var(--c-text-muted);
  border-radius: var(--radius-sm); transition: color var(--t-fast), background var(--t-fast);
  flex-shrink: 0; margin-top: 28px;
}
.repeater-remove:hover { color: var(--c-error); background: var(--c-error-subtle); }

.repeater-add {
  background: none; border: 1.5px dashed var(--c-border);
  color: var(--c-text-muted); font-size: 13px; font-weight: 600;
  padding: 6px 14px; border-radius: var(--radius-md); cursor: pointer;
  transition: border-color var(--t-fast), color var(--t-fast);
}
.repeater-add:hover { border-color: var(--c-primary); color: var(--c-primary); }

.empty-hint { font-size: 13px; color: var(--c-text-muted); padding: 12px 0; }

/* Modal */
.modal-hint { font-size: 14px; color: var(--c-text-muted); }

/* Toast */
.toast-wrap { position: fixed; bottom: 24px; right: 24px; z-index: 600; width: 340px; max-width: calc(100vw - 48px); }

@media (max-width: 700px) {
  .prof-header { flex-direction: column; align-items: flex-start; }
  .grid-3 { grid-template-columns: 1fr; }
  .grid-2 { grid-template-columns: 1fr; }
  .tab-body { padding: 16px; }
  .grid-4col, .grid-3col, .grid-2col { grid-template-columns: 1fr 28px; }
}
</style>
