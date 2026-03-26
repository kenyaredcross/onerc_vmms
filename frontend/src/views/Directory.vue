<template>
  <div class="directory">
    <div class="directory-header">
      <h2>{{ appStore.labels.volunteer }} Directory</h2>
      <p>{{ total }} {{ appStore.labels.volunteer }}s found</p>
    </div>

    <div class="directory-layout">
      <div class="filters">
        <div class="filter-title">Filters</div>

        <div class="form-group">
          <label>Status</label>
          <select v-model="filters.availability_status" @change="search">
            <option value="">All</option>
            <option>Available</option>
            <option>Unavailable</option>
            <option>On Deployment</option>
            <option>On Leave</option>
          </select>
        </div>

        <div
          v-for="(level, index) in appStore.geo.levels"
          :key="level.level_key"
          class="form-group"
        >
          <label>{{ level.level_name }}</label>
          <select v-model="geoSelections[index]" @change="onGeoFilter(index)">
            <option value="">All</option>
            <option
              v-for="node in geoOptions[index]"
              :key="node.name"
              :value="node.name"
            >
              {{ node.node_name }}
            </option>
          </select>
        </div>

        <button class="btn-clear" @click="clearFilters">Clear Filters</button>
      </div>

      <div class="results">
        <div v-if="loading" class="loading-state">Loading...</div>

        <div v-else-if="volunteers.length === 0" class="empty-state">
          No volunteers found.
        </div>

        <div v-else class="volunteer-grid">
          <div
            v-for="v in volunteers"
            :key="v.name"
            class="volunteer-card"
          >
            <div class="volunteer-avatar">
              {{ initials(v.full_name) }}
            </div>
            <div class="volunteer-info">
              <div class="volunteer-name">{{ v.full_name }}</div>
              <div class="volunteer-id">{{ v.name }}</div>
              <div class="volunteer-location">{{ v.home_geo_node || '—' }}</div>
              <div class="volunteer-phone">{{ v.primary_phone || '—' }}</div>
            </div>
            <div class="volunteer-status" :class="statusClass(v.availability_status)">
              {{ v.availability_status || 'Unknown' }}
            </div>
          </div>
        </div>

        <div class="pagination" v-if="total > pageSize">
          <button :disabled="page === 1" @click="prevPage">Previous</button>
          <span>Page {{ page }}</span>
          <button :disabled="volunteers.length < pageSize" @click="nextPage">Next</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAppStore } from '../stores/app'
import axios from 'axios'

const appStore = useAppStore()

const volunteers = ref([])
const total = ref(0)
const loading = ref(false)
const page = ref(1)
const pageSize = 20

const filters = ref({ availability_status: '' })
const geoSelections = ref([])
const geoOptions = ref([])

onMounted(async () => {
  const levels = appStore.geo.levels || []
  geoSelections.value = levels.map(() => '')
  geoOptions.value = levels.map(() => [])
  if (levels.length > 0) await loadGeoOptions(0, null)
  await search()
})

async function loadGeoOptions(levelIndex, parentNode) {
  try {
    const f = { geo_level: appStore.geo.levels[levelIndex].name, is_active: 1 }
    if (parentNode) f.parent_geo_node = parentNode
    const res = await axios.get('/api/resource/Geo Node', {
      params: { filters: JSON.stringify(f), fields: JSON.stringify(['name', 'node_name']), limit: 500 }
    })
    geoOptions.value[levelIndex] = res.data.data
  } catch(e) { console.error(e) }
}

async function onGeoFilter(levelIndex) {
  const selected = geoSelections.value[levelIndex]
  for (let i = levelIndex + 1; i < appStore.geo.levels.length; i++) {
    geoSelections.value[i] = ''
    geoOptions.value[i] = []
  }
  if (selected && levelIndex + 1 < appStore.geo.levels.length) {
    await loadGeoOptions(levelIndex + 1, selected)
  }
  page.value = 1
  await search()
}

async function search() {
  loading.value = true
  try {
    const lastSelected = [...geoSelections.value].reverse().find(v => v)
    const params = {
      page: page.value,
      page_size: pageSize,
      volunteer_status: 'Active',
    }
    if (filters.value.availability_status) params.availability_status = filters.value.availability_status
    if (lastSelected) params.geo_node = lastSelected

    const res = await axios.get(
      '/api/method/onerc_vmms.api.volunteer.get_volunteers',
      { params }
    )
    volunteers.value = res.data.message.volunteers
    total.value = res.data.message.total
  } catch(e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

async function clearFilters() {
  filters.value = { availability_status: '' }
  geoSelections.value = geoSelections.value.map(() => '')
  geoOptions.value = geoOptions.value.map((_, i) => i === 0 ? geoOptions.value[0] : [])
  page.value = 1
  await search()
}

function prevPage() { page.value--; search() }
function nextPage() { page.value++; search() }

function initials(name) {
  if (!name) return '?'
  return name.split(' ').map(n => n[0]).slice(0, 2).join('').toUpperCase()
}

function statusClass(status) {
  if (status === 'Available') return 'status-available'
  if (status === 'On Deployment') return 'status-deployed'
  if (status === 'On Leave') return 'status-leave'
  return 'status-unavailable'
}
</script>

<style scoped>
.directory-header {
  margin-bottom: 24px;
}
.directory-header h2 {
  font-size: 24px;
  font-weight: 700;
  color: var(--secondary);
}
.directory-header p {
  font-size: 14px;
  color: var(--text-muted);
}
.directory-layout {
  display: grid;
  grid-template-columns: 240px 1fr;
  gap: 24px;
}
.filters {
  background: white;
  border-radius: var(--radius);
  padding: 20px;
  box-shadow: var(--shadow);
  height: fit-content;
}
.filter-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--secondary);
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 2px solid var(--primary);
}
.form-group {
  margin-bottom: 14px;
}
.form-group label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: var(--secondary);
  margin-bottom: 4px;
}
.form-group select {
  width: 100%;
  padding: 8px 10px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  font-size: 13px;
  outline: none;
}
.btn-clear {
  width: 100%;
  background: none;
  border: 1px solid var(--border);
  color: var(--text-muted);
  padding: 8px;
  border-radius: var(--radius);
  font-size: 13px;
  margin-top: 8px;
}
.volunteer-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}
.volunteer-card {
  background: white;
  border-radius: var(--radius);
  padding: 16px;
  box-shadow: var(--shadow);
  display: flex;
  gap: 14px;
  align-items: flex-start;
}
.volunteer-avatar {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: var(--secondary);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 14px;
  flex-shrink: 0;
}
.volunteer-info { flex: 1; }
.volunteer-name {
  font-size: 14px;
  font-weight: 700;
  color: var(--secondary);
}
.volunteer-id {
  font-size: 11px;
  color: var(--text-muted);
  margin-bottom: 4px;
}
.volunteer-location, .volunteer-phone {
  font-size: 12px;
  color: var(--text-muted);
}
.volunteer-status {
  font-size: 11px;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: 20px;
  flex-shrink: 0;
}
.status-available { background: #E8F5EE; color: #0F6E56; }
.status-deployed { background: #FCEAEA; color: #EE2435; }
.status-leave { background: #FFF4E0; color: #854F0B; }
.status-unavailable { background: #F1EFE8; color: #5F5E5A; }
.loading-state, .empty-state {
  text-align: center;
  padding: 60px;
  color: var(--text-muted);
  background: white;
  border-radius: var(--radius);
}
.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  margin-top: 20px;
}
.pagination button {
  background: var(--secondary);
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: var(--radius);
  font-size: 13px;
}
.pagination button:disabled {
  opacity: 0.4;
}
.pagination span {
  font-size: 14px;
  color: var(--text-muted);
}
</style>
