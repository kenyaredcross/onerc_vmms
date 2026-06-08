<template>
  <div class="verify-shell">
    <div v-if="loading" class="verify-center"><AppSpinner size="lg" /></div>

    <div v-else class="verify-card" :class="cardClass">
      <!-- Header stripe -->
      <div class="verify-card__stripe">
        <div class="stripe-cross"><div class="cross-v"/><div class="cross-h"/></div>
        <span class="stripe-text">OneRC Volunteer Management System</span>
      </div>

      <!-- Status icon -->
      <div class="verify-card__icon-wrap">
        <CheckCircle2 v-if="isActive" :size="64" class="status-icon status-icon--ok" />
        <XCircle     v-else           :size="64" class="status-icon status-icon--bad" />
      </div>

      <!-- Photo -->
      <div class="verify-card__photo-wrap">
        <AppAvatar :name="result.name || ''" :photo="result.photo" size="2xl" />
      </div>

      <h1 class="verify-card__name">{{ result.name || 'Unknown Member' }}</h1>

      <template v-if="result.status === 'Active' || result.status === 'Expired'">
        <AppBadge :variant="result.status === 'Active' ? 'primary' : 'neutral'" size="md" class="plan-badge">
          {{ result.plan || 'Member' }}
        </AppBadge>
        <div class="verify-card__meta">
          <div class="meta-row">
            <span class="meta-label">Volunteer ID</span>
            <span class="meta-val mono">{{ result.vol_id }}</span>
          </div>
          <div class="meta-row">
            <span class="meta-label">Valid from</span>
            <span class="meta-val">{{ fmtDate(result.from_date) }}</span>
          </div>
          <div class="meta-row">
            <span class="meta-label">Valid until</span>
            <span class="meta-val">{{ fmtDate(result.to_date) }}</span>
          </div>
        </div>
      </template>

      <template v-else>
        <p class="verify-card__msg">{{ notFoundMsg }}</p>
      </template>

      <div class="verify-card__footer" :class="footerClass">{{ footerText }}</div>
    </div>

    <p v-if="!loading" class="verify-ts">Verified {{ new Date().toLocaleString() }}</p>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { CheckCircle2, XCircle } from 'lucide-vue-next'
import http from '../lib/axios'
import AppSpinner from '../components/ui/AppSpinner.vue'
import AppAvatar  from '../components/ui/AppAvatar.vue'
import AppBadge   from '../components/ui/AppBadge.vue'

const route   = useRoute()
const loading = ref(true)
const result  = ref({})

const isActive  = computed(() => result.value.status === 'Active')

const cardClass = computed(() => ({
  'verify-card--active':  result.value.status === 'Active',
  'verify-card--expired': result.value.status === 'Expired',
  'verify-card--invalid': !['Active','Expired'].includes(result.value.status),
}))

const footerClass = computed(() => ({
  'footer--active':  result.value.status === 'Active',
  'footer--expired': result.value.status === 'Expired',
  'footer--invalid': !['Active','Expired'].includes(result.value.status),
}))

const footerText = computed(() => ({
  Active:  '✓ ACTIVE MEMBER',
  Expired: '✗ EXPIRED MEMBERSHIP',
}[result.value.status] || '✗ NOT A REGISTERED MEMBER'))

const notFoundMsg = computed(() => ({
  not_found:      'This volunteer ID does not exist in the system.',
  not_a_member:   `${result.value.name || 'This volunteer'} is not a registered member.`,
  no_subscription:'No active membership subscription found.',
}[result.value.status] || 'Verification failed.'))

function fmtDate(d) {
  if (!d) return '—'
  return new Date(d).toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' })
}

onMounted(async () => {
  try {
    const r = await http.get('/api/method/onerc_vmms.api.membership.verify_member', {
      params: { vol_id: route.params.volId }
    })
    result.value = r.data.message || { status: 'not_found' }
  } catch {
    result.value = { status: 'not_found' }
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.verify-shell {
  min-height: 100vh; display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  padding: 24px 16px; background: var(--c-bg);
}
.verify-center { display: flex; align-items: center; justify-content: center; min-height: 60vh; }

.verify-card {
  width: 100%; max-width: 380px; background: var(--c-surface);
  border-radius: var(--radius-xl); overflow: hidden;
  box-shadow: var(--shadow-lg); border: 1px solid var(--c-border);
  display: flex; flex-direction: column; align-items: center;
}

.verify-card__stripe {
  width: 100%; background: var(--c-secondary);
  padding: 14px 18px; display: flex; align-items: center; gap: 10px;
}
.stripe-cross { position: relative; width: 24px; height: 24px; flex-shrink: 0; }
.cross-v { position: absolute; left: 50%; top: 0; transform: translateX(-50%); width: 8px; height: 100%; background: var(--c-primary); border-radius: 2px; }
.cross-h { position: absolute; top: 50%; left: 0; transform: translateY(-50%); width: 100%; height: 8px; background: var(--c-primary); border-radius: 2px; }
.stripe-text { font-size: 11px; font-weight: 700; color: rgba(255,255,255,0.7); text-transform: uppercase; letter-spacing: 0.08em; }

.verify-card__icon-wrap { margin-top: 24px; }
.status-icon--ok  { color: var(--c-success); }
.status-icon--bad { color: var(--c-error); }

.verify-card__photo-wrap { margin-top: 14px; }

.verify-card__name {
  font-size: 22px; font-weight: 800; color: var(--c-text);
  margin: 12px 18px 4px; text-align: center; line-height: 1.2;
}

.plan-badge { margin: 6px 0 10px; }

.verify-card__meta { width: 100%; padding: 0 20px 16px; display: flex; flex-direction: column; gap: 8px; }
.meta-row { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.meta-label { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--c-text-muted); }
.meta-val   { font-size: 14px; font-weight: 600; color: var(--c-text); }
.mono { font-family: var(--font-mono, monospace); }

.verify-card__msg { font-size: 14px; color: var(--c-text-muted); text-align: center; padding: 12px 20px 16px; line-height: 1.5; }

.verify-card__footer {
  width: 100%; padding: 14px; text-align: center;
  font-size: 15px; font-weight: 800; letter-spacing: 0.1em; color: #fff;
}
.footer--active  { background: var(--c-success); }
.footer--expired { background: var(--c-error); }
.footer--invalid { background: var(--c-text-muted); }

.verify-ts { margin-top: 14px; font-size: 11px; color: var(--c-text-muted); }
</style>
