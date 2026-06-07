<template>
  <div class="pub">
    <header class="pub-header">
      <div class="pub-header__inner">
        <img v-if="app.logo" :src="app.logo" :alt="app.orgName" class="pub-header__logo" />
        <div v-else class="pub-header__abbr">{{ app.orgName.slice(0, 2).toUpperCase() }}</div>
        <span class="pub-header__name">{{ app.orgName }}</span>
      </div>
    </header>

    <main class="pub-main">
      <slot />
    </main>
  </div>
</template>

<script setup>
import { useAppStore } from '../stores/app'
const app = useAppStore()
</script>

<style scoped>
.pub {
  min-height: 100vh;
  background: var(--c-bg);
  display: flex;
  flex-direction: column;
}

.pub-header {
  background: var(--c-surface);
  border-bottom: 1px solid var(--c-border);
  padding: 14px 24px;
}

.pub-header__inner {
  max-width: 680px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  gap: 12px;
}

.pub-header__logo {
  height: 36px;
  width: 36px;
  object-fit: contain;
  border-radius: 8px;
}

.pub-header__abbr {
  width: 36px;
  height: 36px;
  background: var(--c-primary);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 800;
  color: #fff;
  flex-shrink: 0;
}

.pub-header__name {
  font-size: 15px;
  font-weight: 700;
  color: var(--c-text);
  letter-spacing: -0.01em;
}

.pub-main {
  flex: 1;
  display: flex;
  flex-direction: column;
}
</style>
