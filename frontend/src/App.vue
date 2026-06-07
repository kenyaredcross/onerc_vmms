<template>
  <!-- Global boot screen -->
  <div v-if="!appReady" class="boot">
    <AppSpinner size="lg" />
    <p class="boot__text">Loading…</p>
  </div>

  <template v-else>
    <PublicLayout v-if="isPublicRoute">
      <RouterView v-slot="{ Component }">
        <Transition name="page" mode="out-in">
          <component :is="Component" />
        </Transition>
      </RouterView>
    </PublicLayout>

    <AppLayout v-else>
      <RouterView v-slot="{ Component }">
        <Transition name="page" mode="out-in">
          <component :is="Component" />
        </Transition>
      </RouterView>
    </AppLayout>
  </template>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore } from './stores/app'
import { useAuthStore } from './stores/auth'
import AppSpinner from './components/ui/AppSpinner.vue'
import PublicLayout from './layouts/PublicLayout.vue'
import AppLayout from './layouts/AppLayout.vue'

const app  = useAppStore()
const auth = useAuthStore()
const route = useRoute()

const appReady = computed(() => app.loaded && !auth.checking)
const isPublicRoute = computed(() => !!route.meta.public)
</script>

<style scoped>
.boot {
  min-height: 100vh; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 16px;
}
.boot__text { font-size: 14px; color: var(--c-text-muted); }
.page-enter-active, .page-leave-active { transition: opacity 0.15s ease; }
.page-enter-from, .page-leave-to { opacity: 0; }
</style>
