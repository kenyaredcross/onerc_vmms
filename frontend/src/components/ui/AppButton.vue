<template>
  <component
    :is="href ? 'a' : 'button'"
    :href="href"
    :type="href ? undefined : type"
    :disabled="disabled || loading"
    :class="['btn', `btn--${variant}`, `btn--${size}`, { 'btn--full': full, 'btn--loading': loading }]"
    @click="!disabled && !loading && $emit('click', $event)"
  >
    <AppSpinner v-if="loading" size="sm" class="btn__spinner" />
    <component :is="icon" v-else-if="icon" :size="iconSize" class="btn__icon" />
    <span v-if="$slots.default" class="btn__label"><slot /></span>
  </component>
</template>

<script setup>
import AppSpinner from './AppSpinner.vue'
defineProps({
  variant: { type: String, default: 'primary' },
  size:    { type: String, default: 'md' },
  type:    { type: String, default: 'button' },
  disabled:{ type: Boolean, default: false },
  loading: { type: Boolean, default: false },
  full:    { type: Boolean, default: false },
  icon:    { type: [Object, Function], default: null },
  iconSize:{ type: Number, default: 16 },
  href:    { type: String, default: null },
})
defineEmits(['click'])
</script>

<style scoped>
.btn {
  display: inline-flex; align-items: center; justify-content: center;
  gap: 7px; font-weight: 600; border-radius: var(--radius-md);
  cursor: pointer; border: 1.5px solid transparent;
  transition: all var(--t-base); white-space: nowrap;
  font-family: var(--font); text-decoration: none; line-height: 1;
}
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn--full { width: 100%; }
.btn__spinner { flex-shrink: 0; }
.btn__icon { flex-shrink: 0; }

/* Sizes */
.btn--xs { padding: 5px 11px; font-size: 12px; }
.btn--sm { padding: 7px 14px; font-size: 13px; }
.btn--md { padding: 9px 18px; font-size: 14px; }
.btn--lg { padding: 12px 24px; font-size: 15px; }

/* Variants */
.btn--primary { background: var(--c-primary); color: #fff; border-color: var(--c-primary); }
.btn--primary:hover:not(:disabled) { background: var(--c-primary-hover); border-color: var(--c-primary-hover); }

.btn--secondary { background: var(--c-secondary); color: #fff; border-color: var(--c-secondary); }
.btn--secondary:hover:not(:disabled) { background: var(--c-secondary-hover); border-color: var(--c-secondary-hover); }

.btn--outline { background: transparent; color: var(--c-primary); border-color: var(--c-primary); }
.btn--outline:hover:not(:disabled) { background: var(--c-primary-subtle); }

.btn--ghost { background: transparent; color: var(--c-text-secondary); border-color: transparent; }
.btn--ghost:hover:not(:disabled) { background: var(--c-border-subtle); color: var(--c-text); }

.btn--danger { background: var(--c-error); color: #fff; border-color: var(--c-error); }
.btn--danger:hover:not(:disabled) { filter: brightness(0.92); }

.btn--neutral { background: var(--c-border); color: var(--c-text-secondary); border-color: var(--c-border); }
.btn--neutral:hover:not(:disabled) { background: var(--c-border); color: var(--c-text); }
</style>
