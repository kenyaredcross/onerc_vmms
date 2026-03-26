<template>
  <div v-if="appStore.loaded">
    <nav class="navbar">
      <div class="navbar-brand">
        <span class="brand-red">One</span>RC
        <span class="brand-divider">|</span>
        <span class="brand-name">{{ appStore.organization.name }}</span>
      </div>
      <div class="navbar-links">
        <router-link to="/">Home</router-link>
        <router-link to="/register">Register</router-link>
        <router-link to="/directory">Directory</router-link>
      </div>
    </nav>
    <main class="main-content">
      <router-view />
    </main>
  </div>
  <div v-else class="loading">
    <div class="loading-spinner"></div>
    <p>Loading...</p>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useAppStore } from './stores/app'
const appStore = useAppStore()
onMounted(() => { appStore.loadBootstrap() })
</script>

<style scoped>
.navbar {
  background: var(--secondary);
  color: white;
  padding: 0 40px;
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.navbar-brand { font-size: 20px; font-weight: 700; color: white; }
.brand-red { color: var(--primary); }
.brand-divider { margin: 0 12px; opacity: 0.3; }
.brand-name { font-size: 14px; font-weight: 400; opacity: 0.8; }
.navbar-links { display: flex; gap: 24px; }
.navbar-links a { color: rgba(255,255,255,0.7); font-size: 14px; transition: color 0.2s; }
.navbar-links a:hover, .navbar-links a.router-link-active { color: white; }
.main-content { max-width: 1100px; margin: 0 auto; padding: 40px 20px; }
.loading { height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 16px; color: #666; }
.loading-spinner { width: 40px; height: 40px; border: 3px solid #e0e0e0; border-top-color: #EE2435; border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
