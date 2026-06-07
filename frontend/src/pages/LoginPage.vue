<template>
  <div class="login-shell">
    <!-- Left panel -->
    <div class="login-panel">
      <div class="login-panel__content">
        <div class="login-panel__logo-wrap">
          <img v-if="app.logo" :src="app.logo" :alt="app.orgName" class="login-panel__logo-img" />
          <div v-else class="login-panel__logo-abbr">{{ app.orgName.slice(0,2).toUpperCase() }}</div>
        </div>
        <h2 class="login-panel__org">{{ app.orgName }}</h2>
        <p class="login-panel__tagline">{{ app.volunteerLabel }} & Surge Deployment Portal</p>

        <!-- Red cross emblem -->
        <div class="login-panel__emblem">
          <div class="rc-cross">
            <div class="rc-cross__v" />
            <div class="rc-cross__h" />
          </div>
        </div>

        <p class="login-panel__caption">Helping people in crisis. One mission at a time.</p>
      </div>
    </div>

    <!-- Right form -->
    <div class="login-form-wrap">
      <div class="login-form">
        <div class="login-form__header">
          <h1 class="login-form__title">Welcome back</h1>
          <p class="login-form__sub">Sign in to your {{ app.volunteerLabel.toLowerCase() }} account</p>
        </div>

        <AppAlert v-if="errorMsg" variant="error" class="mb-5">{{ errorMsg }}</AppAlert>

        <form @submit.prevent="submit" novalidate>
          <div class="form-stack">
            <AppInput
              v-model="email" label="Email address" type="email"
              placeholder="you@example.com" :prefix-icon="Mail"
              :error="errors.email" required autocomplete="email"
            />
            <AppInput
              v-model="password" label="Password" type="password"
              placeholder="••••••••" :prefix-icon="Lock"
              :error="errors.password" required autocomplete="current-password"
            />
          </div>

          <AppButton
            type="submit" variant="primary" full size="lg"
            :loading="loading" class="login-form__btn"
          >
            Sign In
          </AppButton>
        </form>

        <p class="login-form__footer">
          Not registered yet?
          <router-link to="/register">Register as a {{ app.volunteerLabel.toLowerCase() }}</router-link>
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Mail, Lock } from 'lucide-vue-next'
import { useAppStore } from '../stores/app'
import { useAuthStore } from '../stores/auth'
import AppInput from '../components/ui/AppInput.vue'
import AppButton from '../components/ui/AppButton.vue'
import AppAlert from '../components/ui/AppAlert.vue'

const app    = useAppStore()
const auth   = useAuthStore()
const router = useRouter()
const route  = useRoute()

const email = ref(''), password = ref('')
const errors = ref({}), errorMsg = ref(''), loading = ref(false)

async function submit() {
  errors.value = {}; errorMsg.value = ''
  if (!email.value)    { errors.value.email    = 'Email is required'; return }
  if (!password.value) { errors.value.password = 'Password is required'; return }
  loading.value = true
  try {
    await auth.login(email.value, password.value)
    router.push(route.query.redirect || '/dashboard')
  } catch { errorMsg.value = 'Incorrect email or password. Please try again.' }
  finally { loading.value = false }
}
</script>

<style scoped>
.login-shell {
  display: flex; min-height: 100vh;
}

/* Left panel */
.login-panel {
  width: 420px; flex-shrink: 0;
  background: linear-gradient(160deg, var(--c-secondary) 0%, color-mix(in srgb, var(--c-secondary) 85%, #000) 100%);
  display: flex; align-items: center; justify-content: center; padding: 48px 40px;
}
.login-panel__content { display: flex; flex-direction: column; align-items: center; text-align: center; gap: 0; }
.login-panel__logo-wrap { margin-bottom: 20px; }
.login-panel__logo-img { height: 72px; width: 72px; object-fit: contain; border-radius: 12px; background: rgba(255,255,255,0.1); padding: 8px; }
.login-panel__logo-abbr { width: 72px; height: 72px; background: var(--c-primary); border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 28px; font-weight: 800; color: #fff; margin: 0 auto; }
.login-panel__org { font-size: 22px; font-weight: 800; color: #fff; margin-bottom: 6px; }
.login-panel__tagline { font-size: 13px; color: rgba(255,255,255,0.6); margin-bottom: 40px; }

/* Red cross emblem */
.login-panel__emblem { margin-bottom: 32px; }
.rc-cross { position: relative; width: 72px; height: 72px; }
.rc-cross__v { position: absolute; left: 50%; top: 0; transform: translateX(-50%); width: 24px; height: 100%; background: rgba(238,36,53,0.8); border-radius: 4px; }
.rc-cross__h { position: absolute; top: 50%; left: 0; transform: translateY(-50%); height: 24px; width: 100%; background: rgba(238,36,53,0.8); border-radius: 4px; }

.login-panel__caption { font-size: 12px; color: rgba(255,255,255,0.45); font-style: italic; max-width: 240px; line-height: 1.5; }

/* Right form */
.login-form-wrap {
  flex: 1; display: flex; align-items: center; justify-content: center;
  padding: 40px 24px; background: var(--c-bg);
}
.login-form { width: 100%; max-width: 400px; }
.login-form__header { margin-bottom: 28px; }
.login-form__title { font-size: 26px; font-weight: 800; color: var(--c-text); margin-bottom: 6px; }
.login-form__sub { font-size: 14px; color: var(--c-text-muted); }
.form-stack { display: flex; flex-direction: column; gap: 16px; margin-bottom: 20px; }
.login-form__btn { margin-top: 4px; }
.mb-5 { margin-bottom: 20px; }
.login-form__footer { margin-top: 20px; font-size: 14px; color: var(--c-text-muted); text-align: center; }

/* Mobile: stack vertically */
@media (max-width: 767px) {
  .login-shell { flex-direction: column; }
  .login-panel { width: 100%; padding: 36px 24px 28px; }
  .login-panel__emblem { display: none; }
  .login-panel__caption { display: none; }
  .login-panel__tagline { margin-bottom: 0; }
}
</style>
