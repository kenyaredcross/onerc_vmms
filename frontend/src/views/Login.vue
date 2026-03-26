<template>
  <div class="login-wrap">
    <div class="login-card">
      <div class="login-header">
        <div class="login-logo">
          <span class="red">One</span>RC
        </div>
        <h2>Sign in</h2>
        <p>{{ appStore.organization.name }}</p>
      </div>

      <div v-if="error" class="error-box">{{ error }}</div>

      <div class="form-group">
        <label>Email</label>
        <input v-model="form.email" type="email" placeholder="your@email.com" />
      </div>

      <div class="form-group">
        <label>Password</label>
        <input v-model="form.password" type="password" placeholder="••••••••" />
      </div>

      <button class="btn-login" @click="login" :disabled="loading">
        {{ loading ? 'Signing in...' : 'Sign in' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAppStore } from '../stores/app'
import axios from 'axios'

const appStore = useAppStore()
const router = useRouter()

const form = ref({ email: '', password: '' })
const error = ref('')
const loading = ref(false)

async function login() {
  error.value = ''
  loading.value = true
  try {
    await axios.post('/api/method/login', {
      usr: form.value.email,
      pwd: form.value.password
    })
    router.push('/')
  } catch (e) {
    error.value = 'Invalid email or password. Please try again.'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-wrap {
  min-height: 80vh;
  display: flex;
  align-items: center;
  justify-content: center;
}

.login-card {
  background: white;
  border-radius: var(--radius);
  padding: 48px;
  width: 100%;
  max-width: 420px;
  box-shadow: var(--shadow);
}

.login-header {
  text-align: center;
  margin-bottom: 32px;
}

.login-logo {
  font-size: 28px;
  font-weight: 700;
  color: var(--secondary);
  margin-bottom: 16px;
}

.login-logo .red { color: var(--primary); }

.login-header h2 {
  font-size: 22px;
  color: var(--secondary);
  margin-bottom: 4px;
}

.login-header p {
  font-size: 14px;
  color: var(--text-muted);
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: var(--secondary);
  margin-bottom: 6px;
}

.form-group input {
  width: 100%;
  padding: 10px 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s;
}

.form-group input:focus {
  border-color: var(--primary);
}

.btn-login {
  width: 100%;
  background: var(--primary);
  color: white;
  border: none;
  padding: 12px;
  border-radius: var(--radius);
  font-size: 15px;
  font-weight: 600;
  transition: opacity 0.2s;
}

.btn-login:hover { opacity: 0.9; }
.btn-login:disabled { opacity: 0.6; }

.error-box {
  background: #FCEAEA;
  color: #EE2435;
  padding: 10px 14px;
  border-radius: var(--radius);
  font-size: 13px;
  margin-bottom: 20px;
}
</style>