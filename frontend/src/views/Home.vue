<template>
  <div class="home">
    <div class="hero">
      <h1>Welcome to <span>{{ appStore.organization.name }}</span></h1>
      <p>Volunteer & Surge Deployment Platform</p>
      <div class="hero-actions">
        <router-link to="/register" class="btn-primary">
          Register as {{ appStore.labels.volunteer }}
        </router-link>
        <router-link to="/directory" class="btn-secondary">
          View {{ appStore.labels.volunteer }} Directory
        </router-link>
      </div>
    </div>

    <div class="stats-row">
      <div class="stat-card">
        <div class="stat-number">{{ stats.total }}</div>
        <div class="stat-label">Total {{ appStore.labels.volunteer }}s</div>
      </div>
      <div class="stat-card">
        <div class="stat-number">{{ stats.active }}</div>
        <div class="stat-label">Active</div>
      </div>
      <div class="stat-card">
        <div class="stat-number">{{ stats.available }}</div>
        <div class="stat-label">Available Now</div>
      </div>
      <div class="stat-card">
        <div class="stat-number">{{ stats.pending }}</div>
        <div class="stat-label">Pending Approval</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAppStore } from '../stores/app'
import axios from 'axios'

const appStore = useAppStore()

const stats = ref({
  total: 0,
  active: 0,
  available: 0,
  pending: 0
})

onMounted(async () => {
  try {
    const [total, active, available, pending] = await Promise.all([
      axios.get('/api/method/onerc_vmms.api.volunteer.get_volunteers', { params: { page_size: 1 } }),
      axios.get('/api/method/onerc_vmms.api.volunteer.get_volunteers', { params: { volunteer_status: 'Active', page_size: 1 } }),
      axios.get('/api/method/onerc_vmms.api.volunteer.get_volunteers', { params: { availability_status: 'Available', page_size: 1 } }),
      axios.get('/api/method/onerc_vmms.api.volunteer.get_volunteers', { params: { volunteer_status: 'Pending Approval', page_size: 1 } }),
    ])
    stats.value.total = total.data.message.total
    stats.value.active = active.data.message.total
    stats.value.available = available.data.message.total
    stats.value.pending = pending.data.message.total
  } catch(e) {
    console.error(e)
  }
})
</script>

<style scoped>
.hero {
  background: var(--secondary);
  color: white;
  padding: 60px;
  border-radius: var(--radius);
  margin-bottom: 30px;
  text-align: center;
}

.hero h1 {
  font-size: 36px;
  font-weight: 700;
  margin-bottom: 10px;
}

.hero h1 span {
  color: var(--primary);
}

.hero p {
  font-size: 18px;
  opacity: 0.7;
  margin-bottom: 30px;
}

.hero-actions {
  display: flex;
  gap: 16px;
  justify-content: center;
}

.btn-primary {
  background: var(--primary);
  color: white;
  padding: 12px 28px;
  border-radius: var(--radius);
  font-weight: 600;
  font-size: 15px;
  transition: opacity 0.2s;
}

.btn-primary:hover { opacity: 0.9; }

.btn-secondary {
  background: rgba(255,255,255,0.15);
  color: white;
  padding: 12px 28px;
  border-radius: var(--radius);
  font-weight: 600;
  font-size: 15px;
  transition: background 0.2s;
}

.btn-secondary:hover { background: rgba(255,255,255,0.25); }

.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.stat-card {
  background: white;
  border-radius: var(--radius);
  padding: 24px;
  text-align: center;
  box-shadow: var(--shadow);
}

.stat-number {
  font-size: 40px;
  font-weight: 700;
  color: var(--primary);
  line-height: 1;
  margin-bottom: 8px;
}

.stat-label {
  font-size: 14px;
  color: var(--text-muted);
}
</style>