<template>
  <Transition name="alert-fade">
    <div v-if="open" class="alert" :class="`alert--${variant}`" role="alert">
      <component :is="icons[variant]" :size="18" class="alert__icon" />
      <div class="alert__content">
        <p v-if="title" class="alert__title">{{ title }}</p>
        <div class="alert__msg"><slot /></div>
      </div>
      <button v-if="dismissible" class="alert__close" @click="open = false" aria-label="Dismiss">
        <X :size="15" />
      </button>
    </div>
  </Transition>
</template>

<script setup>
import { ref } from 'vue'
import { CheckCircle2, AlertCircle, AlertTriangle, Info, X } from 'lucide-vue-next'
defineProps({
  variant:     { type: String, default: 'info' },
  title:       String,
  dismissible: { type: Boolean, default: false },
})
const open = ref(true)
const icons = { success: CheckCircle2, error: AlertCircle, warning: AlertTriangle, info: Info }
</script>

<style scoped>
.alert {
  display: flex; align-items: flex-start; gap: 11px;
  padding: 13px 14px; border-radius: var(--radius-md);
  border: 1px solid transparent; font-size: 14px;
}
.alert--success { background: var(--c-success-subtle); border-color: color-mix(in srgb, var(--c-success) 30%, transparent); color: #065f46; }
.alert--warning { background: var(--c-warning-subtle); border-color: color-mix(in srgb, var(--c-warning) 30%, transparent); color: #92400e; }
.alert--error   { background: var(--c-error-subtle);   border-color: color-mix(in srgb, var(--c-error)   30%, transparent); color: #991b1b; }
.alert--info    { background: var(--c-info-subtle);    border-color: color-mix(in srgb, var(--c-info)    30%, transparent); color: #1e40af; }
.alert__icon { flex-shrink: 0; margin-top: 1px; }
.alert__content { flex: 1; }
.alert__title { font-weight: 700; margin-bottom: 2px; }
.alert__msg { line-height: 1.5; }
.alert__close { background: none; border: none; color: currentColor; opacity: 0.6; cursor: pointer; padding: 2px; border-radius: 4px; flex-shrink: 0; }
.alert__close:hover { opacity: 1; }
.alert-fade-enter-active, .alert-fade-leave-active { transition: all 0.2s ease; }
.alert-fade-enter-from, .alert-fade-leave-to { opacity: 0; transform: translateY(-4px); }
</style>
