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
          <p v-if="profile.name" class="prof-id mono">{{ profile.name }}</p>
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
            <AppInput v-model="form.first_name"  label="First Name"  placeholder="John"  required />
            <AppInput v-model="form.middle_name" label="Middle Name" placeholder="M." />
            <AppInput v-model="form.last_name"   label="Last Name"   placeholder="Doe"   required />
          </div>
          <div class="grid-3 mt">
            <AppInput  v-model="form.date_of_birth" label="Date of Birth" type="date" />
            <AppSelect v-model="form.gender"        label="Gender"         :options="genders"   placeholder="Select…" />
            <AppSelect v-model="form.nationality"   label="Nationality"    :options="countries" placeholder="Select…" value-key="name" label-key="country_name" />
          </div>
          <div class="grid-2 mt">
            <AppInput v-model="form.primary_phone" label="Primary Phone" type="tel" placeholder="+254700000000" :prefix-icon="Phone" />
            <AppInput v-model="form.email_address" label="Email Address" type="email" placeholder="you@example.com" :prefix-icon="Mail" />
          </div>
        </div>

        <div class="form-section mt-6">
          <p class="section-label">Emergency Contact</p>
          <div class="grid-3">
            <AppInput v-model="form.emergency_contact_name"         label="Contact Name" placeholder="Jane Doe" />
            <AppInput v-model="form.emergency_contact_relationship" label="Relationship" placeholder="Spouse" />
            <AppInput v-model="form.emergency_contact_phone"        label="Phone"        type="tel" placeholder="+254…" />
          </div>
        </div>

        <div class="tab-footer">
          <AppButton variant="primary" :loading="saving === 'personal'" @click="save('personal')">Save Personal Info</AppButton>
        </div>
      </div>

      <!-- Location -->
      <div v-if="activeTab === 'Location'" class="tab-body">
        <GeoSelector :levels="app.geoLevels" v-model="form.home_geo_node" />
        <div class="mt">
          <AppTextarea v-model="form.physical_address" label="Physical Address" placeholder="Street, building, landmark…" :rows="3" />
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
            <button class="repeater-add" @click="form.education.push({ institution: '', qualification: '', field_of_study: '', from_year: '', to_year: '' })">+ Add</button>
          </div>
          <template v-if="form.education.length">
            <div class="repeater-head grid-5col">
              <span>Institution</span><span>Qualification</span><span>Field of Study</span><span>From</span><span>To</span><span></span>
            </div>
            <div v-for="(row, i) in form.education" :key="i" class="repeater-row grid-5col">
              <AppInput v-model="row.institution"   placeholder="University / School" />
              <AppInput v-model="row.qualification" placeholder="Degree / Certificate" />
              <AppInput v-model="row.field_of_study" placeholder="Field of Study" />
              <AppInput v-model="row.from_year"     placeholder="Year" type="number" />
              <AppInput v-model="row.to_year"       placeholder="Year" type="number" />
              <button class="repeater-remove" @click="form.education.splice(i,1)"><X :size="15" /></button>
            </div>
          </template>
          <p v-else class="empty-hint">No education records yet.</p>
        </div>

        <!-- Work Experience -->
        <div class="form-section mt-6">
          <div class="section-row">
            <p class="section-label">Work Experience</p>
            <button class="repeater-add" @click="form.experience.push({ employer: '', role_position: '', from_date: '', to_date: '' })">+ Add</button>
          </div>
          <template v-if="form.experience.length">
            <div class="repeater-head grid-4col">
              <span>Employer</span><span>Role / Position</span><span>From</span><span>To</span><span></span>
            </div>
            <div v-for="(row, i) in form.experience" :key="i" class="repeater-row grid-4col">
              <AppInput v-model="row.employer"       placeholder="Employer name" />
              <AppInput v-model="row.role_position"  placeholder="Job title" />
              <AppInput v-model="row.from_date"      type="date" />
              <AppInput v-model="row.to_date"        type="date" />
              <button class="repeater-remove" @click="form.experience.splice(i,1)"><X :size="15" /></button>
            </div>
          </template>
          <p v-else class="empty-hint">No work experience records yet.</p>
        </div>

        <!-- Training -->
        <div class="form-section mt-6">
          <div class="section-row">
            <p class="section-label">Training &amp; Certifications</p>
            <button class="repeater-add" @click="form.trainings.push({ course_name: '', provider: '', from_date: '', expiry_date: '' })">+ Add</button>
          </div>
          <template v-if="form.trainings.length">
            <div class="repeater-head grid-4col">
              <span>Course</span><span>Provider</span><span>Date</span><span>Expiry</span><span></span>
            </div>
            <div v-for="(row, i) in form.trainings" :key="i" class="repeater-row grid-4col">
              <AppInput v-model="row.course_name"  placeholder="Course name" />
              <AppInput v-model="row.provider"     placeholder="Provider" />
              <AppInput v-model="row.from_date"    type="date" />
              <AppInput v-model="row.expiry_date"  type="date" />
              <button class="repeater-remove" @click="form.trainings.splice(i,1)"><X :size="15" /></button>
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
          <button class="repeater-add" @click="form.skills.push({ skill: '', proficiency_level: '' })">+ Add</button>
        </div>
        <template v-if="form.skills.length">
          <div class="repeater-head grid-2col">
            <span>Skill</span><span>Proficiency</span><span></span>
          </div>
          <div v-for="(row, i) in form.skills" :key="i" class="repeater-row grid-2col">
            <AppSelect v-model="row.skill"             :options="skillTypes"   placeholder="Select skill…" value-key="name" label-key="skill_name" />
            <AppSelect v-model="row.proficiency_level" :options="proficiencies" placeholder="Level…" />
            <button class="repeater-remove" @click="form.skills.splice(i,1)"><X :size="15" /></button>
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
          <button class="repeater-add" @click="form.languages.push({ language: '', spoken_proficiency: '', written_proficiency: '' })">+ Add</button>
        </div>
        <template v-if="form.languages.length">
          <div class="repeater-head grid-3col">
            <span>Language</span><span>Spoken</span><span>Written</span><span></span>
          </div>
          <div v-for="(row, i) in form.languages" :key="i" class="repeater-row grid-3col">
            <AppInput  v-model="row.language"            placeholder="Language…" />
            <AppSelect v-model="row.spoken_proficiency"  :options="langLevels" placeholder="Spoken level…" />
            <AppSelect v-model="row.written_proficiency" :options="langLevels" placeholder="Written level…" />
            <button class="repeater-remove" @click="form.languages.splice(i,1)"><X :size="15" /></button>
          </div>
        </template>
        <p v-else class="empty-hint">No languages added yet.</p>
        <div class="tab-footer">
          <AppButton variant="primary" :loading="saving === 'languages'" @click="save('languages')">Save Languages</AppButton>
        </div>
      </div>

      <!-- Availability -->
      <div v-if="activeTab === 'Availability'" class="tab-body">
        <AppSelect v-model="form.availability_status" label="Current Availability Status" :options="availStatuses" placeholder="Select status…" />

        <div class="mt-6">
          <div class="section-row">
            <p class="section-label">Availability Windows</p>
            <button class="repeater-add" @click="form.availability.push({ availability_type: '', from_date: '', monday: 0, tuesday: 0, wednesday: 0, thursday: 0, friday: 0, saturday: 0, sunday: 0 })">+ Add</button>
          </div>
          <template v-if="form.availability.length">
            <div v-for="(row, i) in form.availability" :key="i" class="avail-row">
              <div class="avail-row__head">
                <AppSelect v-model="row.availability_type" :options="availTypes" placeholder="Type…" class="avail-type" />
                <AppInput  v-model="row.from_date" type="date" label="From Date" />
                <button class="repeater-remove avail-remove" @click="form.availability.splice(i,1)"><X :size="15" /></button>
              </div>
              <div class="avail-days">
                <label v-for="day in weekdays" :key="day" class="day-check">
                  <input type="checkbox" :checked="!!row[day]" @change="row[day] = $event.target.checked ? 1 : 0" />
                  <span>{{ day.slice(0,3) }}</span>
                </label>
              </div>
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

const tabs      = ['Personal', 'Location', 'Professional', 'Skills', 'Languages', 'Availability']
const activeTab = ref('Personal')

const form = ref({
  first_name: '', middle_name: '', last_name: '',
  date_of_birth: '', gender: '', nationality: '',
  primary_phone: '', email_address: '',
  emergency_contact_name: '', emergency_contact_relationship: '', emergency_contact_phone: '',
  home_geo_node: '', physical_address: '',
  education:  [],
  experience: [],
  trainings:  [],
  skills:     [],
  languages:  [],
  availability_status: '',
  availability: [],
})

const genders       = ['Male', 'Female', 'Other', 'Prefer not to say']
const countries     = ref([])
const skillTypes    = ref([])
const proficiencies = ['Beginner', 'Intermediate', 'Advanced', 'Expert']
const langLevels    = ['Basic', 'Conversational', 'Fluent', 'Native']
const availStatuses = ['Available', 'Partially Available', 'Unavailable', 'On Leave']
const availTypes    = ['Full Time', 'Part Time', 'Weekends Only', 'On Call', 'Unavailable']
const weekdays      = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']

const fullName = computed(() =>
  [form.value.first_name, form.value.middle_name, form.value.last_name].filter(Boolean).join(' ')
)

function availVariant(s) {
  return { Available: 'success', 'Partially Available': 'warning', Unavailable: 'error', 'On Leave': 'neutral' }[s] || 'neutral'
}

function showToast(type, message) {
  toast.value = null
  nextTick(() => { toast.value = { type, message }; setTimeout(() => toast.value = null, 4000) })
}

async function save(section) {
  saving.value = section
  try {
    const params = new URLSearchParams()
    params.append('section', section)
    params.append('data', JSON.stringify(form.value))
    await http.post('/api/method/onerc_vmms.api.profile.update_volunteer_profile', params)
    showToast('success', 'Saved successfully.')
  } catch (e) {
    showToast('error', e.response?.data?.exception?.split('\n').pop() || 'Save failed. Please try again.')
  } finally {
    saving.value = ''
  }
}

onMounted(async () => {
  try {
    const { data } = await http.get('/api/method/onerc_vmms.api.profile.get_my_profile')
    const p = data.message
    if (p) {
      profile.value = p
      Object.assign(form.value, p)
    }
  } catch (e) {
    console.error('Failed to load profile', e)
  } finally {
    loading.value = false
  }

  try {
    const [countriesRes, skillsRes] = await Promise.allSettled([
      http.get('/api/method/frappe.client.get_list', { params: { doctype: 'Country', fields: JSON.stringify(['name', 'country_name']), limit_page_length: 300 } }),
      http.get('/api/method/onerc_vmms.api.bootstrap.get_skill_types'),
    ])
    if (countriesRes.status === 'fulfilled') countries.value = countriesRes.value.data.message || []
    if (skillsRes.status  === 'fulfilled')   skillTypes.value = skillsRes.value.data.message || []
  } catch { /* non-critical */ }
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
.form-section { /* grouping */ }
.mt    { margin-top: 14px; }
.mt-6  { margin-top: 24px; }

/* Grids */
.grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 14px; }
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }

/* Repeater */
.repeater-head, .repeater-row { display: grid; gap: 10px; align-items: start; }
.repeater-head {
  font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;
  color: var(--c-text-muted); padding-bottom: 6px;
  border-bottom: 1px solid var(--c-border); margin-bottom: 4px;
}
.grid-5col { grid-template-columns: repeat(5, 1fr) 28px; }
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

/* Availability rows */
.avail-row {
  background: var(--c-border-subtle); border: 1px solid var(--c-border);
  border-radius: var(--radius-md); padding: 14px; margin-bottom: 10px;
}
.avail-row__head { display: grid; grid-template-columns: 1fr 1fr 28px; gap: 12px; align-items: end; margin-bottom: 12px; }
.avail-type { width: 100%; }
.avail-remove { margin-top: 0; }
.avail-days { display: flex; gap: 8px; flex-wrap: wrap; }
.day-check { display: flex; flex-direction: column; align-items: center; gap: 4px; cursor: pointer; }
.day-check input { accent-color: var(--c-primary); width: 16px; height: 16px; }
.day-check span { font-size: 11px; font-weight: 600; color: var(--c-text-muted); text-transform: capitalize; }

/* Modal */
.modal-hint { font-size: 14px; color: var(--c-text-muted); }

/* Toast */
.toast-wrap { position: fixed; bottom: 24px; right: 24px; z-index: 600; width: 340px; max-width: calc(100vw - 48px); }

@media (max-width: 700px) {
  .prof-header { flex-direction: column; align-items: flex-start; }
  .grid-3 { grid-template-columns: 1fr; }
  .grid-2 { grid-template-columns: 1fr; }
  .tab-body { padding: 16px; }
  .grid-5col, .grid-4col, .grid-3col, .grid-2col { grid-template-columns: 1fr 28px; }
  .avail-row__head { grid-template-columns: 1fr 28px; }
}
</style>
