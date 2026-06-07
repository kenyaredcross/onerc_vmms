<template>
  <span class="badge" :class="[`badge--${variant}`, `badge--${size}`, { 'badge--dot': dot }]">
    <span v-if="dot" class="badge__dot" />
    <slot />
  </span>
</template>

<script setup>
defineProps({
  variant: { type: String, default: 'neutral' },
  size:    { type: String, default: 'md' },
  dot:     { type: Boolean, default: false },
})
</script>

<style scoped>
.badge {
  display: inline-flex; align-items: center; gap: 5px;
  border-radius: var(--radius-full); font-weight: 600;
  letter-spacing: 0.01em; white-space: nowrap;
}
.badge--sm  { padding: 2px 8px; font-size: 11px; }
.badge--md  { padding: 3px 10px; font-size: 12px; }
.badge__dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; flex-shrink: 0; }

.badge--success  { background: var(--c-success-subtle);  color: var(--c-success); }
.badge--warning  { background: var(--c-warning-subtle);  color: var(--c-warning); }
.badge--error    { background: var(--c-error-subtle);    color: var(--c-error); }
.badge--info     { background: var(--c-info-subtle);     color: var(--c-info); }
.badge--primary  { background: var(--c-primary-subtle);  color: var(--c-primary); }
.badge--secondary{ background: var(--c-secondary-subtle);color: var(--c-secondary); }
.badge--neutral  { background: var(--c-border-subtle);   color: var(--c-text-secondary); }
</style>
